"""Async HTTP client for Tunarr REST API (read-only proxy operations)."""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class TunarrClient:
    """Thin wrapper around Tunarr OpenAPI routes used by StreamTV hybrid UI."""

    def __init__(self, base_url: str, *, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def _get_json(self, path: str, *, params: Optional[dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()

    async def health(self) -> dict[str, Any]:
        try:
            data = await self._get_json("/system/health")
            return {"reachable": True, "health": data}
        except Exception as exc:
            logger.debug("Tunarr health check failed for %s: %s", self.base_url, exc)
            return {"reachable": False, "error": str(exc)}

    async def list_media_sources(self) -> list[dict[str, Any]]:
        data = await self._get_json("/media-sources")
        return data if isinstance(data, list) else []

    async def list_libraries(self, media_source_id: str) -> list[dict[str, Any]]:
        data = await self._get_json(f"/media-sources/{media_source_id}/libraries")
        return data if isinstance(data, list) else []

    async def list_library_programs(
        self,
        library_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        data = await self._get_json(
            f"/media-libraries/{library_id}/programs",
            params={"limit": limit, "offset": offset},
        )
        return data if isinstance(data, list) else []

    async def search_programs(self, query: str, *, limit: int = 25) -> list[dict[str, Any]]:
        data = await self._get_json(
            "/programs/search",
            params={"query": query, "limit": limit},
        )
        return data if isinstance(data, list) else []

    async def list_custom_shows(self) -> list[dict[str, Any]]:
        data = await self._get_json("/custom-shows")
        return data if isinstance(data, list) else []

    async def list_smart_collections(self) -> list[dict[str, Any]]:
        data = await self._get_json("/smart_collections")
        return data if isinstance(data, list) else []

    async def list_filler_lists(self) -> list[dict[str, Any]]:
        data = await self._get_json("/filler-lists")
        return data if isinstance(data, list) else []
