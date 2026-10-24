"""Closed-loop policy feedback manager writing temporary restrictions to SpiceDB and Redis."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

import redis.asyncio as redis
from shared.config import get_settings
from shared.schemas.decision import ClosedLoopAction

from decision_engine.policy.spicedb import SpiceDBClient

logger = logging.getLogger("decision_engine.closed_loop")

ACTIVE_NARROW_ZSET = "active_narrow_restrictions"


class ClosedLoopManager:
    """Manages temporary restricting relations in SpiceDB and lifecycle tracking in Redis."""

    def __init__(
        self,
        spicedb_client: SpiceDBClient,
        redis_client: redis.Redis,
        default_ttl_seconds: int | None = None,
    ) -> None:
        self.spicedb_client = spicedb_client
        self.redis_client = redis_client
        settings = get_settings()
        self.default_ttl_seconds = (
            default_ttl_seconds if default_ttl_seconds is not None else settings.narrow_ttl_seconds
        )

    def _format_key(
        self, resource_type: str, resource_id: str, subject_type: str, subject_id: str
    ) -> str:
        return f"narrow:{resource_type}:{resource_id}:{subject_type}:{subject_id}"

    def _format_member(
        self, resource_type: str, resource_id: str, subject_type: str, subject_id: str
    ) -> str:
        return f"{resource_type}:{resource_id}:{subject_type}:{subject_id}"

    async def apply_narrow(
        self,
        resource_type: str,
        resource_id: str,
        subject_type: str,
        subject_id: str,
        ttl_seconds: int | None = None,
        current_time: datetime | None = None,
    ) -> ClosedLoopAction:
        """Write restricting relation to SpiceDB and record active narrowing in Redis."""
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        now = current_time or datetime.now(UTC)
        expires_at = now + timedelta(seconds=ttl)

        # 1. Closed-loop feedback: write restricting relation into SpiceDB graph
        #    (blocking gRPC call is run in a worker thread so it does not stall the event loop)
        zedtoken = await asyncio.to_thread(
            self.spicedb_client.write_relationship,
            resource_type=resource_type,
            resource_id=resource_id,
            relation="restricted_subject",
            subject_type=subject_type,
            subject_id=subject_id,
        )

        relation_tuple = (
            f"{resource_type}:{resource_id}#restricted_subject@{subject_type}:{subject_id}"
        )

        # 2. Record state and expiry in Redis
        key = self._format_key(resource_type, resource_id, subject_type, subject_id)
        member = self._format_member(resource_type, resource_id, subject_type, subject_id)

        pipe = self.redis_client.pipeline()
        pipe.set(key, relation_tuple, ex=ttl)
        if isinstance(zedtoken, str) and zedtoken:
            # Consistency token of the write: later checks use it so the restriction is
            # visible immediately (at_least_as_fresh) on every data-plane worker.
            pipe.set(f"{key}:zedtoken", zedtoken, ex=ttl)
        pipe.zadd(ACTIVE_NARROW_ZSET, {member: expires_at.timestamp()})
        await pipe.execute()

        logger.info(
            "Applied closed-loop narrow: %s with TTL %ds (expires %s)",
            relation_tuple,
            ttl,
            expires_at.isoformat(),
        )

        return ClosedLoopAction(
            action="spicedb_relation_written",
            relation_tuple=relation_tuple,
            ttl_seconds=ttl,
            created_at=now,
            expires_at=expires_at,
        )

    async def revoke_narrow(
        self,
        resource_type: str,
        resource_id: str,
        subject_type: str,
        subject_id: str,
    ) -> bool:
        """Manually or proactively remove restricting relation from SpiceDB and Redis."""
        await asyncio.to_thread(
            self.spicedb_client.delete_relationship,
            resource_type=resource_type,
            resource_id=resource_id,
            relation="restricted_subject",
            subject_type=subject_type,
            subject_id=subject_id,
        )

        key = self._format_key(resource_type, resource_id, subject_type, subject_id)
        member = self._format_member(resource_type, resource_id, subject_type, subject_id)

        pipe = self.redis_client.pipeline()
        pipe.delete(key)
        pipe.delete(f"{key}:zedtoken")
        pipe.zrem(ACTIVE_NARROW_ZSET, member)
        await pipe.execute()

        logger.info(
            "Revoked closed-loop narrow for %s:%s on %s:%s",
            subject_type,
            subject_id,
            resource_type,
            resource_id,
        )
        return True

    async def is_narrowed(
        self,
        resource_type: str,
        resource_id: str,
        subject_type: str,
        subject_id: str,
    ) -> bool:
        """Check if an active narrowing restriction exists in Redis."""
        key = self._format_key(resource_type, resource_id, subject_type, subject_id)
        exists = await self.redis_client.exists(key)
        return bool(exists)

    async def get_restriction_token(
        self,
        resource_type: str,
        resource_id: str,
        subject_type: str,
        subject_id: str,
    ) -> str | None:
        """Return the ZedToken of an active restriction write, if any."""
        key = self._format_key(resource_type, resource_id, subject_type, subject_id)
        raw = await self.redis_client.get(f"{key}:zedtoken")
        if raw is None:
            return None
        return raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)

    async def sweep_expired_restrictions(self, current_time: datetime | None = None) -> int:
        """Find expired narrowing entries and delete their restriction from SpiceDB."""
        now = current_time or datetime.now(UTC)
        now_ts = now.timestamp()

        # Query all members whose score is <= current timestamp
        expired_members = await self.redis_client.zrangebyscore(
            ACTIVE_NARROW_ZSET, min=0, max=now_ts
        )

        if not expired_members:
            return 0

        swept_count = 0
        for raw_member in expired_members:
            member = (
                raw_member.decode("utf-8") if isinstance(raw_member, bytes) else str(raw_member)
            )
            parts = member.split(":")
            if len(parts) == 4:
                resource_type, resource_id, subject_type, subject_id = parts
                try:
                    await asyncio.to_thread(
                        self.spicedb_client.delete_relationship,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        relation="restricted_subject",
                        subject_type=subject_type,
                        subject_id=subject_id,
                    )
                except Exception as exc:
                    logger.warning(
                        "Error cleaning expired SpiceDB restriction for %s: %s",
                        member,
                        exc,
                    )
            await self.redis_client.zrem(ACTIVE_NARROW_ZSET, member)
            swept_count += 1

        logger.info("Swept %d expired closed-loop restrictions", swept_count)
        return swept_count
