"""Channel manager for continuous background streaming (StreamTV Schedule v1)."""

import asyncio
import logging
from typing import Any, Dict, Optional, AsyncIterator, List
from datetime import datetime, timedelta, time
from collections import deque
import weakref

from streamtv.database import Channel, MediaItem
from streamtv.database.models import ChannelPlaybackPosition, PlayoutMode, StreamSource
from sqlalchemy.orm import Session
from streamtv.streaming.mpegts_streamer import MPEGTSStreamer
from streamtv.streaming.mpegts_keepalive import keepalive_chunk
from streamtv.streaming.archive_org_playback import skip_non_mp4_archive_item
from streamtv.config import config

# Boot priority: archive-primary first, hybrid second, YouTube-only last.
# YouTube playout defer is per-item (_defer_youtube_playout_until_tuner), not per-channel.


def _youtube_only_boot_defer() -> frozenset:
    return frozenset(str(n) for n in config.playout.youtube_only_boot_defer)


def _hybrid_boot_defer() -> frozenset:
    return frozenset(str(n) for n in config.playout.hybrid_boot_defer)


def _channel_boot_tier(channel_number: str) -> int:
    n = str(channel_number)
    if n in _youtube_only_boot_defer():
        return 2
    if n in _hybrid_boot_defer():
        return 1
    return 0


def _defer_youtube_playout_until_tuner(media_item: MediaItem, client_count: int) -> bool:
    """YouTube-only: skip yt-dlp until a tuner connects. Archive/hybrid archive items unaffected."""
    if media_item.source != StreamSource.YOUTUBE:
        return False
    from streamtv.cache.playback_mode import youtube_full_cache_enabled

    if youtube_full_cache_enabled():
        return False
    return client_count == 0


def _is_youtube_media_item(media_item: MediaItem) -> bool:
    return media_item.source == StreamSource.YOUTUBE

logger = logging.getLogger(__name__)

# ~4 MB buffer per tuned client; Plex probes can pause reads briefly.
_CLIENT_QUEUE_MAXSIZE = 512


def _item_source_id(schedule_items: List[Dict], item_index: int) -> Optional[str]:
    if not (0 <= item_index < len(schedule_items)):
        return None
    media = schedule_items[item_index].get("media_item")
    sid = getattr(media, "source_id", None) if media else None
    return str(sid) if sid else None


def _schedule_source_ids(schedule_items: List[Dict]) -> set[str]:
    """All source_ids referenced by one channel schedule (eviction scope)."""
    keep: set[str] = set()
    for item in schedule_items:
        media = item.get("media_item")
        sid = getattr(media, "source_id", None) if media else None
        if sid:
            keep.add(str(sid))
    return keep


def _schedule_keep_source_ids(
    schedule_items: List[Dict],
    start_index: int,
    prefetch_count: int,
    *,
    extra_keep_source_ids: Optional[set[str]] = None,
) -> set[str]:
    """Source IDs for current item + upcoming prefetch window (off-schedule eviction)."""
    keep: set[str] = set(extra_keep_source_ids or ())
    lo = max(0, start_index - 1)
    hi = min(len(schedule_items), start_index + max(1, prefetch_count))
    for item in schedule_items[lo:hi]:
        media = item.get("media_item")
        sid = getattr(media, "source_id", None) if media else None
        if sid:
            keep.add(str(sid))
    return keep


def _release_finished_item_cache(
    media_item: object,
    *,
    reason: str = "after_play",
) -> None:
    """Tunarr-style: drop RAM cache when an item's playout session ends."""
    from streamtv.cache.playback_mode import evict_after_play_enabled

    if not evict_after_play_enabled():
        return
    sid = getattr(media_item, "source_id", None) if media_item else None
    if not sid:
        return
    from streamtv.cache import get_runtime

    cache_manager, _ = get_runtime()
    if cache_manager:
        cache_manager.evict_source(str(sid), reason=reason)


def _evict_off_schedule_cache(
    schedule_items: List[Dict],
    start_index: int,
    prefetch_count: int,
    *,
    extra_keep_source_ids: Optional[set[str]] = None,
) -> None:
    """Remove cached files not needed for current/upcoming playout."""
    from streamtv.cache.playback_mode import evict_off_schedule_enabled

    if not evict_off_schedule_enabled():
        return
    if not schedule_items:
        return
    from streamtv.cache import get_runtime

    cache_manager, _ = get_runtime()
    if not cache_manager:
        return
    keep = _schedule_keep_source_ids(
        schedule_items,
        start_index,
        prefetch_count,
        extra_keep_source_ids=extra_keep_source_ids,
    )
    cache_manager.evict_sources_not_in(
        keep,
        reason="off_schedule",
        candidate_source_ids=_schedule_source_ids(schedule_items),
    )


async def _prefetch_schedule_items(
    schedule_items: List[Dict],
    start_index: int = 0,
    count: Optional[int] = None,
    *,
    tuner_active: bool = False,
    extra_keep_source_ids: Optional[set[str]] = None,
) -> None:
    """Enqueue upcoming schedule items for background cache download (full / YouTube RAM cache)."""
    from streamtv.config import config
    from streamtv.cache.playback_mode import (
        prefetch_downloads_enabled,
        tune_only_buffering,
        youtube_full_cache_enabled,
        youtube_prefetch_enabled,
    )

    if tune_only_buffering() and not youtube_full_cache_enabled():
        return
    if not youtube_prefetch_enabled():
        return

    prefetch_count = count if count is not None else config.cache.prefetch_count
    if prefetch_count <= 0 or not schedule_items:
        return

    from streamtv.cache import get_runtime

    _, download_queue = get_runtime()
    if not download_queue:
        return

    end_index = min(start_index + prefetch_count, len(schedule_items))
    for item in schedule_items[start_index:end_index]:
        media = item.get("media_item")
        if media and getattr(media, "source_id", None):
            if youtube_full_cache_enabled() and not prefetch_downloads_enabled():
                if media.source != StreamSource.YOUTUBE:
                    continue
            await download_queue.enqueue(media)

    _evict_off_schedule_cache(
        schedule_items,
        start_index,
        prefetch_count,
        extra_keep_source_ids=extra_keep_source_ids,
    )

