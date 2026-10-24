"""Unit tests for TrustScorer and TrustEngineService."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
import redis.asyncio as redis
from decision_engine.policy.spicedb import SpiceDBClient
from shared.schemas.trust import (
    BehavioralFeatures,
    FeatureVector,
    GraphFeatures,
    RequestTelemetry,
)
from trust_engine.scoring import TrustScorer
from trust_engine.service import TrustEngineService


@pytest.fixture
def trust_scorer(fake_redis: redis.Redis) -> TrustScorer:
    """Fixture providing initialized TrustScorer loaded with production artifacts."""
    return TrustScorer(
        redis_client=fake_redis,
        model_path="models/isolation_forest.joblib",
        explainer_path="models/shap_explainer.joblib",
        half_life_seconds=300.0,
        anomaly_weight=0.35,
    )


@pytest.mark.asyncio
async def test_benign_features_maintain_high_trust(trust_scorer: TrustScorer) -> None:
    """Verify that normal enterprise requests maintain high trust near baseline 1.0."""
    benign_fv = FeatureVector(
        behavioral=BehavioralFeatures(
            req_rate_10s=0.5,
            req_rate_60s=0.5,
            rate_burst_ratio=1.0,
            geo_velocity_kmh=0.0,
            tls_fingerprint_mismatch=0.0,
            time_of_day_deviation=0.1,
        ),
        graph=GraphFeatures(
            path_length=2.0,
            path_novelty=0.0,
            privilege_shortcut_score=0.1,
            intermediate_node_degree=5.0,
        ),
    )

    now = datetime(2026, 10, 19, 12, 0, 0, tzinfo=UTC)
    result = await trust_scorer.score_features(
        session_id="sess_benign",
        subject_id="user:alice",
        feature_vector=benign_fv,
        current_time=now,
    )

    assert result.is_anomaly is False
    assert result.current_score >= 0.95
    assert len(result.shap_attributions) == 10


@pytest.mark.asyncio
async def test_anomalous_features_lower_trust_with_shap_attribution(
    trust_scorer: TrustScorer,
) -> None:
    """Verify anomaly triggers penalty, reduces score, and generates feature attribution."""
    anomaly_fv = FeatureVector(
        behavioral=BehavioralFeatures(
            req_rate_10s=38.0,  # massive rate spike
            req_rate_60s=1.0,
            rate_burst_ratio=15.0,
            geo_velocity_kmh=1800.0,  # impossible travel
            tls_fingerprint_mismatch=1.0,  # session hijacking
            time_of_day_deviation=0.9,
        ),
        graph=GraphFeatures(
            path_length=1.0,
            path_novelty=1.0,  # novel shortcut
            privilege_shortcut_score=0.95,
            intermediate_node_degree=1.0,
        ),
    )

    now = datetime(2026, 10, 19, 12, 0, 0, tzinfo=UTC)
    result = await trust_scorer.score_features(
        session_id="sess_attack",
        subject_id="user:mallory",
        feature_vector=anomaly_fv,
        current_time=now,
    )

    assert result.is_anomaly is True
    assert result.anomaly_severity > 0.0
    assert result.current_score < 0.85  # dropped into narrow/step-up band
    assert result.score_delta < 0.0

    # Verify SHAP attributions reflect the anomaly features
    assert "geo_velocity_kmh" in result.shap_attributions
    assert "req_rate_10s" in result.shap_attributions


@pytest.mark.asyncio
async def test_time_decay_and_recovery(trust_scorer: TrustScorer) -> None:
    """Verify that score recovers exponentially over elapsed time without new anomalies."""
    session_id = "sess_decay_test"
    t0 = datetime(2026, 10, 19, 12, 0, 0, tzinfo=UTC)

    # 1. Trigger an anomaly to depress trust score
    anomaly_fv = FeatureVector(
        behavioral=BehavioralFeatures(
            req_rate_10s=35.0,
            req_rate_60s=1.0,
            rate_burst_ratio=12.0,
            geo_velocity_kmh=1500.0,
        ),
        graph=GraphFeatures(path_novelty=1.0, privilege_shortcut_score=0.9),
    )
    res_drop = await trust_scorer.score_features(
        session_id=session_id,
        subject_id="user:bob",
        feature_vector=anomaly_fv,
        current_time=t0,
    )
    depressed_score = res_drop.current_score
    assert depressed_score < 0.85

    # 2. Simulate subsequent benign request exactly 1 half-life (300 seconds) later
    t1 = t0 + timedelta(seconds=300)
    benign_fv = FeatureVector()
    res_recover = await trust_scorer.score_features(
        session_id=session_id,
        subject_id="user:bob",
        feature_vector=benign_fv,
        current_time=t1,
    )

    # After 1 half-life without anomalies, score should recover approximately 50% toward 1.0
    expected_recovery = depressed_score + (1.0 - depressed_score) * 0.5
    assert abs(res_recover.current_score - expected_recovery) < 0.05
    assert res_recover.current_score > depressed_score


@pytest.mark.asyncio
async def test_reset_session_trust(trust_scorer: TrustScorer) -> None:
    """Verify that reset_session_trust resets score to 1.0."""
    session_id = "sess_reset_test"
    t0 = datetime(2026, 10, 19, 12, 0, 0, tzinfo=UTC)

    # Depress score
    anomaly_fv = FeatureVector(
        behavioral=BehavioralFeatures(req_rate_10s=40.0, geo_velocity_kmh=2000.0)
    )
    await trust_scorer.score_features(session_id, "user:dave", anomaly_fv, t0)

    # Reset score following MFA step-up verification
    await trust_scorer.reset_session_trust(session_id, new_score=1.0)

    # Verify score is restored
    res = await trust_scorer.score_features(session_id, "user:dave", FeatureVector(), t0)
    assert res.current_score >= 0.99


@pytest.mark.asyncio
async def test_trust_engine_service_coordinator(fake_redis: redis.Redis) -> None:
    """Verify TrustEngineService coordinates extraction and scoring end-to-end."""
    mock_spicedb = MagicMock(spec=SpiceDBClient)
    mock_spicedb.expand_permission_tree.return_value = {
        "expanded_resource": "document:doc_99",
        "permission": "view",
        "has_tree": True,
    }

    service = TrustEngineService(
        redis_client=fake_redis,
        spicedb_client=mock_spicedb,
        model_path="models/isolation_forest.joblib",
        explainer_path="models/shap_explainer.joblib",
    )

    telemetry = RequestTelemetry(
        session_id="sess_coord_test",
        subject_id="user:eve",
        client_ip="10.20.30.40",
        method="GET",
        path="/api/documents/doc_99",
    )

    result = await service.evaluate(
        telemetry=telemetry,
        resource="document:doc_99",
        permission="view",
        traversal_path=["user:eve", "organization:eng#member", "document:doc_99#viewer"],
    )

    assert result.session_id == "sess_coord_test"
    assert result.subject_id == "user:eve"
    assert result.current_score >= 0.9
    assert result.feature_vector.graph.path_length == 3.0


def test_single_pass_inference_matches_sklearn(trust_scorer: TrustScorer) -> None:
    """score_samples - offset_ reproduces decision_function and predict exactly."""
    import numpy as np

    from scripts.generate_synthetic_traffic import generate_traffic

    x_data, _, _ = generate_traffic(num_samples=400, anomaly_fraction=0.1, random_seed=7)
    model = trust_scorer.model
    for row in x_data:
        x = row.reshape(1, -1)
        decision, _ = trust_scorer._infer(x)
        assert np.isclose(decision, model.decision_function(x)[0])
        assert (decision < 0) == (model.predict(x)[0] == -1)
