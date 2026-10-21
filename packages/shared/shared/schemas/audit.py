"""Audit record schema with SHAP explainability attribution."""

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from shared.schemas.decision import ClosedLoopAction, DecisionAction


class AuditRecord(BaseModel):
    """Immutable decision audit record persisted in MongoDB."""

    id: str | None = Field(default=None, alias="_id", description="MongoDB ObjectId string")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    request_id: str
    session_id: str
    subject_id: str
    client_ip: str
    route_id: str
    resource: str
    permission: str
    trust_score_before: float
    trust_score_after: float
    decision: DecisionAction
    decision_reason: str
    features: dict[str, float]
    shap_attributions: dict[str, float] = Field(default_factory=dict)
    closed_loop_feedback: ClosedLoopAction | None = None
    latency_ms: float = 0.0

    model_config = {
        "populate_by_name": True,
    }
