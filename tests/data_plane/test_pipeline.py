"""Integration tests for ZeroTrustPipeline and Data Plane proxy interception."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import data_plane.main as dp_module
import pytest
from audit.service import AuditService
from data_plane.pipeline import (
    ZeroTrustPipeline,
    extract_resource_id,
    extract_session_id,
    extract_subject_id,
)
from decision_engine.service import DecisionEngineService
from fastapi import Request as FastAPIRequest
from httpx import ASGITransport, AsyncClient, MockTransport, Request, Response
from shared.schemas.decision import (
    ClosedLoopAction,
    DecisionAction,
    DecisionResult,
)
from shared.schemas.gateway import ConfigBundle, RouteConfig, UpstreamConfig
from shared.schemas.trust import (
    BehavioralFeatures,
    FeatureVector,
    GraphFeatures,
    TrustScoreResult,
)
from trust_engine.service import TrustEngineService


def _dummy_trust_result(score: float, is_anomaly: bool = False) -> TrustScoreResult:
    return TrustScoreResult(
        session_id="sess_test",
        subject_id="user:alice",
        previous_score=1.0,
        current_score=score,
        score_delta=score - 1.0,
        is_anomaly=is_anomaly,
        anomaly_severity=0.0 if not is_anomaly else 0.8,
        feature_vector=FeatureVector(
            behavioral=BehavioralFeatures(),
            graph=GraphFeatures(),
        ),
        shap_attributions={"req_rate_10s": 0.02},
    )


def test_extract_helpers() -> None:
    """Verify subject, session, and resource extraction logic."""
    # 1. Subject extraction
    scope_sub = {
        "type": "http",
        "method": "GET",
        "path": "/api/test",
        "headers": [(b"x-subject", b"user:bob")],
    }
    req_sub = FastAPIRequest(scope_sub)
    assert extract_subject_id(req_sub) == "user:bob"

    scope_bearer = {
        "type": "http",
        "method": "GET",
        "path": "/api/test",
        "headers": [(b"authorization", b"Bearer token_charlie")],
    }
    req_bearer = FastAPIRequest(scope_bearer)
    assert extract_subject_id(req_bearer) == "user:token_charlie"

    scope_anon = {
        "type": "http",
        "method": "GET",
        "path": "/api/test",
        "headers": [],
    }
    req_anon = FastAPIRequest(scope_anon)
    assert extract_subject_id(req_anon) == "user:anonymous"

    # 2. Session extraction
    scope_sess = {
        "type": "http",
        "method": "GET",
        "path": "/api/test",
        "headers": [(b"x-session-id", b"custom_session_123")],
    }
    assert extract_session_id(FastAPIRequest(scope_sess), "127.0.0.1") == "custom_session_123"

    scope_no_sess = {
        "type": "http",
        "method": "GET",
        "path": "/api/test",
        "headers": [(b"user-agent", b"TestAgent")],
    }
    derived = extract_session_id(FastAPIRequest(scope_no_sess), "127.0.0.1")
    assert derived.startswith("sess_")

    # 3. Resource ID extraction
    route = RouteConfig(
        id="r1",
        upstream_id="u1",
        path_prefix="/api/docs",
        resource_id_extractor="path_param:id",
    )
    scope_path = {
        "type": "http",
        "method": "GET",
        "path": "/api/docs/doc_xyz/details",
        "headers": [],
    }
    assert extract_resource_id(FastAPIRequest(scope_path), route) == "doc_xyz"


@pytest.mark.asyncio
async def test_pipeline_decision_allow() -> None:
    """Verify pipeline allows request and appends trust headers when score is nominal."""
    mock_trust = MagicMock(spec=TrustEngineService)
    mock_trust.evaluate = AsyncMock(return_value=_dummy_trust_result(0.95))

    mock_decision = MagicMock(spec=DecisionEngineService)
    mock_decision.evaluate = AsyncMock(
        return_value=DecisionResult(
            decision=DecisionAction.ALLOW,
            decision_reason="trust_nominal",
            rebac_allowed=True,
            trust_score=0.95,
            trust_result=_dummy_trust_result(0.95),
        )
    )

    mock_audit = MagicMock(spec=AuditService)
    mock_audit.log_decision = MagicMock(return_value=True)

    pipeline = ZeroTrustPipeline(
        trust_engine=mock_trust,
        decision_engine=mock_decision,
        audit_service=mock_audit,
    )

    route = RouteConfig(
        id="r1",
        upstream_id="u1",
        path_prefix="/api/documents",
        auth_required=True,
    )
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/documents/doc_1",
        "headers": [(b"x-subject", b"user:alice")],
    }
    req = FastAPIRequest(scope)

    res = await pipeline.evaluate_request(req, route)
    assert res.allowed is True
    assert res.headers["X-Trust-Score"] == "0.9500"
    assert res.headers["X-Trust-Decision"] == "allow"
    assert "X-Trust-Narrowed" not in res.headers
    mock_audit.log_decision.assert_called_once()


@pytest.mark.asyncio
async def test_pipeline_decision_narrow_and_step_up_and_deny() -> None:
    """Verify pipeline behaves correctly across narrow, step_up, and deny actions."""
    mock_trust = MagicMock(spec=TrustEngineService)
    mock_decision = MagicMock(spec=DecisionEngineService)
    mock_audit = MagicMock(spec=AuditService)
    mock_audit.log_decision = MagicMock(return_value=True)

    pipeline = ZeroTrustPipeline(
        trust_engine=mock_trust,
        decision_engine=mock_decision,
        audit_service=mock_audit,
    )
    route = RouteConfig(id="r1", upstream_id="u1", path_prefix="/api/documents", auth_required=True)
    req = FastAPIRequest(
        {"type": "http", "method": "GET", "path": "/api/documents/doc_1", "headers": []}
    )

    # 1. NARROW
    narrow_action = ClosedLoopAction(
        relation_tuple="document:doc_1#restricted_subject@user:alice",
        expires_at=datetime.now(UTC),
    )
    mock_trust.evaluate = AsyncMock(return_value=_dummy_trust_result(0.70))
    mock_decision.evaluate = AsyncMock(
        return_value=DecisionResult(
            decision=DecisionAction.NARROW,
            decision_reason="narrow_applied",
            rebac_allowed=True,
            trust_score=0.70,
            trust_result=_dummy_trust_result(0.70),
            closed_loop_action=narrow_action,
        )
    )
    res_narrow = await pipeline.evaluate_request(req, route)
    assert res_narrow.allowed is True
    assert res_narrow.headers["X-Trust-Narrowed"] == "true"
    assert res_narrow.headers["X-Trust-Decision"] == "narrow"

    # 2. STEP_UP
    mock_trust.evaluate = AsyncMock(return_value=_dummy_trust_result(0.50))
    mock_decision.evaluate = AsyncMock(
        return_value=DecisionResult(
            decision=DecisionAction.STEP_UP,
            decision_reason="mfa_required",
            rebac_allowed=True,
            trust_score=0.50,
            trust_result=_dummy_trust_result(0.50),
        )
    )
    res_step_up = await pipeline.evaluate_request(req, route)
    assert res_step_up.allowed is False
    assert res_step_up.intercept_response is not None
    assert res_step_up.intercept_response.status_code == 401
    auth_header = res_step_up.intercept_response.headers.get("WWW-Authenticate", "")
    assert "Bearer challenge=step_up_mfa" in auth_header

    # 3. DENY
    mock_trust.evaluate = AsyncMock(return_value=_dummy_trust_result(0.20, is_anomaly=True))
    mock_decision.evaluate = AsyncMock(
        return_value=DecisionResult(
            decision=DecisionAction.DENY,
            decision_reason="critical_anomaly",
            rebac_allowed=True,
            trust_score=0.20,
            trust_result=_dummy_trust_result(0.20, is_anomaly=True),
        )
    )
    res_deny = await pipeline.evaluate_request(req, route)
    assert res_deny.allowed is False
    assert res_deny.intercept_response is not None
    assert res_deny.intercept_response.status_code == 403


@pytest.mark.asyncio
async def test_full_http_gateway_pipeline_interception() -> None:
    """Verify full HTTP request cycle through Data Plane app with pipeline injection."""
    dp_module.sync_manager._current_bundle = ConfigBundle(
        version=11,
        etag='"etag11"',
        updated_at=datetime.now(UTC),
        upstreams=[
            UpstreamConfig(id="u_doc", name="Doc Svc", target_url="http://upstream.local/docs")
        ],
        routes=[
            RouteConfig(
                id="r_doc",
                upstream_id="u_doc",
                path_prefix="/api/v1/docs",
                methods=["GET"],
                strip_path=False,
                auth_required=True,
            )
        ],
        middlewares=[],
    )
    dp_module.sync_manager._rebuild_indices()

    def upstream_handler(request: Request) -> Response:
        return Response(200, json={"content": "confidential_document_body"})

    mock_client = AsyncClient(transport=MockTransport(upstream_handler))
    dp_module.proxy_engine._client = mock_client

    mock_trust = MagicMock(spec=TrustEngineService)
    mock_decision = MagicMock(spec=DecisionEngineService)
    mock_audit = MagicMock(spec=AuditService)
    mock_audit.log_decision = MagicMock(return_value=True)

    test_pipeline = ZeroTrustPipeline(
        trust_engine=mock_trust,
        decision_engine=mock_decision,
        audit_service=mock_audit,
    )
    dp_module.set_pipeline(test_pipeline)

    transport = ASGITransport(app=dp_module.app)
    async with AsyncClient(transport=transport, base_url="http://testgateway") as client:
        # 1. ALLOW scenario
        mock_trust.evaluate = AsyncMock(return_value=_dummy_trust_result(0.95))
        mock_decision.evaluate = AsyncMock(
            return_value=DecisionResult(
                decision=DecisionAction.ALLOW,
                decision_reason="nominal",
                rebac_allowed=True,
                trust_score=0.95,
                trust_result=_dummy_trust_result(0.95),
            )
        )
        resp_allow = await client.get(
            "/api/v1/docs/101",
            headers={"X-Subject": "user:alice"},
        )
        assert resp_allow.status_code == 200
        assert resp_allow.headers.get("X-Trust-Score") == "0.9500"
        assert resp_allow.headers.get("X-Trust-Decision") == "allow"
        assert resp_allow.json()["content"] == "confidential_document_body"

        # 2. NARROW scenario (still proxies, but tagged as narrowed)
        mock_trust.evaluate = AsyncMock(return_value=_dummy_trust_result(0.72))
        mock_decision.evaluate = AsyncMock(
            return_value=DecisionResult(
                decision=DecisionAction.NARROW,
                decision_reason="degraded_narrow",
                rebac_allowed=True,
                trust_score=0.72,
                trust_result=_dummy_trust_result(0.72),
            )
        )
        resp_narrow = await client.get("/api/v1/docs/101")
        assert resp_narrow.status_code == 200
        assert resp_narrow.headers.get("X-Trust-Narrowed") == "true"
        assert resp_narrow.headers.get("X-Trust-Decision") == "narrow"

        # 3. STEP_UP scenario (intercepted with 401 challenge)
        mock_trust.evaluate = AsyncMock(return_value=_dummy_trust_result(0.55))
        mock_decision.evaluate = AsyncMock(
            return_value=DecisionResult(
                decision=DecisionAction.STEP_UP,
                decision_reason="mfa_required",
                rebac_allowed=True,
                trust_score=0.55,
                trust_result=_dummy_trust_result(0.55),
            )
        )
        resp_step_up = await client.get("/api/v1/docs/101")
        assert resp_step_up.status_code == 401
        assert resp_step_up.json()["action"] == "step_up"
        assert resp_step_up.headers.get("X-Trust-Decision") == "step_up"

        # 4. DENY scenario (intercepted with 403 forbidden)
        mock_trust.evaluate = AsyncMock(return_value=_dummy_trust_result(0.15))
        mock_decision.evaluate = AsyncMock(
            return_value=DecisionResult(
                decision=DecisionAction.DENY,
                decision_reason="critical_risk",
                rebac_allowed=True,
                trust_score=0.15,
                trust_result=_dummy_trust_result(0.15),
            )
        )
        resp_deny = await client.get("/api/v1/docs/101")
        assert resp_deny.status_code == 403
        assert resp_deny.json()["action"] == "deny"
        assert resp_deny.headers.get("X-Trust-Decision") == "deny"
