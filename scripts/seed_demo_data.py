"""Bootstrap script seeding SpiceDB ReBAC schema/relations, MongoDB routes, and demo audit logs."""

import asyncio
import logging
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from audit.repository import AuditRepository
from control_plane.repositories import ConfigRepository
from decision_engine.policy.spicedb import SpiceDBClient
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from shared.config import get_settings
from shared.logging import configure_logging
from shared.schemas.audit import AuditRecord
from shared.schemas.decision import ClosedLoopAction, DecisionAction
from shared.schemas.gateway import RouteConfig, UpstreamConfig

logger = logging.getLogger("scripts.seed_demo_data")


def seed_spicedb(
    client: SpiceDBClient, schema_path: str = "schema.zed", max_retries: int = 10
) -> None:
    """Upload Zed schema and baseline relationships to SpiceDB with retry logic."""
    schema_file = Path(schema_path)
    if not schema_file.exists():
        logger.error("Schema file not found at %s", schema_path)
        return

    schema_content = schema_file.read_text(encoding="utf-8")
    for attempt in range(1, max_retries + 1):
        try:
            logger.info("Writing schema.zed to SpiceDB (attempt %d/%d)...", attempt, max_retries)
            client.write_schema(schema_content)
            break
        except Exception as exc:
            if attempt == max_retries:
                logger.error(
                    "Failed to connect/write schema to SpiceDB after %d attempts: %s",
                    max_retries,
                    exc,
                )
                raise
            logger.warning("SpiceDB not ready yet (%s). Retrying in 2 seconds...", exc)
            time.sleep(2)

    logger.info("Writing baseline ReBAC relationships to SpiceDB...")
    # Organization memberships
    client.write_relationship("organization", "acme", "member", "user", "alice")
    client.write_relationship("organization", "acme", "member", "user", "bob")
    client.write_relationship("organization", "acme", "member", "user", "charlie")

    # Document ownership & permissions
    client.write_relationship("document", "doc_1", "owner", "user", "alice")
    client.write_relationship("document", "doc_confidential", "owner", "user", "admin")
    client.write_relationship("document", "doc_confidential", "viewer", "user", "alice")
    client.write_relationship("document", "doc_classified", "owner", "user", "admin")
    logger.info("SpiceDB bootstrap completed successfully.")


