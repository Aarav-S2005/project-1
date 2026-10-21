"""Unit tests for Pydantic boundary schemas."""

from datetime import UTC, datetime

from shared.schemas import (
    AuditRecord,
    BehavioralFeatures,
    ClosedLoopAction,
    ConfigBundle,
    DecisionAction,
    DecisionResult,
    FeatureVector,
    GraphFeatures,
    MiddlewareConfig,
    RequestTelemetry,
    RouteConfig,
    TrustScoreResult,
    UpstreamConfig,
)


def test_gateway_schemas() -> None:
    """Verify serialization and validation of gateway configs."""
    upstream = UpstreamConfig(
        id="ups_1",
        name="test-upstream",
        target_url="http://localhost:8080",
        timeout_ms=3000,
    )
    assert upstream.timeout_ms == 3000

    route = RouteConfig(
        id="route_1",
        upstream_id=upstream.id,
        path_prefix="/api/v1/test",
        methods=["GET", "POST"],
    )
    assert "GET" in route.methods

    middleware = MiddlewareConfig(
        id="mid_1",
        name="trust-middleware",
        type="trust_score_evaluator",
        order=1,
    )
    assert middleware.is_active is True

    bundle = ConfigBundle(
        version=1,
        etag="abc123hash",
        updated_at=datetime.now(UTC),
        upstreams=[upstream],
        routes=[route],
        middlewares=[middleware],
    )
    assert bundle.version == 1
    assert len(bundle.upstreams) == 1


def test_feature_vector_serialization() -> None:
    """Verify feature vector converts cleanly to ordered array and dictionary."""
    b = BehavioralFeatures(
        req_rate_10s=5.0,
        req_rate_60s=1.0,
        rate_burst_ratio=5.0,
        geo_velocity_kmh=200.0,
        tls_fingerprint_mismatch=0.0,
        time_of_day_deviation=0.1,
    )
    g = GraphFeatures(
        path_length=2.0,
        path_novelty=1.0,
        privilege_shortcut_score=0.5,
        intermediate_node_degree=3.0,
    )
    fv = FeatureVector(behavioral=b, graph=g)

    arr = fv.to_array()
    assert len(arr) == 10
    assert arr[0] == 5.0
    assert arr[6] == 2.0  # path_length

    d = fv.to_dict()
    assert d["req_rate_10s"] == 5.0
    assert d["path_novelty"] == 1.0


def test_decision_and_audit_schemas() -> None:
    """Verify decision result and audit record parsing."""
    telemetry = RequestTelemetry(
        session_id="sess_test",
        subject_id="user:alice",
        client_ip="127.0.0.1",
        method="GET",
        path="/api/docs",
    )
    fv = FeatureVector()
    trust_res = TrustScoreResult(
        session_id="sess_test",
        subject_id="user:alice",
        previous_score=0.9,
        current_score=0.7,
        score_delta=-0.2,
        is_anomaly=True,
        anomaly_severity=0.5,
        feature_vector=fv,
    )

    closed_loop = ClosedLoopAction(
        relation_tuple="doc:1#restricted@user:alice",
        ttl_seconds=300,
        expires_at=datetime.now(UTC),
    )

    decision = DecisionResult(
        decision=DecisionAction.NARROW,
        decision_reason="Anomaly detected",
        rebac_allowed=True,
        trust_score=0.7,
        trust_result=trust_res,
        closed_loop_action=closed_loop,
    )
    assert decision.decision == DecisionAction.NARROW
    assert decision.closed_loop_action is not None

    audit = AuditRecord(
        request_id="req_123",
        session_id=telemetry.session_id,
        subject_id=telemetry.subject_id,
        client_ip=telemetry.client_ip,
        route_id="route_1",
        resource="doc:1",
        permission="view",
        trust_score_before=0.9,
        trust_score_after=0.7,
        decision=DecisionAction.NARROW,
        decision_reason="Test reason",
        features=fv.to_dict(),
        shap_attributions={"rate_burst_ratio": -0.2},
        closed_loop_feedback=closed_loop,
        latency_ms=12.5,
    )
    assert audit.decision == DecisionAction.NARROW
    assert audit.features["req_rate_10s"] == 0.0
