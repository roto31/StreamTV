"""URL resolution for Channel Builder — Archive.org, YouTube, PBS, Plex, community."""

from __future__ import annotations

import re
from typing import Any, Optional
from urllib.parse import quote, unquote, urlparse

import requests
import yt_dlp

from streamtv.builder.pbs_show import expand_pbs_show
from streamtv.builder.sources import detect_source_for_url, get_source
from streamtv.builder.titles import humanize_media_title, title_from_media_url
from streamtv.youtube.ydl_opts import youtube_ydl_opts

from .models import BuilderDraft

ARCHIVE_DETAILS_RE = re.compile(
    r"archive\.org/details/([^/?#]+)", re.IGNORECASE
)
ARCHIVE_DOWNLOAD_RE = re.compile(
    r"archive\.org/download/([^/?#]+)", re.IGNORECASE
)
YOUTUBE_PLAYLIST_RE = re.compile(
    r"(?:youtube\.com|youtu\.be).*(?:list=|/playlist)", re.IGNORECASE
)
VIDEO_EXTENSIONS = (".mp4", ".avi", ".mkv", ".mov", ".m4v", ".webm")


def detect_url_kind(url: str) -> str:
    lower = url.lower().strip()
    if "archive.org/details/" in lower or (
        "archive.org/download/" in lower and "/" in lower.split("download/", 1)[-1]
    ):
        if ARCHIVE_DETAILS_RE.search(url) and not _is_archive_file_url(url):
            return "archive_collection"
    if "archive.org" in lower or "archive" in lower:
        return "archive"
    if YOUTUBE_PLAYLIST_RE.search(url):
        return "youtube_playlist"
    if "youtube.com" in lower or "youtu.be" in lower:
        return "youtube"
    if "pbs.org" in lower:
        path = urlparse(url).path.lower().rstrip("/")
        if "/show/" in path and "/video/" not in path:
            return "pbs_show"
        return "pbs"
    if lower.startswith("plex://") or "/library/metadata/" in lower:
        return "plex"
    community = detect_source_for_url(url)
    if community and community.status == "community":
        return f"community:{community.id.split(':', 1)[-1]}"
    return "unknown"


def _is_archive_file_url(url: str) -> bool:
    path = urlparse(url).path.lower()
    return any(path.endswith(ext) for ext in VIDEO_EXTENSIONS)


def _extract_archive_identifier(url: str) -> Optional[str]:
    for pattern in (ARCHIVE_DETAILS_RE, ARCHIVE_DOWNLOAD_RE):
        match = pattern.search(url)
        if match:
            return match.group(1)
    stripped = url.strip().rstrip("/")
    if "/" not in stripped and "?" not in stripped:
        return stripped
    return None


def _slugify(text: str, max_len: int = 48) -> str:
    """Legacy short slug (fillers / non-archive). Archive file ids use ``ids.archive_stream_id``."""
    slug = re.sub(r"[^\w]+", "_", text.lower()).strip("_")
    return slug[:max_len] or "item"


def fetch_archive_metadata(identifier: str) -> dict[str, Any]:
    """Fetch Archive.org item metadata JSON (includes per-file ``length``)."""
    api_url = f"https://archive.org/metadata/{identifier}"
    response = requests.get(api_url, timeout=60)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError(f"Unexpected Archive.org metadata for {identifier}")
    return data


def lookup_archive_file_duration(
    identifier: str,
    filename: str,
    *,
    metadata: Optional[dict[str, Any]] = None,
) -> Optional[int]:
    """Return duration seconds for a file inside an Archive.org item, if known.

    Uses the metadata API ``files[].length`` field (seconds). Missing length
    returns ``None`` — callers must not invent a default for EPG.
    """
    if not identifier or not filename:
        return None
    data = metadata if metadata is not None else fetch_archive_metadata(identifier)
    target = unquote(filename).rsplit("/", 1)[-1].strip().lower()
    if not target:
        return None
    for file_info in data.get("files") or []:
        if not isinstance(file_info, dict):
            continue
        name = unquote(str(file_info.get("name") or "")).rsplit("/", 1)[-1].strip().lower()
        if name != target:
            continue
        length = file_info.get("length")
        if length is None or length == "":
            return None
        try:
            seconds = int(float(length))
        except (TypeError, ValueError):
            return None
        return seconds if seconds > 0 else None
    return None


def resolve_archive_collection(url: str) -> list[dict[str, Any]]:
    identifier = _extract_archive_identifier(url)
    if not identifier:
        raise ValueError(f"Could not parse Archive.org identifier from: {url}")

    metadata = fetch_archive_metadata(identifier)

    results: list[dict[str, Any]] = []
    for file_info in metadata.get("files", []):
        filename = file_info.get("name", "")
        if not filename.lower().endswith(VIDEO_EXTENSIONS):
            continue
        encoded = quote(filename, safe="")
        file_url = f"https://archive.org/download/{identifier}/{encoded}"
        title = humanize_media_title(filename)
        duration = lookup_archive_file_duration(
            identifier, filename, metadata=metadata
        )
        stream_id = _slugify(f"{identifier}_{filename}")
        results.append(
            {
                "url": file_url,
                "title": title or humanize_media_title(filename),
                "source": "archive_org",
                "stream_id": stream_id,
                "duration": duration,
                "upload_date": metadata.get("metadata", {}).get("date"),
                "expanded_from": url,
            }
        )
    if not results:
        raise ValueError(f"No video files found in Archive.org collection: {identifier}")
    return results


