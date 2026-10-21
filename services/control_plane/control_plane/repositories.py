"""MongoDB repository managing gateway configuration state and revisions."""

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from shared.schemas.gateway import (
    ConfigBundle,
    ConfigVersionResponse,
    MiddlewareConfig,
    RouteConfig,
    UpstreamConfig,
)


class ConfigRepository:
    """Async repository for upstreams, routes, middlewares, and version tracking."""

    def __init__(self, db: AsyncIOMotorDatabase[Any]) -> None:
        self.db = db
        self.upstreams_col = db["upstreams"]
        self.routes_col = db["routes"]
        self.middlewares_col = db["middlewares"]
        self.meta_col = db["config_meta"]

    async def get_version(self) -> ConfigVersionResponse:
        """Fetch current configuration version and timestamp."""
        doc = await self.meta_col.find_one({"_id": "global_version"})
        if not doc:
            # Initialize version to 1 if not present
            now = datetime.now(UTC)
            await self.meta_col.update_one(
                {"_id": "global_version"},
                {"$setOnInsert": {"version": 1, "updated_at": now}},
                upsert=True,
            )
            return ConfigVersionResponse(version=1, updated_at=now)

        return ConfigVersionResponse(
            version=int(doc.get("version", 1)),
            updated_at=doc.get("updated_at", datetime.now(UTC)),
        )

    async def bump_version(self) -> int:
        """Increment the global version counter and return new version."""
        now = datetime.now(UTC)
        result = await self.meta_col.find_one_and_update(
            {"_id": "global_version"},
            {"$inc": {"version": 1}, "$set": {"updated_at": now}},
            upsert=True,
            return_document=True,
        )
        if result and "version" in result:
            return int(result["version"])
        return 1

    # --- Upstreams CRUD ---
    async def list_upstreams(self) -> list[UpstreamConfig]:
        """List all configured upstream backend services."""
        cursor = self.upstreams_col.find({})
        items: list[UpstreamConfig] = []
        async for doc in cursor:
            doc["id"] = doc.pop("_id")
            items.append(UpstreamConfig(**doc))
        return items

    async def get_upstream(self, upstream_id: str) -> UpstreamConfig | None:
        """Get an upstream by ID."""
        doc = await self.upstreams_col.find_one({"_id": upstream_id})
        if not doc:
            return None
        doc["id"] = doc.pop("_id")
        return UpstreamConfig(**doc)

    async def save_upstream(self, upstream: UpstreamConfig) -> UpstreamConfig:
        """Create or update an upstream and bump configuration version."""
        data = upstream.model_dump()
        doc_id = data.pop("id")
        data["_id"] = doc_id
        data["updated_at"] = datetime.now(UTC)
        await self.upstreams_col.replace_one({"_id": doc_id}, data, upsert=True)
        await self.bump_version()
        return upstream

    async def delete_upstream(self, upstream_id: str) -> bool:
        """Delete an upstream and bump version if deleted."""
        result = await self.upstreams_col.delete_one({"_id": upstream_id})
        if result.deleted_count > 0:
            await self.bump_version()
            return True
        return False

    # --- Routes CRUD ---
    async def list_routes(self) -> list[RouteConfig]:
        """List all configured routes."""
        cursor = self.routes_col.find({})
        items: list[RouteConfig] = []
        async for doc in cursor:
            doc["id"] = doc.pop("_id")
            items.append(RouteConfig(**doc))
        return items

    async def get_route(self, route_id: str) -> RouteConfig | None:
        """Get a route by ID."""
        doc = await self.routes_col.find_one({"_id": route_id})
        if not doc:
            return None
        doc["id"] = doc.pop("_id")
        return RouteConfig(**doc)

    async def save_route(self, route: RouteConfig) -> RouteConfig:
        """Create or update a route and bump configuration version."""
        data = route.model_dump()
        doc_id = data.pop("id")
        data["_id"] = doc_id
        data["updated_at"] = datetime.now(UTC)
        await self.routes_col.replace_one({"_id": doc_id}, data, upsert=True)
        await self.bump_version()
        return route

    async def delete_route(self, route_id: str) -> bool:
        """Delete a route and bump version if deleted."""
        result = await self.routes_col.delete_one({"_id": route_id})
        if result.deleted_count > 0:
            await self.bump_version()
            return True
        return False

    # --- Middlewares CRUD ---
    async def list_middlewares(self) -> list[MiddlewareConfig]:
        """List all middlewares ordered by execution priority."""
        cursor = self.middlewares_col.find({}).sort("order", 1)
        items: list[MiddlewareConfig] = []
        async for doc in cursor:
            doc["id"] = doc.pop("_id")
            items.append(MiddlewareConfig(**doc))
        return items

    async def get_middleware(self, middleware_id: str) -> MiddlewareConfig | None:
        """Get a middleware by ID."""
        doc = await self.middlewares_col.find_one({"_id": middleware_id})
        if not doc:
            return None
        doc["id"] = doc.pop("_id")
        return MiddlewareConfig(**doc)

    async def save_middleware(self, middleware: MiddlewareConfig) -> MiddlewareConfig:
        """Create or update a middleware and bump configuration version."""
        data = middleware.model_dump()
        doc_id = data.pop("id")
        data["_id"] = doc_id
        await self.middlewares_col.replace_one({"_id": doc_id}, data, upsert=True)
        await self.bump_version()
        return middleware

    async def delete_middleware(self, middleware_id: str) -> bool:
        """Delete a middleware and bump version if deleted."""
        result = await self.middlewares_col.delete_one({"_id": middleware_id})
        if result.deleted_count > 0:
            await self.bump_version()
            return True
        return False

    # --- Compiled Bundle Generation ---
    async def compile_bundle(self) -> ConfigBundle:
        """Compile complete configuration bundle with version and ETag."""
        version_info = await self.get_version()
        upstreams = await self.list_upstreams()
        routes = await self.list_routes()
        middlewares = await self.list_middlewares()

        # Compute deterministic ETag
        content_repr = json.dumps(
            {
                "version": version_info.version,
                "upstreams": [u.model_dump(mode="json") for u in upstreams],
                "routes": [r.model_dump(mode="json") for r in routes],
                "middlewares": [m.model_dump(mode="json") for m in middlewares],
            },
            sort_keys=True,
        )
        etag = hashlib.sha256(content_repr.encode("utf-8")).hexdigest()[:16]

        return ConfigBundle(
            version=version_info.version,
            etag=f'"{etag}"',
            updated_at=version_info.updated_at,
            upstreams=upstreams,
            routes=routes,
            middlewares=middlewares,
        )
