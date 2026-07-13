"""Schedule and playout media format filters (MP4-first)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ..config import config
from ..database.models import MediaItem, StreamSource
from ..streaming.archive_org_playback import is_playable_archive_org_mp4

if TYPE_CHECKING:
    from .parser import ParsedSchedule


def _content_media_rules(
    schedule: "ParsedSchedule", content_key: Optional[str]
) -> Dict[str, Any]:
    rules: Dict[str, Any] = dict(getattr(schedule, "media_defaults", {}) or {})
    if content_key and content_key in schedule.content_map:
        for key, value in schedule.content_map[content_key].items():
            if key in ("preferred_extension", "mp4_only", "preferred_format"):
                rules[key] = value
    return rules


def mp4_only_for_content(
    schedule: "ParsedSchedule", content_key: Optional[str]
) -> bool:
    rules = _content_media_rules(schedule, content_key)
    if "mp4_only" in rules:
        return bool(rules["mp4_only"])
    return bool(getattr(config.archive_org, "mp4_only", True))


def filter_media_items(
    media_items: List[MediaItem],
    schedule: "ParsedSchedule",
    content_key: Optional[str] = None,
) -> List[MediaItem]:
    """Drop archive.org items that fail MP4-only rules for this schedule/content."""
    if not mp4_only_for_content(schedule, content_key):
        return media_items
    return [m for m in media_items if is_playable_archive_org_mp4(m)]
