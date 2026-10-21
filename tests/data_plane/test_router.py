"""Unit tests for GatewayRouter prefix matching and URL resolution."""

from datetime import UTC, datetime

import pytest
from data_plane.config_sync import ConfigSyncManager
from data_plane.router import GatewayRouter
from shared.errors import GatewayError, RouteNotFoundError, UpstreamError
from shared.schemas.gateway import ConfigBundle, RouteConfig, UpstreamConfig


@pytest.fixture
def mock_sync_manager() -> ConfigSyncManager:
    """Fixture providing ConfigSyncManager with pre-populated in-memory bundle."""
    manager = ConfigSyncManager(control_plane_url="http://mock.cp")

    upstream1 = UpstreamConfig(
        id="ups_docs",
        name="Docs Service",
        target_url="http://docs.internal:8080",
    )
    upstream2 = UpstreamConfig(
        id="ups_auth",
        name="Auth Service",
        target_url="http://auth.internal:8081",
    )

    route_docs = RouteConfig(
        id="route_docs",
        upstream_id="ups_docs",
        path_prefix="/api/v1/documents",
        methods=["GET", "POST"],
        strip_path=False,
    )
    route_docs_drafts = RouteConfig(
        id="route_docs_drafts",
        upstream_id="ups_docs",
        path_prefix="/api/v1/documents/drafts",
        methods=["GET"],
        strip_path=True,
    )
    route_auth = RouteConfig(
        id="route_auth",
        upstream_id="ups_auth",
        path_prefix="/auth",
        methods=["POST"],
        strip_path=True,
    )

    manager._current_bundle = ConfigBundle(
        version=1,
        etag='"etag1"',
        updated_at=datetime.now(UTC),
        upstreams=[upstream1, upstream2],
        routes=[route_docs, route_docs_drafts, route_auth],
        middlewares=[],
    )
    manager._rebuild_indices()
    return manager


def test_exact_and_subpath_matching(mock_sync_manager: ConfigSyncManager) -> None:
    """Verify standard path matching and target URL resolution."""
    router = GatewayRouter(mock_sync_manager)

    # Exact prefix match without strip_path
    match1 = router.match(path="/api/v1/documents", method="GET")
    assert match1.route.id == "route_docs"
    assert match1.target_url == "http://docs.internal:8080/api/v1/documents"

    # Subpath match without strip_path
    match2 = router.match(path="/api/v1/documents/doc-123", method="GET")
    assert match2.route.id == "route_docs"
    assert match2.target_url == "http://docs.internal:8080/api/v1/documents/doc-123"


def test_longest_prefix_priority_and_path_stripping(mock_sync_manager: ConfigSyncManager) -> None:
    """Verify that more specific prefix wins and strip_path trims correctly."""
    router = GatewayRouter(mock_sync_manager)

    # Path /api/v1/documents/drafts/42 matches route_docs_drafts over route_docs
    match = router.match(path="/api/v1/documents/drafts/42", method="GET")
    assert match.route.id == "route_docs_drafts"
    assert match.forwarded_path == "/42"
    assert match.target_url == "http://docs.internal:8080/42"


def test_method_not_allowed(mock_sync_manager: ConfigSyncManager) -> None:
    """Verify 405 error when path matches but method is not supported."""
    router = GatewayRouter(mock_sync_manager)

    with pytest.raises(GatewayError) as exc_info:
        router.match(path="/auth", method="GET")  # route_auth only allows POST
    assert exc_info.value.status_code == 405


def test_route_not_found(mock_sync_manager: ConfigSyncManager) -> None:
    """Verify 404 RouteNotFoundError when no prefix matches."""
    router = GatewayRouter(mock_sync_manager)

    with pytest.raises(RouteNotFoundError) as exc_info:
        router.match(path="/unmapped/path", method="GET")
    assert exc_info.value.status_code == 404


def test_missing_upstream_error(mock_sync_manager: ConfigSyncManager) -> None:
    """Verify 502 UpstreamError when route points to non-existent upstream."""
    mock_sync_manager._routes_map["route_broken"] = RouteConfig(
        id="route_broken",
        upstream_id="non_existent",
        path_prefix="/broken",
        methods=["GET"],
    )
    mock_sync_manager._current_bundle.routes.append(mock_sync_manager._routes_map["route_broken"])
    router = GatewayRouter(mock_sync_manager)

    with pytest.raises(UpstreamError) as exc_info:
        router.match(path="/broken", method="GET")
    assert exc_info.value.status_code == 502
