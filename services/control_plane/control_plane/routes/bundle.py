"""Config bundle compilation and version polling routes."""

from fastapi import APIRouter, Depends, Header, Response, status
from shared.schemas.gateway import ConfigBundle, ConfigVersionResponse

from control_plane.deps import get_repository
from control_plane.repositories import ConfigRepository

router = APIRouter(prefix="/api/v1/config", tags=["config"])


@router.get("/version", response_model=ConfigVersionResponse)
async def get_config_version(
    repo: ConfigRepository = Depends(get_repository),
) -> ConfigVersionResponse:
    """Return the current configuration version and timestamp for polling."""
    return await repo.get_version()


@router.get("/bundle", response_model=ConfigBundle)
async def get_config_bundle(
    response: Response,
    if_none_match: str | None = Header(default=None),
    repo: ConfigRepository = Depends(get_repository),
) -> ConfigBundle | Response:
    """Return the compiled configuration bundle, with ETag caching support."""
    bundle = await repo.compile_bundle()

    if if_none_match and if_none_match.strip() == bundle.etag:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED)

    response.headers["ETag"] = bundle.etag
    return bundle
