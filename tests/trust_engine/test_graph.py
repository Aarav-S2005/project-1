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
    """An unseen path that ReBAC does not authorize is novel; authorized paths are cached."""
    extractor = GraphFeatureExtractor(spicedb_client=mock_spicedb, redis_client=fake_redis)
    traversal_path = ["user:alice", "organization:eng#member", "document:doc_1#viewer"]

    # Unauthorized and never seen -> novel
    mock_spicedb.check_permission.return_value = False
    feat1 = await extractor.extract(
        subject="user:alice",
        resource="document:doc_1",
        permission="view",
        traversal_path=traversal_path,
    )
    assert feat1.path_novelty == 1.0
    assert feat1.path_length == 3.0

    # Authorized -> routine path, remembered in seen_paths
    mock_spicedb.check_permission.return_value = True
    feat2 = await extractor.extract(
        subject="user:alice",
        resource="document:doc_1",
        permission="view",
        traversal_path=traversal_path,
    )
    assert feat2.path_novelty == 0.0

    # Previously seen path stays non-novel even if a later check fails
    mock_spicedb.check_permission.return_value = False
    feat3 = await extractor.extract(
        subject="user:alice",
        resource="document:doc_1",
        permission="view",
        traversal_path=traversal_path,
    )
    assert feat3.path_novelty == 0.0


@pytest.mark.asyncio
async def test_privilege_shortcut_score(fake_redis: redis.Redis, mock_spicedb: MagicMock) -> None:
    """Paths not backed by a relationship receive the high shortcut score and low degree."""
    extractor = GraphFeatureExtractor(spicedb_client=mock_spicedb, redis_client=fake_redis)

    mock_spicedb.check_permission.return_value = True
    feat_normal = await extractor.extract(
        subject="user:alice",
        resource="document:doc_1",
        permission="view",
        traversal_path=["user:alice", "organization:eng#member", "document:doc_1#viewer"],
    )
    assert feat_normal.privilege_shortcut_score == 0.1
    assert feat_normal.intermediate_node_degree == 5.0

    mock_spicedb.check_permission.return_value = False
    feat_direct = await extractor.extract(
        subject="user:bob",
        resource="document:doc_finance",
        permission="edit",
        traversal_path=["document:doc_finance#owner"],
    )
    assert feat_direct.privilege_shortcut_score == 0.85
    assert feat_direct.intermediate_node_degree == 1.0
    assert feat_direct.path_length == 1.0


@pytest.mark.asyncio
async def test_active_restriction_is_not_graph_anomalous(
    fake_redis: redis.Redis, mock_spicedb: MagicMock
) -> None:
    """A denial caused by the gateway's own closed-loop restriction must not look anomalous."""
    extractor = GraphFeatureExtractor(spicedb_client=mock_spicedb, redis_client=fake_redis)
    mock_spicedb.check_permission.return_value = False
    await fake_redis.set("narrow:document:doc_2:user:carol", "tuple", ex=60)

    feat = await extractor.extract(
        subject="user:carol", resource="document:doc_2", permission="view"
    )
    assert feat.path_novelty == 0.0
    assert feat.privilege_shortcut_score == 0.1
    assert feat.intermediate_node_degree == 5.0


@pytest.mark.asyncio
async def test_supplied_rebac_result_skips_spicedb(
    fake_redis: redis.Redis, mock_spicedb: MagicMock
) -> None:
    """When the pipeline supplies the ReBAC result, the extractor makes no SpiceDB calls."""
    extractor = GraphFeatureExtractor(spicedb_client=mock_spicedb, redis_client=fake_redis)
    feat = await extractor.extract(
        subject="user:alice", resource="document:doc_9", permission="view", has_permission=True
    )
    assert feat.path_novelty == 0.0
    assert feat.path_length == 2.0
    mock_spicedb.check_permission.assert_not_called()
    mock_spicedb.expand_permission_tree.assert_not_called()

    denied = await extractor.extract(
        subject="user:alice", resource="document:doc_10", permission="view", has_permission=False
    )
    assert denied.path_novelty == 1.0
    assert denied.privilege_shortcut_score == 0.85
    mock_spicedb.check_permission.assert_not_called()
