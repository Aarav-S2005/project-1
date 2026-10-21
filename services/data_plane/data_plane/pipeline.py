"""Zero-Trust middleware evaluation pipeline for the Data Plane proxy."""

import hashlib
import logging
import time
from uuid import uuid4

from audit.service import AuditService
from decision_engine.service import DecisionEngineService
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from shared.schemas.audit import AuditRecord
from shared.schemas.decision import DecisionAction, DecisionResult, EvaluationRequest
from shared.schemas.gateway import RouteConfig
from shared.schemas.trust import RequestTelemetry, TrustScoreResult
from trust_engine.service import TrustEngineService

logger = logging.getLogger("data_plane.pipeline")


class PipelineResult(BaseModel):
    """Result of running a request through the Zero-Trust pipeline."""

    allowed: bool
    headers: dict[str, str] = Field(default_factory=dict)
    intercept_response: Response | None = Field(default=None, exclude=True)
    decision_result: DecisionResult | None = None
    trust_result: TrustScoreResult | None = None

    model_config = {
        "arbitrary_types_allowed": True,
    }


def extract_subject_id(request: Request) -> str:
    """Extract authenticated subject principal or return default anonymous user."""
    sub = (
        request.headers.get("x-subject")
        or request.headers.get("x-user-id")
        or request.headers.get("x-subject-id")
    )
    if not sub:
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            if token.startswith("user:"):
                return token
            if token:
                return f"user:{token}"
        return "user:anonymous"

    if ":" not in sub:
        return f"user:{sub}"
    return sub


def extract_session_id(request: Request, client_ip: str, subject_id: str) -> str:
    """Extract or derive reproducible session tracking identifier strictly scoped per subject."""
    sess = request.headers.get("x-session-id") or request.headers.get("session-id")
    safe_sub = subject_id.replace(":", "_")
    if sess:
        if sess.startswith(safe_sub) or sess.startswith(subject_id):
            return sess
        return f"{safe_sub}_{sess}"

    ua = request.headers.get("user-agent", "")
    digest = hashlib.sha256(f"{subject_id}:{client_ip}:{ua}".encode()).hexdigest()[:12]
    return f"sess_{safe_sub}_{digest}"



def extract_resource_id(request: Request, route: RouteConfig) -> str:
    """Extract SpiceDB resource ID from headers, query, or path according to route configuration."""
    header_val = request.headers.get("x-resource-id")
    if header_val:
        return header_val

    rule = route.resource_id_extractor
    if rule.startswith("header:"):
        h_name = rule.split(":", 1)[1]
        val = request.headers.get(h_name)
        if val:
            return val
    elif rule.startswith("query:"):
        q_name = rule.split(":", 1)[1]
        val = request.query_params.get(q_name)
        if val:
            return val
    elif rule.startswith("path_param:") or rule.startswith("path:"):
        path = request.url.path
        if path.startswith(route.path_prefix):
            remainder = path[len(route.path_prefix) :].strip("/")
            if remainder:
                return remainder.split("/")[0]

    segments = [s for s in request.url.path.strip("/").split("/") if s]
    return segments[-1] if segments else "doc_default"


