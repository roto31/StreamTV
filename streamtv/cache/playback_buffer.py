"""Wait for minimum playback buffer before starting FFmpeg (Tunarr-style head start)."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Callable, Optional

from streamtv.config import config
from streamtv.database.models import MediaItem, StreamSource
from streamtv.cache.cache_manager import CacheManager
from streamtv.cache.download_queue import DownloadQueue
from streamtv.cache.playback_mode import (
    playback_mode,
    prefetch_downloads_enabled,
    ring_buffer_max_bytes,
    tune_only_buffering,
    youtube_full_cache_enabled,
)

logger = logging.getLogger(__name__)

def min_buffer_seconds() -> float:
    return max(0.0, float(getattr(config.cache, "stream_buffer_seconds", 0.0) or 0.0))

def tune_max_wait_seconds() -> float:
    """Max seconds to block a live tuner before starting CDN playback."""
    raw = float(getattr(config.cache, "tune_buffer_max_wait_seconds", 5.0) or 5.0)
    return max(0.0, raw)

def youtube_cache_wait_seconds() -> float:
    """Max wait for YouTube full-cache download before CDN fallback (background)."""
    raw = float(
        getattr(config.cache, "youtube_cache_wait_seconds", 120.0) or 120.0
    )
    return max(0.0, raw)


def resolve_buffer_max_wait_seconds(*, on_tune: bool, yt_full: bool) -> float:
    """Cap blocking wait so Plex tuners do not spin on long RAM-cache fills."""
    if yt_full and on_tune:
        return tune_max_wait_seconds()
    if yt_full:
        return youtube_cache_wait_seconds()
    if on_tune:
        return tune_max_wait_seconds()
    return 120.0

def buffer_wait_enabled() -> bool:
    return (
        config.cache.enabled
        and playback_mode() in ("buffer", "full")
        and min_buffer_seconds() > 0
    )

async def wait_for_playback_buffer(
    media_item: MediaItem,
    cache_manager: CacheManager,
    download_queue: DownloadQueue,
    *,
    channel_number: str,
    tuner_active: bool,
    on_wait_tick: Optional[Callable[[], None]] = None,
    is_running: Optional[Callable[[], bool]] = None,
) -> bool:
    """Block until enough media is buffered, or timeout.

    In tune-only buffer mode, skips download/wait when no tuner is connected.
    When a tuner is connected, caps blocking wait so Plex does not time out.
    """
    wait_started = time.monotonic()

    if not buffer_wait_enabled():
        return True

    if tune_only_buffering() and not tuner_active:
        return True

    if not prefetch_downloads_enabled() and playback_mode() != "full":
        if not tune_only_buffering() and not (
            media_item.source == StreamSource.YOUTUBE
            and youtube_full_cache_enabled()
        ):
            return True

    min_sec = min_buffer_seconds()
    if cache_manager.get_cached_path(media_item.source_id):
        return True

    playable = cache_manager.get_playable_path(media_item.source_id)
    if playable and not tune_only_buffering():
        return True

    on_tune = tune_only_buffering() and tuner_active
    yt_full = (
        media_item.source == StreamSource.YOUTUBE
        and youtube_full_cache_enabled()
    )
    max_block = resolve_buffer_max_wait_seconds(on_tune=on_tune, yt_full=yt_full)
    target_sec = min_sec if not on_tune else min(min_sec, max_block)

    cache_manager.evict_lru_to_fit(ring_buffer_max_bytes())

    # Live tuner + CDN-first: do not block Plex on ring-buffer fill.
    # Runtime (ch80): 20s wait + keepalive-only → client disconnect before FFmpeg.
    from streamtv.cache.playback_mode import direct_stream_first

    if on_tune and direct_stream_first() and not yt_full:
        if tune_only_buffering():
            asyncio.create_task(
                download_queue.ensure_ring_buffer(
                    media_item, ring_buffer_max_bytes()
                )
            )
        logger.info(
            f"Channel {channel_number}: CDN-first tune — skip buffer wait for "
            f"{media_item.title[:60]}"
        )
        return True

    # YouTube live tune: skip ring-buffer wait unless youtube_full_cache (RAM download).
    if on_tune and media_item.source == StreamSource.YOUTUBE and not yt_full:
        logger.info(
            f"Channel {channel_number}: YouTube tune — skip buffer wait for "
            f"{media_item.title[:60]}"
        )
        return True

    if yt_full or tune_only_buffering():
        if yt_full:
            await download_queue.ensure_download_started(media_item)
        elif tune_only_buffering():
            await download_queue.ensure_ring_buffer(
                media_item, ring_buffer_max_bytes()
            )
    else:
        await download_queue.ensure_download_started(media_item)

    deadline = wait_started + max_block
    logged = False

    while time.monotonic() < deadline:
        if is_running is not None and not is_running():
            return False

        if cache_manager.get_cached_path(media_item.source_id):
            return True

        buffered = cache_manager.estimate_buffered_seconds(
            media_item.source_id, media_item
        )
        if buffered >= target_sec:
            logger.info(
                f"Channel {channel_number}: playback buffer ready "
                f"({buffered:.1f}s / {target_sec:.0f}s) for "
                f"{media_item.title[:60]}"
            )
            return True

        if not logged:
            if on_tune:
                logger.info(
                    f"Channel {channel_number}: tune buffer (max {max_block:.0f}s wait) "
                    f"for {media_item.title[:60]}"
                )
            else:
                logger.info(
                    f"Channel {channel_number}: waiting for {target_sec:.0f}s buffer "
                    f"before playback ({media_item.title[:60]})"
                )
            logged = True

        if on_wait_tick is not None:
            on_wait_tick()

        await asyncio.sleep(0.25)

    if on_tune:
        logger.info(
            f"Channel {channel_number}: tune buffer cap ({max_block:.0f}s) reached; "
            f"starting CDN stream for {media_item.title[:60]}"
        )
        return True

    logger.warning(
        f"Channel {channel_number}: buffer wait timed out after {max_block:.0f}s for "
        f"{media_item.title[:60]}; starting playback anyway"
    )
    return True
