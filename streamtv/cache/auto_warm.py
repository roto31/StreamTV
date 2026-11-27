"""Idle-channel YouTube full-cache auto-warm.

With ``tune_only_buffer`` + ``playback_mode=buffer``, continuous ChannelStreams
sleep on a 15s idle loop and never re-enter boundary prefetch. Wall-clock
YouTube openings therefore stay cold until a Plex zap. This module fills that
gap: periodically enqueue / prioritize the on-air + lookahead YouTube window
without HDHomeRun tune or CDN fallback.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Sequence

from streamtv.database.models import MediaItem, StreamSource

logger = logging.getLogger(__name__)


def auto_warm_enabled() -> bool:
    """True when idle YouTube full-cache auto-warm should run."""
    from streamtv.config import config
    from streamtv.cache.playback_mode import youtube_full_cache_enabled

    if not youtube_full_cache_enabled():
        return False
    return bool(getattr(config.cache, "auto_warm_enabled", True))


def auto_warm_interval_seconds() -> float:
    from streamtv.config import config

    raw = float(getattr(config.cache, "auto_warm_interval_seconds", 60.0) or 60.0)
    return max(15.0, raw)


def select_youtube_warm_items(
    schedule_items: Sequence[Dict[str, Any]],
    start_index: int,
    count: int,
) -> List[MediaItem]:
    """Return YouTube MediaItems in ``[start_index, start_index + count)``."""
    if count <= 0 or not schedule_items:
        return []
    if start_index < 0 or start_index >= len(schedule_items):
        return []
    end = min(start_index + count, len(schedule_items))
    out: List[MediaItem] = []
    for item in schedule_items[start_index:end]:
        media = item.get("media_item") if isinstance(item, dict) else None
        if media is None:
            continue
        if getattr(media, "source", None) != StreamSource.YOUTUBE:
            continue
        if not getattr(media, "source_id", None):
            continue
        out.append(media)
    return out


async def warm_idle_youtube_window(
    *,
    channel_number: str,
    schedule_items: Sequence[Dict[str, Any]],
    guide_index: int,
    download_queue: Any,
    last_warm_mono: float,
    now_mono: Optional[float] = None,
    prefetch_count: Optional[int] = None,
) -> float:
    """Enqueue / prioritize on-air YouTube window when due.

    Returns the updated ``last_warm_mono`` (unchanged when skipped).
    """
    if download_queue is None or not auto_warm_enabled():
        return last_warm_mono

    now = time.monotonic() if now_mono is None else now_mono
    interval = auto_warm_interval_seconds()
    if last_warm_mono > 0 and (now - last_warm_mono) < interval:
        return last_warm_mono

    from streamtv.config import config

    count = (
        prefetch_count
        if prefetch_count is not None
        else int(getattr(config.cache, "prefetch_count", 3) or 3)
    )
    count = max(1, count)
    items = select_youtube_warm_items(schedule_items, guide_index, count)
    if not items:
        # Still advance the timer so archive-led windows do not re-check every 15s.
        return now

    for media in items:
        await download_queue.enqueue(media)
    head = items[0]
    await download_queue.ensure_download_started(head)
    await download_queue.prioritize(head)
    logger.info(
        "Channel %s: auto-warm YouTube window idx=%s count=%s head=%s",
        channel_number,
        guide_index,
        len(items),
        getattr(head, "source_id", "?"),
    )
    return now
