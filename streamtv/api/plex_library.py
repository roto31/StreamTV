"""Native Plex library browse API (fallback when Tunarr is unavailable)."""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..config import config
from ..database import get_db
from .auth_checker import verify_api_key
from .media import PlexRatingKeyRequest, create_media_from_plex_rating_key

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/plex",
    tags=["Plex Library"],
    dependencies=[Depends(verify_api_key)],
)


class PlexBulkImportRequest(BaseModel):
    rating_keys: list[str] = Field(..., min_length=1, max_length=100)


def _plex_headers() -> dict[str, str]:
    headers = {
        "X-Plex-Product": "StreamTV",
        "X-Plex-Version": "1.0.0",
        "X-Plex-Client-Identifier": "streamtv-plex-library",
        "Accept": "application/json",
    }
    if config.plex.token:
        headers["X-Plex-Token"] = config.plex.token
    return headers


def _require_plex() -> str:
    if not config.plex.enabled or not config.plex.base_url:
        raise HTTPException(status_code=400, detail="Plex is not enabled")
    if not config.plex.token:
        raise HTTPException(status_code=400, detail="Plex token is not configured")
    return config.plex.base_url.rstrip("/")


async def _plex_get_json(path: str, *, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    base = _require_plex()
    url = f"{base}{path}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, headers=_plex_headers(), params=params)
        resp.raise_for_status()
        return resp.json()


def _directories(payload: dict[str, Any]) -> list[dict[str, Any]]:
    container = payload.get("MediaContainer") or {}
    items = container.get("Directory") or container.get("Metadata") or []
    if isinstance(items, dict):
        items = [items]
    out: list[dict[str, Any]] = []
    for item in items:
        rating_key = str(item.get("ratingKey") or item.get("key") or "")
        if not rating_key:
            continue
        out.append(
            {
                "rating_key": rating_key,
                "title": item.get("title") or item.get("tag") or "Untitled",
                "type": item.get("type") or "",
                "child_count": item.get("childCount"),
                "leaf_count": item.get("leafCount"),
            }
        )
    return out


@router.get("/libraries")
async def list_plex_libraries() -> list[dict[str, Any]]:
    """List Plex movie/show libraries (native fallback)."""
    data = await _plex_get_json("/library/sections")
    return [
        {"id": item["rating_key"], "title": item["title"], "type": item["type"]}
        for item in _directories(data)
    ]


@router.get("/libraries/{section_id}/children")
async def list_plex_library_children(section_id: str) -> list[dict[str, Any]]:
    """List shows or movies in a Plex library section."""
    data = await _plex_get_json(f"/library/sections/{section_id}/all")
    return _directories(data)


@router.get("/metadata/{rating_key}/children")
async def list_plex_metadata_children(rating_key: str) -> list[dict[str, Any]]:
    """List seasons/episodes under a Plex metadata item."""
    data = await _plex_get_json(f"/library/metadata/{rating_key}/children")
    return _directories(data)


@router.post("/media/bulk", status_code=status.HTTP_201_CREATED)
async def bulk_import_plex_media(
    body: PlexBulkImportRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Create MediaItem rows from Plex rating keys."""
    created: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for key in body.rating_keys:
        try:
            item = await create_media_from_plex_rating_key(
                PlexRatingKeyRequest(rating_key=key),
                db,
            )
            created.append({"id": item.id, "title": item.title, "rating_key": key})
        except HTTPException as exc:
            errors.append({"rating_key": key, "detail": str(exc.detail)})
        except Exception as exc:
            logger.warning("Plex bulk import failed for %s: %s", key, exc)
            errors.append({"rating_key": key, "detail": str(exc)})
    return {"created": created, "errors": errors, "source": "native"}
