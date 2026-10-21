"""Upstream service management routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from shared.schemas.gateway import UpstreamConfig

from control_plane.deps import get_repository
from control_plane.repositories import ConfigRepository

router = APIRouter(prefix="/api/v1/upstreams", tags=["upstreams"])


@router.get("", response_model=list[UpstreamConfig])
async def list_upstreams(
    repo: ConfigRepository = Depends(get_repository),
) -> list[UpstreamConfig]:
    """List all upstream services."""
    return await repo.list_upstreams()


@router.post("", response_model=UpstreamConfig, status_code=status.HTTP_201_CREATED)
async def create_upstream(
    upstream: UpstreamConfig,
    repo: ConfigRepository = Depends(get_repository),
) -> UpstreamConfig:
    """Create a new upstream service."""
    existing = await repo.get_upstream(upstream.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Upstream with ID '{upstream.id}' already exists",
        )
    return await repo.save_upstream(upstream)


@router.get("/{upstream_id}", response_model=UpstreamConfig)
async def get_upstream(
    upstream_id: str,
    repo: ConfigRepository = Depends(get_repository),
) -> UpstreamConfig:
    """Fetch an upstream service by ID."""
    upstream = await repo.get_upstream(upstream_id)
    if not upstream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upstream '{upstream_id}' not found",
        )
    return upstream


@router.put("/{upstream_id}", response_model=UpstreamConfig)
async def update_upstream(
    upstream_id: str,
    upstream: UpstreamConfig,
    repo: ConfigRepository = Depends(get_repository),
) -> UpstreamConfig:
    """Update an existing upstream service."""
    if upstream.id != upstream_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload ID does not match route parameter",
        )
    existing = await repo.get_upstream(upstream_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upstream '{upstream_id}' not found",
        )
    return await repo.save_upstream(upstream)


@router.delete("/{upstream_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_upstream(
    upstream_id: str,
    repo: ConfigRepository = Depends(get_repository),
) -> None:
    """Delete an upstream service."""
    deleted = await repo.delete_upstream(upstream_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upstream '{upstream_id}' not found",
        )
