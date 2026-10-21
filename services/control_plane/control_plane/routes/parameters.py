"""Trust score parameters management endpoint for dynamic runtime tuning."""

import logging
from typing import Any

import redis.asyncio as redis
from fastapi import APIRouter
from pydantic import BaseModel, Field
from shared.config import get_settings

logger = logging.getLogger("control_plane.routes.parameters")

router = APIRouter(prefix="/api/v1/trust/parameters", tags=["parameters"])

REDIS_PARAMS_KEY = "trust:runtime_parameters"


class TrustParametersPayload(BaseModel):
    """Dynamic parameters for trust scoring and decision engine."""

    half_life_seconds: float = Field(default=300.0, ge=10.0, le=3600.0)
    anomaly_weight: float = Field(default=0.4, ge=0.01, le=2.0)
    narrow_band_threshold: float = Field(default=0.85, ge=0.1, le=1.0)
    step_up_band_threshold: float = Field(default=0.60, ge=0.05, le=1.0)
    narrow_ttl_seconds: int = Field(default=60, ge=5, le=3600)


@router.get("", response_model=dict[str, Any])
async def get_parameters() -> dict[str, Any]:
    """Get active trust parameters from Redis with settings fallback."""
    settings = get_settings()
    client = redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        password=settings.redis_password,
    )
    try:
        raw = await client.hgetall(REDIS_PARAMS_KEY)
        return {
            "half_life_seconds": float(
                raw.get(b"half_life_seconds", settings.trust_half_life_seconds)
            ),
            "anomaly_weight": float(raw.get(b"anomaly_weight", settings.trust_anomaly_weight)),
            "narrow_band_threshold": float(
                raw.get(b"narrow_band_threshold", settings.band_threshold_narrow)
            ),
            "step_up_band_threshold": float(
                raw.get(b"step_up_band_threshold", settings.band_threshold_step_up)
            ),
            "narrow_ttl_seconds": int(raw.get(b"narrow_ttl_seconds", settings.narrow_ttl_seconds)),
        }
    finally:
        await client.aclose()


@router.put("", response_model=dict[str, Any])
async def update_parameters(payload: TrustParametersPayload) -> dict[str, Any]:
    """Update runtime trust scoring parameters in Redis."""
    settings = get_settings()
    client = redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        password=settings.redis_password,
    )
    try:
        mapping: dict[Any, Any] = {
            "half_life_seconds": str(payload.half_life_seconds),
            "anomaly_weight": str(payload.anomaly_weight),
            "narrow_band_threshold": str(payload.narrow_band_threshold),
            "step_up_band_threshold": str(payload.step_up_band_threshold),
            "narrow_ttl_seconds": str(payload.narrow_ttl_seconds),
        }
        await client.hset(REDIS_PARAMS_KEY, mapping=mapping)
        return {"status": "updated", "parameters": payload.model_dump()}
    finally:
        await client.aclose()
