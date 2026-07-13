"""Serve cached media files with safe handling for in-progress .part downloads."""

from __future__ import annotations

import logging
import mimetypes
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, Response, StreamingResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cache"])

_cache_root: Optional[Path] = None


def configure_cache_serving(cache_dir: Path) -> None:
    """Bind the cache directory used by /cache/files routes."""
    global _cache_root
    _cache_root = cache_dir.expanduser().resolve()
    logger.info("Cache file routes configured → %s", _cache_root)


def _resolve_cache_path(file_path: str) -> Path:
    if _cache_root is None:
        raise HTTPException(status_code=503, detail="Cache serving not configured")
    candidate = (_cache_root / file_path).resolve()
    if not str(candidate).startswith(str(_cache_root)):
        raise HTTPException(status_code=403, detail="Invalid cache path")
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="Cache file not found")
    return candidate


def _is_partial_download(path: Path) -> bool:
    return path.suffix == ".part" or path.name.endswith(".part")


def _guess_media_type(path: Path) -> str:
    if _is_partial_download(path):
        base = path.name
        if base.endswith(".part"):
            base = base[:-5]
        guessed, _ = mimetypes.guess_type(base)
        return guessed or "application/octet-stream"
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


async def _stream_file_chunks(path: Path, chunk_size: int = 1024 * 1024):
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            yield chunk


@router.api_route("/cache/files/{file_path:path}", methods=["GET", "HEAD"])
async def serve_cache_file(file_path: str, request: Request):
    """Serve cached files; partial .part downloads use chunked encoding (no Content-Length)."""
    path = _resolve_cache_path(file_path)
    media_type = _guess_media_type(path)

    if request.method == "HEAD":
        headers = {
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-cache" if _is_partial_download(path) else "public, max-age=3600",
        }
        if not _is_partial_download(path):
            headers["Content-Length"] = str(path.stat().st_size)
        return Response(status_code=200, media_type=media_type, headers=headers)

    if _is_partial_download(path):
        return StreamingResponse(
            _stream_file_chunks(path),
            media_type=media_type,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Accept-Ranges": "none",
                "Transfer-Encoding": "chunked",
            },
        )

    return FileResponse(
        path,
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=3600"},
    )
