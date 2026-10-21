"""MongoDB repository for persisting and querying immutable audit logs."""

import logging
from datetime import datetime
from typing import Any

import pymongo
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from shared.config import get_settings
from shared.schemas.audit import AuditRecord

logger = logging.getLogger("audit.repository")


class AuditRepository:
    """MongoDB repository for storing and retrieving decision audit records."""

    def __init__(
        self,
        db: AsyncIOMotorDatabase[Any] | None = None,
        mongo_uri: str | None = None,
        db_name: str | None = None,
    ) -> None:
        self._client: AsyncIOMotorClient[Any] | None = None
        if db is not None:
            self.db = db
        else:
            settings = get_settings()
            uri = mongo_uri or settings.mongo_uri
            database_name = db_name or settings.mongo_db_name
            self._client = AsyncIOMotorClient(uri)
            self.db = self._client[database_name]

        self.collection = self.db["audit_logs"]

    async def create_indexes(self) -> None:
        """Create database indexes for optimized audit search and filtering."""
        await self.collection.create_index([("timestamp", pymongo.DESCENDING)])
        await self.collection.create_index([("session_id", pymongo.ASCENDING)])
        await self.collection.create_index([("subject_id", pymongo.ASCENDING)])
        await self.collection.create_index([("decision", pymongo.ASCENDING)])
        logger.info("Created indexes on audit_logs collection.")

    async def insert_one(self, record: AuditRecord) -> str:
        """Insert a single audit record into MongoDB."""
        doc = record.model_dump(by_alias=True, exclude_none=True)
        if "_id" in doc and doc["_id"] is None:
            del doc["_id"]

        result = await self.collection.insert_one(doc)
        inserted_id = str(result.inserted_id)
        logger.debug("Persisted audit record with id: %s", inserted_id)
        return inserted_id

    async def insert_many(self, records: list[AuditRecord]) -> list[str]:
        """Batch insert multiple audit records into MongoDB."""
        if not records:
            return []

        docs = []
        for record in records:
            doc = record.model_dump(by_alias=True, exclude_none=True)
            if "_id" in doc and doc["_id"] is None:
                del doc["_id"]
            docs.append(doc)

        result = await self.collection.insert_many(docs)
        inserted_ids = [str(oid) for oid in result.inserted_ids]
        logger.debug("Batch inserted %d audit records.", len(inserted_ids))
        return inserted_ids

    async def find(
        self,
        session_id: str | None = None,
        subject_id: str | None = None,
        decision: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
        skip: int = 0,
    ) -> list[AuditRecord]:
        """Query audit records with optional filters, sorted by timestamp descending."""
        query: dict[str, Any] = {}
        if session_id:
            query["session_id"] = session_id
        if subject_id:
            query["subject_id"] = subject_id
        if decision:
            query["decision"] = decision

        if start_time or end_time:
            time_filter: dict[str, datetime] = {}
            if start_time:
                time_filter["$gte"] = start_time
            if end_time:
                time_filter["$lte"] = end_time
            query["timestamp"] = time_filter

        cursor = (
            self.collection.find(query)
            .sort("timestamp", pymongo.DESCENDING)
            .skip(skip)
            .limit(limit)
        )

        records: list[AuditRecord] = []
        async for doc in cursor:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            records.append(AuditRecord.model_validate(doc))

        return records

    async def count(
        self,
        session_id: str | None = None,
        subject_id: str | None = None,
        decision: str | None = None,
    ) -> int:
        """Count audit records matching the specified filters."""
        query: dict[str, Any] = {}
        if session_id:
            query["session_id"] = session_id
        if subject_id:
            query["subject_id"] = subject_id
        if decision:
            query["decision"] = decision

        count: int = await self.collection.count_documents(query)
        return count

    def close(self) -> None:
        """Close MongoDB client connection if owned by repository."""
        if self._client is not None:
            self._client.close()
