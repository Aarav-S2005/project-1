"""Pytest fixtures for Control Plane testing."""

import hashlib
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from control_plane.deps import get_repository
from control_plane.main import app
from control_plane.repositories import ConfigRepository
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from shared.schemas.gateway import (
    ConfigBundle,
    ConfigVersionResponse,
    MiddlewareConfig,
    RouteConfig,
    UpstreamConfig,
)


class InMemoryConfigRepository(ConfigRepository):
    """In-memory implementation of ConfigRepository for isolated testing."""

    def __init__(self) -> None:
        self.version = 1
        self.version_updated_at = datetime.now(UTC)
        self.upstreams: dict[str, UpstreamConfig] = {}
        self.routes: dict[str, RouteConfig] = {}
        self.middlewares: dict[str, MiddlewareConfig] = {}

    async def get_version(self) -> ConfigVersionResponse:
        return ConfigVersionResponse(version=self.version, updated_at=self.version_updated_at)

    async def bump_version(self) -> int:
        self.version += 1
        self.version_updated_at = datetime.now(UTC)
        return self.version

    async def list_upstreams(self) -> list[UpstreamConfig]:
        return list(self.upstreams.values())

    async def get_upstream(self, upstream_id: str) -> UpstreamConfig | None:
        return self.upstreams.get(upstream_id)

    async def save_upstream(self, upstream: UpstreamConfig) -> UpstreamConfig:
        self.upstreams[upstream.id] = upstream
        await self.bump_version()
        return upstream

    async def delete_upstream(self, upstream_id: str) -> bool:
        if upstream_id in self.upstreams:
            del self.upstreams[upstream_id]
            await self.bump_version()
            return True
        return False

    async def list_routes(self) -> list[RouteConfig]:
        return list(self.routes.values())

    async def get_route(self, route_id: str) -> RouteConfig | None:
        return self.routes.get(route_id)

    async def save_route(self, route: RouteConfig) -> RouteConfig:
        self.routes[route.id] = route
        await self.bump_version()
        return route

    async def delete_route(self, route_id: str) -> bool:
        if route_id in self.routes:
            del self.routes[route_id]
            await self.bump_version()
            return True
        return False

    async def list_middlewares(self) -> list[MiddlewareConfig]:
        sorted_items = sorted(self.middlewares.values(), key=lambda m: m.order)
        return sorted_items

    async def get_middleware(self, middleware_id: str) -> MiddlewareConfig | None:
        return self.middlewares.get(middleware_id)

    async def save_middleware(self, middleware: MiddlewareConfig) -> MiddlewareConfig:
        self.middlewares[middleware.id] = middleware
        await self.bump_version()
        return middleware

    async def delete_middleware(self, middleware_id: str) -> bool:
        if middleware_id in self.middlewares:
            del self.middlewares[middleware_id]
            await self.bump_version()
            return True
        return False

    async def compile_bundle(self) -> ConfigBundle:
        upstreams = await self.list_upstreams()
        routes = await self.list_routes()
        middlewares = await self.list_middlewares()

        content_repr = json.dumps(
            {
                "version": self.version,
                "upstreams": [u.model_dump(mode="json") for u in upstreams],
                "routes": [r.model_dump(mode="json") for r in routes],
                "middlewares": [m.model_dump(mode="json") for m in middlewares],
            },
            sort_keys=True,
        )
        etag = hashlib.sha256(content_repr.encode("utf-8")).hexdigest()[:16]

        return ConfigBundle(
            version=self.version,
            etag=f'"{etag}"',
            updated_at=self.version_updated_at,
            upstreams=upstreams,
            routes=routes,
            middlewares=middlewares,
        )


@pytest.fixture
def mock_repo() -> InMemoryConfigRepository:
    """Fixture providing clean InMemoryConfigRepository."""
    return InMemoryConfigRepository()


@pytest.fixture
def test_app(mock_repo: InMemoryConfigRepository) -> FastAPI:
    """Fixture providing FastAPI application with mocked repository."""
    app.dependency_overrides[get_repository] = lambda: mock_repo
    return app


@pytest.fixture
async def client(test_app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Async test client bound to FastAPI application."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    test_app.dependency_overrides.clear()
