"""Wait for minimum playback buffer before starting FFmpeg (Tunarr-style head start)."""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
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

# On-tune YouTube full-cache: allow yt-dlp to finish (download_now is ungated).
# 15s was too short for ~80–100 MB music videos → stream-miss + Plex spinner.
_YOUTUBE_TUNE_WAIT_CAP_SEC = 60.0
_MIN_YOUTUBE_MP4_BYTES = 50_000


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
    """Cap blocking wait so Plex tuners do not spin on long RAM-cache fills.

    YouTube full-cache on tune: short cap then skip item (no CDN — mid-stream 403).
    """
    if yt_full and on_tune:
        return min(
            youtube_cache_wait_seconds(),
            max(tune_max_wait_seconds(), _YOUTUBE_TUNE_WAIT_CAP_SEC),
        )
    if yt_full:
        return youtube_cache_wait_seconds()
    if on_tune:
        return tune_max_wait_seconds()
    return 120.0


def _youtube_disk_mp4(cache_manager: CacheManager, source_id: str) -> Optional[Path]:
    """Return on-disk youtube/{id}.mp4 if present (even when DB status is stale)."""
    path = cache_manager.cache_dir / "youtube" / f"{source_id}.mp4"
    try:
        if path.is_file() and path.stat().st_size >= _MIN_YOUTUBE_MP4_BYTES:
            return path
    except OSError:
        return None
    return None


def _adopt_youtube_disk_file(
    cache_manager: CacheManager,
    download_queue: DownloadQueue,
    media_item: MediaItem,
) -> bool:
    """If the mp4 is already on TunarrRAM, mark READY and return True."""
    source_id = media_item.source_id
    disk = _youtube_disk_mp4(cache_manager, source_id)
    if disk is None:
        return False
    if cache_manager.get_cached_path(source_id):
        return True
    try:
        # Ensure manifest row exists, then mark READY from disk.
        download_queue.cache_manager.queue_for_download(media_item)
        cache_manager.register_download_complete(source_id, disk)
        logger.info(
            "Adopted on-disk YouTube cache %s → %s",
            source_id,
            disk,
        )
        return True
    except Exception as exc:
        logger.warning("Failed to adopt on-disk YouTube %s: %s", source_id, exc)
        # Still allow playback if file exists — callers treat True as buffered.
        return True

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

    # Kickstart / DB race: file on TunarrRAM but manifest not READY yet.
    if (
        media_item.source == StreamSource.YOUTUBE
        and youtube_full_cache_enabled()
        and _adopt_youtube_disk_file(cache_manager, download_queue, media_item)
    ):
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
            # Bypass prefetch gates: reload MediaItem in a task and download_now.
            media_id = media_item.id
            source_id = media_item.source_id
            if source_id not in download_queue._in_flight:
                download_queue._in_flight.add(source_id)
                factory = download_queue.db_session_factory

                async def _on_air_youtube_download() -> None:
                    db = factory()
                    try:
                        from streamtv.database.models import MediaItem as _MI

                        item = db.query(_MI).filter(_MI.id == media_id).first()
                        if item is None:
                            logger.warning(
                                "Channel %s: on-air YouTube media_id=%s missing",
                                channel_number,
                                media_id,
                            )
                            return
                        logger.info(
                            "Channel %s: on-air YouTube download_now %s",
                            channel_number,
                            source_id,
                        )
                        await download_queue.download_now(item)
                    except Exception as exc:
                        logger.warning(
                            "Channel %s: on-air YouTube download failed for %s: %s",
                            channel_number,
                            source_id,
                            exc,
                        )
                    finally:
                        db.close()
                        download_queue._in_flight.discard(source_id)

                asyncio.create_task(_on_air_youtube_download())
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

        if _youtube_disk_mp4(cache_manager, media_item.source_id):
            _adopt_youtube_disk_file(cache_manager, download_queue, media_item)
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
        if yt_full:
            # Refuse googlevideo CDN fallback — signed URL mid-stream 403 stutter.
            if cache_manager.get_cached_path(media_item.source_id) or (
                cache_manager.get_playable_path(media_item.source_id)
            ):
                return True
            if _youtube_disk_mp4(cache_manager, media_item.source_id):
                _adopt_youtube_disk_file(cache_manager, download_queue, media_item)
                return True
            logger.warning(
                f"Channel {channel_number}: YouTube full-cache tune wait "
                f"({max_block:.0f}s) timed out with no local file for "
                f"{media_item.title[:60]}; skipping item (no CDN fallback)"
            )
            return False
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
