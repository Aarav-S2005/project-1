"""Asynchronous streaming reverse proxy engine."""

import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx
from fastapi import Request
from fastapi.responses import Response, StreamingResponse
from shared.errors import UpstreamError

logger = logging.getLogger("data_plane.proxy")

# Headers that must not be blindly passed between client and upstream
HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
}


class ProxyEngine:
    """Streams requests to target upstreams and streams back responses."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._external_client = client is not None
        self._client = client or httpx.AsyncClient(
            follow_redirects=False,
            timeout=httpx.Timeout(10.0, connect=3.0),
        )

    async def close(self) -> None:
        """Close HTTP client on service shutdown."""
        if not self._external_client and not self._client.is_closed:
            await self._client.aclose()

    def _filter_headers(self, headers: Any) -> dict[str, str]:
        """Strip hop-by-hop headers."""
        filtered: dict[str, str] = {}
        for key, value in headers.items():
            k_lower = key.lower()
            if k_lower not in HOP_BY_HOP_HEADERS:
                filtered[key] = value
        return filtered

    async def proxy_request(
        self,
        request: Request,
        target_url: str,
        timeout_ms: int = 5000,
    ) -> Response:
        """Forward incoming request to target URL and return streaming response."""
        req_headers = self._filter_headers(request.headers)

        # Set standard forward headers
        client_host = request.client.host if request.client else "127.0.0.1"
        req_headers["x-forwarded-for"] = client_host
        req_headers["x-forwarded-proto"] = request.url.scheme
        req_headers["x-forwarded-host"] = request.headers.get("host", "")

        # Read request body
        body = await request.body()
        timeout_sec = max(0.1, timeout_ms / 1000.0)

        candidate_urls = [target_url]
        if "localhost" in target_url or "127.0.0.1" in target_url:
            candidate_urls.append(
                target_url.replace("localhost", "host.docker.internal").replace("127.0.0.1", "host.docker.internal")
            )
            candidate_urls.append(
                target_url.replace("localhost", "zero_trust_demo_backend").replace("127.0.0.1", "zero_trust_demo_backend")
            )

        last_connect_err: Exception | None = None
        for current_url in candidate_urls:
            try:
                req = self._client.build_request(
                    method=request.method,
                    url=current_url,
                    headers=req_headers,
                    params=request.query_params,
                    content=body if body else None,
                    timeout=timeout_sec,
                )
                upstream_resp = await self._client.send(req, stream=True)

                resp_headers = self._filter_headers(upstream_resp.headers)
                # Remove content-length and content-encoding so StreamingResponse recalculates
                resp_headers.pop("content-length", None)
                resp_headers.pop("content-encoding", None)

                async def body_stream() -> AsyncIterator[bytes]:
                    try:
                        async for chunk in upstream_resp.aiter_bytes():
                            yield chunk
                    finally:
                        await upstream_resp.aclose()

                return StreamingResponse(
                    body_stream(),
                    status_code=upstream_resp.status_code,
                    headers=resp_headers,
                    media_type=upstream_resp.headers.get("content-type"),
                )

            except httpx.ConnectError as exc:
                last_connect_err = exc
                logger.debug("Failed to connect to %s, trying next candidate if available...", current_url)
                continue

            except httpx.TimeoutException as exc:
                logger.error("Upstream timeout at %s: %s", current_url, exc)
                raise UpstreamError(
                    f"Upstream request timed out after {timeout_sec:.1f}s",
                    status_code=504,
                    details={"target_url": current_url, "timeout_seconds": timeout_sec},
                ) from exc

            except httpx.HTTPError as exc:
                logger.error("HTTP error proxying to %s: %s", current_url, exc)
                raise UpstreamError(
                    f"Upstream proxy failed: {exc}",
                    status_code=502,
                    details={"target_url": current_url, "error": str(exc)},
                ) from exc

        logger.error(
            "Connection failed to upstream at %s (tried: %s): %s",
            target_url,
            candidate_urls,
            last_connect_err,
        )
        raise UpstreamError(
            f"Could not connect to upstream service at {target_url}",
            status_code=502,
            details={"target_url": target_url, "error": str(last_connect_err)},
        )

