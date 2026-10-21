"""Reusable asynchronous HTTP client helper with retry and error translation."""

import asyncio
from typing import Any

import httpx

from shared.errors import UpstreamError


class AsyncHttpClient:
    """Async HTTP client wrapper providing retries, timeouts, and error handling."""

    def __init__(
        self,
        base_url: str = "",
        timeout_seconds: float = 5.0,
        max_retries: int = 2,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.base_url = base_url
        self.timeout = timeout_seconds
        self.max_retries = max_retries
        self.default_headers = headers or {}
        self._client: httpx.AsyncClient | None = None

    async def get_client(self) -> httpx.AsyncClient:
        """Return or lazily initialize httpx.AsyncClient."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
                headers=self.default_headers,
            )
        return self._client

    async def close(self) -> None:
        """Gracefully close the underlying client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json: Any = None,
        content: bytes | None = None,
    ) -> httpx.Response:
        """Execute HTTP request with automatic retries on transient connection errors."""
        client = await self.get_client()
        last_exception: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=json,
                    content=content,
                )
                return response
            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                last_exception = exc
                if attempt < self.max_retries:
                    await asyncio.sleep(0.1 * (2**attempt))
                    continue
                break
            except httpx.HTTPError as exc:
                raise UpstreamError(
                    f"HTTP error connecting to upstream: {exc}",
                    status_code=502,
                    details={"url": url, "method": method, "error": str(exc)},
                ) from exc

        msg = (
            f"Failed to communicate with upstream service after "
            f"{self.max_retries + 1} attempts: {last_exception}"
        )
        raise UpstreamError(
            msg,
            status_code=504,
            details={"url": url, "method": method, "error": str(last_exception)},
        )
