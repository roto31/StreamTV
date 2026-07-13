"""Async download queue: drives CacheManager + source-specific downloaders.

The DownloadQueue is the single orchestrator for all downloads.
It:
  1. Polls the database for QUEUED items.
  2. Dispatches to the correct downloader (ArchiveOrgDownloader or YouTubeDownloader).
  3. Updates CacheManager on success/failure.
  4. Enforces per-source concurrency limits.
"""

import asyncio
import logging
from pathlib import Path
from typing import Callable, Optional

from sqlalchemy.orm import Session

from ..config import config
from ..database.models import CachedMedia, CacheStatus, MediaItem, StreamSource
from .cache_manager import CacheManager
from .archive_org_downloader import ArchiveOrgDownloader
from .archive_org_http_downloader import ArchiveOrgHttpDownloader
from .youtube_downloader import YouTubeDownloader

logger = logging.getLogger(__name__)


class DownloadQueue:
    """Background worker that drains the QUEUED items from the cache manifest."""

    def __init__(
        self,
        cache_manager: CacheManager,
        db_session_factory: Callable[[], Session],
    ):
        self.cache_manager = cache_manager
        self.db_session_factory = db_session_factory
        from ..streaming.stream_manager import StreamManager

        stream_manager = StreamManager()
        if stream_manager.archive_org_adapter:
            self._archive_dl = ArchiveOrgHttpDownloader(
                cache_manager.cache_dir,
                stream_manager.archive_org_adapter,
            )
            logger.info("Archive.org cache: using authenticated HTTP downloader")
            self._archive_cli_fallback = None
        else:
            self._archive_dl = None
            self._archive_cli_fallback = ArchiveOrgDownloader(cache_manager.cache_dir)
            if self._archive_cli_fallback._ia_path:
                logger.info("Archive.org cache: using ia CLI fallback downloader")
            else:
                logger.error(
                    "Archive.org cache: no HTTP adapter and ia CLI not found. "
                    "Restricted-item downloads will fail until internetarchive "
                    "is installed or ArchiveOrgAdapter is enabled. "
                    "Install: pip install internetarchive"
                )
                self._archive_cli_fallback = None
        self._youtube_dl = YouTubeDownloader(cache_manager.cache_dir)
        self._running = False
        self._task: asyncio.Task | None = None
        self._poll_interval = config.cache.queue_poll_interval_seconds
        self._in_flight: set[str] = set()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the background polling loop."""
        if self._running:
            return
        from streamtv.cache.playback_mode import (
            background_downloads_enabled,
            youtube_full_cache_enabled,
        )

        if not background_downloads_enabled() and not youtube_full_cache_enabled():
            cleared = self.cache_manager.suspend_queued_downloads()
            if cleared:
                logger.info(
                    f"DownloadQueue: suspended {cleared} stale QUEUED item(s) "
                    f"(playback_mode={config.cache.playback_mode})"
                )
        elif youtube_full_cache_enabled():
            logger.info(
                "DownloadQueue: youtube_full_cache enabled — YouTube VOD downloads to RAM/disk"
            )
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("DownloadQueue started.")

    async def stop(self) -> None:
        """Stop the background polling loop gracefully."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await asyncio.wait_for(self._task, timeout=10)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        logger.info("DownloadQueue stopped.")

    # ------------------------------------------------------------------
    # On-demand enqueue (called from CacheFirstStreamManager on cache miss)
    # ------------------------------------------------------------------

    async def enqueue(self, media_item: MediaItem) -> None:
        """Queue a media item for background download (idempotent)."""
        from streamtv.cache.playback_mode import source_downloads_enabled

        if not source_downloads_enabled(media_item.source):
            return
        self.cache_manager.queue_for_download(media_item)

    async def download_now(self, media_item: MediaItem) -> Optional[Path]:
        """Download a single item immediately (used for cache-first Archive.org playback)."""
        if media_item.source not in (StreamSource.ARCHIVE_ORG, StreamSource.YOUTUBE):
            return None
        await self.enqueue(media_item)
        await self._download_one(media_item.source_id, media_item)
        return self.cache_manager.get_cached_path(media_item.source_id)

    async def ensure_ring_buffer(self, media_item: MediaItem, max_bytes: int) -> None:
        """Start a capped partial download for tune-time streaming buffer."""
        if media_item.source not in (StreamSource.ARCHIVE_ORG, StreamSource.YOUTUBE):
            return
        # YouTube has no ring-buffer downloader; live tunes use CDN-first yt-dlp only.
        if media_item.source == StreamSource.YOUTUBE:
            return
        source_id = media_item.source_id
        if source_id in self._in_flight:
            return
        self._in_flight.add(source_id)

        async def _run() -> None:
            try:
                await self._download_ring_buffer_one(source_id, media_item, max_bytes)
            finally:
                self._in_flight.discard(source_id)

        asyncio.create_task(_run())

    async def _download_ring_buffer_one(
        self, source_id: str, media_item: MediaItem, max_bytes: int
    ) -> None:
        """Pull only ``max_bytes`` into a .part file; never marks READY."""
        from streamtv.cache.playback_mode import tune_only_buffering

        if not tune_only_buffering():
            return

        logger.info(
            f"Ring buffer dispatch: {source_id} "
            f"(cap {max_bytes / 1024 / 1024:.1f} MB)"
        )
        dest_path = self._dest_path(media_item)
        self.cache_manager.register_download_start(
            media_item, dest_path, ring_buffer=True
        )
        self.cache_manager.evict_lru_to_fit(max_bytes)

        part_path: Optional[Path] = None
        try:
            if media_item.source == StreamSource.ARCHIVE_ORG:
                downloader = self._archive_dl
                if downloader:
                    part_path = await downloader.download_ring_buffer(
                        media_item.url,
                        max_bytes,
                        config.cache.download_strategy.format_preference,
                    )
        except Exception as exc:
            logger.warning(f"Ring buffer failed for {source_id}: {exc}")

        if not part_path or not part_path.exists():
            self.cache_manager.release_ring_buffer(source_id)

    async def ensure_download_started(self, media_item: MediaItem) -> None:
        """Queue and kick off a background download without blocking the caller."""
        from streamtv.cache.playback_mode import source_downloads_enabled

        if not source_downloads_enabled(media_item.source):
            return
        await self.enqueue(media_item)
        source_id = media_item.source_id
        if source_id in self._in_flight:
            return
        self._in_flight.add(source_id)

        async def _run() -> None:
            try:
                await self._download_one(source_id, media_item)
            finally:
                self._in_flight.discard(source_id)

        asyncio.create_task(_run())

    async def prioritize(self, media_item: MediaItem) -> None:
        """Move a queued item to the front of the download batch."""
        from datetime import datetime, timedelta

        await self.enqueue(media_item)
        db = self.db_session_factory()
        try:
            row = (
                db.query(CachedMedia)
                .filter(CachedMedia.source_id == media_item.source_id)
                .first()
            )
            if row and row.status == CacheStatus.QUEUED:
                row.created_at = datetime.utcnow() - timedelta(days=3650)
                db.commit()
        finally:
            db.close()
        await self.ensure_download_started(media_item)

    # ------------------------------------------------------------------
    # Internal loop
    # ------------------------------------------------------------------

    async def _poll_loop(self) -> None:
        """Continuously check for QUEUED items and dispatch downloads."""
        logger.info(
            f"DownloadQueue polling every {self._poll_interval}s"
        )
        while self._running:
            try:
                await self._process_next_batch()
            except Exception as exc:
                logger.error(f"DownloadQueue poll error: {exc}", exc_info=True)
            await asyncio.sleep(self._poll_interval)

    async def _process_next_batch(self) -> None:
        """Fetch QUEUED items and download them sequentially (or concurrently)."""
        from streamtv.cache.playback_mode import (
            background_downloads_enabled,
            youtube_full_cache_enabled,
        )

        yt_only = youtube_full_cache_enabled() and not background_downloads_enabled()
        if not background_downloads_enabled() and not youtube_full_cache_enabled():
            return
        db = self.db_session_factory()
        try:
            queued = (
                db.query(CachedMedia)
                .filter(CachedMedia.status == CacheStatus.QUEUED)
                .filter(
                    (CachedMedia.error_message.is_(None))
                    | (CachedMedia.error_message != "ring_buffer")
                )
                .order_by(CachedMedia.created_at.asc())
                .limit(config.cache.download_strategy.max_concurrent_downloads)
                .all()
            )
            if not queued:
                return

            # Fetch related MediaItems while session is open
            items: list[tuple[str, MediaItem | None]] = []
            for row in queued:
                media_item = (
                    db.query(MediaItem)
                    .filter(MediaItem.id == row.media_item_id)
                    .first()
                )
                if yt_only and (
                    media_item is None
                    or media_item.source != StreamSource.YOUTUBE
                ):
                    continue
                items.append((row.source_id, media_item))
        finally:
            db.close()

        # Dispatch downloads (concurrently up to max_concurrent_downloads)
        tasks = [
            self._download_one(source_id, media_item)
            for source_id, media_item in items
            if media_item is not None
        ]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _download_one(
        self, source_id: str, media_item: MediaItem
    ) -> None:
        """Download a single media item, update the manifest, evict if needed."""
        logger.info(
            f"DownloadQueue dispatching: {source_id} "
            f"(source={media_item.source.value})"
        )

        # Mark as DOWNLOADING in manifest
        dest_path = self._dest_path(media_item)
        self.cache_manager.register_download_start(media_item, dest_path)

        # Evict LRU if needed (estimate 500 MB per item as safety margin)
        self.cache_manager.evict_lru_to_fit(500 * 1024 * 1024)

        result: Path | None = None
        error: str | None = None

        try:
            if media_item.source == StreamSource.ARCHIVE_ORG:
                downloader = self._archive_dl or self._archive_cli_fallback
                if downloader is None:
                    error = (
                        "No Archive.org downloader available "
                        "(HTTP adapter disabled and ia CLI missing)"
                    )
                    logger.error(error)
                else:
                    result = await downloader.download_item(
                        media_item.url,
                        config.cache.download_strategy.format_preference,
                    )
            elif media_item.source == StreamSource.YOUTUBE:
                result = await self._youtube_dl.download_video(
                    media_item.url,
                    config.cache.download_strategy.format_preference,
                )
            else:
                error = f"Unsupported source for caching: {media_item.source}"
                logger.warning(error)

        except Exception as exc:
            error = str(exc)
            logger.error(
                f"Download failed for {source_id}: {exc}", exc_info=True
            )

        if result and result.exists():
            self.cache_manager.register_download_complete(source_id, result)
        else:
            self.cache_manager.register_download_failed(
                source_id, error or "Download returned no file"
            )

    def _dest_path(self, media_item: MediaItem) -> Path:
        """Compute expected destination path for a media item."""
        if media_item.source == StreamSource.ARCHIVE_ORG:
            from ..streaming.stream_manager import StreamManager

            adapter = StreamManager().archive_org_adapter
            identifier = (
                adapter.extract_identifier(media_item.url)
                if adapter
                else None
            )
            filename = (
                adapter.extract_filename(media_item.url) if adapter else None
            )
            base = (
                self.cache_manager.cache_dir
                / "archive_org"
                / (identifier or "unknown")
            )
            if filename:
                return base / filename.replace("/", "__")
            return base
        if media_item.source == StreamSource.YOUTUBE:
            return (
                self.cache_manager.cache_dir
                / "youtube"
                / f"{media_item.source_id}.mp4"
            )
        return self.cache_manager.cache_dir / media_item.source_id
