"""FastAPI dependency injection providers for Control Plane."""

from typing import Any

from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from control_plane.db import get_database
from control_plane.repositories import ConfigRepository


def get_repository(db: AsyncIOMotorDatabase[Any] = Depends(get_database)) -> ConfigRepository:
    """Provide ConfigRepository instance backed by active database."""
    return ConfigRepository(db)
