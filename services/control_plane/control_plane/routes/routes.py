"""Gateway route configuration routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from shared.schemas.gateway import RouteConfig

from control_plane.deps import get_repository
from control_plane.repositories import ConfigRepository

router = APIRouter(prefix="/api/v1/routes", tags=["routes"])


@router.get("", response_model=list[RouteConfig])
async def list_routes(
    repo: ConfigRepository = Depends(get_repository),
) -> list[RouteConfig]:
    """List all configured routes."""
    return await repo.list_routes()


@router.post("", response_model=RouteConfig, status_code=status.HTTP_201_CREATED)
async def create_route(
    route: RouteConfig,
    repo: ConfigRepository = Depends(get_repository),
) -> RouteConfig:
    """Create a new route."""
    existing = await repo.get_route(route.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Route with ID '{route.id}' already exists",
        )
    upstream = await repo.get_upstream(route.upstream_id)
    if not upstream:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Target upstream '{route.upstream_id}' does not exist",
        )
    return await repo.save_route(route)


@router.get("/{route_id}", response_model=RouteConfig)
async def get_route(
    route_id: str,
    repo: ConfigRepository = Depends(get_repository),
) -> RouteConfig:
    """Fetch a route by ID."""
    route = await repo.get_route(route_id)
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Route '{route_id}' not found",
        )
    return route


@router.put("/{route_id}", response_model=RouteConfig)
async def update_route(
    route_id: str,
    route: RouteConfig,
    repo: ConfigRepository = Depends(get_repository),
) -> RouteConfig:
    """Update an existing route."""
    if route.id != route_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload ID does not match route parameter",
        )
    existing = await repo.get_route(route_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Route '{route_id}' not found",
        )
    upstream = await repo.get_upstream(route.upstream_id)
    if not upstream:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Target upstream '{route.upstream_id}' does not exist",
        )
    return await repo.save_route(route)


@router.delete("/{route_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_route(
    route_id: str,
    repo: ConfigRepository = Depends(get_repository),
) -> None:
    """Delete a route."""
    deleted = await repo.delete_route(route_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Route '{route_id}' not found",
        )
