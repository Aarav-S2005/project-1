"""ReBAC relationship management and permission inspection endpoints for Control Plane."""

import logging
from typing import Any

from decision_engine.policy.spicedb import SpiceDBClient
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("control_plane.routes.rebac")

router = APIRouter(prefix="/api/v1/rebac", tags=["rebac"])


class RelationshipPayload(BaseModel):
    """Payload to create or delete a relationship tuple in SpiceDB."""

    resource_type: str = Field(default="document", description="Resource type, e.g. document")
    resource_id: str = Field(description="Resource ID, e.g. doc_1")
    relation: str = Field(description="Relation, e.g. owner, editor, viewer, member")
    subject_type: str = Field(default="user", description="Subject type, e.g. user, organization")
    subject_id: str = Field(description="Subject ID, e.g. alice, bob, acme")


class PermissionCheckPayload(BaseModel):
    """Payload to check whether a subject has a specific permission on a resource."""

    resource_type: str = Field(default="document")
    resource_id: str
    permission: str = Field(default="view")
    subject_type: str = Field(default="user")
    subject_id: str


class SchemaPayload(BaseModel):
    """Payload to write or compile schema to SpiceDB."""

    schema_text: str | None = None


@router.post("/schema", response_model=dict[str, str])
def apply_schema(payload: SchemaPayload | None = None) -> dict[str, str]:
    """Compile and apply Zed schema to SpiceDB."""
    client = SpiceDBClient()
    try:
        content = payload.schema_text if payload and payload.schema_text else None
        if not content:
            with open("schema.zed", encoding="utf-8") as f:
                content = f.read()
        client.write_schema(content)
        return {"status": "success", "message": "SpiceDB schema applied successfully"}
    except Exception as exc:
        logger.error("Failed to apply SpiceDB schema: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        client.close()


@router.get("/relationships", response_model=list[dict[str, Any]])
def list_relationships(
    resource_type: str | None = None,
    subject_id: str | None = None,
) -> list[dict[str, Any]]:
    """List ReBAC relationships from SpiceDB across known resource types."""
    client = SpiceDBClient()
    try:
        types_to_query = (
            [resource_type] if resource_type else ["document", "organization", "workspace"]
        )
        all_rels: list[dict[str, Any]] = []

        for r_type in types_to_query:
            rels = client.read_relationships(
                resource_type=r_type,
                subject_id=subject_id,
            )
            all_rels.extend(rels)

        return all_rels
    except Exception as exc:
        logger.warning("Failed to query SpiceDB relationships: %s", exc)
        return []
    finally:
        client.close()


@router.post("/relationships", response_model=dict[str, str])
def create_relationship(payload: RelationshipPayload) -> dict[str, str]:
    """Create or update a relationship tuple in SpiceDB."""
    client = SpiceDBClient()
    try:
        client.write_relationship(
            resource_type=payload.resource_type.strip(),
            resource_id=payload.resource_id.strip(),
            relation=payload.relation.strip(),
            subject_type=payload.subject_type.strip(),
            subject_id=payload.subject_id.strip(),
        )
        tuple_str = (
            f"{payload.resource_type}:{payload.resource_id}#"
            f"{payload.relation}@{payload.subject_type}:{payload.subject_id}"
        )
        return {
            "status": "created",
            "tuple": tuple_str,
        }
    except Exception as exc:
        logger.error("Failed to write SpiceDB relationship: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        client.close()


@router.delete("/relationships", response_model=dict[str, str])
def remove_relationship(
    resource_type: str,
    resource_id: str,
    relation: str,
    subject_type: str = "user",
    subject_id: str = "",
) -> dict[str, str]:
    """Delete a relationship tuple from SpiceDB."""
    client = SpiceDBClient()
    try:
        client.delete_relationship(
            resource_type=resource_type.strip(),
            resource_id=resource_id.strip(),
            relation=relation.strip(),
            subject_type=subject_type.strip(),
            subject_id=subject_id.strip(),
        )
        return {
            "status": "deleted",
            "tuple": f"{resource_type}:{resource_id}#{relation}@{subject_type}:{subject_id}",
        }
    except Exception as exc:
        logger.error("Failed to delete SpiceDB relationship: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        client.close()


@router.post("/check", response_model=dict[str, Any])
def check_permission(payload: PermissionCheckPayload) -> dict[str, Any]:
    """Evaluate whether a subject currently has permission on a resource in SpiceDB."""
    client = SpiceDBClient()
    try:
        has_permission = client.check_permission(
            resource_type=payload.resource_type.strip(),
            resource_id=payload.resource_id.strip(),
            permission=payload.permission.strip(),
            subject_type=payload.subject_type.strip(),
            subject_id=payload.subject_id.strip(),
        )
        return {
            "allowed": has_permission,
            "resource": f"{payload.resource_type}:{payload.resource_id}",
            "permission": payload.permission,
            "subject": f"{payload.subject_type}:{payload.subject_id}",
        }
    except Exception as exc:
        logger.error("Failed to check SpiceDB permission: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        client.close()


@router.get("/user-access/{subject_id}", response_model=list[dict[str, Any]])
def get_user_access(subject_id: str) -> list[dict[str, Any]]:
    """Inspect all known resources and check what permissions a specific user has."""
    # Normalize subject
    sub = subject_id.replace("user:", "")
    client = SpiceDBClient()
    try:
        # 1. Read all document relationships to find distinct resources
        rels = client.read_relationships(resource_type="document")
        resource_ids = sorted(
            list({r["resource_id"] for r in rels} | {"doc_1", "doc_confidential", "doc_classified"})
        )

        access_list: list[dict[str, Any]] = []
        for rid in resource_ids:
            can_view = client.check_permission("document", rid, "view", "user", sub)
            can_edit = client.check_permission("document", rid, "edit", "user", sub)
            is_narrowed = client.check_permission("document", rid, "narrow_view", "user", sub)

            # Determine relation
            user_rels = [
                r["relation"] for r in rels if r["resource_id"] == rid and r["subject_id"] == sub
            ]

            access_list.append(
                {
                    "resource": f"document:{rid}",
                    "resource_id": rid,
                    "relations": user_rels,
                    "permissions": {
                        "view": can_view,
                        "edit": can_edit,
                        "narrow_view": is_narrowed,
                    },
                    "effective_access": "Full Access"
                    if can_edit
                    else ("View Only" if can_view else "No Access"),
                }
            )

        return access_list
    except Exception as exc:
        logger.warning("Failed to evaluate user access: %s", exc)
        return []
    finally:
        client.close()
