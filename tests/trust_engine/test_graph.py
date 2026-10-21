"""Unit tests for GraphFeatureExtractor."""

from unittest.mock import MagicMock

import pytest
import redis.asyncio as redis
from decision_engine.policy.spicedb import SpiceDBClient
from trust_engine.features.graph import GraphFeatureExtractor


@pytest.fixture
def mock_spicedb() -> MagicMock:
    """Fixture providing a mock SpiceDBClient."""
    mock = MagicMock(spec=SpiceDBClient)
    mock.expand_permission_tree.return_value = {
        "expanded_resource": "document:doc_1",
        "permission": "view",
        "has_tree": True,
    }
    return mock


@pytest.mark.asyncio
async def test_path_novelty_detection(fake_redis: redis.Redis, mock_spicedb: MagicMock) -> None:
    """Verify that a newly observed relation path is flagged novel, then cached."""
    extractor = GraphFeatureExtractor(spicedb_client=mock_spicedb, redis_client=fake_redis)

    traversal_path = ["user:alice", "organization:eng#member", "document:doc_1#viewer"]

    # First request: path has never been traversed by alice -> path_novelty = 1.0
    feat1 = await extractor.extract(
        subject="user:alice",
        resource="document:doc_1",
        permission="view",
        traversal_path=traversal_path,
    )
    assert feat1.path_novelty == 1.0
    assert feat1.path_length == 3.0

    # Second request: exact same path -> path_novelty = 0.0
    feat2 = await extractor.extract(
        subject="user:alice",
        resource="document:doc_1",
        permission="view",
        traversal_path=traversal_path,
    )
    assert feat2.path_novelty == 0.0


@pytest.mark.asyncio
async def test_privilege_shortcut_score(fake_redis: redis.Redis, mock_spicedb: MagicMock) -> None:
    """Verify direct privileged owner shortcuts receive higher anomaly risk scores."""
    extractor = GraphFeatureExtractor(spicedb_client=mock_spicedb, redis_client=fake_redis)

    # 1. Standard organizational delegation path (low shortcut risk)
    feat_normal = await extractor.extract(
        subject="user:alice",
        resource="document:doc_1",
        permission="view",
        traversal_path=["user:alice", "organization:eng#member", "document:doc_1#viewer"],
    )
    assert feat_normal.privilege_shortcut_score == 0.1
    assert feat_normal.intermediate_node_degree == 5.0

    # 2. Direct single-hop owner grant on sensitive document (suspicious shortcut)
    feat_direct_owner = await extractor.extract(
        subject="user:bob",
        resource="document:doc_finance",
        permission="edit",
        traversal_path=["document:doc_finance#owner"],
    )
    assert feat_direct_owner.privilege_shortcut_score == 0.85
    assert feat_direct_owner.path_length == 1.0