class ChannelStream:
    """Manages a continuous stream for a single channel (ErsatzTV-style)"""
    
    def __init__(self, channel: Channel, db_session_factory):
        # Store channel ID and number instead of the object to avoid session issues
        self.channel_id = channel.id
        self.channel_number = channel.number
        self.channel_name = channel.name
        self.db_session_factory = db_session_factory
        self.streamer = None  # Will be created when needed
        self._broadcast_queue: asyncio.Queue = asyncio.Queue(maxsize=50)  # Broadcast queue
        self._stream_task: Optional[asyncio.Task] = None
        self._client_queues: List[asyncio.Queue] = []
        self._is_running = False
        self._lock = asyncio.Lock()
        self._client_count = 0
        
        # Playout timeline tracking (ErsatzTV-style)
        self._playout_start_time: Optional[datetime] = None
        self._schedule_items: List[Dict] = []
        self._timeline_items: List[Dict] = []
        self._current_item_index = 0
        self._current_item_start_time: Optional[datetime] = None
        self._timeline_lock = asyncio.Lock()
        self._forced_item_index: Optional[int] = None
        self._direct_stream_fallback = False
        self._item_stream_retries: Dict[int, int] = {}
        self._pending_archive_tune_seek_seconds: float = 0.0
        self._abort_current_item_for_tune: bool = False

    async def start(self):
        """Start the continuous stream in the background"""
        if self._is_running:
            return
        
        async with self._lock:
            if self._is_running:
                return
            
            # Initialize playout timeline - try to resume from saved position, otherwise start from beginning
            # Uses system time (UTC) for all calculations
            async with self._timeline_lock:
                if not self._playout_start_time:
                    # Try to load saved playout start time from database
                    db = self.db_session_factory()
                    try:
                        from streamtv.database.models import ChannelPlaybackPosition
                        playback_pos = db.query(ChannelPlaybackPosition).filter(
                            ChannelPlaybackPosition.channel_id == self.channel_id
                        ).first()
                        
                        if playback_pos and playback_pos.playout_start_time:
                            # Resume from saved position
                            self._playout_start_time = playback_pos.playout_start_time
                            logger.info(f"Resuming channel {self.channel_number} from saved playout start time: {self._playout_start_time}")
                        else:
                            # First time or no saved position - start from now
                            self._playout_start_time = datetime.utcnow()
                            logger.info(f"Starting channel {self.channel_number} from current time: {self._playout_start_time}")
                            
                            # Save the start time for future resumes
                            if not playback_pos:
                                playback_pos = ChannelPlaybackPosition(
                                    channel_id=self.channel_id,
                                    channel_number=self.channel_number,
                                    playout_start_time=self._playout_start_time,
                                    last_position_update=datetime.utcnow()
                                )
                                db.add(playback_pos)
                            else:
                                playback_pos.playout_start_time = self._playout_start_time
                                playback_pos.last_position_update = datetime.utcnow()
                            db.commit()
                    except Exception as e:
                        logger.error(f"Error loading saved position for channel {self.channel_number}: {e}", exc_info=True)
                        # Fallback to starting from now
                        self._playout_start_time = datetime.utcnow()
                        logger.info(f"Starting channel {self.channel_number} from current time (fallback): {self._playout_start_time}")
                    finally:
                        db.close()
            
            self._is_running = True
            logger.info(f"ChannelStream.start() - Creating background task for channel {self.channel_number}...")
            self._stream_task = asyncio.create_task(self._run_continuous_stream())
            logger.info(f"Started continuous stream for channel {self.channel_number} ({self.channel_name}) - background task created")
    
    async def stop(self, *, save_position: bool = True):
        """Stop the continuous stream.

        save_position=False skips writing in-memory playout_start_time back to the DB
        (required for playout-reset / stream-restart so stop cannot overwrite a fresh anchor).
        """
        if not self._is_running:
            return
        
        async with self._lock:
            # Set flag FIRST to prevent new items from starting
            self._is_running = False
            if self._stream_task:
                self._stream_task.cancel()
                try:
                    # Wait for task to complete cancellation (with timeout to prevent hanging)
                    await asyncio.wait_for(self._stream_task, timeout=10.0)
                except asyncio.TimeoutError:
                    logger.warning(f"Stream task for channel {self.channel_number} did not cancel within timeout")
                except asyncio.CancelledError:
                    pass
            
            # Save current position before stopping (unless caller already wrote a new anchor)
            if save_position:
                try:
                    db = self.db_session_factory()
                    try:
                        from streamtv.database.models import ChannelPlaybackPosition
                        position = await self._get_current_position()
                        current_index = self._current_item_index
                        
                        playback_pos = db.query(ChannelPlaybackPosition).filter(
                            ChannelPlaybackPosition.channel_id == self.channel_id
                        ).first()
                        
                        if not playback_pos:
                            playback_pos = ChannelPlaybackPosition(
                                channel_id=self.channel_id,
                                channel_number=self.channel_number,
                                playout_start_time=self._playout_start_time,
                                last_item_index=current_index,
                                last_position_update=datetime.utcnow()
                            )
                            db.add(playback_pos)
                        else:
                            playback_pos.playout_start_time = self._playout_start_time
                            playback_pos.last_item_index = current_index
                            playback_pos.last_position_update = datetime.utcnow()
                        db.commit()
                        logger.info(f"Saved position for channel {self.channel_number}: item {current_index}, playout_start_time={self._playout_start_time}")
                    except Exception as e:
                        logger.error(f"Error saving position for channel {self.channel_number}: {e}", exc_info=True)
                        db.rollback()
                    finally:
                        db.close()
                except Exception as e:
                    logger.error(f"Error saving position on stop for channel {self.channel_number}: {e}", exc_info=True)
            
            # Clear all client queues
            self._client_queues.clear()
            # DON'T reset playout_start_time - keep timeline continuous for resume
            logger.info(
                f"Stopped continuous stream for channel {self.channel_number} "
                f"(save_position={save_position})"
            )    
    def _broadcast_to_clients(self, chunk: bytes) -> None:
        """Push one MPEG-TS chunk to every tuned client queue."""
        for queue in self._client_queues:
            try:
                queue.put_nowait(chunk)
            except asyncio.QueueFull:
                try:
                    queue.get_nowait()
                    queue.put_nowait(chunk)
                except Exception:
                    pass

    def _consume_archive_tune_seek_seconds(self, *, eligible: bool) -> float:
        """Return pending archive tune seek once; only when eligible (archive tune path)."""
        if not eligible or self._pending_archive_tune_seek_seconds <= 0:
            return 0.0
        offset = self._pending_archive_tune_seek_seconds
        self._pending_archive_tune_seek_seconds = 0.0
        return offset

    async def _jump_to_cached_item_for_tune(self) -> None:
        """Snap playout to the EPG timeline item when a tuner connects."""
        if not self._schedule_items:
            return

        position = await self._get_current_position()
        start = position["item_index"]
        if start >= len(self._schedule_items):
            start = 0

        # Never skip forward on tune — wall-clock guide may be ahead of continuous playout.
        if start > self._current_item_index:
            logger.info(
                f"Channel {self.channel_number}: tune join holds playout item "
                f"{self._current_item_index} (wall-clock guide {start}; no forward skip)"
            )
            return

        # Do not skip ahead mid-song when playout lags the wall-clock guide.
        if (
            self._is_running
            and self._current_item_index < start
            and self._current_item_start_time is not None
            and self._current_item_index < len(self._schedule_items)
        ):
            from streamtv.scheduling.playout_timeline import item_duration

            _elapsed = (
                datetime.utcnow() - self._current_item_start_time
            ).total_seconds()
            _slot = item_duration(self._schedule_items[self._current_item_index])
            if _elapsed < max(15, int(_slot * 0.85)):
                logger.info(
                    f"Channel {self.channel_number}: tune join deferred "
                    f"(playing item {self._current_item_index}, guide {start}, "
                    f"elapsed {_elapsed:.0f}s / {_slot}s)"
                )
                return

        if start == self._current_item_index and self._is_running:
            logger.info(
                f"Channel {self.channel_number}: already streaming guide item "
                f"{start}, skipping tune jump"
            )
        else:
            self._forced_item_index = start
        self._direct_stream_fallback = False

        schedule_item = self._schedule_items[start]
        media_item = schedule_item.get("media_item")
        if not media_item:
            return

        from streamtv.scheduling.playout_timeline import (
            archive_tune_seek_enabled,
            compute_intra_item_tune_offset,
        )

        if (
            media_item.source == StreamSource.ARCHIVE_ORG
            and archive_tune_seek_enabled()
        ):
            seek_offset = compute_intra_item_tune_offset(position, schedule_item)
            if seek_offset > 0:
                self._pending_archive_tune_seek_seconds = seek_offset
                self._forced_item_index = start
                self._abort_current_item_for_tune = True
                self._direct_stream_fallback = True
                logger.info(
                    f"Channel {self.channel_number}: archive tune seek "
                    f"{seek_offset:.1f}s into guide item {start}"
                )

        from streamtv.cache import get_runtime

        cache_manager, download_queue = get_runtime()
        if not cache_manager:
            return

        from streamtv.cache.playback_mode import (
            background_downloads_enabled,
            direct_stream_first,
            prefetch_downloads_enabled,
            ring_buffer_max_bytes,
            tune_only_buffering,
        )

        if download_queue and tune_only_buffering() and self._client_count > 0:
            if media_item.source == StreamSource.YOUTUBE:
                from streamtv.cache.playback_mode import youtube_full_cache_enabled

                if youtube_full_cache_enabled():
                    await download_queue.ensure_download_started(media_item)
            else:
                await download_queue.ensure_ring_buffer(
                    media_item, ring_buffer_max_bytes()
                )
        elif download_queue and (
            background_downloads_enabled() or prefetch_downloads_enabled()
        ):
            await download_queue.prioritize(media_item)

        if media_item.source != StreamSource.ARCHIVE_ORG:
            return

        if cache_manager.get_cached_path(media_item.source_id):
            logger.info(
                f"Channel {self.channel_number}: tune to cached guide item "
                f"{start}/{len(self._schedule_items)}: {media_item.title[:60]}"
            )
            return

        if direct_stream_first():
            logger.info(
                f"Channel {self.channel_number}: tune to guide item {start} "
                f"({media_item.title[:60]}); direct archive.org stream"
            )
            self._direct_stream_fallback = True
            return

        logger.info(
            f"Channel {self.channel_number}: guide item {start} not cached "
            f"({media_item.title[:60]}); waiting for cache (then direct fallback)"
        )
        self._direct_stream_fallback = True
    
    async def _stream_item_to_clients(self, media_item: MediaItem) -> bool:
        """Transcode one schedule item and broadcast chunks. Returns True if any data sent."""
        from streamtv.cache.playback_mode import direct_stream_first, playback_mode, tune_only_buffering

        if _defer_youtube_playout_until_tuner(media_item, self._client_count):
            return False

        # tune_only_buffer: do not pull CDN / spawn FFmpeg until a tuner connects.
        if tune_only_buffering() and self._client_count == 0 and not self._direct_stream_fallback:
            return False

        from streamtv.cache.playback_buffer import wait_for_playback_buffer

        archive_direct = (
            media_item.source == StreamSource.ARCHIVE_ORG
            and (
                self._client_count > 0
                or self._direct_stream_fallback
                or (direct_stream_first() and not tune_only_buffering())
            )
        )
        guide_aligned_tune = (
            self._direct_stream_fallback
            and self._client_count > 0
            and media_item.source == StreamSource.ARCHIVE_ORG
        )
        allow_direct = guide_aligned_tune or archive_direct
        sent = False
        tune_priority = self._client_count > 0
        archive_tune_seek_seconds = self._consume_archive_tune_seek_seconds(
            eligible=guide_aligned_tune or self._direct_stream_fallback
        )

        if playback_mode() == "buffer" and getattr(media_item, "source_id", None):
            from streamtv.cache import get_runtime

            cache_manager, download_queue = get_runtime()
            if cache_manager and download_queue:
                ready = await wait_for_playback_buffer(
                    media_item,
                    cache_manager,
                    download_queue,
                    channel_number=self.channel_number,
                    tuner_active=self._client_count > 0,
                    on_wait_tick=(
                        lambda: self._broadcast_to_clients(keepalive_chunk())
                        if self._client_count > 0
                        else None
                    ),
                    is_running=lambda: self._is_running,
                )
                if not ready:
                    return False

        if allow_direct:
            import time as _stream_time
            _first_real_chunk_at: Optional[float] = None
            try:
                async for chunk in self.streamer._stream_single_item(
                    media_item,
                    self.channel_number,
                    allow_direct_archive=True,
                    tune_priority=tune_priority,
                    archive_tune_seek_seconds=archive_tune_seek_seconds,
                ):
                    if not self._is_running or self._abort_current_item_for_tune:
                        if self._abort_current_item_for_tune:
                            self._abort_current_item_for_tune = False
                        break
                    if _first_real_chunk_at is None:
                        _first_real_chunk_at = _stream_time.monotonic()
                    sent = True
                    self._broadcast_to_clients(chunk)
            except Exception as direct_exc:
                logger.warning(
                    f"Channel {self.channel_number}: direct archive.org failed for "
                    f"{media_item.title[:60]}, waiting for cache: {direct_exc}"
                )

        elif media_item.source == StreamSource.ARCHIVE_ORG:
            async for chunk in self.streamer._stream_single_item(
                media_item,
                self.channel_number,
                allow_direct_archive=archive_direct,
                tune_priority=tune_priority,
                archive_tune_seek_seconds=archive_tune_seek_seconds,
            ):
                if not self._is_running or self._abort_current_item_for_tune:
                    if self._abort_current_item_for_tune:
                        self._abort_current_item_for_tune = False
                    break
                sent = True
                self._broadcast_to_clients(chunk)
        else:
            async for chunk in self.streamer._stream_single_item(
                media_item,
                self.channel_number,
                allow_direct_archive=False,
                tune_priority=tune_priority,
            ):
                if not self._is_running:
                    break
                sent = True
                self._broadcast_to_clients(chunk)

        if sent:
            if guide_aligned_tune:
                self._direct_stream_fallback = False
            return True

        if media_item.source != StreamSource.ARCHIVE_ORG:
            return False

        from streamtv.cache.playback_mode import (
            background_downloads_enabled,
            ring_buffer_max_bytes,
            tune_only_buffering,
        )

        if direct_stream_first() and not background_downloads_enabled():
            if tune_only_buffering() and self._client_count > 0:
                from streamtv.cache import get_runtime

                cache_manager, download_queue = get_runtime()
                if download_queue and media_item.source != StreamSource.YOUTUBE:
                    await download_queue.ensure_ring_buffer(
                        media_item, ring_buffer_max_bytes()
                    )
            else:
                return False

        if not background_downloads_enabled():
            if not (tune_only_buffering() and self._client_count > 0):
                return False

        from streamtv.cache import get_runtime

        cache_manager, download_queue = get_runtime()
        if not cache_manager or not download_queue:
            return False

        if background_downloads_enabled():
            await download_queue.ensure_download_started(media_item)
        logged_waiting = False
        import time as _time
        from streamtv.config import config

        # Guide-aligned tune: hold EPG item until cache fills (large movies may take minutes).
        if guide_aligned_tune:
            wait_deadline = _time.monotonic() + 900.0
        else:
            wait_deadline = _time.monotonic() + 120.0
        client_wait_started: Optional[float] = None
        attempt = 0
        min_buffer_bytes = int(config.cache.stream_buffer_mb * 1024 * 1024)
        while _time.monotonic() < wait_deadline:
            if not self._is_running:
                return False
            has_clients = self._client_count > 0

            # Tuner connected after background cache wait started (guide_aligned_tune
            # was False at function entry). Retry direct/buffer stream immediately.
            if (
                not guide_aligned_tune
                and self._direct_stream_fallback
                and has_clients
                and media_item.source == StreamSource.ARCHIVE_ORG
            ):
                guide_aligned_tune = True
                wait_deadline = max(wait_deadline, _time.monotonic() + 900.0)
                late_seek = self._consume_archive_tune_seek_seconds(eligible=True)
                if late_seek > 0:
                    archive_tune_seek_seconds = late_seek
                logger.info(
                    f"Channel {self.channel_number}: tuner connected during cache wait; "
                    f"starting archive.org stream for {media_item.title[:60]}"
                )
                try:
                    async for chunk in self.streamer._stream_single_item(
                        media_item,
                        self.channel_number,
                        allow_direct_archive=True,
                        tune_priority=True,
                        archive_tune_seek_seconds=archive_tune_seek_seconds,
                    ):
                        if not self._is_running or self._abort_current_item_for_tune:
                            if self._abort_current_item_for_tune:
                                self._abort_current_item_for_tune = False
                            break
                        sent = True
                        self._broadcast_to_clients(chunk)
                except Exception as direct_exc:
                    logger.warning(
                        f"Channel {self.channel_number}: tune-time archive.org stream "
                        f"failed for {media_item.title[:60]}: {direct_exc}"
                    )
                if sent:
                    self._direct_stream_fallback = False
                    return True

            if has_clients:
                if client_wait_started is None:
                    client_wait_started = _time.monotonic()
                if not logged_waiting:
                    logger.info(
                        f"Channel {self.channel_number}: clients waiting, polling cache for "
                        f"{media_item.title[:60]}"
                    )
                    logged_waiting = True
                self._broadcast_to_clients(keepalive_chunk())
            elif guide_aligned_tune:
                # Tuner left; stop holding this item for cache.
                return False
            if cache_manager.get_cached_path(media_item.source_id) or cache_manager.get_buffer_path(
                media_item.source_id, min_buffer_bytes
            ):
                self._direct_stream_fallback = False
                async for chunk in self.streamer._stream_single_item(
                    media_item,
                    self.channel_number,
                    tune_priority=tune_priority,
                    archive_tune_seek_seconds=archive_tune_seek_seconds,
                ):
                    if not self._is_running or self._abort_current_item_for_tune:
                        if self._abort_current_item_for_tune:
                            self._abort_current_item_for_tune = False
                        break
                    sent = True
                    self._broadcast_to_clients(chunk)
                return sent
            elif has_clients:
                self._broadcast_to_clients(keepalive_chunk())
            else:
                logger.debug(
                    f"Channel {self.channel_number}: background playout waiting for cache "
                    f"{media_item.title[:60]}"
                )
            attempt += 1
            await asyncio.sleep(0.5)

        if self._client_count > 0 and guide_aligned_tune:
            logger.warning(
                f"Channel {self.channel_number}: cache wait exhausted for tuned guide item "
                f"{media_item.title[:60]} (clients still connected)"
            )
        elif self._client_count == 0:
            logger.warning(
                f"Channel {self.channel_number}: cache wait timeout for "
                f"{media_item.title[:60]}, advancing to next item"
            )
        return False
    
    async def get_stream(self) -> AsyncIterator[bytes]:
        """Get the current stream - joins existing continuous stream at current position (ErsatzTV-style)"""
        # Check playout mode first
        db_check = self.db_session_factory()
        try:
            channel_check = db_check.query(Channel).filter(Channel.id == self.channel_id).first()
            playout_mode_raw = getattr(channel_check, 'playout_mode', PlayoutMode.CONTINUOUS) if channel_check else PlayoutMode.CONTINUOUS
            # Convert string to enum if needed (handle database string values)
            if isinstance(playout_mode_raw, str):
                normalized = playout_mode_raw.lower()
                for mode in PlayoutMode:
                    if mode.value.lower() == normalized:
                        playout_mode = mode
                        break
                else:
                    # Fallback: try to match by name (uppercase)
                    try:
                        playout_mode = PlayoutMode[playout_mode_raw.upper()]
                    except KeyError:
                        playout_mode = PlayoutMode.CONTINUOUS
            else:
                playout_mode = playout_mode_raw
        finally:
            db_check.close()
        
        # For ON_DEMAND mode, create independent stream starting from saved position or item 0
        if playout_mode == PlayoutMode.ON_DEMAND:
            db_session = None
            try:
                # Always load fresh schedule items for ON_DEMAND (don't use cached/shared state)
                db_session = self.db_session_factory()
                from streamtv.scheduling.parser import ScheduleParser
                from streamtv.scheduling.engine import ScheduleEngine, playout_shuffle_seed
                
                schedule_file = ScheduleParser.find_schedule_file(self.channel_number)
                if not schedule_file:
                    error_msg = f"No schedule file found for ON_DEMAND channel {self.channel_number}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                
                logger.debug(f"ON_DEMAND: Found schedule file for channel {self.channel_number}: {schedule_file}")
                parsed_schedule = ScheduleParser.parse_file(schedule_file, schedule_file.parent)
                schedule_engine = ScheduleEngine(
                    db_session,
                    seed=playout_shuffle_seed(self.channel_number, None, 0),
                )
                channel = db_session.query(Channel).filter(Channel.id == self.channel_id).first()
                
                if not channel:
                    error_msg = f"Channel {self.channel_number} not found in database"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                
                logger.debug(f"ON_DEMAND: Generating schedule items for channel {self.channel_number}")
                # Generate fresh schedule items for this ON_DEMAND client
                schedule_items = schedule_engine.generate_playlist_from_schedule(
                    channel, parsed_schedule, max_items=None
                )
                
                if not schedule_items:
                    error_msg = f"No schedule items generated for ON_DEMAND channel {self.channel_number}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                
                # Check for saved playback position
                playback_pos = db_session.query(ChannelPlaybackPosition).filter(
                    ChannelPlaybackPosition.channel_id == self.channel_id
                ).first()
                
                start_index = 0
                if playback_pos and playback_pos.last_item_index > 0:
                    start_index = playback_pos.last_item_index
                    # Ensure start_index is within bounds
                    if start_index >= len(schedule_items):
                        start_index = 0
                        logger.warning(f"ON_DEMAND: Saved position {playback_pos.last_item_index} exceeds schedule length, starting from beginning")
                    else:
                        first_item_title = schedule_items[start_index].get('media_item', {}).title if schedule_items[start_index].get('media_item') else 'N/A'
                        logger.info(f"ON_DEMAND: Resuming channel {self.channel_number} from saved position: item {start_index}/{len(schedule_items)} - {first_item_title}")
                else:
                    first_item_title = schedule_items[0].get('media_item', {}).title if schedule_items and schedule_items[0].get('media_item') else 'N/A'
                    logger.info(f"ON_DEMAND: Starting channel {self.channel_number} from beginning (item 0): {first_item_title}")
                
                # Create independent streamer for this client
                streamer = MPEGTSStreamer(db_session)
                
                # Track items tried to prevent infinite loops if all items fail
                items_yielded = 0
                consecutive_failures = 0
                max_consecutive_failures = 10
                is_first_loop = True
                
                # Stream all items starting from saved position (or 0)
                while True:
                    # On first loop, start from saved position; on subsequent loops, start from 0
                    loop_start_index = start_index if is_first_loop else 0
                    
                    for idx in range(loop_start_index, len(schedule_items)):
                        schedule_item = schedule_items[idx]
                        media_item = schedule_item.get('media_item')
                        if not media_item:
                            logger.debug(f"ON_DEMAND: Skipping item {idx} - no media_item")
                            continue
                        
                        # Skip placeholder URLs
                        if 'PLACEHOLDER' in media_item.url.upper():
                            logger.debug(f"ON_DEMAND: Skipping item {idx} - placeholder URL")
                            continue
                        
                        # Skip very short videos
                        if media_item.duration and media_item.duration < 5:
                            logger.debug(f"ON_DEMAND: Skipping item {idx} - duration too short ({media_item.duration}s)")
                            continue
                        
                        # Archive.org: MP4/H.264 only (same policy as channel 80)
                        if skip_non_mp4_archive_item(media_item):
                            logger.debug(
                                f"Skipping non-MP4 archive.org file: "
                                f"{media_item.title} ({media_item.url[:80]})"
                            )
                            continue
                        
                        logger.info(f"ON_DEMAND: Streaming item {idx}/{len(schedule_items)}: {media_item.title[:60]} (URL: {media_item.url[:80]})")
                        
                        # Stream this item directly to client with timeout to prevent hanging
                        item_yielded = False
                        first_chunk_time = None
                        try:
                            chunk_iter = streamer._stream_single_item(
                                media_item,
                                self.channel_number,
                                tune_priority=True,
                            )
                            timeout_seconds = 30.0  # 30 second timeout for first chunk
                            start_time = asyncio.get_event_loop().time()
                            
                            async for chunk in chunk_iter:
                                if first_chunk_time is None:
                                    first_chunk_time = asyncio.get_event_loop().time() - start_time
                                    logger.info(f"ON_DEMAND: First chunk received for item {idx} after {first_chunk_time:.2f}s")
                                
                                yield chunk
                                items_yielded += 1
                                item_yielded = True
                                consecutive_failures = 0  # Reset failure counter on success
                                
                                # Reset timeout after first chunk (item is working)
                                timeout_seconds = None
                            
                            if not item_yielded:
                                logger.warning(f"ON_DEMAND: Item {idx} completed without yielding any chunks for channel {self.channel_number}")
                                consecutive_failures += 1
                            else:
                                logger.info(f"ON_DEMAND: Successfully streamed item {idx} for channel {self.channel_number} ({items_yielded} chunks total so far)")
                                
                                # Save playback position after each item completes successfully
                                # Save next item index (idx + 1) so we resume from the next item
                                next_index = idx + 1
                                if next_index >= len(schedule_items):
                                    next_index = 0  # Loop back to beginning
                                
                                self._save_playback_position(
                                    db_session,
                                    self.channel_id,
                                    channel.number,
                                    next_index,
                                    media_item.id
                                )
                                
                        except asyncio.TimeoutError:
                            consecutive_failures += 1
                            logger.error(f"ON_DEMAND: Timeout waiting for first chunk from item {idx} ({media_item.title[:60]}) for channel {self.channel_number} - skipping to next item")
                        except Exception as e:
                            consecutive_failures += 1
                            logger.error(f"Error streaming ON_DEMAND item {idx} ({media_item.title[:60]}) for channel {self.channel_number}: {e}", exc_info=True)
                            # If we've had too many consecutive failures, log a warning but continue
                            if consecutive_failures >= max_consecutive_failures:
                                logger.error(f"ON_DEMAND: {consecutive_failures} consecutive failures for channel {self.channel_number}, but continuing...")
                    
                    # If we've yielded at least some data, reset failure counter for next cycle
                    if items_yielded > 0:
                        consecutive_failures = 0
                    
                    # Mark first loop as complete
                    is_first_loop = False
                    
                    # Loop back to beginning for continuous playback
                    logger.info(f"ON_DEMAND: Completed playout cycle for channel {self.channel_number}, looping back to beginning (total items yielded: {items_yielded})")
            except Exception as e:
                logger.error(f"Error in ON_DEMAND stream for channel {self.channel_number}: {e}", exc_info=True)
                raise
            finally:
                if db_session:
                    try:
                        db_session.close()
                    except Exception:
                        pass
            # Note: The async generator will naturally exit when the while True loop ends
            # No explicit return needed - async generators automatically stop when function completes
        
        # CONTINUOUS mode: use broadcast queue (existing logic)
        # Create a queue for this client
        client_queue = asyncio.Queue(maxsize=_CLIENT_QUEUE_MAXSIZE)
        
        async with self._lock:
            # If stream is not running, start it
            if not self._is_running:
                await self.start()
                # Wait for stream to initialize
                await asyncio.sleep(0.5)
            
            # Register this client
            self._client_queues.append(client_queue)
            self._client_count += 1
            try:
                client_queue.put_nowait(keepalive_chunk())
            except asyncio.QueueFull:
                pass
            
            # Continuous: calculate position in playout timeline using system time (ErsatzTV-style)
            current_position = await self._get_current_position()
            now = datetime.utcnow()
            elapsed_hours = int(current_position['elapsed_seconds'] // 3600)
            elapsed_minutes = int((current_position['elapsed_seconds'] % 3600) // 60)
            logger.info(f"Client connected to channel {self.channel_number} (CONTINUOUS mode) at {now} - position {current_position['item_index']}/{len(self._schedule_items)} ({elapsed_hours}h {elapsed_minutes}m from midnight, total clients: {self._client_count})")
            wall_idx = int(current_position["item_index"])
            air_idx = int(self._current_item_index)
            if wall_idx > air_idx:
                from streamtv.plex.guide_reload import maybe_reload_plex_guide_on_lag

                asyncio.create_task(
                    maybe_reload_plex_guide_on_lag(
                        lag_items=wall_idx - air_idx,
                        channel_number=str(self.channel_number),
                        wall_index=wall_idx,
                        air_index=air_idx,
                        min_lag=3,
                    )
                )
            asyncio.create_task(self._jump_to_cached_item_for_tune())
        
        # Stream from the broadcast queue
        first_yield = True
        try:
            while self._is_running:
                try:
                    chunk = await asyncio.wait_for(client_queue.get(), timeout=2.0)
                    if first_yield:
                        first_yield = False
                    yield chunk
                except asyncio.TimeoutError:
                    # Check if still running
                    if not self._is_running:
                        break
                    # Continue waiting
                    continue
        finally:
            # Client disconnected
            async with self._lock:
                if client_queue in self._client_queues:
                    self._client_queues.remove(client_queue)
                self._client_count -= 1
                logger.debug(f"Client disconnected from channel {self.channel_number} (remaining clients: {self._client_count})")
    
    def _persist_playout_anchor(
        self,
        db_session: Session,
        item_index: int,
        media_id: Optional[int] = None,
    ) -> None:
        """Persist continuous-playout anchor so XMLTV EPG matches the live stream."""
        if not self._playout_start_time:
            return
        try:
            playback_pos = db_session.query(ChannelPlaybackPosition).filter(
                ChannelPlaybackPosition.channel_id == self.channel_id
            ).first()
            if not playback_pos:
                playback_pos = ChannelPlaybackPosition(
                    channel_id=self.channel_id,
                    channel_number=self.channel_number,
                    playout_start_time=self._playout_start_time,
                    last_item_index=item_index,
                    last_position_update=datetime.utcnow(),
                )
                db_session.add(playback_pos)
            else:
                playback_pos.playout_start_time = self._playout_start_time
                playback_pos.last_item_index = item_index
                playback_pos.last_position_update = datetime.utcnow()
            if media_id is not None:
                playback_pos.last_item_media_id = media_id
            db_session.commit()
        except Exception as e:
            logger.error(
                f"Error persisting playout anchor for channel {self.channel_number}: {e}",
                exc_info=True,
            )
            db_session.rollback()

    def _save_playback_position(
        self,
        db_session: Session,
        channel_id: int,
        channel_number: str,
        item_index: int,
        media_id: Optional[int] = None
    ):
        """Save playback position for on-demand channel"""
        try:
            playback_pos = db_session.query(ChannelPlaybackPosition).filter(
                ChannelPlaybackPosition.channel_id == channel_id
            ).first()
            
            if not playback_pos:
                playback_pos = ChannelPlaybackPosition(
                    channel_id=channel_id,
                    channel_number=channel_number
                )
                db_session.add(playback_pos)
            
            playback_pos.last_item_index = item_index
            playback_pos.last_item_media_id = media_id
            playback_pos.last_played_at = datetime.utcnow()
            playback_pos.total_items_watched = max(playback_pos.total_items_watched, item_index)
            
            db_session.commit()
            logger.debug(f"ON_DEMAND: Saved playback position for channel {channel_number}: item {item_index}")
        except Exception as e:
            logger.error(f"Error saving playback position for channel {channel_number}: {e}", exc_info=True)
            db_session.rollback()
    
    async def _get_current_position(self) -> Dict:
        """Calculate current position in playout timeline based on saved playout start time"""
        from streamtv.scheduling.playout_timeline import resolve_stream_playout_position

        async with self._timeline_lock:
            if not self._schedule_items:
                return {'item_index': 0, 'elapsed_seconds': 0}

            if not self._playout_start_time:
                self._playout_start_time = datetime.utcnow()

            timeline = self._timeline_items or self._schedule_items
            return resolve_stream_playout_position(
                self._schedule_items,
                timeline,
                self._playout_start_time,
            )
    
    async def _run_continuous_stream(self):
        """Run the continuous stream in the background and broadcast to all clients"""
        logger.info(f"ChannelStream._run_continuous_stream() - Starting for channel {self.channel_number}")
        # Create a database session for this stream
        db = self.db_session_factory()
        try:
            # Load schedule items and initialize timeline
            logger.info(f"ChannelStream._run_continuous_stream() - Loading schedule parser/engine for channel {self.channel_number}")
            from streamtv.scheduling.parser import ScheduleParser
            from streamtv.scheduling.engine import ScheduleEngine, playout_shuffle_seed
            
            logger.info(f"ChannelStream._run_continuous_stream() - Finding schedule file for channel {self.channel_number}")
            schedule_file = ScheduleParser.find_schedule_file(self.channel_number)
            if schedule_file:
                logger.info(f"ChannelStream._run_continuous_stream() - Parsing schedule file for channel {self.channel_number}: {schedule_file}")
                parsed_schedule = ScheduleParser.parse_file(schedule_file, schedule_file.parent)
                logger.info(f"ChannelStream._run_continuous_stream() - Schedule parsed, creating ScheduleEngine for channel {self.channel_number}")
                if not self._playout_start_time:
                    try:
                        from streamtv.database.models import ChannelPlaybackPosition
                        playback_pos = db.query(ChannelPlaybackPosition).filter(
                            ChannelPlaybackPosition.channel_id == self.channel_id
                        ).first()
                        if playback_pos and playback_pos.playout_start_time:
                            self._playout_start_time = playback_pos.playout_start_time
                    except Exception:
                        pass
                schedule_engine = ScheduleEngine(
                    db,
                    seed=playout_shuffle_seed(
                        self.channel_number, self._playout_start_time, 0
                    ),
                )
                # Query channel from current session
                channel = db.query(Channel).filter(Channel.id == self.channel_id).first()
                if channel:
                    logger.info(f"ChannelStream._run_continuous_stream() - Generating playlist from schedule for channel {self.channel_number}...")
                    self._schedule_items = schedule_engine.generate_playlist_from_schedule(
                        channel, parsed_schedule, max_items=None
                    )
                    from streamtv.scheduling.media_format import mp4_only_for_content
                    from streamtv.scheduling.playout_timeline import generate_canonical_timeline_playlist

                    if mp4_only_for_content(parsed_schedule, None):
                        self._timeline_items = generate_canonical_timeline_playlist(
                            schedule_engine, channel, parsed_schedule
                        )
                    else:
                        self._timeline_items = self._schedule_items
                    logger.info(
                        f"ChannelStream._run_continuous_stream() - Generated "
                        f"{len(self._schedule_items)} stream / {len(self._timeline_items)} timeline "
                        f"schedule items for channel {self.channel_number}"
                    )
                    for itm in self._schedule_items:
                        media = itm.get("media_item")
                        if media:
                            itm["cached_duration"] = getattr(media, "__dict__", {}).get("duration") or 1800
                else:
                    logger.error(f"Channel {self.channel_number} not found in database")
                    self._schedule_items = []
            else:
                # Fallback to playlist
                from streamtv.database import Playlist, PlaylistItem
                playlists = db.query(Playlist).filter(Playlist.channel_id == self.channel_id).all()
                if playlists:
                    playlist = playlists[0]
                    items = db.query(PlaylistItem).filter(
                        PlaylistItem.playlist_id == playlist.id
                    ).order_by(PlaylistItem.order).all()
                    
                    for item in items:
                        media_item = db.query(MediaItem).filter(
                            MediaItem.id == item.media_item_id
                        ).first()
                        if media_item:
                            self._schedule_items.append({
                                'media_item': media_item,
                                'custom_title': None,
                                'filler_kind': None,
                                'start_time': None,
                                'cached_duration': getattr(media_item, "__dict__", {}).get("duration") or 1800
                            })
            
            await _prefetch_schedule_items(self._schedule_items, 0)
            
            if not self._schedule_items:
                logger.error(f"No schedule items for channel {self.channel_number}")
                self._is_running = False
                return
            
            # Ensure playout_start_time is set (should be set in start(), but double-check)
            async with self._timeline_lock:
                if not self._playout_start_time:
                    # Try to load from database one more time
                    try:
                        from streamtv.database.models import ChannelPlaybackPosition
                        playback_pos = db.query(ChannelPlaybackPosition).filter(
                            ChannelPlaybackPosition.channel_id == self.channel_id
                        ).first()
                        
                        if playback_pos and playback_pos.playout_start_time:
                            self._playout_start_time = playback_pos.playout_start_time
                            logger.info(f"Loaded playout start time for channel {self.channel_number} from database: {self._playout_start_time}")
                        else:
                            # Fallback: use now
                            self._playout_start_time = datetime.utcnow()
                            logger.info(f"Using current time as playout start for channel {self.channel_number}: {self._playout_start_time}")
                    except Exception as e:
                        logger.error(f"Error loading playout start time in _run_continuous_stream: {e}")
                        self._playout_start_time = datetime.utcnow()
            
            logger.info(f"Streaming playout for channel {self.channel_number} with {len(self._schedule_items)} items (resuming from saved position)")
            
            # Create streamer with this session
            self.streamer = MPEGTSStreamer(db)
            
            # Get playout mode from channel (query from DB to get latest value)
            channel = db.query(Channel).filter(Channel.id == self.channel_id).first()
            playout_mode_raw = getattr(channel, 'playout_mode', PlayoutMode.CONTINUOUS) if channel else PlayoutMode.CONTINUOUS
            # Convert string to enum if needed (handle database string values)
            if isinstance(playout_mode_raw, str):
                normalized = playout_mode_raw.lower()
                for mode in PlayoutMode:
                    if mode.value.lower() == normalized:
                        playout_mode = mode
                        break
                else:
                    # Fallback: try to match by name (uppercase)
                    try:
                        playout_mode = PlayoutMode[playout_mode_raw.upper()]
                    except KeyError:
                        playout_mode = PlayoutMode.CONTINUOUS
            else:
                playout_mode = playout_mode_raw

            # Release init DB connection — each channel must not hold a pool slot
            # for the 24/7 playout loop (14 channels exceeded pool_size=5).
            _channel_name = channel.name if channel else None
            _channel_transcode_profile = (
                getattr(channel, "transcode_profile", None) if channel else None
            )
            try:
                db.close()
            except Exception:
                pass
            if self.streamer:
                self.streamer.db = None
            
            # Calculate starting position based on playout mode
            if playout_mode == PlayoutMode.ON_DEMAND:
                # On-demand channels don't run continuous broadcast - each client gets independent stream
                logger.info(f"Channel {self.channel_number} using ON-DEMAND mode - no continuous broadcast (clients get independent streams)")
                # Don't start continuous stream for ON_DEMAND - clients will get independent streams
                return
            
            # CONTINUOUS mode: calculate position based on ErsatzTV-style cycle (daily reset at midnight UTC)
            start_position = await self._get_current_position()
            start_index = start_position['item_index']
            wall_clock_index = start_index
            resume_air_index: Optional[int] = None
            # After restart, resume the actual playout index when behind wall-clock guide.
            try:
                _resume_db = self.db_session_factory()
                try:
                    from streamtv.database.models import ChannelPlaybackPosition

                    _saved = _resume_db.query(ChannelPlaybackPosition).filter(
                        ChannelPlaybackPosition.channel_id == self.channel_id
                    ).first()
                    if (
                        _saved
                        and _saved.last_item_index is not None
                        and _saved.last_item_index < start_index
                    ):
                        resume_air_index = int(_saved.last_item_index)
                        logger.info(
                            f"Channel {self.channel_number}: resuming playout item "
                            f"{resume_air_index} (wall-clock guide at {start_index})"
                        )
                        start_index = resume_air_index
                        lag = wall_clock_index - resume_air_index
                        if lag > 0:
                            from streamtv.plex.guide_reload import maybe_reload_plex_guide_on_lag

                            asyncio.create_task(
                                maybe_reload_plex_guide_on_lag(
                                    lag_items=lag,
                                    channel_number=str(self.channel_number),
                                    wall_index=wall_clock_index,
                                    air_index=resume_air_index,
                                )
                            )
                finally:
                    _resume_db.close()
            except Exception as resume_err:
                logger.debug(
                    f"Channel {self.channel_number}: saved playout index resume skipped: {resume_err}"
                )
            elapsed = start_position['elapsed_seconds']
            cycle_position = start_position.get('cycle_position', 0)
            total_duration = start_position.get('total_duration', 0)
            
            # Log timeline info for debugging
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            cycle_hours = int(cycle_position // 3600)
            cycle_minutes = int((cycle_position % 3600) // 60)
            playout_start = start_position.get('playout_start_time', self._playout_start_time)
            logger.info(f"Channel {self.channel_number} CONTINUOUS timeline: {hours}h {minutes}m elapsed from playout start ({playout_start}), position in cycle: {cycle_hours}h {cycle_minutes}m, starting from item {start_index}/{len(self._schedule_items)} (cycle duration: {total_duration/3600:.1f}h)")

            async with self._timeline_lock:
                self._current_item_index = start_index
                self._current_item_start_time = datetime.utcnow()
            
            resume_sid = _item_source_id(self._schedule_items, start_index)
            resume_keep = {resume_sid} if resume_sid else None
            await _prefetch_schedule_items(
                self._schedule_items,
                start_index,
                count=5,
                tuner_active=False,
                extra_keep_source_ids=resume_keep,
            )
            if start_index < len(self._schedule_items):
                head_media = self._schedule_items[start_index].get("media_item")
                if head_media and getattr(head_media, "source_id", None):
                    from streamtv.cache import get_runtime
                    from streamtv.cache.playback_mode import (
                        background_downloads_enabled,
                        youtube_full_cache_enabled,
                    )

                    _, download_queue = get_runtime()
                    if download_queue and (
                        background_downloads_enabled()
                        or (
                            youtube_full_cache_enabled()
                            and _is_youtube_media_item(head_media)
                        )
                    ):
                        await download_queue.ensure_download_started(head_media)
            
            # Stream continuously, starting from calculated position
            # After first loop, always start from 0
            first_loop = True
            while self._is_running:
                # Determine starting index for this loop
                loop_start = start_index if first_loop else 0
                
                # Loop through schedule items starting from calculated position
                idx = loop_start
                while idx < len(self._schedule_items):
                    if not self._is_running:
                        break

                    from streamtv.cache.playback_mode import tune_only_buffering as _tune_only

                    if _tune_only() and self._client_count == 0:
                        await asyncio.sleep(15.0)
                        if not self._is_running:
                            break
                        pos = await self._get_current_position()
                        guide_idx = int(pos.get("item_index", 0))
                        if guide_idx >= len(self._schedule_items):
                            guide_idx = 0
                        # Only snap when playout ran ahead of guide; never skip
                        # intermediate songs while idle and behind wall-clock.
                        if idx > guide_idx:
                            idx = guide_idx
                        continue

                    if self._forced_item_index is not None:
                        forced = self._forced_item_index
                        self._forced_item_index = None
                        if forced != idx:
                            idx = forced
                            logger.info(
                                f"Channel {self.channel_number}: applying forced playout jump to item {idx}"
                            )
                        else:
                            logger.info(
                                f"Channel {self.channel_number}: tune jump noop "
                                f"(already on item {idx})"
                            )
                    
                    schedule_item = self._schedule_items[idx]
                    media_item = schedule_item.get('media_item')
                    if not media_item:
                        idx += 1
                        continue
                    
                    # Skip placeholder URLs
                    if 'PLACEHOLDER' in media_item.url.upper():
                        idx += 1
                        continue
                    
                    # Skip very short videos
                    if media_item.duration and media_item.duration < 5:
                        idx += 1
                        continue
                    
                    # Archive.org: MP4/H.264 only (avoids AVI demuxing errors)
                    if skip_non_mp4_archive_item(media_item):
                        logger.debug(
                            f"Skipping non-MP4 archive.org file: "
                            f"{media_item.title} ({media_item.url[:80]})"
                        )
                        idx += 1
                        continue
                    
                    # Check again if still running before starting new item (prevent race condition during shutdown)
                    if not self._is_running:
                        break

                    if _defer_youtube_playout_until_tuner(media_item, self._client_count):
                        await asyncio.sleep(5.0)
                        continue
                    
                    # Update timeline position using system time
                    async with self._timeline_lock:
                        self._current_item_index = idx
                        self._current_item_start_time = datetime.utcnow()  # Use system time
                    
                    # Save position at every item start so a restart resumes the
                    # current item (every-5 cadence replayed up to 5 items after
                    # kickstart — Van Halen "Jump" looping on channels 1986/1987).
                    save_db = self.db_session_factory()
                    try:
                        self._persist_playout_anchor(
                            save_db,
                            idx,
                            media_item.id if media_item else None,
                        )
                        logger.debug(
                            f"Saved playout anchor for channel {self.channel_number}: "
                            f"item {idx}, playout_start_time={self._playout_start_time}"
                        )
                    except Exception as e:
                        logger.debug(f"Error saving position for channel {self.channel_number}: {e}")
                    finally:
                        save_db.close()
                    
                    playing_sid = _item_source_id(self._schedule_items, idx)
                    playing_keep = {playing_sid} if playing_sid else None
                    await _prefetch_schedule_items(
                        self._schedule_items,
                        idx + 1,
                        tuner_active=self._client_count > 0,
                        extra_keep_source_ids=playing_keep,
                    )

                    _stream_started = datetime.utcnow()
                    try:
                        streamed = await self._stream_item_to_clients(media_item)
                    except asyncio.CancelledError:
                        raise
                    except Exception as e:
                        logger.error(
                            f"Error streaming item {idx} "
                            f"({media_item.title[:60] if media_item else 'unknown'}) "
                            f"for channel {self.channel_number}: {e}"
                        )
                        streamed = False

                    if streamed and getattr(media_item, "source_id", None):
                        from streamtv.cache.playback_mode import tune_only_buffering
                        from streamtv.cache import get_runtime

                        if tune_only_buffering():
                            cache_manager, _ = get_runtime()
                            if cache_manager:
                                cache_manager.release_ring_buffer(
                                    media_item.source_id
                                )
                        self._item_stream_retries.pop(idx, None)

                    if not streamed and self._client_count > 0 and self._direct_stream_fallback:
                        # Stay on guide item briefly while cache fills; then fall through
                        # to retry/skip so dead CDN items (e.g. duets-2000) do not wedge the tuner.
                        self._broadcast_to_clients(keepalive_chunk())
                        await asyncio.sleep(0.5)

                    from streamtv.cache.playback_mode import playback_mode as _playback_mode

                    if not streamed and _playback_mode() == "buffer":
                        retries = self._item_stream_retries.get(idx, 0) + 1
                        self._item_stream_retries[idx] = retries
                        max_retries = 3 if self._client_count > 0 else 8
                        if retries < max_retries:
                            logger.warning(
                                f"Channel {self.channel_number}: stream miss on item {idx} "
                                f"({media_item.title[:60] if media_item else 'unknown'}), "
                                f"retry {retries}/{max_retries}"
                            )
                            await asyncio.sleep(1.0)
                            continue
                        logger.warning(
                            f"Channel {self.channel_number}: giving up on item {idx} "
                            f"after {retries} retries; skipping to next item"
                        )
                        self._item_stream_retries.pop(idx, None)

                    if not streamed:
                        logger.warning(
                            f"Skipping item {idx} due to error or cache miss, continuing to next item"
                        )
                        # Immediate skip with timeline jump so EPG and playout stay aligned:
                        # subtract remaining duration of the failed item from the cycle clock.
                        try:
                            remaining = int(
                                (self._schedule_items[idx].get("cached_duration") or 1800)
                            )
                            if self._playout_start_time and remaining > 0:
                                self._playout_start_time = (
                                    self._playout_start_time
                                    - timedelta(seconds=remaining)
                                )
                                logger.info(
                                    f"Channel {self.channel_number}: timeline jump "
                                    f"-{remaining}s after failed item {idx}"
                                )
                                save_db = self.db_session_factory()
                                try:
                                    self._persist_playout_anchor(
                                        save_db,
                                        idx,
                                        media_item.id if media_item else None,
                                    )
                                finally:
                                    save_db.close()
                        except Exception as jump_err:
                            logger.debug(
                                f"Channel {self.channel_number}: timeline jump skipped: {jump_err}"
                            )

                    # Realign loop index to wall-clock guide. Never race ahead of the
                    # EPG slot; only advance after a near-complete stream pass.
                    _idx_before_resync = idx
                    _resync_action = ""
                    try:
                        from streamtv.scheduling.playout_timeline import item_duration

                        pos = await self._get_current_position()
                        guide_idx = int(pos.get("item_index", idx))
                        _stream_elapsed = (
                            datetime.utcnow() - _stream_started
                        ).total_seconds()
                        _slot_dur = item_duration(self._schedule_items[idx])
                        _complete_threshold = max(15, int(_slot_dur * 0.85))
                        if idx > guide_idx:
                            idx = guide_idx
                            _resync_action = "snap_back_to_guide"
                        elif not streamed:
                            idx += 1
                            _resync_action = "advance_on_fail"
                        elif _stream_elapsed >= _complete_threshold:
                            # Near-full play: advance one item only (never skip
                            # multiple slots to catch wall-clock guide).
                            idx += 1
                            _resync_action = "advance_after_complete"
                            remaining = max(0, int(_slot_dur) - int(_stream_elapsed))
                            if remaining > 0 and self._playout_start_time:
                                self._playout_start_time = (
                                    self._playout_start_time
                                    - timedelta(seconds=remaining)
                                )
                                logger.info(
                                    f"Channel {self.channel_number}: timeline bump "
                                    f"-{remaining}s after early EOF (slot {_slot_dur}s, "
                                    f"played {_stream_elapsed:.0f}s)"
                                )
                                save_db = self.db_session_factory()
                                try:
                                    self._persist_playout_anchor(
                                        save_db,
                                        idx,
                                        media_item.id if media_item else None,
                                    )
                                finally:
                                    save_db.close()
                        elif guide_idx > idx:
                            # Behind guide but mid-item: finish current song first.
                            _resync_action = "hold_behind_guide"
                        else:
                            # Short partial (premature FFmpeg EOF / 403): hold idx
                            # until wall-clock guide advances — do not race ahead.
                            _resync_action = "hold_partial"
                    except Exception as resync_err:
                        logger.debug(
                            f"Channel {self.channel_number}: playout resync skipped: {resync_err}"
                        )
                        idx += 1

                    if _resync_action in (
                        "advance_after_complete",
                        "advance_on_fail",
                    ):
                        _release_finished_item_cache(
                            media_item, reason=_resync_action
                        )
                
                # After first loop, always start from beginning
                first_loop = False
                # Loop back to beginning (continuous playout)
                # Don't reset timeline - keep it continuous so clients join at current position
                logger.debug(f"Channel {self.channel_number} completed playout cycle, looping back to start (timeline continues)")
                
        except asyncio.CancelledError:
            logger.info(f"Continuous stream cancelled for channel {self.channel_number}")
        except Exception as e:
            logger.error(f"Error in continuous stream for channel {self.channel_number}: {e}", exc_info=True)
        finally:
            self._is_running = False
            # Close database session if still open (init path may have closed early)
            try:
                if "db" in locals() and db is not None:
                    db.close()
            except Exception:
                pass

class ChannelManager:
    """Manages continuous streams for all channels (ErsatzTV-style)"""
    
    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory
        self._streams: Dict[str, ChannelStream] = {}
        self._lock = asyncio.Lock()
        self._running = False
    
    async def start_all_channels(self):
        """Start continuous streaming for all enabled channels (non-blocking boot)."""
        logger.info("ChannelManager.start_all_channels() - Acquiring lock...")
        async with self._lock:
            if self._running:
                logger.info("ChannelManager.start_all_channels() - Already running, returning")
                return
            self._running = True
        logger.info("ChannelManager.start_all_channels() - Lock acquired, querying channels...")

        db = self.db_session_factory()
        channels: list[Channel] = []
        try:
            try:
                channels = db.query(Channel).filter(Channel.enabled == True).all()
            except (LookupError, ValueError, Exception) as query_error:
                # Handle SQLAlchemy enum validation errors with fallback to raw SQL
                error_str = str(query_error)
                error_type = type(query_error).__name__
                # Check if this is an enum validation error
                if isinstance(query_error, LookupError) or "is not among the defined enum values" in error_str or any(enum_name in error_str.lower() for enum_name in ["playoutmode", "streamingmode", "channeltranscodemode", "transcodemode", "subtitlemode", "streamselectormode"]):
                    logger.warning(f"SQLAlchemy enum validation error when querying channels for startup: {query_error}")
                    logger.info("Attempting to query channels using raw SQL to work around enum validation issue...")
                    # Query using raw SQL to avoid enum validation, then construct Channel objects
                    from sqlalchemy import text
                    # Import enum maps for fast O(1) lookup (same as @reconstructor uses)
                    from ..database.models import (
                        PlayoutMode, StreamingMode, ChannelTranscodeMode, ChannelSubtitleMode,
                        ChannelStreamSelectorMode, ChannelMusicVideoCreditsMode, ChannelSongVideoMode,
                        ChannelIdleBehavior, ChannelPlayoutSource
                    )
                    # Access the pre-built enum maps from models.py module
                    import streamtv.database.models as models_module
                    _PLAYOUT_MODE_MAP = getattr(models_module, '_PLAYOUT_MODE_MAP', {})
                    _STREAMING_MODE_MAP = getattr(models_module, '_STREAMING_MODE_MAP', {})
                    _TRANSCODE_MODE_MAP = getattr(models_module, '_TRANSCODE_MODE_MAP', {})
                    
                    raw_result = db.execute(text("""
                        SELECT * FROM channels WHERE enabled = 1
                    """)).fetchall()
                    channels = []
                    for row in raw_result:
                        channel = Channel()
                        # Copy all attributes from row, converting enum strings to enums using optimized dict lookups
                        for key, value in row._mapping.items():
                            if value is None:
                                setattr(channel, key, None)
                            elif key == 'playout_mode' and isinstance(value, str):
                                normalized = value.lower()
                                enum_val = _PLAYOUT_MODE_MAP.get(normalized)
                                if not enum_val:
                                    try:
                                        enum_val = PlayoutMode[value.upper().replace('-', '_')]
                                    except KeyError:
                                        enum_val = PlayoutMode.CONTINUOUS
                                setattr(channel, key, enum_val)
                            elif key == 'streaming_mode' and isinstance(value, str):
                                normalized = value.lower()
                                enum_val = _STREAMING_MODE_MAP.get(normalized)
                                if not enum_val:
                                    try:
                                        enum_val = StreamingMode[value.upper().replace('-', '_')]
                                    except KeyError:
                                        enum_val = StreamingMode.TRANSPORT_STREAM_HYBRID
                                setattr(channel, key, enum_val)
                            elif key == 'transcode_mode' and isinstance(value, str):
                                normalized = value.lower()
                                enum_val = _TRANSCODE_MODE_MAP.get(normalized)
                                if not enum_val:
                                    try:
                                        enum_val = ChannelTranscodeMode[value.upper().replace('-', '_')]
                                    except KeyError:
                                        enum_val = ChannelTranscodeMode.ON_DEMAND
                                setattr(channel, key, enum_val)
                            elif key in ['subtitle_mode', 'stream_selector_mode', 'music_video_credits_mode', 
                                         'song_video_mode', 'idle_behavior', 'playout_source'] and isinstance(value, str):
                                # These will be handled by @reconstructor, just set as string for now
                                setattr(channel, key, value)
                            else:
                                setattr(channel, key, value)
                        channels.append(channel)
                    logger.info(f"Loaded {len(channels)} channels using raw SQL query for startup")
                else:
                    # Re-raise if it's a different error
                    raise

            from ..database.models import PlayoutMode

            logger.info(f"ChannelManager.start_all_channels() - Found {len(channels)} enabled channels")
            # Convert playout_mode strings to enums for each channel (handle database string values)
            for channel in channels:
                if hasattr(channel, 'playout_mode') and isinstance(channel.playout_mode, str):
                    try:
                        normalized = channel.playout_mode.lower()
                        for mode in PlayoutMode:
                            if mode.value.lower() == normalized:
                                channel.playout_mode = mode
                                break
                        else:
                            channel.playout_mode = PlayoutMode[channel.playout_mode.upper()]
                    except (KeyError, AttributeError):
                        channel.playout_mode = PlayoutMode.CONTINUOUS
            channels.sort(key=lambda ch: (_channel_boot_tier(ch.number), str(ch.number)))
        finally:
            db.close()
            logger.info("ChannelManager.start_all_channels() - Database session closed")

        async def _start_after_delay(delay_secs: float, channel: Channel, idx: int) -> None:
            if delay_secs > 0:
                await asyncio.sleep(delay_secs)
            logger.info(
                f"ChannelManager.start_all_channels() - Starting channel "
                f"{idx + 1}/{len(channels)}: {channel.number} ({channel.name})"
            )
            await self._start_channel(channel)
            logger.info(
                f"ChannelManager.start_all_channels() - Completed starting channel {channel.number}"
            )

        for idx, channel in enumerate(channels):
            asyncio.create_task(_start_after_delay(idx * 3.0, channel, idx))
        logger.info(
            f"ChannelManager.start_all_channels() - Scheduled staggered boot for {len(channels)} channels"
        )
    
    async def stop_all_channels(self):
        """Stop all continuous streams"""
        async with self._lock:
            self._running = False
            stream_list = list(self._streams.values())
            for stream in stream_list:
                await stream.stop()
            self._streams.clear()
            logger.info("Stopped all continuous streams")
    
    def get_live_playout_start_time(self, channel_number: str) -> Optional[datetime]:
        """Return in-memory playout anchor when the channel stream is running."""
        stream = self._streams.get(str(channel_number))
        if stream and stream._playout_start_time:
            return stream._playout_start_time
        return None

    def get_live_playout_state(self, channel_number: str) -> Optional[Dict[str, Any]]:
        """Return in-memory on-air item index/time when the channel stream is running."""
        stream = self._streams.get(str(channel_number))
        if not stream or not stream._is_running:
            return None
        return {
            "item_index": stream._current_item_index,
            "item_start_time": stream._current_item_start_time,
            "playout_start_time": stream._playout_start_time,
        }

    async def get_channel_stream(self, channel_number: str) -> AsyncIterator[bytes]:
        """Get the continuous stream for a channel (async generator)"""
        # Query channel
        db = self.db_session_factory()
        try:
            channel = db.query(Channel).filter(
                Channel.number == channel_number,
                Channel.enabled == True
            ).first()
            
            if not channel:
                raise ValueError(f"Channel {channel_number} not found or not enabled")
            
            async with self._lock:
                if channel_number not in self._streams:
                    await self._start_channel(channel)
                
                stream = self._streams[channel_number]
        finally:
            db.close()
        
        # Yield from the stream's async iterator
        async for chunk in stream.get_stream():
            yield chunk
    
    async def _start_channel(self, channel: Channel):
        """Start continuous streaming for a channel"""
        if channel.number in self._streams:
            logger.info(f"_start_channel() - Channel {channel.number} already started, skipping")
            return
        
        logger.info(f"_start_channel() - Creating ChannelStream for channel {channel.number}...")
        stream = ChannelStream(channel, self.db_session_factory)
        logger.info(f"_start_channel() - ChannelStream created, adding to streams dict...")
        self._streams[channel.number] = stream
        logger.info(f"_start_channel() - Calling stream.start() for channel {channel.number}...")
        await stream.start()
        logger.info(f"_start_channel() - stream.start() completed for channel {channel.number}")
    
    async def stop_channel(self, channel_number: str, *, save_position: bool = False):
        """Stop continuous streaming for a specific channel.

        Default save_position=False so operator stop/reset does not overwrite a
        freshly written playout_start_time with stale in-memory state.
        """
        channel_number = str(channel_number)
        async with self._lock:
            if channel_number in self._streams:
                stream = self._streams[channel_number]
                await stream.stop(save_position=save_position)
                del self._streams[channel_number]
                logger.info(f"Stopped continuous stream for channel {channel_number}")

    async def restart_channel(self, channel_number: str) -> dict:
        """Stop and restart one channel's continuous stream (reloads playout_start_time from DB).

        Other channels are untouched. Used after playout-reset so a global StreamTV
        restart is not required.
        """
        channel_number = str(channel_number)
        db = self.db_session_factory()
        try:
            channel = db.query(Channel).filter(
                Channel.number == channel_number,
                Channel.enabled == True,  # noqa: E712
            ).first()
            if not channel:
                raise ValueError(
                    f"Channel {channel_number} not found or not enabled"
                )

            was_running = False
            async with self._lock:
                if channel_number in self._streams:
                    was_running = True
                    stream = self._streams[channel_number]
                    # Do not write in-memory timeline back — caller may have just
                    # reset playout_start_time in the DB.
                    await stream.stop(save_position=False)
                    del self._streams[channel_number]
                    logger.info(
                        f"restart_channel: stopped channel {channel_number}"
                    )

            # Start outside the stop critical section so start() can take its own locks
            async with self._lock:
                await self._start_channel(channel)

            logger.info(
                f"restart_channel: started channel {channel_number} "
                f"(was_running={was_running})"
            )
            return {
                "channel_number": channel_number,
                "channel_name": channel.name,
                "was_running": was_running,
                "restarted": True,
            }
        finally:
            db.close()

