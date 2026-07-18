"""Filter PBS show harvest results to full episodes (skip trailers, short clips)."""

from __future__ import annotations

import re
from typing import Any, Optional

DEFAULT_MIN_EPISODE_SECONDS = 300
SKIP_TITLE_RE = re.compile(
    r"\b(trailer|trailers|preview|previews|sneak peek|teaser|promo|coming soon|"
    r"extended preview|clip reel|resume watching|watch with pbs passport)\b",
    re.IGNORECASE,
)
PASSPORT_URL_RE = re.compile(r"/video/watch-passport-", re.IGNORECASE)


def is_full_pbs_episode(
    item: dict[str, Any],
    *,
    min_seconds: int = DEFAULT_MIN_EPISODE_SECONDS,
) -> bool:
    url = (item.get("url") or "").strip()
    if url and PASSPORT_URL_RE.search(url):
        return False
    title = (item.get("title") or "").strip()
    if not title:
        return False
    if SKIP_TITLE_RE.search(title):
        return False
    duration = item.get("duration")
    if duration is not None and int(duration) < min_seconds:
        return False
    return True


def filter_full_pbs_episodes(
    items: list[dict[str, Any]],
    *,
    min_seconds: int = DEFAULT_MIN_EPISODE_SECONDS,
) -> list[dict[str, Any]]:
    return [item for item in items if is_full_pbs_episode(item, min_seconds=min_seconds)]


def pbs_show_max_videos(override: Optional[int] = None) -> int:
    if override is not None:
        return max(1, int(override))
    try:
        from streamtv.config import config

        return max(1, int(getattr(config.pbs, "show_max_videos", 5000)))
    except Exception:
        return 5000
