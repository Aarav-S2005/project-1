"""SpiceDB gRPC client wrapper for ReBAC schema, checks, mutations, and tree expansion."""

import logging
from typing import Any

import grpc
from authzed.api.v1 import (
    CheckPermissionRequest,
    CheckPermissionResponse,
    Client,
    DeleteRelationshipsRequest,
    ExpandPermissionTreeRequest,
    InsecureClient,
    ObjectReference,
    ReadRelationshipsRequest,
    ReadSchemaRequest,
    Relationship,
    RelationshipFilter,
    RelationshipUpdate,
    SubjectFilter,
    SubjectReference,
    WriteRelationshipsRequest,
    WriteSchemaRequest,
)
from shared.config import get_settings
from shared.errors import PolicyDeniedError

logger = logging.getLogger("decision_engine.spicedb")


def _get_error_details(exc: grpc.RpcError) -> str:
    """Safely extract details string from gRPC RpcError."""
    if hasattr(exc, "details") and callable(exc.details):
        return str(exc.details())
    return str(exc)


class SpiceDBClient:
    """Wrapper around AuthZed/SpiceDB gRPC client for Zero-Trust policy operations."""

    def __init__(
        self,
        endpoint: str | None = None,
        preshared_key: str | None = None,
        insecure: bool = True,
        client: Any | None = None,
    ) -> None:
        settings = get_settings()
        self.endpoint = endpoint or settings.spicedb_grpc_endpoint
        self.preshared_key = preshared_key or settings.spicedb_preshared_key
        self.insecure = insecure

        if client is not None:
            self._client = client
        else:
            if self.insecure:
                self._client = InsecureClient(self.endpoint, token=self.preshared_key)
            else:
                credentials = grpc.composite_channel_credentials(
                    grpc.ssl_channel_credentials(),
                    grpc.access_token_call_credentials(self.preshared_key),
                )
                self._client = Client(self.endpoint, credentials)

    def write_schema(self, schema_text: str) -> None:
        """Upload and compile a Zed schema into SpiceDB."""
        try:
            req = WriteSchemaRequest(schema=schema_text)
            self._client.WriteSchema(req)
            logger.info("Successfully updated SpiceDB schema.")
        except grpc.RpcError as exc:
            err_msg = _get_error_details(exc)
            logger.error("Failed to write SpiceDB schema: %s", err_msg)
            raise PolicyDeniedError(
                f"Failed to write SpiceDB schema: {err_msg}",
                details={"error": err_msg},
            ) from exc

    def read_schema(self) -> str:
        """Fetch the current active Zed schema from SpiceDB."""
        try:
            req = ReadSchemaRequest()
            resp = self._client.ReadSchema(req)
            return str(resp.schema_text)
        except grpc.RpcError as exc:
            err_msg = _get_error_details(exc)
            logger.error("Failed to read SpiceDB schema: %s", err_msg)
            raise PolicyDeniedError(
                f"Failed to read SpiceDB schema: {err_msg}",
                details={"error": err_msg},
            ) from exc

    def check_permission(
        self,
        resource_type: str,
        resource_id: str,
        permission: str,
        subject_type: str,
        subject_id: str,
    ) -> bool:
        """Evaluate whether a subject has a specific permission on a resource."""
        try:
            req = CheckPermissionRequest(
                resource=ObjectReference(object_type=resource_type, object_id=resource_id),
                permission=permission,
                subject=SubjectReference(
                    object=ObjectReference(object_type=subject_type, object_id=subject_id)
                ),
            )
            resp: CheckPermissionResponse = self._client.CheckPermission(req)
            is_allowed = (
                resp.permissionship
                == CheckPermissionResponse.Permissionship.PERMISSIONSHIP_HAS_PERMISSION
            )
            logger.debug(
                "SpiceDB check %s:%s#%s@%s:%s -> %s",
                resource_type,
                resource_id,
                permission,
                subject_type,
                subject_id,
                is_allowed,
            )
            return bool(is_allowed)
        except grpc.RpcError as exc:
            err_msg = _get_error_details(exc)
            logger.error("SpiceDB CheckPermission failed: %s", err_msg)
            raise PolicyDeniedError(
                f"SpiceDB authorization check failed: {err_msg}",
                details={"error": err_msg},
            ) from exc

    def write_relationship(
        self,
        resource_type: str,
        resource_id: str,
        relation: str,
        subject_type: str,
        subject_id: str,
    ) -> None:
        """Insert or touch a relationship tuple in SpiceDB."""
        try:
            rel = Relationship(
                resource=ObjectReference(object_type=resource_type, object_id=resource_id),
                relation=relation,
                subject=SubjectReference(
                    object=ObjectReference(object_type=subject_type, object_id=subject_id)
                ),
            )
            req = WriteRelationshipsRequest(
                updates=[
                    RelationshipUpdate(
                        operation=RelationshipUpdate.Operation.OPERATION_TOUCH,
                        relationship=rel,
                    )
                ]
            )
            self._client.WriteRelationships(req)
            logger.info(
                "Wrote SpiceDB relationship: %s:%s#%s@%s:%s",
                resource_type,
                resource_id,
                relation,
                subject_type,
                subject_id,
            )
        except grpc.RpcError as exc:
            err_msg = _get_error_details(exc)
            logger.error("SpiceDB WriteRelationship failed: %s", err_msg)
            raise PolicyDeniedError(
                f"Failed to write relationship: {err_msg}",
                details={"error": err_msg},
            ) from exc

    def delete_relationship(
        self,
        resource_type: str,
        resource_id: str,
        relation: str,
        subject_type: str,
        subject_id: str,
    ) -> None:
        """Delete an existing relationship tuple (used to revoke restrictions)."""
        try:
            req = DeleteRelationshipsRequest(
                relationship_filter=RelationshipFilter(
                    resource_type=resource_type,
                    optional_resource_id=resource_id,
                    optional_relation=relation,
                    optional_subject_filter=SubjectFilter(
                        subject_type=subject_type,
                        optional_subject_id=subject_id,
                    ),
                )
            )
            self._client.DeleteRelationships(req)
            logger.info(
                "Deleted SpiceDB relationship: %s:%s#%s@%s:%s",
                resource_type,
                resource_id,
                relation,
                subject_type,
                subject_id,
            )
        except grpc.RpcError as exc:
            err_msg = _get_error_details(exc)
            logger.error("SpiceDB DeleteRelationship failed: %s", err_msg)
            raise PolicyDeniedError(
                f"Failed to delete relationship: {err_msg}",
                details={"error": err_msg},
            ) from exc

    def read_relationships(
        self,
        resource_type: str = "document",
        resource_id: str | None = None,
        relation: str | None = None,
        subject_type: str | None = None,
        subject_id: str | None = None,
    ) -> list[dict[str, str]]:
        """Read relationships matching a filter from SpiceDB."""
        try:
            sub_filter = None
            if subject_type:
                sub_filter = SubjectFilter(
                    subject_type=subject_type,
                    optional_subject_id=subject_id or "",
                )

            req = ReadRelationshipsRequest(
                relationship_filter=RelationshipFilter(
                    resource_type=resource_type,
                    optional_resource_id=resource_id or "",
                    optional_relation=relation or "",
                    optional_subject_filter=sub_filter,
                )
            )
            results = []
            for resp in self._client.ReadRelationships(req):
                rel = resp.relationship
                results.append(
                    {
                        "resource_type": rel.resource.object_type,
                        "resource_id": rel.resource.object_id,
                        "relation": rel.relation,
                        "subject_type": rel.subject.object.object_type,
                        "subject_id": rel.subject.object.object_id,
                        "tuple": (
                            f"{rel.resource.object_type}:{rel.resource.object_id}#"
                            f"{rel.relation}@"
                            f"{rel.subject.object.object_type}:{rel.subject.object.object_id}"
                        ),
                    }
                )
            return results
        except grpc.RpcError as exc:
            err_msg = _get_error_details(exc)
            logger.warning("SpiceDB ReadRelationships returned error: %s", err_msg)
            return []

    def expand_permission_tree(
        self,
        resource_type: str,
        resource_id: str,
        permission: str,
    ) -> dict[str, Any]:
        """Expand the permission resolution tree to derive graph structural features."""
        try:
            req = ExpandPermissionTreeRequest(
                resource=ObjectReference(object_type=resource_type, object_id=resource_id),
                permission=permission,
            )
            resp = self._client.ExpandPermissionTree(req)
            tree_root = resp.tree_root
            return {
                "expanded_resource": f"{resource_type}:{resource_id}",
                "permission": permission,
                "has_tree": tree_root is not None,
            }
        except grpc.RpcError as exc:
            err_msg = _get_error_details(exc)
            logger.error("SpiceDB ExpandPermissionTree failed: %s", err_msg)
            raise PolicyDeniedError(
                f"SpiceDB tree expansion failed: {err_msg}",
                details={"error": err_msg},
            ) from exc

    def close(self) -> None:
        """Gracefully release client resources."""
        if hasattr(self._client, "close"):
            self._client.close()
