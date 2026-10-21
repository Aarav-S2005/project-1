"""Schemas for policy decision evaluation and closed-loop feedback."""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from shared.schemas.trust import RequestTelemetry, TrustScoreResult


class DecisionAction(StrEnum):
    """Possible outcomes determined by the Decision Engine."""

    ALLOW = "allow"
    STEP_UP = "step_up"
    NARROW = "narrow"
    DENY = "deny"


class EvaluationRequest(BaseModel):
    """Request payload sent to the Decision Engine."""

    session_id: str
    subject: str = Field(description="Subject principal, e.g. user:alice")
    resource: str = Field(description="SpiceDB resource, e.g. document:doc_123")
    permission: str = Field(description="Requested permission, e.g. view")
    telemetry: RequestTelemetry
    traversal_path: list[str] = Field(default_factory=list, description="Resolved ReBAC path edges")


class ClosedLoopAction(BaseModel):
    """Details of temporary restricting relation written to SpiceDB."""

    action: str = Field(default="spicedb_relation_written")
    relation_tuple: str = Field(
        description="Written tuple, e.g. document:doc_123#restricted_subject@user:alice"
    )
    ttl_seconds: int = Field(default=900, description="Duration before restriction expires")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime = Field(description="Timestamp when restriction expires")


class DecisionResult(BaseModel):
    """Decision output determining gateway proxy behavior."""

    decision: DecisionAction
    decision_reason: str
    rebac_allowed: bool
    trust_score: float
    trust_result: TrustScoreResult
    closed_loop_action: ClosedLoopAction | None = None
