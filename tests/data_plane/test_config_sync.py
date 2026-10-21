"""Unit tests for ConfigSyncManager background polling and cache resilience."""

from datetime import UTC, datetime

import httpx
import pytest
from data_plane.config_sync import ConfigSyncManager
from shared.schemas.gateway import ConfigBundle, RouteConfig, UpstreamConfig


@pytest.mark.asyncio
async def test_sync_once_success_and_etag_caching() -> None:
    """Verify successful bundle fetch and subsequent 304 Not Modified caching."""
    upstream = UpstreamConfig(
        id="ups_1",
        name="Test Upstream",
        target_url="http://backend:8080",
    )
    route = RouteConfig(
        id="r_1",
        upstream_id="ups_1",
        path_prefix="/test",
        methods=["GET"],
    )
    bundle_data = {
        "version": 1,
        "etag": '"etag_abc"',
        "updated_at": datetime.now(UTC).isoformat(),
        "upstreams": [upstream.model_dump(mode="json")],
        "routes": [route.model_dump(mode="json")],
        "middlewares": [],
    }

    # Mock handler simulating Control Plane responses
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/config/version":
            payload = {"version": 1, "updated_at": datetime.now(UTC).isoformat()}
            return httpx.Response(200, json=payload)
        if request.url.path == "/api/v1/config/bundle":
            if request.headers.get("if-none-match") == '"etag_abc"':
                return httpx.Response(304)
            return httpx.Response(200, json=bundle_data)
        return httpx.Response(404)

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    manager = ConfigSyncManager(
        control_plane_url="http://control-plane",
        poll_interval_seconds=4,
        http_client=mock_client,
    )

    # First sync: version is 1, updates config
    updated = await manager.sync_once()
    assert updated is True
    assert manager.current_bundle.version == 1
    assert manager.get_upstream("ups_1") is not None
    assert manager.get_route("r_1") is not None

    # Second sync with same remote version: returns False, no network bundle call needed
    updated_again = await manager.sync_once()
    assert updated_again is False

    await manager.stop_polling()


@pytest.mark.asyncio
async def test_control_plane_offline_fallback() -> None:
    """Verify data plane retains last-known-good config when control plane is down."""
    # Start with pre-loaded last known good config
    manager = ConfigSyncManager(
        control_plane_url="http://control-plane",
        poll_interval_seconds=4,
    )
    manager._current_bundle = ConfigBundle(
        version=5,
        etag='"lkg_etag"',
        updated_at=datetime.now(UTC),
        upstreams=[UpstreamConfig(id="ups_lkg", name="LKG", target_url="http://lkg:8080")],
        routes=[],
        middlewares=[],
    )
    manager._rebuild_indices()

    # Transport that throws ConnectError simulating down Control Plane
    def failing_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused to control plane")

    manager._client = httpx.AsyncClient(transport=httpx.MockTransport(failing_handler))

    # Sync fails gracefully without raising exception
    updated = await manager.sync_once()
    assert updated is False
    # Still serves with last-known-good configuration v5!
    assert manager.current_bundle.version == 5
    assert manager.get_upstream("ups_lkg") is not None

    await manager.stop_polling()
