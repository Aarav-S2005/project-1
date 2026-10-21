"""Gateway middleware configuration routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from shared.schemas.gateway import MiddlewareConfig

from control_plane.deps import get_repository
from control_plane.repositories import ConfigRepository

router = APIRouter(prefix="/api/v1/middlewares", tags=["middlewares"])


@router.get("", response_model=list[MiddlewareConfig])
async def list_middlewares(
    repo: ConfigRepository = Depends(get_repository),
) -> list[MiddlewareConfig]:
    """List all configured middlewares."""
    return await repo.list_middlewares()


@router.post("", response_model=MiddlewareConfig, status_code=status.HTTP_201_CREATED)
async def create_middleware(
    middleware: MiddlewareConfig,
    repo: ConfigRepository = Depends(get_repository),
) -> MiddlewareConfig:
    """Create a new middleware configuration."""
    existing = await repo.get_middleware(middleware.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Middleware with ID '{middleware.id}' already exists",
        )
    return await repo.save_middleware(middleware)


@router.get("/{middleware_id}", response_model=MiddlewareConfig)
async def get_middleware(
    middleware_id: str,
    repo: ConfigRepository = Depends(get_repository),
) -> MiddlewareConfig:
    """Fetch a middleware configuration by ID."""
    middleware = await repo.get_middleware(middleware_id)
    if not middleware:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Middleware '{middleware_id}' not found",
        )
    return middleware


@router.put("/{middleware_id}", response_model=MiddlewareConfig)
async def update_middleware(
    middleware_id: str,
    middleware: MiddlewareConfig,
    repo: ConfigRepository = Depends(get_repository),
) -> MiddlewareConfig:
    """Update an existing middleware configuration."""
    if middleware.id != middleware_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload ID does not match route parameter",
        )
    existing = await repo.get_middleware(middleware_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Middleware '{middleware_id}' not found",
        )
    return await repo.save_middleware(middleware)


@router.delete("/{middleware_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_middleware(
    middleware_id: str,
    repo: ConfigRepository = Depends(get_repository),
) -> None:
    """Delete a middleware configuration."""
    deleted = await repo.delete_middleware(middleware_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Middleware '{middleware_id}' not found",
        )
