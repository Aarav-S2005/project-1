"""Stateful trust scoring using Isolation Forest, SHAP attributions, and Redis decay state."""

import asyncio
import logging
import math
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import redis.asyncio as redis
from shared.config import get_settings
from shared.schemas.trust import FeatureVector, TrustScoreResult

from scripts.generate_synthetic_traffic import FEATURE_NAMES

logger = logging.getLogger("trust_engine.scoring")


class TrustScorer:
    """Computes anomaly scores, local SHAP attributions, and maintains decaying trust state."""

    def __init__(
        self,
        redis_client: redis.Redis,
        model_path: str | None = None,
        explainer_path: str | None = None,
        half_life_seconds: float | None = None,
        anomaly_weight: float | None = None,
    ) -> None:
        settings = get_settings()
        self.redis = redis_client
        self.half_life = half_life_seconds or settings.trust_half_life_seconds
        self.anomaly_weight = anomaly_weight or settings.trust_anomaly_weight
        self.baseline_score = 1.0

        m_path = Path(model_path or settings.model_path)
        e_path = Path(explainer_path or settings.explainer_path)

        if not m_path.exists() or not e_path.exists():
            raise FileNotFoundError(
                f"Model or explainer artifacts not found at {m_path} / {e_path}. "
                "Run `uv run python scripts/train_model.py` first."
            )

        logger.info("Loading Isolation Forest model from %s", m_path)
        self.model = joblib.load(m_path)
        # Single-sample inference: joblib parallelism only adds dispatch overhead per request.
        if hasattr(self.model, "set_params"):
            self.model.set_params(n_jobs=1)
        logger.info("Loading SHAP TreeExplainer from %s", e_path)
        self.explainer = joblib.load(e_path)
        # TreeSHAP decomposes the forest's expected path length E[h(x)] exactly
        # (sum of SHAP values + expected value), so the Isolation Forest score can be recovered
        # from the attribution pass instead of traversing all trees a second time:
        #   score_samples(x) = -2 ** (-E[h(x)] / c(max_samples)),  decision = score - offset_
        self._c_norm: float | None = None
        try:
            from sklearn.ensemble._iforest import _average_path_length

            self._c_norm = float(_average_path_length([self.model._max_samples])[0])
            self._expected_value = float(np.ravel(self.explainer.expected_value)[0])
        except Exception as exc:  # pragma: no cover - fallback for unexpected model types
            logger.warning("Falling back to score_samples for inference: %s", exc)
            self._c_norm = None

    async def score_features(
        self,
        session_id: str,
        subject_id: str,
        feature_vector: FeatureVector,
        current_time: datetime,
    ) -> TrustScoreResult:
        """Run ML inference, calculate SHAP attributions, and update session trust decay."""
        now_ts = current_time.timestamp()
        x_sample = np.array([feature_vector.to_array()])

        # 1. Isolation Forest inference + 2. local SHAP attribution, computed in a worker thread so
        #    the CPU-bound work does not block the event loop. The anomaly decision is derived from
        #    the TreeSHAP pass (see __init__), replacing the earlier predict() + decision_function()
        #    pair that traversed all trees twice; predict(x) = -1 exactly when decision < 0.
        #    Session state and runtime parameters are read from Redis in a single round trip that
        #    overlaps with inference.
        trust_key = f"session:{session_id}:trust"
        (decision_val, shap_arr), (state, runtime_params) = await asyncio.gather(
            asyncio.to_thread(self._infer, x_sample),
            self._read_state(trust_key),
        )
        is_anomaly = decision_val < 0.0

        # Anomaly severity normalized to [0.0, 1.0]
        if is_anomaly:
            # decision_function is typically between -0.01 and -0.25 for strong anomalies
            anomaly_severity = min(1.0, max(0.1, abs(decision_val) / 0.15))
        else:
            anomaly_severity = 0.0

        shap_attributions: dict[str, float] = {
            name: round(float(val), 4) for name, val in zip(FEATURE_NAMES, shap_arr)
        }

        # 3. Stateful Decay & Recovery in Redis

        if state and b"current_score" in state and b"last_updated_ts" in state:
            prev_score = float(state[b"current_score"])
            prev_ts = float(state[b"last_updated_ts"])
            req_count = int(state.get(b"request_count", b"0"))
        else:
            prev_score = self.baseline_score
            prev_ts = now_ts
            req_count = 0

        delta_t = max(0.0, now_ts - prev_ts)

        # Check dynamic runtime parameter overrides from Redis
        half_life = self.half_life
        anomaly_weight = self.anomaly_weight
        try:
            if runtime_params:
                if b"half_life_seconds" in runtime_params:
                    half_life = float(runtime_params[b"half_life_seconds"])
                if b"anomaly_weight" in runtime_params:
                    anomaly_weight = float(runtime_params[b"anomaly_weight"])
        except Exception:
            pass

        # Exponential time-recovery towards baseline (half-life decay of past penalties)
        lambda_val = math.log(2.0) / max(1.0, half_life)
        recovered_score = prev_score + (self.baseline_score - prev_score) * (
            1.0 - math.exp(-lambda_val * delta_t)
        )

        # Apply anomaly penalty
        if is_anomaly:
            penalty = anomaly_weight * anomaly_severity
            current_score = max(0.0, recovered_score - penalty)
        else:
            current_score = min(self.baseline_score, recovered_score)

        score_delta = current_score - prev_score

        # Save updated state to Redis
        pipe = self.redis.pipeline(transaction=False)
        pipe.hset(
            trust_key,
            mapping={
                "current_score": str(current_score),
                "last_updated_ts": str(now_ts),
                "baseline_score": str(self.baseline_score),
                "request_count": str(req_count + 1),
            },
        )
        pipe.expire(trust_key, 86400)  # 24 hours session retention
        await pipe.execute()

        return TrustScoreResult(
            session_id=session_id,
            subject_id=subject_id,
            previous_score=round(prev_score, 4),
            current_score=round(current_score, 4),
            score_delta=round(score_delta, 4),
            is_anomaly=is_anomaly,
            anomaly_severity=round(anomaly_severity, 4),
            feature_vector=feature_vector,
            shap_attributions=shap_attributions,
        )

    async def _read_state(self, trust_key: str) -> tuple[dict[bytes, bytes], dict[bytes, bytes]]:
        """Read session trust state and runtime parameter overrides in one Redis round trip."""
        pipe = self.redis.pipeline(transaction=False)
        pipe.hgetall(trust_key)
        pipe.hgetall("trust:runtime_parameters")
        try:
            state, params = await pipe.execute()
        except Exception as exc:
            logger.debug("Could not read trust state from Redis: %s", exc)
            return {}, {}
        return state or {}, params or {}

    def _infer(self, x_sample: np.ndarray) -> tuple[float, np.ndarray]:
        """Return the Isolation Forest decision value and SHAP attribution for one sample."""
        shap_arr = np.asarray(self.explainer.shap_values(x_sample)).flatten()
        if self._c_norm:
            expected_depth = float(shap_arr.sum()) + self._expected_value
            score = -(2.0 ** (-expected_depth / self._c_norm))
        else:
            score = float(self.model.score_samples(x_sample)[0])
        return score - float(self.model.offset_), shap_arr

    async def reset_session_trust(self, session_id: str, new_score: float = 1.0) -> None:
        """Reset session trust score back to baseline following step-up verification."""
        trust_key = f"session:{session_id}:trust"
        now_ts = datetime.now().timestamp()
        await self.redis.hset(
            trust_key,
            mapping={
                "current_score": str(new_score),
                "last_updated_ts": str(now_ts),
                "baseline_score": str(self.baseline_score),
                "request_count": "0",
            },
        )
        logger.info("Reset session %s trust score to %f", session_id, new_score)
