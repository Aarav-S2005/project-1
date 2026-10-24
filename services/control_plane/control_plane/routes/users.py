"""User trust scores, decision history, and explainability endpoints for Control Plane."""

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import redis.asyncio as redis
from decision_engine.closed_loop import ACTIVE_NARROW_ZSET
from fastapi import APIRouter
from pydantic import BaseModel, Field
from shared.config import get_settings

from control_plane.db import get_database

logger = logging.getLogger("control_plane.routes.users")

router = APIRouter(prefix="/api/v1/users", tags=["users"])

# Standard predefined simulator personas
DEFAULT_SUBJECTS = ["user:alice", "user:bob", "user:charlie", "user:darth"]


@router.get("/trust-scores", response_model=list[dict[str, Any]])
async def get_all_users_trust_scores() -> list[dict[str, Any]]:
    """List all subjects/users with their current trust scores, decision breakdown,
    and restriction status.
    """
    db = get_database()
    audit_col = db["audit_logs"]

    # 1. Distinct subjects from audit logs, merged with default personas
    db_subjects = await audit_col.distinct("subject_id")
    subjects_set = set(db_subjects)
    # If database is clean or only has some subjects, include standard personas
    for s in DEFAULT_SUBJECTS:
        subjects_set.add(s)
    subjects = list(subjects_set)

    # 2. Check active narrow restrictions in Redis and per-user live scores
    settings = get_settings()
    active_restricted_subjects: set[str] = set()
    redis_client = redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        password=settings.redis_password,
    )
    try:
        now_ts = datetime.now(UTC).timestamp()
        raw_entries = await redis_client.zrangebyscore(ACTIVE_NARROW_ZSET, min=now_ts, max="+inf")
        for item in raw_entries:
            member = item.decode("utf-8") if isinstance(item, bytes) else str(item)
            parts = member.split(":")
            if len(parts) == 4:
                active_restricted_subjects.add(f"{parts[2]}:{parts[3]}")

        results: list[dict[str, Any]] = []

        for sub in subjects:
            cursor = audit_col.find({"subject_id": sub}).sort("timestamp", -1).limit(1)
            latest_record = await cursor.to_list(length=1)

            total_reqs = await audit_col.count_documents({"subject_id": sub})
            anomaly_reqs = await audit_col.count_documents(
                {"subject_id": sub, "decision": {"$in": ["narrow", "deny", "step_up"]}}
            )

            if latest_record:
                rec = latest_record[0]
                current_score = rec.get("trust_score_after", 1.0)
                latest_decision = rec.get("decision", "allow")
                latest_reason = rec.get("decision_reason", "")
                last_seen = rec.get("timestamp")
                if hasattr(last_seen, "isoformat"):
                    last_seen_str = last_seen.isoformat()
                else:
                    last_seen_str = str(last_seen)
                latest_shap = rec.get("shap_attributions", {})
            else:
                current_score = 1.0
                latest_decision = "allow"
                latest_reason = "baseline_trust"
                last_seen_str = datetime.now(UTC).isoformat()
                latest_shap = {}

            # Query Redis for live, subject-isolated session trust score
            safe_sub = sub.replace(":", "_")
            try:
                sub_keys = set(await redis_client.keys(f"session:*{sub}*:trust"))
                sub_keys.update(await redis_client.keys(f"session:*{safe_sub}*:trust"))
                for sk in sub_keys:
                    val = await redis_client.hget(sk, "current_score")
                    if val is not None:
                        current_score = float(val)
                        break
            except Exception:
                pass

            is_restricted = sub in active_restricted_subjects or latest_decision == "narrow"

            results.append(
                {
                    "subject_id": sub,
                    "current_trust_score": round(float(current_score), 3),
                    "latest_decision": latest_decision,
                    "latest_reason": latest_reason,
                    "total_requests": total_reqs,
                    "anomalous_requests": anomaly_reqs,
                    "is_restricted": is_restricted,
                    "last_seen": last_seen_str,
                    "latest_shap": latest_shap,
                }
            )

        # Sort by lowest trust score first to highlight risks
        results.sort(key=lambda x: x["current_trust_score"])
        return results
    finally:
        await redis_client.aclose()


