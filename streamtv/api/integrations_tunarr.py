"""StreamTV API proxy for Tunarr hybrid workflows (non-bedrock)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from ..integrations.tunarr_client import TunarrClient
from ..integrations.tunarr_config import get_tunarr_base_url
from .auth_checker import verify_api_key

router = APIRouter(
    prefix="/integrations/tunarr",
    tags=["Tunarr Integration"],
    dependencies=[Depends(verify_api_key)],
)


def _client_or_503() -> TunarrClient:
    base = get_tunarr_base_url()
    if not base:
        raise HTTPException(
            status_code=503,
            detail="No Tunarr tuner configured in tuner_manager.tuners",
        )
    return TunarrClient(base)


@router.get("/status")
async def tunarr_status() -> dict[str, Any]:
    """Reachability and configured upstream URL."""
    base = get_tunarr_base_url()
    if not base:
        return {"configured": False, "reachable": False, "url": None}
    client = TunarrClient(base)
    health = await client.health()
    return {
        "configured": True,
        "url": base,
        "web_url": f"{base}/web",
        **health,
    }


@router.get("/media-sources")
async def tunarr_media_sources() -> list[dict[str, Any]]:
    client = _client_or_503()
    return await client.list_media_sources()


@router.get("/media-sources/{media_source_id}/libraries")
async def tunarr_libraries(media_source_id: str) -> list[dict[str, Any]]:
    client = _client_or_503()
    return await client.list_libraries(media_source_id)


@router.get("/libraries/{library_id}/programs")
async def tunarr_library_programs(
    library_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[dict[str, Any]]:
    client = _client_or_503()
    return await client.list_library_programs(library_id, limit=limit, offset=offset)


@router.get("/search")
async def tunarr_search(
    q: str = Query(..., min_length=1),
    limit: int = Query(25, ge=1, le=100),
) -> list[dict[str, Any]]:
    client = _client_or_503()
    return await client.search_programs(q, limit=limit)


@router.get("/custom-shows")
async def tunarr_custom_shows() -> list[dict[str, Any]]:
    client = _client_or_503()
    return await client.list_custom_shows()


@router.get("/smart-collections")
async def tunarr_smart_collections() -> list[dict[str, Any]]:
    client = _client_or_503()
    return await client.list_smart_collections()


@router.get("/filler-lists")
async def tunarr_filler_lists() -> list[dict[str, Any]]:
    client = _client_or_503()
    return await client.list_filler_lists()
