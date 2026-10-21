"""Control Plane FastAPI application."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from shared.config import get_settings
from shared.errors import GatewayError
from shared.logging import configure_logging

from control_plane.db import close_mongo_client
from control_plane.routes import (
    audit_router,
    bundle_router,
    closed_loop_router,
    middlewares_router,
    parameters_router,
    rebac_router,
    routes_router,
    stats_router,
    upstreams_router,
    users_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application startup and shutdown lifecycle management."""
    settings = get_settings()
    configure_logging(level=settings.log_level)
    yield
    await close_mongo_client()


app = FastAPI(
    title="Zero-Trust API Gateway - Control Plane",
    description="Configuration management plane for upstreams, routes, and middlewares",
    version="0.1.0",
    lifespan=lifespan,
)

# Enable CORS for the frontend dashboard and external simulator
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# Mount API routers
app.include_router(bundle_router)
app.include_router(upstreams_router)
app.include_router(routes_router)
app.include_router(middlewares_router)
app.include_router(audit_router)
app.include_router(closed_loop_router)
app.include_router(stats_router)
app.include_router(rebac_router)
app.include_router(users_router)
app.include_router(parameters_router)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Health check endpoint for service status verification."""
    return {"status": "ok", "service": "control_plane"}


@app.exception_handler(GatewayError)
async def gateway_exception_handler(request: Request, exc: GatewayError) -> JSONResponse:
    """Standardized error handler for domain errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "details": exc.details},
    )