class ZeroTrustPipeline:
    """Evaluates incoming requests against Trust Engine, Decision Engine, and Audit logger."""

    def __init__(
        self,
        trust_engine: TrustEngineService,
        decision_engine: DecisionEngineService,
        audit_service: AuditService,
    ) -> None:
        self.trust_engine = trust_engine
        self.decision_engine = decision_engine
        self.audit_service = audit_service

    async def evaluate_request(self, request: Request, route: RouteConfig) -> PipelineResult:
        """Run the end-to-end Zero-Trust evaluation pipeline for a request."""
        if not route.auth_required:
            return PipelineResult(allowed=True)

        start_time = time.perf_counter()
        forwarded_for = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        client_ip = (
            forwarded_for
            or request.headers.get("x-client-ip", "").strip()
            or (request.client.host if request.client else "127.0.0.1")
        )
        subject_id = extract_subject_id(request)
        session_id = extract_session_id(request, client_ip, subject_id)
        resource_id = extract_resource_id(request, route)

        resource = f"{route.resource_type}:{resource_id}"
        permission = route.permission_mapping.get(request.method, "view")
        user_agent = request.headers.get("user-agent", "")
        tls_fp = request.headers.get("x-tls-fingerprint", "")

        telemetry = RequestTelemetry(
            session_id=session_id,
            subject_id=subject_id,
            client_ip=client_ip,
            user_agent=user_agent,
            tls_fingerprint=tls_fp,
            method=request.method,
            path=request.url.path,
        )

        # 1. Trust Engine evaluation (Behavioral + Graph features + Anomaly scoring + Redis decay)
        trust_result = await self.trust_engine.evaluate(
            telemetry=telemetry,
            resource=resource,
            permission=permission,
        )

        # 2. Decision Engine evaluation (SpiceDB ReBAC + Trust score bands + Closed-loop narrowing)
        eval_request = EvaluationRequest(
            session_id=session_id,
            subject=subject_id,
            resource=resource,
            permission=permission,
            telemetry=telemetry,
            traversal_path=[],
        )
        decision_result = await self.decision_engine.evaluate(
            request=eval_request,
            trust_result=trust_result,
        )

        # 3. Offload audit record asynchronously without blocking proxy latency
        latency_ms = (time.perf_counter() - start_time) * 1000
        audit_record = AuditRecord(
            request_id=f"req_{uuid4().hex[:8]}",
            session_id=session_id,
            subject_id=subject_id,
            client_ip=client_ip,
            route_id=route.id,
            resource=resource,
            permission=permission,
            trust_score_before=trust_result.previous_score,
            trust_score_after=trust_result.current_score,
            decision=decision_result.decision,
            decision_reason=decision_result.decision_reason,
            features=trust_result.feature_vector.to_dict(),
            shap_attributions=trust_result.shap_attributions,
            closed_loop_feedback=decision_result.closed_loop_action,
            latency_ms=latency_ms,
        )
        self.audit_service.log_decision(audit_record)

        # 4. Action handling and response header propagation
        headers = {
            "X-Trust-Score": f"{trust_result.current_score:.4f}",
            "X-Trust-Decision": decision_result.decision.value,
        }

        if decision_result.decision == DecisionAction.ALLOW:
            return PipelineResult(
                allowed=True,
                headers=headers,
                decision_result=decision_result,
                trust_result=trust_result,
            )

        if decision_result.decision == DecisionAction.NARROW:
            headers["X-Trust-Narrowed"] = "true"
            return PipelineResult(
                allowed=True,
                headers=headers,
                decision_result=decision_result,
                trust_result=trust_result,
            )

        if decision_result.decision == DecisionAction.STEP_UP:
            headers["WWW-Authenticate"] = "Bearer challenge=step_up_mfa"
            intercept = JSONResponse(
                status_code=401,
                content={
                    "error": "Step-up authentication required",
                    "action": "step_up",
                    "trust_score": trust_result.current_score,
                    "reason": decision_result.decision_reason,
                },
                headers=headers,
            )
            return PipelineResult(
                allowed=False,
                headers=headers,
                intercept_response=intercept,
                decision_result=decision_result,
                trust_result=trust_result,
            )

        # DENY
        intercept = JSONResponse(
            status_code=403,
            content={
                "error": "Access denied by Zero-Trust policy",
                "action": "deny",
                "trust_score": trust_result.current_score,
                "reason": decision_result.decision_reason,
            },
            headers=headers,
        )
        return PipelineResult(
            allowed=False,
            headers=headers,
            intercept_response=intercept,
            decision_result=decision_result,
            trust_result=trust_result,
        )