@router.get("/{subject_id}/history", response_model=list[dict[str, Any]])
async def get_user_request_history(subject_id: str, limit: int = 50) -> list[dict[str, Any]]:
    """Retrieve chronologically ordered requests for a specific user with SHAP attributions."""
    db = get_database()
    audit_col = db["audit_logs"]

    cursor = audit_col.find({"subject_id": subject_id}).sort("timestamp", -1).limit(limit)
    records = await cursor.to_list(length=limit)

    formatted: list[dict[str, Any]] = []
    for r in records:
        ts = r.get("timestamp")
        formatted.append(
            {
                "request_id": r.get("request_id"),
                "session_id": r.get("session_id"),
                "subject_id": r.get("subject_id"),
                "client_ip": r.get("client_ip"),
                "route_id": r.get("route_id"),
                "resource": r.get("resource"),
                "permission": r.get("permission"),
                "trust_score_before": r.get("trust_score_before"),
                "trust_score_after": r.get("trust_score_after"),
                "decision": r.get("decision"),
                "decision_reason": r.get("decision_reason"),
                "features": r.get("features", {}),
                "shap_attributions": r.get("shap_attributions", {}),
                "latency_ms": r.get("latency_ms", 0.0),
                "timestamp": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
            }
        )

    return formatted


@router.post("/{subject_id}/reset-trust", response_model=dict[str, str])
async def reset_user_trust(subject_id: str) -> dict[str, str]:
    """Restore a user's trust score to 1.0 in Redis and append a MongoDB reset record."""
    settings = get_settings()
    db = get_database()
    audit_col = db["audit_logs"]
    now = datetime.now(UTC)

    # 1. Fetch current score before reset
    cursor = audit_col.find({"subject_id": subject_id}).sort("timestamp", -1).limit(1)
    last_rec = await cursor.to_list(length=1)
    prev_score = last_rec[0].get("trust_score_after", 1.0) if last_rec else 1.0

    safe_sub = subject_id.replace(":", "_")
    try:
        redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
        )
        keys = set(await redis_client.keys(f"session:*{subject_id}*:trust"))
        keys.update(await redis_client.keys(f"session:*{safe_sub}*:trust"))
        for k in keys:
            await redis_client.hset(k, "current_score", "1.0")

        # Initialize explicit clean session key
        init_key = f"session:sess_{safe_sub}:trust"
        await redis_client.hset(
            init_key,
            mapping={
                "current_score": "1.0",
                "baseline_score": "1.0",
                "request_count": "0",
                "last_updated_ts": str(now.timestamp()),
            },
        )

        # Clear behavioral rate spikes & seen paths so user starts fresh
        rate_keys = set(await redis_client.keys(f"session:*{subject_id}*:req_timestamps"))
        rate_keys.update(await redis_client.keys(f"session:*{safe_sub}*:req_timestamps"))
        for rk in rate_keys:
            await redis_client.delete(rk)

        await redis_client.aclose()
    except Exception as exc:
        logger.error("Failed to reset trust score in Redis: %s", exc)

    # 2. Append audit log in MongoDB so UI updates immediately
    await audit_col.insert_one(
        {
            "request_id": f"reset_{uuid4().hex[:8]}",
            "session_id": f"sess_{safe_sub}",
            "subject_id": subject_id,
            "client_ip": "127.0.0.1",
            "route_id": "operator_admin",
            "resource": "user_trust:profile",
            "permission": "operator_reset",
            "trust_score_before": prev_score,
            "trust_score_after": 1.0,
            "decision": "allow",
            "decision_reason": "Operator manually restored trust score to baseline (1.0)",
            "features": {},
            "shap_attributions": {},
            "latency_ms": 0.0,
            "timestamp": now,
        }
    )

    return {"status": "reset", "subject_id": subject_id}


class SetUserTrustPayload(BaseModel):
    """Payload to configure a user's trust score manually."""

    score: float = Field(..., ge=0.0, le=1.0)


