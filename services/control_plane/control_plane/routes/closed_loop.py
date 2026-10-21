"""Closed-loop restriction management endpoints for the Control Plane."""

import logging
from datetime import UTC, datetime
from typing import Any

import redis.asyncio as redis
from decision_engine.closed_loop import ACTIVE_NARROW_ZSET, ClosedLoopManager
from decision_engine.policy.spicedb import SpiceDBClient
from decision_engine.service import parse_entity
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from shared.config import get_settings

logger = logging.getLogger("control_plane.routes.closed_loop")

router = APIRouter(prefix="/api/v1/closed-loop", tags=["closed-loop"])


class RevokeRequest(BaseModel):
    """Payload to revoke an active narrowing restriction."""

    resource: str = Field(description="SpiceDB resource, e.g. document:doc_1")
    subject: str = Field(description="Subject principal, e.g. user:alice")


def get_closed_loop_manager() -> ClosedLoopManager:
    """Dependency provider for ClosedLoopManager."""
    settings = get_settings()
    redis_client = redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        password=settings.redis_password,
    )
    spicedb_client = SpiceDBClient()
    return ClosedLoopManager(spicedb_client=spicedb_client, redis_client=redis_client)


@router.get("/restrictions", response_model=list[dict[str, Any]])
async def list_active_restrictions() -> list[dict[str, Any]]:
    """List all currently active closed-loop narrowing restrictions from Redis."""
    settings = get_settings()
    redis_client = redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        password=settings.redis_password,
    )

    now = datetime.now(UTC)
    now_ts = now.timestamp()

    # Query active members with score >= now_ts
    raw_entries = await redis_client.zrangebyscore(
        ACTIVE_NARROW_ZSET, min=now_ts, max="+inf", withscores=True
    )
    await redis_client.aclose()

    restrictions: list[dict[str, Any]] = []
    for item in raw_entries:
        member_val: Any = item[0]
        raw_score: Any = item[1]
        score = float(raw_score)
        member = member_val.decode("utf-8") if isinstance(member_val, bytes) else str(member_val)
        parts = member.split(":")
        if len(parts) == 4:
            rt, rid, st, sid = parts[0], parts[1], parts[2], parts[3]
            ttl_remaining = max(0, int(score - now_ts))
            restrictions.append(
                {
                    "tuple": f"{rt}:{rid}#restricted_subject@{st}:{sid}",
                    "resource": f"{rt}:{rid}",
                    "subject": f"{st}:{sid}",
                    "expires_at": datetime.fromtimestamp(score, tz=UTC).isoformat(),
                    "ttl_remaining_seconds": ttl_remaining,
                }
            )

    return restrictions


@router.post("/revoke")
async def revoke_restriction(body: RevokeRequest) -> dict[str, str]:
    """Manually revoke an active closed-loop restriction from SpiceDB and Redis."""
    try:
        res_type, res_id = parse_entity(body.resource)
        sub_type, sub_id = parse_entity(body.subject)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    manager = get_closed_loop_manager()
    await manager.revoke_narrow(
        resource_type=res_type,
        resource_id=res_id,
        subject_type=sub_type,
        subject_id=sub_id,
    )
    return {"status": "revoked", "resource": body.resource, "subject": body.subject}
