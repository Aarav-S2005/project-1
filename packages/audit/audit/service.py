"""Asynchronous audit logger service buffering records in-memory and batching to MongoDB."""

import asyncio
import logging
from datetime import datetime

from shared.schemas.audit import AuditRecord

from audit.repository import AuditRepository

logger = logging.getLogger("audit.service")


class AuditService:
    """Asynchronously buffers and batches audit records to avoid database latency
    in the proxy request path.
    """

    def __init__(
        self,
        repository: AuditRepository,
        queue_maxsize: int = 10000,
        batch_size: int = 50,
        flush_interval_seconds: float = 0.5,
    ) -> None:
        self.repository = repository
        self.batch_size = batch_size
        self.flush_interval_seconds = flush_interval_seconds
        self.queue: asyncio.Queue[AuditRecord] = asyncio.Queue(maxsize=queue_maxsize)
        self._worker_task: asyncio.Task[None] | None = None
        self._running = False

    def log_decision(self, record: AuditRecord) -> bool:
        """Enqueue an audit record for asynchronous persistence without blocking request flow."""
        try:
            self.queue.put_nowait(record)
            return True
        except asyncio.QueueFull:
            logger.warning(
                "Audit queue is full (%d items). Dropping audit record.",
                self.queue.qsize(),
            )
            return False

    def start(self) -> None:
        """Start the background batch-flushing worker."""
        if not self._running:
            self._running = True
            self._worker_task = asyncio.create_task(self._worker_loop())
            logger.info("Started background audit log worker.")

    async def stop(self) -> None:
        """Gracefully stop worker and flush any remaining queued records."""
        if not self._running:
            return

        self._running = False
        if self._worker_task is not None:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None

        # Drain any remaining records in queue
        remaining: list[AuditRecord] = []
        while not self.queue.empty():
            try:
                remaining.append(self.queue.get_nowait())
            except asyncio.QueueEmpty:
                break

        if remaining:
            logger.info("Flushing %d remaining audit records on shutdown.", len(remaining))
            try:
                await self.repository.insert_many(remaining)
            except Exception as exc:
                logger.error("Failed to flush remaining audit records: %s", exc)

    async def _flush_batch(self, batch: list[AuditRecord]) -> None:
        """Write a batch of audit records to the repository."""
        if not batch:
            return
        try:
            await self.repository.insert_many(batch)
        except Exception as exc:
            logger.error("Failed to insert audit batch of size %d: %s", len(batch), exc)

    async def _worker_loop(self) -> None:
        """Background loop reading from queue and periodically flushing batches."""
        batch: list[AuditRecord] = []
        last_flush = asyncio.get_event_loop().time()

        while self._running:
            try:
                elapsed = asyncio.get_event_loop().time() - last_flush
                timeout = max(0.05, self.flush_interval_seconds - elapsed)
                try:
                    record = await asyncio.wait_for(self.queue.get(), timeout=timeout)
                    batch.append(record)
                    self.queue.task_done()
                except TimeoutError:
                    pass

                now = asyncio.get_event_loop().time()
                time_to_flush = (now - last_flush) >= self.flush_interval_seconds
                if len(batch) >= self.batch_size or (batch and time_to_flush):
                    await self._flush_batch(batch)
                    batch = []
                    last_flush = now

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Unexpected error in audit worker loop: %s", exc)
                await asyncio.sleep(0.1)

        # Flush any trailing items
        if batch:
            await self._flush_batch(batch)

    async def query_records(
        self,
        session_id: str | None = None,
        subject_id: str | None = None,
        decision: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
        skip: int = 0,
    ) -> list[AuditRecord]:
        """Delegate search query to the audit repository."""
        return await self.repository.find(
            session_id=session_id,
            subject_id=subject_id,
            decision=decision,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            skip=skip,
        )
