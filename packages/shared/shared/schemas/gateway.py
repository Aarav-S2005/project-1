"""Gateway configuration models for Upstreams, Routes, and Middlewares."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class UpstreamConfig(BaseModel):
    """Configuration for an upstream backend service."""

    id: str = Field(description="Unique upstream identifier")
    name: str = Field(description="Human-readable upstream name")
    target_url: str = Field(description="Target base URL, e.g. http://localhost:8080")
    timeout_ms: int = Field(
        default=5000, ge=100, le=60000, description="Request timeout in milliseconds"
    )
    health_check_path: str = Field(default="/healthz", description="Upstream healthcheck endpoint")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RouteConfig(BaseModel):
    """Routing rule mapping path and method to upstream with ReBAC metadata."""

    id: str = Field(description="Unique route identifier")
    upstream_id: str = Field(description="Target upstream ID")
    path_prefix: str = Field(description="Path prefix to match, e.g. /api/v1/documents")
    methods: list[str] = Field(
        default=["GET", "POST", "PUT", "DELETE"], description="Allowed HTTP methods"
    )
    strip_path: bool = Field(default=False, description="Strip prefix before proxying to upstream")
    auth_required: bool = Field(default=True, description="Enforce authentication and trust checks")
    resource_type: str = Field(default="document", description="SpiceDB resource type")
    resource_id_extractor: str = Field(
        default="path_param:id",
        description="Rule to extract resource ID (e.g. path_param:id, query:id, header:X-ID)",
    )
    permission_mapping: dict[str, str] = Field(
        default_factory=lambda: {
            "GET": "view",
            "POST": "create",
            "PUT": "edit",
            "DELETE": "delete",
        },
        description="Mapping from HTTP method to SpiceDB permission",
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MiddlewareConfig(BaseModel):
    """Configuration for a gateway middleware."""

    id: str = Field(description="Unique middleware identifier")
    name: str = Field(description="Middleware name")
    type: str = Field(description="Middleware type identifier, e.g. trust_score_evaluator")
    order: int = Field(default=1, description="Execution priority order")
    config: dict[str, Any] = Field(default_factory=dict, description="Custom middleware parameters")
    is_active: bool = Field(default=True, description="Whether middleware is enabled")


class ConfigVersionResponse(BaseModel):
    """Lightweight response for version polling."""

    version: int = Field(description="Monotonically increasing configuration revision")
    updated_at: datetime = Field(description="Timestamp of last configuration modification")


class ConfigBundle(BaseModel):
    """Complete compiled configuration bundle fetched by the Data Plane."""

    version: int = Field(description="Configuration revision number")
    etag: str = Field(description="Hash/ETag representation of bundle state")
    updated_at: datetime = Field(description="Timestamp of bundle build")
    upstreams: list[UpstreamConfig] = Field(default_factory=list)
    routes: list[RouteConfig] = Field(default_factory=list)
    middlewares: list[MiddlewareConfig] = Field(default_factory=list)
