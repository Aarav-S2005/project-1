"""Pytest fixtures for Trust Engine tests."""

from collections.abc import AsyncIterator

import fakeredis.aioredis
import pytest
import redis.asyncio as redis


@pytest.fixture
async def fake_redis() -> AsyncIterator[redis.Redis]:
    """Fixture providing an in-memory asynchronous fake Redis client."""
    client = fakeredis.aioredis.FakeRedis()
    yield client
    await client.flushall()
    await client.aclose()
