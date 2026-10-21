"""Unit tests for DecisionBandEvaluator, ClosedLoopManager, and DecisionEngineService."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import fakeredis.aioredis
import pytest
from decision_engine.bands import DecisionBandEvaluator
from decision_engine.closed_loop import ClosedLoopManager
from decision_engine.policy.spicedb import SpiceDBClient
from decision_engine.service import DecisionEngineService, parse_entity
from shared.schemas.decision import DecisionAction, EvaluationRequest
from shared.schemas.trust import (
    BehavioralFeatures,
    FeatureVector,
    GraphFeatures,
    RequestTelemetry,
    TrustScoreResult,
)


@pytest.fixture
def fake_redis() -> fakeredis.aioredis.FakeRedis:
    """Fixture providing an in-memory asynchronous Redis instance."""
    return fakeredis.aioredis.FakeRedis()


@pytest.fixture
def mock_spicedb() -> MagicMock:
    """Fixture providing a mocked SpiceDBClient instance."""
    client = MagicMock(spec=SpiceDBClient)
    client.check_permission.return_value = True
    return client


def _dummy_trust_result(score: float) -> TrustScoreResult:
    """Helper to build a dummy TrustScoreResult with given score."""
    return TrustScoreResult(
        session_id="sess_123",
        subject_id="user:alice",
        previous_score=1.0,
        current_score=score,
        score_delta=score - 1.0,
        is_anomaly=(score < 0.85),
        anomaly_severity=max(0.0, 1.0 - score),
        feature_vector=FeatureVector(
            behavioral=BehavioralFeatures(
                req_rate_10s=1.0,
                req_rate_60s=5.0,
                rate_burst_ratio=0.2,
                geo_velocity_kmh=0.0,
                tls_fingerprint_mismatch=0.0,
                time_of_day_deviation=0.0,
            ),
            graph=GraphFeatures(
                path_length=2.0,
                path_novelty=0.1,
                privilege_shortcut_score=0.0,
                intermediate_node_degree=1.0,
            ),
        ),
        shap_attributions={"req_rate_10s": 0.05},
    )


def test_parse_entity() -> None:
    """Verify parse_entity extracts type and id and rejects malformed values."""
    res_type, res_id = parse_entity("document:doc_abc")
    assert res_type == "document"
    assert res_id == "doc_abc"

    sub_type, sub_id = parse_entity("user:alice")
    assert sub_type == "user"
    assert sub_id == "alice"

    with pytest.raises(ValueError, match="Invalid entity format"):
        parse_entity("invalid_string_without_colon")

    with pytest.raises(ValueError, match="Invalid entity format"):
        parse_entity(":missing_type")


def test_decision_band_evaluator_rebac_denied() -> None:
    """Verify ReBAC denial always results in DENY even with 1.0 trust score."""
    evaluator = DecisionBandEvaluator(
        allow_threshold=0.85,
        step_up_threshold=0.60,
        deny_threshold=0.40,
    )
    action, reason = evaluator.evaluate(rebac_allowed=False, trust_score=0.99)
    assert action == DecisionAction.DENY
    assert reason == "rebac_permission_denied"


def test_decision_band_evaluator_thresholds() -> None:
    """Verify trust score mapping across all four decision bands."""
    evaluator = DecisionBandEvaluator(
        allow_threshold=0.85,
        step_up_threshold=0.60,
        deny_threshold=0.40,
    )

    # 1. ALLOW (>= 0.85)
    action, reason = evaluator.evaluate(rebac_allowed=True, trust_score=0.95)
    assert action == DecisionAction.ALLOW
    assert "nominal_allow" in reason

    action, _ = evaluator.evaluate(rebac_allowed=True, trust_score=0.85)
    assert action == DecisionAction.ALLOW

    # 2. NARROW ([0.60, 0.85))
    action, reason = evaluator.evaluate(rebac_allowed=True, trust_score=0.84)
    assert action == DecisionAction.NARROW
    assert "degraded_narrow" in reason

    action, _ = evaluator.evaluate(rebac_allowed=True, trust_score=0.60)
    assert action == DecisionAction.NARROW

    # 3. STEP_UP ([0.40, 0.60))
    action, reason = evaluator.evaluate(rebac_allowed=True, trust_score=0.59)
    assert action == DecisionAction.STEP_UP
    assert "step_up" in reason

    action, _ = evaluator.evaluate(rebac_allowed=True, trust_score=0.40)
    assert action == DecisionAction.STEP_UP

    # 4. DENY (< 0.40)
    action, reason = evaluator.evaluate(rebac_allowed=True, trust_score=0.39)
    assert action == DecisionAction.DENY
    assert "critical_denied" in reason

    action, _ = evaluator.evaluate(rebac_allowed=True, trust_score=0.05)
    assert action == DecisionAction.DENY


@pytest.mark.asyncio
async def test_closed_loop_manager_apply_and_is_narrowed(
    fake_redis: fakeredis.aioredis.FakeRedis, mock_spicedb: MagicMock
) -> None:
    """Verify ClosedLoopManager writes restricting tuple to SpiceDB and sets Redis TTL."""
    manager = ClosedLoopManager(
        spicedb_client=mock_spicedb,
        redis_client=fake_redis,
        default_ttl_seconds=300,
    )

    action = await manager.apply_narrow(
        resource_type="document",
        resource_id="doc_100",
        subject_type="user",
        subject_id="alice",
    )

    # SpiceDB write verified
    mock_spicedb.write_relationship.assert_called_once_with(
        resource_type="document",
        resource_id="doc_100",
        relation="restricted_subject",
        subject_type="user",
        subject_id="alice",
    )

    assert action.relation_tuple == "document:doc_100#restricted_subject@user:alice"
    assert action.ttl_seconds == 300

    # Redis check
    is_narrow = await manager.is_narrowed("document", "doc_100", "user", "alice")
    assert is_narrow is True


@pytest.mark.asyncio
async def test_closed_loop_manager_revoke(
    fake_redis: fakeredis.aioredis.FakeRedis, mock_spicedb: MagicMock
) -> None:
    """Verify ClosedLoopManager revocation cleans both SpiceDB and Redis."""
    manager = ClosedLoopManager(
        spicedb_client=mock_spicedb,
        redis_client=fake_redis,
        default_ttl_seconds=300,
    )

    await manager.apply_narrow("document", "doc_100", "user", "alice")
    assert await manager.is_narrowed("document", "doc_100", "user", "alice") is True

    # Revoke
    revoked = await manager.revoke_narrow("document", "doc_100", "user", "alice")
    assert revoked is True

    mock_spicedb.delete_relationship.assert_called_once_with(
        resource_type="document",
        resource_id="doc_100",
        relation="restricted_subject",
        subject_type="user",
        subject_id="alice",
    )
    assert await manager.is_narrowed("document", "doc_100", "user", "alice") is False


@pytest.mark.asyncio
async def test_closed_loop_manager_sweep_expired(
    fake_redis: fakeredis.aioredis.FakeRedis, mock_spicedb: MagicMock
) -> None:
    """Verify sweep_expired_restrictions removes expired restrictions from SpiceDB and Redis."""
    manager = ClosedLoopManager(
        spicedb_client=mock_spicedb,
        redis_client=fake_redis,
        default_ttl_seconds=60,
    )

    now = datetime.now(UTC)
    # Apply with timestamp in the past
    past_time = now - timedelta(seconds=120)
    await manager.apply_narrow(
        resource_type="document",
        resource_id="doc_expired",
        subject_type="user",
        subject_id="bob",
        ttl_seconds=60,
        current_time=past_time,
    )

    # Sweep at current time
    swept = await manager.sweep_expired_restrictions(current_time=now)
    assert swept == 1

    mock_spicedb.delete_relationship.assert_called_once_with(
        resource_type="document",
        resource_id="doc_expired",
        relation="restricted_subject",
        subject_type="user",
        subject_id="bob",
    )


@pytest.mark.asyncio
async def test_decision_engine_service_evaluate_allow(
    fake_redis: fakeredis.aioredis.FakeRedis, mock_spicedb: MagicMock
) -> None:
    """Verify evaluate yields ALLOW and no closed loop write-back when trust is high."""
    service = DecisionEngineService(spicedb_client=mock_spicedb, redis_client=fake_redis)

    req = EvaluationRequest(
        session_id="sess_1",
        subject="user:alice",
        resource="document:doc_1",
        permission="view",
        telemetry=RequestTelemetry(
            session_id="sess_1",
            subject_id="user:alice",
            client_ip="127.0.0.1",
            user_agent="test-agent",
            method="GET",
            path="/api/documents/doc_1",
        ),
    )

    result = await service.evaluate(req, _dummy_trust_result(0.92))
    assert result.decision == DecisionAction.ALLOW
    assert result.rebac_allowed is True
    assert result.closed_loop_action is None
    mock_spicedb.write_relationship.assert_not_called()


@pytest.mark.asyncio
async def test_decision_engine_service_evaluate_narrow_triggers_closed_loop(
    fake_redis: fakeredis.aioredis.FakeRedis, mock_spicedb: MagicMock
) -> None:
    """Verify evaluate yields NARROW and performs SpiceDB closed-loop write-back
    when score is degraded.
    """
    service = DecisionEngineService(spicedb_client=mock_spicedb, redis_client=fake_redis)

    req = EvaluationRequest(
        session_id="sess_2",
        subject="user:attacker",
        resource="document:doc_confidential",
        permission="view",
        telemetry=RequestTelemetry(
            session_id="sess_2",
            subject_id="user:attacker",
            client_ip="198.51.100.1",
            user_agent="malicious-agent",
            method="GET",
            path="/api/documents/doc_confidential",
        ),
    )

    # Score in narrow band (e.g. 0.70)
    result = await service.evaluate(req, _dummy_trust_result(0.70))
    assert result.decision == DecisionAction.NARROW
    assert result.rebac_allowed is True
    assert result.closed_loop_action is not None
    assert (
        result.closed_loop_action.relation_tuple
        == "document:doc_confidential#restricted_subject@user:attacker"
    )

    mock_spicedb.write_relationship.assert_called_once_with(
        resource_type="document",
        resource_id="doc_confidential",
        relation="restricted_subject",
        subject_type="user",
        subject_id="attacker",
    )
