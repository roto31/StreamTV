"""Persistent Archive.org ffprobe results (Lesson 41c).

Non-faststart multi-GB Archive MP4s (moov at the tail) can take ~40s to probe
over HTTP, so live tunes miss the probe budget and fall back to Issue 23
force-libx264. Codec info for an Archive file is immutable, so a real past
ffprobe success is safe to reuse. Never store inferred (unprobed) results.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Optional
from urllib.parse import unquote, urlparse

from streamtv.config import config

logger = logging.getLogger(__name__)

PROBE_CACHE_TTL_SEC = 30 * 24 * 3600
SIDECAR_SUFFIX = ".probe.json"
# Separate from archive_org/: Archive cache lookups scan that tree by filename
# token (e.g. "*h264*") and must never pick up a sidecar as media.
SIDECAR_DIRNAME = "archive_probe"
_STORED_KEYS = (
    "video_codec",
    "audio_codec",
    "container_format",
    "container",
    "can_copy_video",
    "can_copy_audio",
    "needs_annexb_filter",
    "needs_annexb",
    "subtitle_streams",
    "audio_language",
    # Video geometry: written by scripts/warm_archive_probe_cache.py; read by
    # tuners/video_hold to pick a hold asset that matches the program SPS.
    "width",
    "height",
    "profile",
)


def video_geometry(codec_info: Optional[dict[str, Any]]) -> Optional[tuple[int, int]]:
    """Return (width, height) from sidecar codec info, or None if absent/invalid."""
    if not codec_info:
        return None
    try:
        width = int(codec_info.get("width") or 0)
        height = int(codec_info.get("height") or 0)
    except (TypeError, ValueError):
        return None
    if width <= 0 or height <= 0:
        return None
    return width, height


def archive_item_key(stream_url: str) -> Optional[tuple[str, str]]:
    """Return (identifier, filename) for archive.org /download/ or /items/ URLs."""
    parsed = urlparse(stream_url)
    path = unquote(parsed.path or "")
    parts = [p for p in path.strip("/").split("/") if p]
    for marker in ("download", "items"):
        if marker in parts:
            i = parts.index(marker)
            if len(parts) > i + 2:
                return parts[i + 1], "/".join(parts[i + 2 :])
    return None


def sidecar_path(identifier: str, filename: str) -> Path:
    safe_name = filename.replace("/", "__")
    return (
        Path(config.cache.cache_directory).expanduser()
        / SIDECAR_DIRNAME
        / identifier
        / f"{safe_name}{SIDECAR_SUFFIX}"
    )


def load(stream_url: str, *, now: Optional[float] = None) -> Optional[dict[str, Any]]:
    """Return cached codec info for this Archive URL, or None if missing/expired."""
    key = archive_item_key(stream_url)
    if key is None:
        return None
    path = sidecar_path(*key)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Archive probe cache unreadable %s: %s", path, exc)
        return None
    probed_at = float(payload.get("probed_at") or 0)
    current = time.time() if now is None else now
    if current - probed_at > PROBE_CACHE_TTL_SEC:
        return None
    info = payload.get("codec_info")
    if not isinstance(info, dict) or not info.get("video_codec"):
        return None
    return info


def save(stream_url: str, codec_info: dict[str, Any]) -> bool:
    """Persist a real ffprobe result. Returns False for inferred or non-Archive input."""
    if codec_info.get("probe_inferred"):
        return False
    if not codec_info.get("video_codec") or codec_info.get("video_codec") == "unknown":
        return False
    key = archive_item_key(stream_url)
    if key is None:
        return False
    path = sidecar_path(*key)
    payload = {
        "identifier": key[0],
        "filename": key[1],
        "probed_at": time.time(),
        "codec_info": {k: codec_info[k] for k in _STORED_KEYS if k in codec_info},
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        os.replace(tmp, path)
    except OSError as exc:
        logger.warning("Archive probe cache write failed %s: %s", path, exc)
        return False
    return True