async def seed_mongodb(db: AsyncIOMotorDatabase[Any]) -> None:
    """Seed Gateway upstream services, dynamic routes, and demo audit records in MongoDB."""
    config_repo = ConfigRepository(db=db)
    audit_repo = AuditRepository(db=db)

    logger.info("Seeding Gateway Upstream...")
    upstream = UpstreamConfig(
        id="ups_echo",
        name="HTTPBin Echo Backend",
        target_url="https://httpbin.org",
        timeout_ms=5000,
        health_check_path="/get",
    )
    await config_repo.save_upstream(upstream)

    logger.info("Seeding Gateway Routes...")
    route_docs = RouteConfig(
        id="route_documents",
        upstream_id="ups_echo",
        path_prefix="/api/v1/documents",
        methods=["GET", "POST", "PUT", "DELETE"],
        strip_path=False,
        auth_required=True,
        resource_type="document",
        resource_id_extractor="path_param:id",
        permission_mapping={
            "GET": "view",
            "POST": "create",
            "PUT": "edit",
            "DELETE": "delete",
        },
    )
    await config_repo.save_route(route_docs)

    route_public = RouteConfig(
        id="route_public",
        upstream_id="ups_echo",
        path_prefix="/api/v1/public",
        methods=["GET"],
        strip_path=False,
        auth_required=False,
    )
    await config_repo.save_route(route_public)

    # Initialize Audit Indexes
    await audit_repo.create_indexes()

    # Seed Sample Audit Records across all decision bands
    logger.info("Seeding sample historical audit logs for Dashboard visualization...")
    now = datetime.now(UTC)
    sample_records: list[AuditRecord] = [
        AuditRecord(
            request_id="req_demo_001",
            session_id="sess_alice_norm",
            subject_id="user:alice",
            client_ip="192.168.1.100",
            route_id="route_documents",
            resource="document:doc_1",
            permission="view",
            trust_score_before=1.0,
            trust_score_after=0.965,
            decision=DecisionAction.ALLOW,
            decision_reason="trust_score_0.97_nominal_allow",
            features={
                "req_rate_10s": 0.8,
                "req_rate_60s": 4.5,
                "geo_velocity_kmh": 0.0,
                "tls_fingerprint_mismatch": 0.0,
                "path_length": 1.0,
                "path_novelty": 0.0,
            },
            shap_attributions={
                "req_rate_10s": 0.045,
                "path_novelty": 0.032,
                "geo_velocity_kmh": 0.015,
            },
            latency_ms=1.15,
            timestamp=now - timedelta(minutes=15),
        ),
        AuditRecord(
            request_id="req_demo_002",
            session_id="sess_charlie_novel",
            subject_id="user:charlie",
            client_ip="203.0.113.45",
            route_id="route_documents",
            resource="document:doc_confidential",
            permission="view",
            trust_score_before=0.88,
            trust_score_after=0.725,
            decision=DecisionAction.NARROW,
            decision_reason="trust_score_0.72_degraded_narrow_applied",
            features={
                "req_rate_10s": 2.2,
                "req_rate_60s": 8.0,
                "geo_velocity_kmh": 12.0,
                "tls_fingerprint_mismatch": 0.0,
                "path_length": 3.0,
                "path_novelty": 1.0,
                "privilege_shortcut_score": 0.65,
            },
            shap_attributions={
                "path_novelty": -0.145,
                "privilege_shortcut_score": -0.085,
                "req_rate_10s": -0.035,
            },
            closed_loop_feedback=ClosedLoopAction(
                action="spicedb_relation_written",
                relation_tuple="document:doc_confidential#restricted_subject@user:charlie",
                ttl_seconds=900,
                created_at=now - timedelta(minutes=10),
                expires_at=now + timedelta(minutes=5),
            ),
            latency_ms=1.42,
            timestamp=now - timedelta(minutes=10),
        ),
        AuditRecord(
            request_id="req_demo_003",
            session_id="sess_bob_burst",
            subject_id="user:bob",
            client_ip="198.51.100.88",
            route_id="route_documents",
            resource="document:doc_1",
            permission="edit",
            trust_score_before=0.75,
            trust_score_after=0.510,
            decision=DecisionAction.STEP_UP,
            decision_reason="trust_score_0.51_suspicious_step_up_required",
            features={
                "req_rate_10s": 15.0,
                "req_rate_60s": 42.0,
                "rate_burst_ratio": 3.2,
                "geo_velocity_kmh": 0.0,
                "tls_fingerprint_mismatch": 0.0,
                "path_length": 1.0,
                "path_novelty": 0.0,
            },
            shap_attributions={
                "req_rate_10s": -0.210,
                "rate_burst_ratio": -0.115,
                "req_rate_60s": -0.090,
            },
            latency_ms=0.98,
            timestamp=now - timedelta(minutes=5),
        ),
        AuditRecord(
            request_id="req_demo_004",
            session_id="sess_attacker_999",
            subject_id="user:attacker",
            client_ip="198.51.100.200",
            route_id="route_documents",
            resource="document:doc_classified",
            permission="delete",
            trust_score_before=0.45,
            trust_score_after=0.180,
            decision=DecisionAction.DENY,
            decision_reason="trust_score_0.18_critical_denied",
            features={
                "req_rate_10s": 28.0,
                "req_rate_60s": 95.0,
                "geo_velocity_kmh": 1250.0,
                "tls_fingerprint_mismatch": 1.0,
                "path_length": 4.0,
                "path_novelty": 1.0,
                "privilege_shortcut_score": 0.95,
            },
            shap_attributions={
                "geo_velocity_kmh": -0.320,
                "tls_fingerprint_mismatch": -0.185,
                "path_novelty": -0.160,
                "req_rate_10s": -0.140,
            },
            latency_ms=0.85,
            timestamp=now - timedelta(minutes=1),
        ),
    ]

    await audit_repo.insert_many(sample_records)
    logger.info("MongoDB bootstrap completed successfully.")


async def main() -> None:
    """Run full bootstrap seeding."""
    settings = get_settings()
    configure_logging(level=settings.log_level)

    logger.info("Connecting to SpiceDB and MongoDB for bootstrap...")
    spicedb_client = SpiceDBClient()
    mongo_client: AsyncIOMotorClient[Any] = AsyncIOMotorClient(settings.mongo_uri)
    db = mongo_client[settings.mongo_db_name]

    try:
        seed_spicedb(spicedb_client)
        await seed_mongodb(db)
        logger.info("All demo data seeded successfully!")
    finally:
        spicedb_client.close()
        mongo_client.close()


if __name__ == "__main__":
    asyncio.run(main())
