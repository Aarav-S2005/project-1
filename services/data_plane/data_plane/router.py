"""High-performance route matching and target URL resolution."""

from dataclasses import dataclass

from fastapi import status
from shared.errors import GatewayError, RouteNotFoundError, UpstreamError
from shared.schemas.gateway import RouteConfig, UpstreamConfig

from data_plane.config_sync import ConfigSyncManager


@dataclass
class MatchedRoute:
    """Resolved routing target and path for an incoming request."""

    route: RouteConfig
    upstream: UpstreamConfig
    target_url: str
    forwarded_path: str


class GatewayRouter:
    """Matches incoming HTTP requests against active routes and upstreams."""

    def __init__(self, sync_manager: ConfigSyncManager) -> None:
        self.sync_manager = sync_manager

    def match(self, path: str, method: str) -> MatchedRoute:
        """Find the best matching route for the given request path and method.

        Applies longest-prefix matching.
        Raises:
            RouteNotFoundError: If no configured route matches the path prefix.
            GatewayError: If path matches but method is not permitted (405).
            UpstreamError: If the route's target upstream cannot be resolved.
        """
        # Ensure path starts with leading slash
        norm_path = "/" + path.lstrip("/")
        routes = self.sync_manager.get_all_routes()

        matched_route: RouteConfig | None = None
        longest_prefix_len = -1
        method_matched = False

        for route in routes:
            prefix = "/" + route.path_prefix.strip("/")
            # Check if norm_path matches or is a subpath of prefix
            if norm_path == prefix or norm_path.startswith(prefix + "/"):
                if len(prefix) > longest_prefix_len:
                    longest_prefix_len = len(prefix)
                    matched_route = route
                    method_matched = method.upper() in [m.upper() for m in route.methods]

        if matched_route is None:
            raise RouteNotFoundError(path=norm_path, method=method)

        if not method_matched:
            raise GatewayError(
                f"Method '{method}' not allowed for route '{matched_route.id}'",
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                details={"path": norm_path, "method": method, "allowed": matched_route.methods},
            )

        upstream = self.sync_manager.get_upstream(matched_route.upstream_id)
        if upstream is None:
            msg = (
                f"Upstream '{matched_route.upstream_id}' configured "
                f"on route '{matched_route.id}' not found"
            )
            raise UpstreamError(msg, status_code=status.HTTP_502_BAD_GATEWAY)

        # Compute forwarded path
        if matched_route.strip_path:
            prefix = "/" + matched_route.path_prefix.strip("/")
            stripped = norm_path[len(prefix) :]
            forwarded_path = "/" + stripped.lstrip("/")
        else:
            forwarded_path = norm_path

        base_url = upstream.target_url.rstrip("/")
        target_url = f"{base_url}{forwarded_path}"

        return MatchedRoute(
            route=matched_route,
            upstream=upstream,
            target_url=target_url,
            forwarded_path=forwarded_path,
        )
