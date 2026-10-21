"""Unified Trust Engine service combining feature extraction, scoring, and decay."""

import logging

import redis.asyncio as redis
from decision_engine.policy.spicedb import SpiceDBClient
from shared.schemas.trust import FeatureVector, RequestTelemetry, TrustScoreResult

from trust_engine.features.behavioral import BehavioralFeatureExtractor
from trust_engine.features.graph import GraphFeatureExtractor
from trust_engine.scoring import TrustScorer

logger = logging.getLogger("trust_engine.service")


class TrustEngineService:
    """High-level service orchestrating feature extraction, ML scoring, and session decay."""

    def __init__(
        self,
        redis_client: redis.Redis,
        spicedb_client: SpiceDBClient,
        model_path: str | None = None,
        explainer_path: str | None = None,
    ) -> None:
        self.redis = redis_client
        self.spicedb = spicedb_client
        self.behavioral_extractor = BehavioralFeatureExtractor(redis_client)
        self.graph_extractor = GraphFeatureExtractor(spicedb_client, redis_client)
        self.scorer = TrustScorer(
            redis_client=redis_client,
            model_path=model_path,
            explainer_path=explainer_path,
        )

    async def evaluate(
        self,
        telemetry: RequestTelemetry,
        resource: str,
        permission: str,
        traversal_path: list[str] | None = None,
    ) -> TrustScoreResult:
        """Extract dual-stream features, run Isolation Forest + SHAP, and update trust score."""
        # Extract behavioral stream
        behavioral_feats = await self.behavioral_extractor.extract(telemetry)

        # Extract graph stream
        graph_feats = await self.graph_extractor.extract(
            subject=telemetry.subject_id,
            resource=resource,
            permission=permission,
            traversal_path=traversal_path,
        )

        # Combine into canonical 10-dimensional feature vector
        feature_vector = FeatureVector(
            behavioral=behavioral_feats,
            graph=graph_feats,
        )

        # Evaluate ML anomaly and stateful decay
        result = await self.scorer.score_features(
            session_id=telemetry.session_id,
            subject_id=telemetry.subject_id,
            feature_vector=feature_vector,
            current_time=telemetry.timestamp,
        )

        logger.debug(
            "Session %s trust score: %.4f (delta: %.4f, anomaly: %s)",
            telemetry.session_id,
            result.current_score,
            result.score_delta,
            result.is_anomaly,
        )
        return result

    async def reset_trust(self, session_id: str, new_score: float = 1.0) -> None:
        """Reset session trust score back to baseline after successful verification."""
        await self.scorer.reset_session_trust(session_id, new_score=new_score)
