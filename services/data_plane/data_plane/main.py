"""Data Plane FastAPI application and proxy gateway with Zero-Trust pipeline."""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import redis.asyncio as redis
from audit.repository import AuditRepository
from audit.service import AuditService
from decision_engine.closed_loop import ClosedLoopManager
from decision_engine.policy.spicedb import SpiceDBClient
from decision_engine.service import DecisionEngineService
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from shared.config import get_settings
from shared.errors import GatewayError
from shared.logging import configure_logging
from trust_engine.service import TrustEngineService

from data_plane.config_sync import ConfigSyncManager
from data_plane.pipeline import PipelineResult, ZeroTrustPipeline
from data_plane.proxy import ProxyEngine
from data_plane.router import GatewayRouter

logger = logging.getLogger("data_plane.main")

# Global service singletons
sync_manager = ConfigSyncManager()
router = GatewayRouter(sync_manager)
proxy_engine = ProxyEngine()
pipeline: ZeroTrustPipeline | None = None
_sweeper_task: asyncio.Task[None] | None = None


def get_pipeline() -> ZeroTrustPipeline:
    """Retrieve or lazily initialize the Zero-Trust evaluation pipeline."""
    global pipeline
    if pipeline is None:
        settings = get_settings()
        redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
        )
        spicedb_client = SpiceDBClient()
        trust_engine = TrustEngineService(
            redis_client=redis_client,
            spicedb_client=spicedb_client,
        )
        closed_loop = ClosedLoopManager(
            spicedb_client=spicedb_client,
            redis_client=redis_client,
        )
        decision_engine = DecisionEngineService(
            spicedb_client=spicedb_client,
            redis_client=redis_client,
            closed_loop=closed_loop,
        )
        audit_repo = AuditRepository()
        audit_service = AuditService(repository=audit_repo)
        pipeline = ZeroTrustPipeline(
            trust_engine=trust_engine,
            decision_engine=decision_engine,
            audit_service=audit_service,
        )
    return pipeline


def set_pipeline(new_pipeline: ZeroTrustPipeline | None) -> None:
    """Set or override the global Zero-Trust evaluation pipeline (used in testing)."""
    global pipeline
    pipeline = new_pipeline


async def _narrow_sweeper_loop(
    closed_loop: ClosedLoopManager, interval_seconds: float = 10.0
) -> None:
    """Periodically sweep and clean up expired SpiceDB narrowing restrictions."""
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            await closed_loop.sweep_expired_restrictions()
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.warning("Error in background narrow sweeper: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup and shutdown lifecycle management for Data Plane."""
    global _sweeper_task
    settings = get_settings()
    configure_logging(level=settings.log_level)

    pipe = get_pipeline()
    pipe.audit_service.start()

    # Initial sync from Control Plane
    await sync_manager.sync_once()
    # Start background 4-second polling loop
    sync_manager.start_polling()

    # Background task for sweeping expired narrow restrictions
    _sweeper_task = asyncio.create_task(_narrow_sweeper_loop(pipe.decision_engine.closed_loop))

    yield

    # Graceful shutdown
    if _sweeper_task is not None:
        _sweeper_task.cancel()
        try:
            await _sweeper_task
        except asyncio.CancelledError:
            pass
        _sweeper_task = None

    await sync_manager.stop_polling()
    await pipe.audit_service.stop()
    await proxy_engine.close()


app = FastAPI(
    title="Zero-Trust API Gateway - Data Plane",
    description="High-performance proxy gateway with dynamic routing and policy evaluation",
    version="0.1.0",
    lifespan=lifespan,
)

# Enable CORS allowing all requests, origins, methods, and headers
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, Any]:
    """Health check endpoint exposing configuration sync state."""
    bundle = sync_manager.current_bundle
    return {
        "status": "ok",
        "service": "data_plane",
        "config_version": bundle.version,
        "routes_count": len(bundle.routes),
        "upstreams_count": len(bundle.upstreams),
    }


@app.post("/internal/sync", tags=["internal"])
async def manual_sync() -> dict[str, Any]:
    """Manually trigger immediate configuration synchronization from Control Plane."""
    updated = await sync_manager.sync_once()
    bundle = sync_manager.current_bundle
    return {
        "status": "updated" if updated else "unchanged",
        "version": bundle.version,
    }


@app.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
)
async def proxy_gateway(request: Request, path: str) -> Response:
    """Catch-all proxy endpoint matching incoming requests and evaluating Zero-Trust pipeline."""
    # Preflight OPTIONS requests handled immediately
    if request.method == "OPTIONS":
        return Response(status_code=200)

    # 1. Match route
    matched = router.match(path=path, method=request.method)


    # 2. Evaluate Zero-Trust pipeline (Trust scoring, ReBAC check, Closed loop, Audit)
    pipe = get_pipeline()
    pipeline_result: PipelineResult = await pipe.evaluate_request(
        request=request, route=matched.route
    )

    if not pipeline_result.allowed:
        if pipeline_result.intercept_response is not None:
            return pipeline_result.intercept_response
        return JSONResponse(status_code=403, content={"error": "Access denied"})

    # 3. Forward to upstream target
    response = await proxy_engine.proxy_request(
        request=request,
        target_url=matched.target_url,
        timeout_ms=matched.upstream.timeout_ms,
    )

    # 4. Attach Zero-Trust trust score headers to client response
    for header_name, header_value in pipeline_result.headers.items():
        response.headers[header_name] = header_value

    return response


@app.exception_handler(GatewayError)
async def gateway_error_handler(request: Request, exc: GatewayError) -> JSONResponse:
    """Standardized error handler for domain exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "details": exc.details},
    )
