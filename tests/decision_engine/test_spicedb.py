"""Unit tests for SpiceDB policy client wrapper and schema definition."""

from unittest.mock import MagicMock

import grpc
import pytest
from authzed.api.v1 import (
    CheckPermissionResponse,
    ReadSchemaResponse,
)
from decision_engine.policy.spicedb import SpiceDBClient
from shared.errors import PolicyDeniedError


@pytest.fixture
def mock_authzed_client() -> MagicMock:
    """Fixture providing a mocked Authzed API Client."""
    return MagicMock()


def test_schema_file_exists_and_contains_narrow_definitions() -> None:
    """Verify schema.zed contains ReBAC definitions and closed-loop narrowing."""
    with open("schema.zed", encoding="utf-8") as f:
        content = f.read()

    assert "definition user {}" in content
    assert "definition organization {" in content
    assert "definition document {" in content
    assert "relation restricted_subject: user" in content
    assert "permission view = (owner + editor + viewer) - restricted_subject" in content
    assert "permission narrow_view = viewer & restricted_subject" in content


def test_write_and_read_schema(mock_authzed_client: MagicMock) -> None:
    """Verify write_schema and read_schema calls dispatch to schema service."""
    mock_authzed_client.ReadSchema.return_value = ReadSchemaResponse(
        schema_text="definition user {}"
    )

    client = SpiceDBClient(client=mock_authzed_client)

    # Test write_schema
    client.write_schema("definition user {}")
    mock_authzed_client.WriteSchema.assert_called_once()

    # Test read_schema
    schema = client.read_schema()
    assert schema == "definition user {}"
    mock_authzed_client.ReadSchema.assert_called_once()


def test_check_permission_allowed_and_denied(mock_authzed_client: MagicMock) -> None:
    """Verify check_permission maps Permissionship enum properly."""
    # Allowed response
    mock_authzed_client.CheckPermission.return_value = CheckPermissionResponse(
        permissionship=CheckPermissionResponse.Permissionship.PERMISSIONSHIP_HAS_PERMISSION
    )

    client = SpiceDBClient(client=mock_authzed_client)
    allowed = client.check_permission(
        resource_type="document",
        resource_id="doc_1",
        permission="view",
        subject_type="user",
        subject_id="alice",
    )
    assert allowed is True

    # Denied response
    mock_authzed_client.CheckPermission.return_value = CheckPermissionResponse(
        permissionship=CheckPermissionResponse.Permissionship.PERMISSIONSHIP_NO_PERMISSION
    )
    denied = client.check_permission(
        resource_type="document",
        resource_id="doc_1",
        permission="view",
        subject_type="user",
        subject_id="mallory",
    )
    assert denied is False


def test_write_and_delete_relationship(mock_authzed_client: MagicMock) -> None:
    """Verify relationship mutations for narrow write-back and revoking."""
    client = SpiceDBClient(client=mock_authzed_client)

    # Write narrow restricting relationship
    client.write_relationship(
        resource_type="document",
        resource_id="doc_123",
        relation="restricted_subject",
        subject_type="user",
        subject_id="bob",
    )
    mock_authzed_client.WriteRelationships.assert_called_once()

    # Delete restricting relationship upon TTL expiration
    client.delete_relationship(
        resource_type="document",
        resource_id="doc_123",
        relation="restricted_subject",
        subject_type="user",
        subject_id="bob",
    )
    mock_authzed_client.DeleteRelationships.assert_called_once()


def test_expand_permission_tree(mock_authzed_client: MagicMock) -> None:
    """Verify expand_permission_tree invokes client."""
    mock_resp = MagicMock()
    mock_resp.tree_root = MagicMock()
    mock_authzed_client.ExpandPermissionTree.return_value = mock_resp

    client = SpiceDBClient(client=mock_authzed_client)
    res = client.expand_permission_tree(
        resource_type="document",
        resource_id="doc_1",
        permission="view",
    )
    assert res["expanded_resource"] == "document:doc_1"
    assert res["permission"] == "view"
    assert res["has_tree"] is True


def test_error_translation_on_grpc_failure(mock_authzed_client: MagicMock) -> None:
    """Verify gRPC failures are mapped to PolicyDeniedError."""
    mock_authzed_client.CheckPermission.side_effect = grpc.RpcError("gRPC Unavailable")

    client = SpiceDBClient(client=mock_authzed_client)
    with pytest.raises(PolicyDeniedError):
        client.check_permission(
            resource_type="document",
            resource_id="doc_1",
            permission="view",
            subject_type="user",
            subject_id="alice",
        )


def test_write_returns_zedtoken_and_check_uses_it(mock_authzed_client: MagicMock) -> None:
    """Closed-loop writes return a ZedToken that later checks pass as at_least_as_fresh."""
    from authzed.api.v1 import WriteRelationshipsResponse, ZedToken

    mock_authzed_client.WriteRelationships.return_value = WriteRelationshipsResponse(
        written_at=ZedToken(token="tok-123")
    )
    mock_authzed_client.CheckPermission.return_value = CheckPermissionResponse(
        permissionship=CheckPermissionResponse.Permissionship.PERMISSIONSHIP_NO_PERMISSION
    )
    client = SpiceDBClient(client=mock_authzed_client)

    token = client.write_relationship("document", "d1", "restricted_subject", "user", "u1")
    assert token == "tok-123"

    allowed = client.check_permission(
        "document", "d1", "view", "user", "u1", at_least_as_fresh=token
    )
    assert allowed is False
    req = mock_authzed_client.CheckPermission.call_args[0][0]
    assert req.consistency.at_least_as_fresh.token == "tok-123"

    client.check_permission("document", "d1", "view", "user", "u1")
    req = mock_authzed_client.CheckPermission.call_args[0][0]
    assert not req.HasField("consistency")
