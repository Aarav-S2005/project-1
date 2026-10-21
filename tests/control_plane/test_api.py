"""Comprehensive tests for Control Plane REST API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient) -> None:
    """Verify /health endpoint returns status ok."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "service": "control_plane"}


@pytest.mark.asyncio
async def test_upstreams_crud(client: AsyncClient) -> None:
    """Verify full CRUD lifecycle for upstreams."""
    upstream_payload = {
        "id": "ups_docs",
        "name": "Document Service",
        "target_url": "http://localhost:8081",
        "timeout_ms": 4000,
        "health_check_path": "/healthz",
    }

    # Create upstream
    create_resp = await client.post("/api/v1/upstreams", json=upstream_payload)
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    assert created_data["id"] == "ups_docs"
    assert created_data["timeout_ms"] == 4000

    # Conflict on duplicate ID
    dup_resp = await client.post("/api/v1/upstreams", json=upstream_payload)
    assert dup_resp.status_code == 409

    # Get upstream
    get_resp = await client.get("/api/v1/upstreams/ups_docs")
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Document Service"

    # List upstreams
    list_resp = await client.get("/api/v1/upstreams")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    # Update upstream
    upstream_payload["name"] = "Updated Document Service"
    upstream_payload["timeout_ms"] = 6000
    update_resp = await client.put("/api/v1/upstreams/ups_docs", json=upstream_payload)
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Updated Document Service"

    # Delete upstream
    del_resp = await client.delete("/api/v1/upstreams/ups_docs")
    assert del_resp.status_code == 204

    # 404 after deletion
    not_found_resp = await client.get("/api/v1/upstreams/ups_docs")
    assert not_found_resp.status_code == 404


@pytest.mark.asyncio
async def test_routes_crud_and_upstream_validation(client: AsyncClient) -> None:
    """Verify route operations and upstream reference validation."""
    # Attempting to create route with non-existent upstream fails with 400
    route_payload = {
        "id": "route_doc_view",
        "upstream_id": "non_existent_ups",
        "path_prefix": "/api/v1/documents",
        "methods": ["GET"],
        "strip_path": False,
        "auth_required": True,
        "resource_type": "document",
        "resource_id_extractor": "path_param:id",
    }
    fail_resp = await client.post("/api/v1/routes", json=route_payload)
    assert fail_resp.status_code == 400
    assert "does not exist" in fail_resp.json()["detail"]

    # Create the upstream first
    await client.post(
        "/api/v1/upstreams",
        json={
            "id": "ups_1",
            "name": "Backend 1",
            "target_url": "http://localhost:8080",
        },
    )

    # Now create route with valid upstream
    route_payload["upstream_id"] = "ups_1"
    create_resp = await client.post("/api/v1/routes", json=route_payload)
    assert create_resp.status_code == 201
    assert create_resp.json()["id"] == "route_doc_view"

    # List routes
    list_resp = await client.get("/api/v1/routes")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    # Update route
    route_payload["methods"] = ["GET", "POST"]
    update_resp = await client.put("/api/v1/routes/route_doc_view", json=route_payload)
    assert update_resp.status_code == 200
    assert "POST" in update_resp.json()["methods"]

    # Delete route
    del_resp = await client.delete("/api/v1/routes/route_doc_view")
    assert del_resp.status_code == 204


@pytest.mark.asyncio
async def test_middlewares_crud(client: AsyncClient) -> None:
    """Verify middleware creation and priority ordering."""
    m1 = {
        "id": "mid_trust",
        "name": "Trust Scorer",
        "type": "trust_evaluator",
        "order": 2,
        "config": {"threshold": 0.8},
        "is_active": True,
    }
    m2 = {
        "id": "mid_auth",
        "name": "Auth Extractor",
        "type": "auth_extractor",
        "order": 1,
        "config": {},
        "is_active": True,
    }

    # Create in reverse order
    await client.post("/api/v1/middlewares", json=m1)
    await client.post("/api/v1/middlewares", json=m2)

    # Listing should return sorted by order (m2 order 1, m1 order 2)
    list_resp = await client.get("/api/v1/middlewares")
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert len(items) == 2
    assert items[0]["id"] == "mid_auth"
    assert items[1]["id"] == "mid_trust"


@pytest.mark.asyncio
async def test_config_version_and_bundle_caching(client: AsyncClient) -> None:
    """Verify version bumping and ETag 304 Not Modified caching on bundle endpoint."""
    # Initial version
    v_resp1 = await client.get("/api/v1/config/version")
    assert v_resp1.status_code == 200
    v1 = v_resp1.json()["version"]

    # Initial bundle
    b_resp1 = await client.get("/api/v1/config/bundle")
    assert b_resp1.status_code == 200
    etag1 = b_resp1.headers.get("ETag")
    assert etag1 is not None

    # Conditional request with matching ETag returns 304 Not Modified
    b_cached = await client.get("/api/v1/config/bundle", headers={"If-None-Match": etag1})
    assert b_cached.status_code == 304

    # Create an upstream -> triggers version bump
    await client.post(
        "/api/v1/upstreams",
        json={
            "id": "ups_new",
            "name": "New Upstream",
            "target_url": "http://localhost:9000",
        },
    )

    # Version should have increased
    v_resp2 = await client.get("/api/v1/config/version")
    v2 = v_resp2.json()["version"]
    assert v2 > v1

    # Request with old ETag now returns 200 with new bundle
    b_resp2 = await client.get("/api/v1/config/bundle", headers={"If-None-Match": etag1})
    assert b_resp2.status_code == 200
    etag2 = b_resp2.headers.get("ETag")
    assert etag2 != etag1
    assert len(b_resp2.json()["upstreams"]) == 1
