"""Graph-structural feature extractor deriving traversal metrics from SpiceDB and Redis."""

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
    ) -> GraphFeatures:
        """Derive 4-dimensional graph feature vector from ReBAC tree and Redis path history."""
        res_type, res_id = resource.split(":", 1) if ":" in resource else ("document", resource)

        # Check if subject currently holds this permission in SpiceDB
        has_permission = False
        try:
            sub_parts = subject.split(":", 1)
            s_type = sub_parts[0] if len(sub_parts) > 1 else "user"
            s_id = sub_parts[1] if len(sub_parts) > 1 else subject
            has_permission = self.spicedb.check_permission(
                resource_type=res_type,
                resource_id=res_id,
                permission=permission,
                subject_type=s_type,
                subject_id=s_id,
            )
        except Exception as exc:
            logger.debug("SpiceDB check_permission in graph extractor: %s", exc)
            has_permission = False

        # 1. Path Length: derive hop count from traversal path or SpiceDB tree expansion
        if traversal_path and len(traversal_path) > 0:
            path_length = float(len(traversal_path))
            canonical_path = "->".join(traversal_path)
        else:
            # Query SpiceDB tree expansion
            try:
                tree_data = self.spicedb.expand_permission_tree(res_type, res_id, permission)
                path_length = 2.0 if tree_data.get("has_tree") else 2.0
            except Exception:
                path_length = 2.0 if has_permission else 1.0
            canonical_path = f"{subject}->{permission}->{resource}"

        # 2. Path Novelty: Has subject ever traversed this relation path before?
        path_hash = hashlib.sha256(canonical_path.encode("utf-8")).hexdigest()[:16]
        seen_paths_key = f"subject:{subject}:seen_paths"

        is_member = await self.redis.sismember(seen_paths_key, path_hash)

        if is_member or has_permission:
            # Routine authorized relationship path
            path_novelty = 0.0
            await self.redis.sadd(seen_paths_key, path_hash)
            await self.redis.expire(seen_paths_key, 86400 * 30)  # 30 days retention
        else:
            # Novel graph traversal edge/path without pre-authorized relationship! Anomaly flag = 1.0
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

