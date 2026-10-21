"""Unit tests for AsyncHttpClient."""

from unittest import mock

import httpx
import pytest
from shared.errors import UpstreamError
from shared.http import AsyncHttpClient


@pytest.mark.asyncio
async def test_client_request_success() -> None:
    """Verify successful request handling."""
    client = AsyncHttpClient(timeout_seconds=2.0)
    mock_resp = httpx.Response(status_code=200, json={"status": "ok"})

    with mock.patch("httpx.AsyncClient.request", return_value=mock_resp):
        resp = await client.request("GET", "http://test.local/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    await client.close()


@pytest.mark.asyncio
async def test_client_retry_and_failure() -> None:
    """Verify retries on connection error and eventual UpstreamError."""
    client = AsyncHttpClient(timeout_seconds=0.1, max_retries=1)

    with mock.patch(
        "httpx.AsyncClient.request",
        side_effect=httpx.ConnectError("Connection refused"),
    ):
        with pytest.raises(UpstreamError) as exc_info:
            await client.request("GET", "http://test.local/failing")
        assert exc_info.value.status_code == 504
        assert "Failed to communicate with upstream" in str(exc_info.value)

    await client.close()
