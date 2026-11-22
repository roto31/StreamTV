"""Stable stream ids for Channel Builder (D2 / D15 / D16).

Reimplements Archive.org source-id shape without importing frozen streaming code.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
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


def normalize_stream_url(url: str) -> str:
    """Normalize for D16 URL→id index.

    Keeps YouTube ``v=`` (and similar) query params — stripping ``?v=`` would
    collapse every watch URL to the same key. Archive.org download paths are
    decoded; fragments are dropped.
    """
    if not url:
        return ""
    from urllib.parse import parse_qs, urlencode

    parsed = urlparse(url.strip())
    path = unquote(parsed.path or "")
    query = ""
    if parsed.query:
        qs = parse_qs(parsed.query, keep_blank_values=False)
        # Prefer stable video id key order for youtube
        prefer = ["v", "list", "t"]
        ordered: list[tuple[str, str]] = []
        for key in prefer:
            if key in qs and qs[key]:
                ordered.append((key, qs[key][0]))
        for key, vals in sorted(qs.items()):
            if key in prefer:
                continue
            if vals:
                ordered.append((key, vals[0]))
        if ordered:
            query = "?" + urlencode(ordered)
    return f"{parsed.scheme}://{parsed.netloc}{path}{query}".rstrip("/")


def build_url_id_index(data_dir: Path) -> dict[str, str]:
    """Map normalized URL → existing stream id across ``data/*.yaml`` (D16)."""
    import yaml

    index: dict[str, str] = {}
    if not data_dir.is_dir():
        return index
    for path in sorted(data_dir.glob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception:  # noqa: BLE001
            continue
        for ch in data.get("channels") or []:
            for s in ch.get("streams") or []:
                url = normalize_stream_url(str(s.get("url") or ""))
                sid = str(s.get("id") or "")
                if url and sid and url not in index:
                    index[url] = sid
    return index


def apply_existing_url_ids(
    candidates: list[dict],
    data_dir: Path,
) -> tuple[list[dict], list[dict]]:
    """Reuse known stream ids when URL already exists (D16).

    Returns (updated_candidates, reuse_log) where reuse_log entries are
    ``{url, from_id, to_id}``.
    """
    index = build_url_id_index(data_dir)
    out: list[dict] = []
    log: list[dict] = []
    for raw in candidates:
        c = dict(raw)
        url = normalize_stream_url(str(c.get("url") or ""))
        old = str(c.get("id") or "")
        if url and url in index:
            existing = index[url]
            if existing != old:
                log.append({"url": url, "from_id": old, "to_id": existing})
            c["id"] = existing
            c["existing_id"] = existing
        out.append(c)
    return out, log
