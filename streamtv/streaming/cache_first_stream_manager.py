"""Cache-first stream manager.

Wraps StreamManager with a cache lookup layer. Behavior depends on
``config.cache.playback_mode``:

  direct — always resolve CDN URL; never enqueue downloads
  buffer — direct stream; prefetch may queue read-ahead only
  full   — cache-first with background downloads (legacy)
"""

import logging
from pathlib import Path

from ..config import config
from ..database.models import MediaItem, StreamSource
from ..cache.cache_manager import CacheManager
from ..cache.download_queue import DownloadQueue
from ..cache.playback_mode import (
    background_downloads_enabled,
    direct_stream_first,
    prefetch_downloads_enabled,
    youtube_full_cache_enabled,
)
from .stream_manager import StreamManager

logger = logging.getLogger(__name__)

# Sources that support download-first caching
_CACHEABLE_SOURCES = {StreamSource.YOUTUBE, StreamSource.ARCHIVE_ORG}


class CacheFirstStreamManager:
    """Provides cache-first URL resolution for the streaming pipeline.

    Used by MPEGTSStreamer._stream_single_item() instead of calling
    StreamManager.get_stream_url() directly.
    """

    def __init__(
        self,
        stream_manager: StreamManager,
        cache_manager: CacheManager,
        download_queue: DownloadQueue,
        base_url: str,
    ):
        self._stream = stream_manager
        self._cache = cache_manager
        self._queue = download_queue
        self._base_url = base_url.rstrip("/")

    # ------------------------------------------------------------------
    # Primary entry point
    # ------------------------------------------------------------------

    async def get_stream_url(
        self,
        media_item: MediaItem,
        force_cache: bool = False,
        *,
        tune_priority: bool = False,
    ) -> str:
        """Return the best URL for playback of media_item.

        Decision tree:
          1. Cache READY → return local file HTTP URL (fastest, no API)
          2. Cache DISABLED or source not cacheable → direct stream
          3. Cache MISS + force_cache=True → enqueue download, raise (caller retries later)
          4. Cache MISS + force_cache=False → enqueue download, fall back to direct stream
        """
        if not config.cache.enabled:
            return await self._stream.get_stream_url(
                media_item.url,
                source=media_item.source,
                tune_priority=tune_priority,
            )

        # ── 1. Cache hit (optional fast path in any mode) ─────────────
        # Prefer a local filesystem path so FFmpeg never loops back through
        # this process's HTTP server (mid-stream drops on restart / port conflict).
        cached_path = self._cache.get_cached_path(media_item.source_id)
        if not cached_path:
            cached_path = self._cache.get_playable_path(media_item.source_id)
        if cached_path:
            local = str(cached_path.resolve())
            logger.info(
                f"[CACHE HIT] {media_item.title[:60]} → {cached_path.name} (local)"
            )
            return local

        # ── 2. Non-cacheable source → direct stream ───────────────────
        if media_item.source not in _CACHEABLE_SOURCES:
            logger.debug(
                f"Source {media_item.source} not cacheable, streaming directly."
            )
            return await self._stream.get_stream_url(
                media_item.url,
                source=media_item.source,
                tune_priority=tune_priority,
            )

        # ── 3. Cacheable source but not yet cached ────────────────────
        archive_org_force_cache = (
            media_item.source == StreamSource.ARCHIVE_ORG
            and background_downloads_enabled()
        )
        youtube_force_cache = (
            media_item.source == StreamSource.YOUTUBE
            and youtube_full_cache_enabled()
        )
        min_buffer_bytes = int(config.cache.stream_buffer_mb * 1024 * 1024)

        if (
            (background_downloads_enabled() or youtube_force_cache)
            and not self._cache.is_download_pending(media_item.source_id)
        ):
            await self._queue.enqueue(media_item)
            logger.info(
                f"[CACHE MISS] Queued background download: "
                f"{media_item.source_id} ({media_item.title[:60]})"
            )

        if youtube_force_cache:
            await self._queue.ensure_download_started(media_item)
            cached_path = self._cache.get_cached_path(media_item.source_id)
            if cached_path:
                local = str(cached_path.resolve())
                logger.info(
                    f"[CACHE HIT] {media_item.title[:60]} → {cached_path.name} (local)"
                )
                return local
            if force_cache:
                raise CacheNotReadyError(
                    f"YouTube content not yet cached: {media_item.source_id}"
                )
            logger.info(
                f"[YOUTUBE CACHE WAIT] {media_item.title[:60]} "
                f"(download in progress; caller should wait)"
            )

        if direct_stream_first():
            from streamtv.cache.playback_mode import playback_mode as _pm

            if _pm() == "buffer":
                min_sec = float(getattr(config.cache, "stream_buffer_seconds", 0.0) or 0.0)
                buffered = self._cache.estimate_buffered_seconds(
                    media_item.source_id, media_item
                )
                buffer_path = self._cache.get_buffer_path(
                    media_item.source_id, min_buffer_bytes
                )
                if buffer_path and (min_sec <= 0 or buffered >= min_sec):
                    url = self._file_to_http_url(buffer_path)
                    logger.info(
                        f"[BUFFER HIT] {media_item.title[:60]} → {buffer_path.name} "
                        f"({buffered:.1f}s buffered)"
                    )
                    return url
            logger.info(
                f"[DIRECT] {media_item.title[:60]} "
                f"(playback_mode={config.cache.playback_mode})"
            )
            return await self._stream.get_stream_url(
                media_item.url,
                source=media_item.source,
                tune_priority=tune_priority,
            )

        if archive_org_force_cache:
            await self._queue.ensure_download_started(media_item)

            cached_path = self._cache.get_cached_path(media_item.source_id)
            if cached_path:
                return str(cached_path.resolve())

            buffer_path = self._cache.get_buffer_path(
                media_item.source_id, min_buffer_bytes
            )
            if buffer_path:
                # Incomplete .part buffers stay on HTTP so the ASGI cache
                # endpoint can stream a growing file; complete files use local paths.
                url = self._file_to_http_url(buffer_path)
                logger.info(
                    f"[BUFFER HIT] {media_item.title[:60]} → {buffer_path.name}"
                )
                return url

            if config.cache.archive_org_stream_while_caching:
                logger.info(
                    f"[STREAM-WHILE-CACHE] {media_item.title[:60]} "
                    f"(direct archive.org, background download continues)"
                )
                return await self._stream.get_stream_url(
                    media_item.url,
                    source=media_item.source,
                    tune_priority=tune_priority,
                )

            raise CacheNotReadyError(
                f"Archive.org content not yet cached: {media_item.source_id}"
            )

        if force_cache:
            raise CacheNotReadyError(
                f"Content not yet cached: {media_item.source_id}"
            )

        # ── 4. Fall back to direct stream while download proceeds ─────
        logger.info(
            f"[CACHE MISS] Falling back to direct stream: {media_item.title[:60]}"
        )
        return await self._stream.get_stream_url(
            media_item.url,
            source=media_item.source,
            tune_priority=tune_priority,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _file_to_http_url(self, path: Path) -> str:
        """Convert a local file Path to an HTTP URL served by StreamTV."""
        # Paths are relative to cache_dir root; serve via /cache/files/ endpoint
        try:
            rel = path.relative_to(self._cache.cache_dir)
        except ValueError:
            rel = path
        return f"{self._base_url}/cache/files/{rel.as_posix()}"


class CacheNotReadyError(RuntimeError):
    """Raised when force_cache=True but content is not yet available."""
