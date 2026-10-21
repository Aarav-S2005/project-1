"""Audit log querying endpoints for the Control Plane and Dashboard."""

import logging
from datetime import datetime
from typing import Any

from audit.repository import AuditRepository
from fastapi import APIRouter, Query
from shared.schemas.audit import AuditRecord

from control_plane.db import get_database

logger = logging.getLogger("control_plane.routes.audit")

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


def get_audit_repository() -> AuditRepository:
    """Dependency provider for AuditRepository."""
    db = get_database()
    return AuditRepository(db=db)


@router.get("/logs", response_model=dict[str, Any])
async def list_audit_logs(
    session_id: str | None = Query(default=None),
    subject_id: str | None = Query(default=None),
    decision: str | None = Query(default=None),
    start_time: datetime | None = Query(default=None),
    end_time: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    skip: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    """Retrieve filtered historical audit records with SHAP attributions."""
    repo = get_audit_repository()
    records: list[AuditRecord] = await repo.find(
        session_id=session_id,
        subject_id=subject_id,
        decision=decision,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        skip=skip,
    )
    total_count: int = await repo.count(
        session_id=session_id,
        subject_id=subject_id,
        decision=decision,
    )
    return {
        "total": total_count,
        "limit": limit,
        "skip": skip,
        "records": [r.model_dump(by_alias=True) for r in records],
    }


@router.delete("/logs", response_model=dict[str, Any])
async def clear_audit_logs() -> dict[str, Any]:
    """Delete all audit records from MongoDB."""
    db = get_database()
    result = await db["audit_logs"].delete_many({})
    return {"status": "cleared", "deleted_count": result.deleted_count}
