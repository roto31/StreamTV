"""Archive.org playback helpers shared across channel streaming paths."""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from ..config import config
from ..database.models import MediaItem, StreamSource

if TYPE_CHECKING:
    from .archive_org_adapter import ArchiveOrgAdapter


def archive_org_source_id(
    url: str, adapter: Optional["ArchiveOrgAdapter"] = None
) -> str:
    """Stable cache key for an Archive.org item.

    Collection items under one identifier must include the filename in source_id;
    otherwise all files share one cache row and BUFFER HIT serves the wrong .part
    file (1980 Olympics channel crash).
    """
    if adapter is None:
        from .archive_org_adapter import ArchiveOrgAdapter

        adapter = ArchiveOrgAdapter()
    identifier = adapter.extract_identifier(url)
    filename = adapter.extract_filename(url)
    if identifier and filename:
        safe_name = filename.replace("/", "__")
        return f"{identifier}/{safe_name}"
    if identifier:
        return identifier
    return url


def archive_org_mp4_only_enabled() -> bool:
    return bool(getattr(config.archive_org, "mp4_only", True))


def is_playable_archive_org_mp4(media_item: MediaItem) -> bool:
    """Return True when an archive.org item should be streamed (MP4/H.264 path)."""
    if media_item.source != StreamSource.ARCHIVE_ORG:
        return True
    if not archive_org_mp4_only_enabled():
        return True
    url_path = media_item.url.lower().split("?")[0].split("#")[0]
    return ".mp4" in url_path


def skip_non_mp4_archive_item(media_item: MediaItem) -> bool:
    """Return True when the playout loop should skip this archive.org item."""
    return not is_playable_archive_org_mp4(media_item)
