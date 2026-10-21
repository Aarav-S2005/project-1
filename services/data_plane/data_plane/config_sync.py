"""Background configuration synchronization manager polling Control Plane every 4 seconds."""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from shared.config import get_settings
from shared.schemas.gateway import ConfigBundle, RouteConfig, UpstreamConfig

logger = logging.getLogger("data_plane.config_sync")


class ConfigSyncManager:
    """Manages periodic polling of Control Plane and maintains in-memory routing tables."""

    def __init__(
        self,
        control_plane_url: str | None = None,
        poll_interval_seconds: int | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        settings = get_settings()
        self.control_plane_url = (control_plane_url or settings.control_plane_url).rstrip("/")
        self.poll_interval = poll_interval_seconds or settings.config_poll_interval_seconds
        self._external_client = http_client is not None
        self._client = http_client or httpx.AsyncClient(timeout=3.0)

        # In-memory last-known-good configuration state
        self._current_bundle: ConfigBundle = ConfigBundle(
            version=0,
            etag='""',
            updated_at=datetime.now(UTC),
            upstreams=[],
            routes=[],
            middlewares=[],
        )
        self._upstreams_map: dict[str, UpstreamConfig] = {}
        self._routes_map: dict[str, RouteConfig] = {}
        self._poller_task: asyncio.Task[Any] | None = None
        self._running = False

    @property
    def current_bundle(self) -> ConfigBundle:
        """Return the current active configuration bundle."""
        return self._current_bundle

    def get_upstream(self, upstream_id: str) -> UpstreamConfig | None:
        """Find an upstream by its ID."""
        return self._upstreams_map.get(upstream_id)

    def get_route(self, route_id: str) -> RouteConfig | None:
        """Find a route by its ID."""
        return self._routes_map.get(route_id)

    def get_all_routes(self) -> list[RouteConfig]:
        """Return all active routes for route matching."""
        return self._current_bundle.routes

    def _rebuild_indices(self) -> None:
        """Rebuild internal fast lookup maps from current bundle."""
        self._upstreams_map = {u.id: u for u in self._current_bundle.upstreams}
        self._routes_map = {r.id: r for r in self._current_bundle.routes}

    async def sync_once(self) -> bool:
        """Query Control Plane for configuration updates and apply if changed."""
        version_url = f"{self.control_plane_url}/api/v1/config/version"
        bundle_url = f"{self.control_plane_url}/api/v1/config/bundle"

        try:
            v_resp = await self._client.get(version_url)
            if v_resp.status_code != 200:
                logger.warning(
                    "Control plane version check returned status %d. "
                    "Retaining last-known-good config.",
                    v_resp.status_code,
                )
                return False

            v_data = v_resp.json()
            remote_version = int(v_data.get("version", 0))

            if remote_version <= self._current_bundle.version and self._current_bundle.version > 0:
                # No change needed
                return False

            headers = {}
            if self._current_bundle.etag and self._current_bundle.etag != '""':
                headers["If-None-Match"] = self._current_bundle.etag

            b_resp = await self._client.get(bundle_url, headers=headers)
            if b_resp.status_code == 304:
                return False

            if b_resp.status_code == 200:
                new_bundle = ConfigBundle(**b_resp.json())
                self._current_bundle = new_bundle
                self._rebuild_indices()
                logger.info(
                    "Successfully updated configuration to version %d (routes: %d, upstreams: %d)",
                    new_bundle.version,
                    len(new_bundle.routes),
                    len(new_bundle.upstreams),
                )
                return True

            logger.warning(
                "Unexpected status %d fetching bundle from %s",
                b_resp.status_code,
                bundle_url,
            )
            return False

        except httpx.HTTPError as exc:
            logger.warning(
                "Failed to reach Control Plane at %s (%s). "
                "Serving with last-known-good config (v%d).",
                self.control_plane_url,
                exc,
                self._current_bundle.version,
            )
            return False

    async def _poll_loop(self) -> None:
        """Continuously poll Control Plane at configured intervals."""
        while self._running:
            await self.sync_once()
            try:
                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                break

    def start_polling(self) -> None:
        """Start the background polling task."""
        if self._poller_task is None or self._poller_task.done():
            self._running = True
            self._poller_task = asyncio.create_task(self._poll_loop())
            logger.info(
                "Started background config sync task (polling every %ds from %s)",
                self.poll_interval,
                self.control_plane_url,
            )

    async def stop_polling(self) -> None:
        """Stop background poller and close client."""
        self._running = False
        if self._poller_task and not self._poller_task.done():
            self._poller_task.cancel()
            try:
                await self._poller_task
            except asyncio.CancelledError:
                pass
            self._poller_task = None

        if not self._external_client and not self._client.is_closed:
            await self._client.aclose()