def resolve_youtube_playlist(url: str) -> list[dict[str, Any]]:
    opts = youtube_ydl_opts(
        quiet=True,
        no_warnings=True,
        skip_download=True,
        ignoreerrors=True,
        extract_flat="in_playlist",
    )
    results: list[dict[str, Any]] = []
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    if not info:
        raise ValueError(f"Could not extract YouTube playlist: {url}")
    for entry in info.get("entries") or []:
        if not entry:
            continue
        video_id = entry.get("id")
        if not video_id:
            continue
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        results.append(
            {
                "url": video_url,
                "title": entry.get("title") or "Untitled",
                "source": "youtube",
                "stream_id": video_id,
                "duration": entry.get("duration"),
                "upload_date": entry.get("upload_date"),
                "expanded_from": url,
            }
        )
    if not results:
        raise ValueError(f"No videos found in playlist: {url}")
    return results


def resolve_community_url(url: str, source_id: str) -> dict[str, Any]:
    spec = get_source(source_id)
    if not spec:
        raise ValueError(f"Unknown community source: {source_id}")
    slug = urlparse(url).path.rsplit("/", 1)[-1] or "item"
    title = slug.replace("-", " ").replace("_", " ").title()
    return {
        "url": url,
        "title": title,
        "source": spec.resolver_source,
        "stream_id": _slugify(f"{spec.id}_{url}"),
        "duration": None,
        "upload_date": None,
    }


def resolve_single_url(url: str) -> dict[str, Any]:
    kind = detect_url_kind(url)
    if kind == "archive_collection":
        items = resolve_archive_collection(url)
        if len(items) == 1:
            return items[0]
        raise ValueError(
            "URL is an Archive.org collection with multiple files; "
            "use collection import instead of single-link resolve"
        )
    if kind == "youtube_playlist":
        items = resolve_youtube_playlist(url)
        if len(items) == 1:
            return items[0]
        raise ValueError("URL is a playlist; use playlist expansion")

    if kind == "youtube":
        opts = youtube_ydl_opts(quiet=True, no_warnings=True, skip_download=True)
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        if not info:
            raise ValueError(f"Could not resolve YouTube URL: {url}")
        video_id = info.get("id") or _slugify(url)
        return {
            "url": url,
            "title": info.get("title") or "Untitled",
            "source": "youtube",
            "stream_id": video_id,
            "duration": info.get("duration"),
            "upload_date": info.get("upload_date"),
            "thumbnail": info.get("thumbnail"),
        }

    if kind == "archive":
        identifier = _extract_archive_identifier(url)
        title = humanize_media_title(unquote(identifier or "")) or (identifier or url)
        duration: Optional[int] = None
        upload_date: Optional[str] = None
        if _is_archive_file_url(url):
            filename = unquote(urlparse(url).path.rsplit("/", 1)[-1])
            title = title_from_media_url(url) or humanize_media_title(filename)
            from streamtv.builder.ids import archive_stream_id

            stream_id = archive_stream_id(
                identifier or "", filename, url=url
            )
            if identifier:
                try:
                    meta = fetch_archive_metadata(identifier)
                    duration = lookup_archive_file_duration(
                        identifier, filename, metadata=meta
                    )
                    upload_date = (meta.get("metadata") or {}).get("date")
                except Exception:
                    # Leave duration unset; build/import gates require a real length
                    # for Archive streams so EPG slots are not invented.
                    duration = None
        else:
            stream_id = _slugify(identifier or url)
        return {
            "url": url,
            "title": title,
            "source": "archive_org",
            "stream_id": stream_id,
            "duration": duration,
            "upload_date": upload_date,
        }

    if kind == "pbs":
        path = urlparse(url).path.lower().rstrip("/")
        slug = path.rsplit("/", 1)[-1] if path else "pbs_item"
        title = slug.replace("-", " ").title()
        if "/video/" in path:
            title = f"PBS Video — {title}"
        return {
            "url": url,
            "title": title,
            "source": "pbs",
            "stream_id": _slugify(url),
            "duration": None,
            "upload_date": None,
        }

    if kind == "plex":
        path = urlparse(url).path
        slug = path.rsplit("/", 1)[-1] if path else "plex_item"
        return {
            "url": url,
            "title": f"Plex — {slug}",
            "source": "plex",
            "stream_id": _slugify(url),
            "duration": None,
            "upload_date": None,
        }

    if kind.startswith("community:"):
        return resolve_community_url(url, f"community:{kind.split(':', 1)[1]}")

    raise ValueError(f"Unsupported or unrecognized URL: {url}")


def expand_url(url: str, *, draft: Optional[BuilderDraft] = None) -> list[dict[str, Any]]:
    """Expand a URL into one or more resolved link dicts."""
    kind = detect_url_kind(url)
    if kind == "archive_collection":
        return resolve_archive_collection(url)
    if kind == "youtube_playlist":
        return resolve_youtube_playlist(url)
    if kind == "pbs_show":
        filter_episodes = bool(draft and draft.pbs_filter_full_episodes)
        min_seconds = draft.pbs_min_episode_seconds if draft else 300
        return expand_pbs_show(
            url,
            filter_full_episodes=filter_episodes,
            min_episode_seconds=min_seconds,
        )
    items = [resolve_single_url(url)]
    if draft and draft.pbs_filter_full_episodes and all(item.get("source") == "pbs" for item in items):
        from streamtv.builder.pbs_episode_filter import filter_full_pbs_episodes

        items = filter_full_pbs_episodes(items, min_seconds=draft.pbs_min_episode_seconds)
        if not items:
            raise ValueError("No full PBS episodes matched the duration/title filter")
    return items


async def resolve_url_async(url: str, *, draft: Optional[BuilderDraft] = None) -> list[dict[str, Any]]:
    import asyncio

    return await asyncio.to_thread(expand_url, url, draft=draft)
