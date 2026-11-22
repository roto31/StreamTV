"""Stable stream ids for Channel Builder (D2 / D15 / D16).

Reimplements Archive.org source-id shape without importing frozen streaming code.
"""

from __future__ import annotations

import hashlib
import re
from typing import Optional
from urllib.parse import unquote, urlparse


_SAFE_RE = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_id_part(text: str) -> str:
    return _SAFE_RE.sub("_", text).strip("_") or "item"


def youtube_stream_id(channel_number: str, video_id: str) -> str:
    return f"{channel_number}_yt_{video_id}"


def archive_stream_id(identifier: str, filename: str, *, url: Optional[str] = None) -> str:
    """Archive file id: ``{identifier}__{decoded_filename}`` (no silent truncation).

    Characters outside ``[A-Za-z0-9._-]`` become ``_``. Paths with ``/`` become ``__``.
    If longer than 120 chars: first 100 + ``_`` + first 10 hex of sha1(url or id).
    """
    decoded = unquote(filename or "").replace("/", "__")
    raw = f"{identifier}__{decoded}" if identifier else decoded
    sid = sanitize_id_part(raw)
    if len(sid) <= 120:
        return sid
    digest_src = url or sid
    digest = hashlib.sha1(digest_src.encode("utf-8")).hexdigest()[:10]
    return f"{sid[:100]}_{digest}"


def archive_stream_id_from_url(url: str) -> str:
    parsed = urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]
    # /download/<identifier>/<filename...>
    identifier = ""
    filename = ""
    if "download" in parts:
        i = parts.index("download")
        if i + 1 < len(parts):
            identifier = unquote(parts[i + 1])
        if i + 2 < len(parts):
            filename = unquote("/".join(parts[i + 2 :]))
    elif "details" in parts:
        i = parts.index("details")
        if i + 1 < len(parts):
            identifier = unquote(parts[i + 1])
    return archive_stream_id(identifier, filename, url=url)
