"""Unit tests for AuditRepository and AuditService."""

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from audit.repository import AuditRepository
from audit.service import AuditService
from bson import ObjectId
from shared.schemas.audit import AuditRecord
from shared.schemas.decision import DecisionAction


class MockAsyncCursor:
    """Mock asynchronous cursor for Motor find operations."""

    def __init__(self, docs: list[dict[str, Any]]) -> None:
        self.docs = list(docs)
        self.index = 0

    def sort(self, *args: Any, **kwargs: Any) -> "MockAsyncCursor":
        return self

    def skip(self, *args: Any, **kwargs: Any) -> "MockAsyncCursor":
        return self

    def limit(self, *args: Any, **kwargs: Any) -> "MockAsyncCursor":
        return self

    def __aiter__(self) -> AsyncIterator[dict[str, Any]]:
        return self

    async def __anext__(self) -> dict[str, Any]:
        if self.index < len(self.docs):
            doc = self.docs[self.index]
            self.index += 1
            return doc
        raise StopAsyncIteration


def _create_sample_record(
    session_id: str = "sess_test",
    decision: DecisionAction = DecisionAction.ALLOW,
    timestamp: datetime | None = None,
) -> AuditRecord:
    """Create a sample AuditRecord for testing."""
    return AuditRecord(
        request_id="req_123",
        session_id=session_id,
        subject_id="user:alice",
        client_ip="127.0.0.1",
        route_id="route_users",
        resource="document:doc_1",
        permission="view",
        trust_score_before=1.0,
        trust_score_after=0.92,
        decision=decision,
        decision_reason="trust_score_nominal",
        features={"req_rate_10s": 1.0, "path_length": 2.0},
        shap_attributions={"req_rate_10s": 0.04},
        timestamp=timestamp or datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_audit_repository_insert_and_find() -> None:
    """Verify AuditRepository inserts and searches records with filters."""
    mock_collection = MagicMock()
    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_collection

    oid = ObjectId()
    mock_collection.insert_one = AsyncMock(return_value=MagicMock(inserted_id=oid))
    mock_collection.insert_many = AsyncMock(return_value=MagicMock(inserted_ids=[oid]))
    mock_collection.count_documents = AsyncMock(return_value=1)

    repo = AuditRepository(db=mock_db)

    # 1. Test insert_one
    record = _create_sample_record()
    res_id = await repo.insert_one(record)
    assert res_id == str(oid)
    mock_collection.insert_one.assert_called_once()

    # 2. Test insert_many
    res_ids = await repo.insert_many([record])
    assert res_ids == [str(oid)]
    mock_collection.insert_many.assert_called_once()

    # 3. Test find with filters
    doc = record.model_dump(by_alias=True)
    doc["_id"] = oid
    mock_collection.find.return_value = MockAsyncCursor([doc])

    now = datetime.now(UTC)
    results = await repo.find(
        session_id="sess_test",
        subject_id="user:alice",
        decision="allow",
        start_time=now - timedelta(minutes=5),
        end_time=now,
    )
    assert len(results) == 1
    assert results[0].session_id == "sess_test"
    assert results[0].decision == DecisionAction.ALLOW
    mock_collection.find.assert_called_once()

    # 4. Test count
    count = await repo.count(session_id="sess_test")
    assert count == 1


@pytest.mark.asyncio
async def test_audit_repository_create_indexes() -> None:
    """Verify AuditRepository creates database indexes on audit_logs."""
    mock_collection = MagicMock()
    mock_collection.create_index = AsyncMock()
    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_collection

    repo = AuditRepository(db=mock_db)
    await repo.create_indexes()
    assert mock_collection.create_index.call_count == 4


@pytest.mark.asyncio
async def test_audit_service_enqueue_and_worker_flush() -> None:
    """Verify AuditService enqueues records and background worker flushes them."""
    mock_repo = MagicMock(spec=AuditRepository)
    mock_repo.insert_many = AsyncMock(return_value=["id1", "id2"])

    service = AuditService(
        repository=mock_repo,
        queue_maxsize=10,
        batch_size=2,
        flush_interval_seconds=0.1,
    )

    service.start()
    record1 = _create_sample_record(session_id="sess_1")
    record2 = _create_sample_record(session_id="sess_2")

    # Non-blocking enqueue
    assert service.log_decision(record1) is True
    assert service.log_decision(record2) is True

    # Allow worker loop to run and flush batch of 2
    await asyncio.sleep(0.15)
    await service.stop()

    assert mock_repo.insert_many.call_count >= 1
    call_args = mock_repo.insert_many.call_args[0][0]
    assert len(call_args) >= 1


@pytest.mark.asyncio
async def test_audit_service_shutdown_flushes_remaining() -> None:
    """Verify AuditService drains remaining queue records on shutdown."""
    mock_repo = MagicMock(spec=AuditRepository)
    mock_repo.insert_many = AsyncMock(return_value=["id1"])

    service = AuditService(
        repository=mock_repo,
        queue_maxsize=10,
        batch_size=100,  # Won't trigger batch size
        flush_interval_seconds=10.0,  # Won't trigger interval
    )

    # We do not start background worker, just enqueue
    record = _create_sample_record(session_id="sess_shutdown")
    service._running = True
    service.log_decision(record)

    # Calling stop should drain remaining items
    await service.stop()

    mock_repo.insert_many.assert_called_once_with([record])


@pytest.mark.asyncio
async def test_audit_service_queue_full_drops_gracefully() -> None:
    """Verify AuditService handles full queue without raising exception."""
    mock_repo = MagicMock(spec=AuditRepository)
    service = AuditService(
        repository=mock_repo,
        queue_maxsize=1,
    )

    record1 = _create_sample_record(session_id="sess_1")
    record2 = _create_sample_record(session_id="sess_2")

    assert service.log_decision(record1) is True
    # Second should return False because queue size is 1
    assert service.log_decision(record2) is False