@router.post("/{subject_id}/set-trust", response_model=dict[str, Any])
async def set_user_trust(subject_id: str, payload: SetUserTrustPayload) -> dict[str, Any]:
    """Manually configure or adjust a user's trust score in Redis and MongoDB."""
    settings = get_settings()
    db = get_database()
    audit_col = db["audit_logs"]
    now = datetime.now(UTC)

    cursor = audit_col.find({"subject_id": subject_id}).sort("timestamp", -1).limit(1)
    last_rec = await cursor.to_list(length=1)
    prev_score = last_rec[0].get("trust_score_after", 1.0) if last_rec else 1.0

    safe_sub = subject_id.replace(":", "_")
    try:
        redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
        )
        keys = set(await redis_client.keys(f"session:*{subject_id}*:trust"))
        keys.update(await redis_client.keys(f"session:*{safe_sub}*:trust"))
        for k in keys:
            await redis_client.hset(k, "current_score", str(payload.score))

        init_key = f"session:sess_{safe_sub}:trust"
        await redis_client.hset(
            init_key,
            mapping={
                "current_score": str(payload.score),
                "baseline_score": "1.0",
                "request_count": "0",
                "last_updated_ts": str(now.timestamp()),
            },
        )
        await redis_client.aclose()
    except Exception as exc:
        logger.error("Failed to set user trust score in Redis: %s", exc)

    decision = "allow" if payload.score >= 0.85 else ("deny" if payload.score < 0.40 else "step_up")
    await audit_col.insert_one(
        {
            "request_id": f"override_{uuid4().hex[:8]}",
            "session_id": f"sess_{safe_sub}",
            "subject_id": subject_id,
            "client_ip": "127.0.0.1",
            "route_id": "operator_admin",
            "resource": "user_trust:profile",
            "permission": "operator_override",
            "trust_score_before": prev_score,
            "trust_score_after": payload.score,
            "decision": decision,
            "decision_reason": f"Operator manually adjusted trust score to {payload.score:.2f}",
            "features": {},
            "shap_attributions": {},
            "latency_ms": 0.0,
            "timestamp": now,
        }
    )

    return {
        "status": "updated",
        "subject_id": subject_id,
        "score": payload.score,
    }


class ResetAllPayload(BaseModel):
    """Payload for global audit and trust reset."""

    target_score: float = Field(default=1.0, ge=0.0, le=1.0)
    clear_audit: bool = True


@router.post("/reset-all", response_model=dict[str, Any])
async def reset_all_trust_and_audit(payload: ResetAllPayload | None = None) -> dict[str, Any]:
    """Clear all audit logs from MongoDB and restore all Redis session trust scores
    to target_score (e.g. 1.0 or 0.0).
    """
    if payload is None:
        payload = ResetAllPayload(target_score=1.0, clear_audit=True)

    db = get_database()
    audit_col = db["audit_logs"]
    cleared_count = 0
    if payload.clear_audit:
        result = await audit_col.delete_many({})
        cleared_count = result.deleted_count

    settings = get_settings()
    now = datetime.now(UTC)
    try:
        redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
        )
        keys = await redis_client.keys("session:*")
        for k in keys:
            await redis_client.delete(k)
        await redis_client.delete(ACTIVE_NARROW_ZSET)

        # Initialize clean baseline session in Redis for all known personas
        decision = (
            "allow"
            if payload.target_score >= 0.85
            else ("deny" if payload.target_score < 0.40 else "step_up")
        )

        for sub in DEFAULT_SUBJECTS:
            safe_sub = sub.replace(":", "_")
            sess_key = f"session:sess_{safe_sub}:trust"
            await redis_client.hset(
                sess_key,
                mapping={
                    "current_score": str(payload.target_score),
                    "baseline_score": "1.0",
                    "request_count": "0",
                    "last_updated_ts": str(now.timestamp()),
                },
            )

            # Insert baseline audit record so user profiles display immediately
            await audit_col.insert_one(
                {
                    "request_id": f"init_{uuid4().hex[:8]}",
                    "session_id": f"sess_{safe_sub}",
                    "subject_id": sub,
                    "client_ip": "127.0.0.1",
                    "route_id": "system_init",
                    "resource": "system:baseline",
                    "permission": "view",
                    "trust_score_before": payload.target_score,
                    "trust_score_after": payload.target_score,
                    "decision": decision,
                    "decision_reason": (
                        f"System reset: trust score restored to {payload.target_score:.2f}"
                    ),
                    "features": {},
                    "shap_attributions": {},
                    "latency_ms": 0.0,
                    "timestamp": now,
                }
            )

        await redis_client.aclose()
    except Exception as exc:
        logger.warning("Could not clear/initialize Redis keys: %s", exc)

    return {
        "status": "reset",
        "cleared_audit_records": cleared_count,
        "target_score": payload.target_score,
        "message": (
            f"Audit logs cleared and all users restored to trust score {payload.target_score:.2f}."
        ),
    }
