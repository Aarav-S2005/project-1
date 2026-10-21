"""Overview statistics endpoint for the Control Plane Dashboard."""

import logging
from datetime import UTC, datetime
from typing import Any

import redis.asyncio as redis
from decision_engine.closed_loop import ACTIVE_NARROW_ZSET
from fastapi import APIRouter, Depends
from shared.config import get_settings

from control_plane.db import get_database
from control_plane.deps import get_repository
from control_plane.repositories import ConfigRepository

logger = logging.getLogger("control_plane.routes.stats")

router = APIRouter(prefix="/api/v1/overview", tags=["overview"])


@router.get("/stats", response_model=dict[str, Any])
async def get_overview_stats(
    config_repo: ConfigRepository = Depends(get_repository),
) -> dict[str, Any]:
    """Provide aggregated operational statistics for the frontend dashboard."""
    db = get_database()
    audit_collection = db["audit_logs"]

    # 1. Total counts & Decision breakdown
    total_logs = await audit_collection.count_documents({})

    allow_count = await audit_collection.count_documents({"decision": "allow"})
    narrow_count = await audit_collection.count_documents({"decision": "narrow"})
    step_up_count = await audit_collection.count_documents({"decision": "step_up"})
    deny_count = await audit_collection.count_documents({"decision": "deny"})

    # 2. Gateway config entity counts
    routes = await config_repo.list_routes()
    upstreams = await config_repo.list_upstreams()
    middlewares = await config_repo.list_middlewares()

    # 3. Active Narrow Restrictions in Redis
    settings = get_settings()
    active_narrow_count = 0
    try:
        redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
        )
        now_ts = datetime.now(UTC).timestamp()
        active_narrow_count = await redis_client.zcount(ACTIVE_NARROW_ZSET, min=now_ts, max="+inf")
        await redis_client.aclose()
    except Exception as exc:
        logger.warning("Could not fetch active narrow count from Redis: %s", exc)

    return {
        "total_requests": total_logs,
        "decisions": {
            "allow": allow_count,
            "narrow": narrow_count,
            "step_up": step_up_count,
            "deny": deny_count,
        },
        "active_narrow_restrictions": active_narrow_count,
        "config": {
            "routes_count": len(routes),
            "upstreams_count": len(upstreams),
            "middlewares_count": len(middlewares),
        },
    }
