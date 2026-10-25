"""Graph-structural feature extractor deriving traversal metrics from SpiceDB and Redis."""

import asyncio
import hashlib
import logging

import redis.asyncio as redis
from decision_engine.policy.spicedb import SpiceDBClient
from shared.schemas.trust import GraphFeatures

logger = logging.getLogger("trust_engine.features.graph")


class GraphFeatureExtractor:
    """Derives graph-structural features from ReBAC resolution paths and historical graph usage."""

    def __init__(self, spicedb_client: SpiceDBClient, redis_client: redis.Redis) -> None:
        self.spicedb = spicedb_client
        self.redis = redis_client

    async def extract(
        self,
        subject: str,
        resource: str,
        permission: str,
        traversal_path: list[str] | None = None,
        has_permission: bool | None = None,
    ) -> GraphFeatures:
        """Derive 4-dimensional graph feature vector from ReBAC permission and path history.

        ``has_permission`` may be supplied by the caller when the ReBAC check has already been
        performed for this request (the data-plane pipeline does this), avoiding a duplicate
        SpiceDB round trip.
        """
        res_type, res_id = resource.split(":", 1) if ":" in resource else ("document", resource)
        sub_parts = subject.split(":", 1)
        s_type = sub_parts[0] if len(sub_parts) > 1 else "user"
        s_id = sub_parts[1] if len(sub_parts) > 1 else subject

        if has_permission is None:
            try:
                has_permission = bool(
                    await asyncio.to_thread(
                        self.spicedb.check_permission,
                        resource_type=res_type,
                        resource_id=res_id,
                        permission=permission,
                        subject_type=s_type,
                        subject_id=s_id,
                    )
                )
            except Exception as exc:
                logger.debug("SpiceDB check_permission in graph extractor: %s", exc)
                has_permission = False

        # 1. Path Length: hop count of a supplied traversal path. Without one, the previous
        #    implementation called ExpandPermissionTree but always mapped the result to 2.0, so the
        #    extra SpiceDB round trip is skipped and the same constant is used.
        if traversal_path:
            path_length = float(len(traversal_path))
            canonical_path = "->".join(traversal_path)
        else:
            path_length = 2.0
            canonical_path = f"{subject}->{permission}->{resource}"

        # 2. Path Novelty: has the subject used this relation path before? One Redis round trip
        #    reads the active-restriction flag and path history (and records routine paths).
        path_hash = hashlib.sha256(canonical_path.encode("utf-8")).hexdigest()[:16]
        seen_paths_key = f"subject:{subject}:seen_paths"
        narrow_key = f"narrow:{res_type}:{res_id}:{s_type}:{s_id}"
        recorded = bool(has_permission)
        pipe = self.redis.pipeline(transaction=False)
        pipe.exists(narrow_key)
        pipe.sismember(seen_paths_key, path_hash)
        if has_permission:
            pipe.sadd(seen_paths_key, path_hash)
            pipe.expire(seen_paths_key, 86400 * 30)  # 30 days retention
        try:
            res = await pipe.execute()
            narrowed, is_member = bool(res[0]), bool(res[1])
        except Exception as exc:
            logger.debug("Redis lookups in graph extractor: %s", exc)
            narrowed, is_member = False, False

        # A denial caused by the gateway's own closed-loop restriction is not evidence of a
        # suspicious graph traversal. Treat restricted-but-related paths as authorized for feature
        # purposes so quarantine does not feed back into further trust penalties (lock-out).
        if not has_permission and narrowed:
            has_permission = True

        if is_member or has_permission:
            # Routine authorized relationship path
            path_novelty = 0.0
            if not recorded:  # not already recorded by the pipeline above
                try:
                    await self.redis.sadd(seen_paths_key, path_hash)
                    await self.redis.expire(seen_paths_key, 86400 * 30)
                except Exception as exc:
                    logger.debug("Redis path record in graph extractor: %s", exc)
        else:
            # Novel traversal without a pre-authorized relationship: anomaly flag = 1.0
            path_novelty = 1.0

        # 3. Privilege Shortcut Score
        # Direct owner/editor shortcut on a document without organization membership
        # indicates a privilege-escalation shortcut or direct grant bypass
        if not has_permission:
            privilege_shortcut_score = 0.85
        else:
            privilege_shortcut_score = 0.10

        # 4. Intermediate Node Degree
        # Organization nodes have higher fan-out (5.0) than unauthorized anomalous links (1.0)
        intermediate_node_degree = 5.0 if has_permission else 1.0

        return GraphFeatures(
            path_length=path_length,
            path_novelty=path_novelty,
            privilege_shortcut_score=privilege_shortcut_score,
            intermediate_node_degree=intermediate_node_degree,
        )
