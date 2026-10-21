"""MongoDB connection lifecycle and client management using Motor."""

import logging
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from shared.config import get_settings

logger = logging.getLogger("control_plane.db")

_mongo_client: AsyncIOMotorClient[Any] | None = None


def get_mongo_client() -> AsyncIOMotorClient[Any]:
    """Retrieve the global Motor client, creating it if necessary."""
    global _mongo_client
    if _mongo_client is None:
        settings = get_settings()
        logger.info("Initializing MongoDB client for URI: %s", settings.mongo_uri)
        _mongo_client = AsyncIOMotorClient(settings.mongo_uri)
    return _mongo_client


def get_database() -> AsyncIOMotorDatabase[Any]:
    """Retrieve the active MongoDB database."""
    settings = get_settings()
    client = get_mongo_client()
    return client[settings.mongo_db_name]


async def close_mongo_client() -> None:
    """Close the global Motor client on application shutdown."""
    global _mongo_client
    if _mongo_client is not None:
        logger.info("Closing MongoDB client connection.")
        _mongo_client.close()
        _mongo_client = None
