"""Stateful trust scoring using Isolation Forest, SHAP attributions, and Redis decay state."""

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
        logger.info("Loading SHAP TreeExplainer from %s", e_path)
        self.explainer = joblib.load(e_path)

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

        # 1. Isolation Forest Inference
        pred = int(self.model.predict(x_sample)[0])  # 1 = inlier, -1 = anomaly
        decision_val = float(self.model.decision_function(x_sample)[0])  # negative = outlier
        is_anomaly = pred == -1

        # Anomaly severity normalized to [0.0, 1.0]
        if is_anomaly:
            # decision_function is typically between -0.01 and -0.25 for strong anomalies
            anomaly_severity = min(1.0, max(0.1, abs(decision_val) / 0.15))
        else:
            anomaly_severity = 0.0

        # 2. Local SHAP Attribution
        shap_raw = self.explainer.shap_values(x_sample)
        shap_arr = np.asarray(shap_raw).flatten()
        shap_attributions: dict[str, float] = {
            name: round(float(val), 4) for name, val in zip(FEATURE_NAMES, shap_arr)
        }

        # 3. Stateful Decay & Recovery in Redis
        trust_key = f"session:{session_id}:trust"
        state = await self.redis.hgetall(trust_key)

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
            runtime_params = await self.redis.hgetall("trust:runtime_parameters")
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
        await self.redis.hset(
            trust_key,
            mapping={
                "current_score": str(current_score),
                "last_updated_ts": str(now_ts),
                "baseline_score": str(self.baseline_score),
                "request_count": str(req_count + 1),
            },
        )
        await self.redis.expire(trust_key, 86400)  # 24 hours session retention

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
