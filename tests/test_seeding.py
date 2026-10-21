from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from decision_engine.policy.spicedb import SpiceDBClient
from motor.motor_asyncio import AsyncIOMotorDatabase

from scripts.seed_demo_data import seed_mongodb, seed_spicedb


def test_seed_spicedb(tmp_path: Path) -> None:
    """Verify seed_spicedb parses schema file and writes relationships."""
    schema_file = tmp_path / "schema.zed"
    schema_file.write_text("definition user {}\n", encoding="utf-8")

    mock_client = MagicMock(spec=SpiceDBClient)
    seed_spicedb(mock_client, schema_path=str(schema_file))

    mock_client.write_schema.assert_called_once_with("definition user {}\n")
    assert mock_client.write_relationship.call_count >= 6


@pytest.mark.asyncio
async def test_seed_mongodb() -> None:
    """Verify seed_mongodb registers upstreams, routes, and audit records."""
    mock_db = MagicMock(spec=AsyncIOMotorDatabase)
    mock_collection = MagicMock()
    mock_collection.insert_one = AsyncMock(return_value=MagicMock(inserted_id="oid_1"))
    mock_collection.insert_many = AsyncMock(return_value=MagicMock(inserted_ids=["oid_1"]))
    mock_collection.create_index = AsyncMock()
    mock_collection.find_one = AsyncMock(return_value=None)
    mock_collection.update_one = AsyncMock()
    mock_collection.replace_one = AsyncMock()
    mock_collection.find_one_and_update = AsyncMock(return_value={"version": 2})
    mock_db.__getitem__.return_value = mock_collection

    await seed_mongodb(mock_db)
    assert mock_collection.replace_one.call_count >= 3  # upstreams + routes
    assert mock_collection.find_one_and_update.call_count >= 3  # bump_version calls
    assert mock_collection.insert_many.call_count >= 1  # audit records
