"""Unit and integration tests for Data Plane proxy engine and main app."""

from datetime import UTC, datetime
from typing import Any

import data_plane.main as dp_module
import httpx
import pytest
from data_plane.proxy import ProxyEngine
from fastapi import FastAPI
from fastapi import Request as FastAPIRequest
from httpx import ASGITransport, AsyncClient, MockTransport, Request, Response
from shared.errors import UpstreamError
from shared.schemas.gateway import ConfigBundle, RouteConfig, UpstreamConfig


@pytest.fixture
def mock_upstream_client() -> AsyncClient:
    """Fixture providing mock client that acts as upstream backend service."""

    def upstream_handler(request: Request) -> Response:
        # Echo path, method, headers, and body back to caller
        if request.url.path == "/backend/data":
            headers = {
                "X-Upstream-Header": "served-from-backend",
                "Content-Type": "application/json",
            }
            return Response(
                200,
                headers=headers,
                json={"echo_method": request.method, "url": str(request.url)},
            )
        if request.url.path == "/backend/timeout":
            raise httpx.ReadTimeout("Mock upstream read timed out")
        if request.url.path == "/backend/fail":
            raise httpx.ConnectError("Mock upstream connection refused")
        return Response(404, json={"error": "not found on upstream"})

    transport = MockTransport(upstream_handler)
    return AsyncClient(transport=transport)


@pytest.mark.asyncio
async def test_proxy_engine_direct_success(mock_upstream_client: AsyncClient) -> None:
    """Verify ProxyEngine correctly streams request to target URL."""
    proxy = ProxyEngine(client=mock_upstream_client)

    app = FastAPI()

    @app.api_route("/dummy", methods=["GET"])
    async def dummy(req: FastAPIRequest) -> Any:
        return await proxy.proxy_request(req, target_url="http://upstream.local/backend/data")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/dummy?param=123", headers={"X-Client-Id": "client-1"})
        assert resp.status_code == 200
        assert resp.headers.get("x-upstream-header") == "served-from-backend"
        data = resp.json()
        assert data["echo_method"] == "GET"
        assert "param=123" in data["url"]


@pytest.mark.asyncio
async def test_proxy_engine_upstream_connection_error(mock_upstream_client: AsyncClient) -> None:
    """Verify ProxyEngine raises 502 UpstreamError when upstream is unreachable."""
    proxy = ProxyEngine(client=mock_upstream_client)

    app = FastAPI()

    @app.api_route("/fail", methods=["GET"])
    async def fail_route(req: FastAPIRequest) -> Any:
        return await proxy.proxy_request(req, target_url="http://upstream.local/backend/fail")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        with pytest.raises(UpstreamError) as exc_info:
            await client.get("/fail")
        assert exc_info.value.status_code == 502


@pytest.mark.asyncio
async def test_data_plane_app_end_to_end() -> None:
    """Verify Data Plane FastAPI application routes, health check, and dynamic proxying."""
    dp_module.sync_manager._current_bundle = ConfigBundle(
        version=10,
        etag='"etag10"',
        updated_at=datetime.now(UTC),
        upstreams=[
            UpstreamConfig(
                id="ups_test", name="Test Ups", target_url="http://backend.internal/backend"
            )
        ],
        routes=[
            RouteConfig(
                id="r_test",
                upstream_id="ups_test",
                path_prefix="/api/test",
                methods=["GET"],
                strip_path=True,
                auth_required=False,
            )
        ],
        middlewares=[],
    )
    dp_module.sync_manager._rebuild_indices()

    def upstream_handler(request: Request) -> Response:
        if request.url.path == "/backend/data":
            return Response(200, json={"message": "proxied successfully"})
        return Response(404)

    mock_client = AsyncClient(transport=MockTransport(upstream_handler))
    dp_module.proxy_engine._client = mock_client

    transport = ASGITransport(app=dp_module.app)
    async with AsyncClient(transport=transport, base_url="http://testgateway") as client:
        # Test health check
        health_resp = await client.get("/health")
        assert health_resp.status_code == 200
        health_data = health_resp.json()
        assert health_data["service"] == "data_plane"
        assert health_data["config_version"] == 10

        # Test proxy catch-all: /api/test/data -> forwarded to /backend/data
        proxy_resp = await client.get("/api/test/data")
        assert proxy_resp.status_code == 200
        assert proxy_resp.json() == {"message": "proxied successfully"}

        # Test 404 on unmapped route
        missing_resp = await client.get("/unmapped/path")
        assert missing_resp.status_code == 404
        assert "No route matching" in missing_resp.json()["error"]
