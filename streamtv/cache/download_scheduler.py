"""APScheduler-based download scheduler.

Reads scheduled_downloads from config.yaml and fires downloads at
the configured cron times (default: 2 AM daily).

Also runs maintenance tasks:
  - Evict expired cache entries (daily at 3 AM)
  - Reconcile manifest vs disk (daily at 3:05 AM)

Dependencies:
    pip install apscheduler>=3.10
"""

import logging
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

from sqlalchemy.orm import Session

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    HAS_APSCHEDULER = True
except ImportError:
    HAS_APSCHEDULER = False

from ..config import config
from ..database.models import MediaItem, StreamSource
from .cache_manager import CacheManager
from .download_queue import DownloadQueue
from .archive_org_downloader import ArchiveOrgDownloader
from .youtube_downloader import YouTubeDownloader

logger = logging.getLogger(__name__)


def _parse_cron(cron_str: str) -> dict:
    """Parse a cron expression string into APScheduler CronTrigger kwargs.

    Expects five fields: minute hour day month day_of_week
    e.g. "0 2 * * *" → {"minute": "0", "hour": "2", ...}
    """
    parts = cron_str.strip().split()
    if len(parts) != 5:
        raise ValueError(
            f"Invalid cron expression (need 5 fields): {cron_str!r}"
        )
    minute, hour, day, month, day_of_week = parts
    return {
        "minute": minute,
        "hour": hour,
        "day": day,
        "month": month,
        "day_of_week": day_of_week,
    }


class DownloadScheduler:
    """Manages all scheduled download jobs for StreamTV.

    Lifecycle:
        scheduler = DownloadScheduler(cache_manager, download_queue, db_factory)
        await scheduler.start()       # called from main.py lifespan startup
        await scheduler.stop()        # called from main.py lifespan shutdown
    """

    def __init__(
        self,
        cache_manager: CacheManager,
        download_queue: DownloadQueue,
        db_session_factory: Callable[[], Session],
    ):
        self.cache_manager = cache_manager
        self.download_queue = download_queue
        self.db_session_factory = db_session_factory
        self._archive_dl = ArchiveOrgDownloader(cache_manager.cache_dir)
        self._youtube_dl = YouTubeDownloader(cache_manager.cache_dir)
        self._scheduler: "AsyncIOScheduler | None" = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Register all cron jobs and start the scheduler."""
        if not HAS_APSCHEDULER:
            logger.warning(
                "apscheduler not installed — scheduled downloads disabled. "
                "Install with: pip install apscheduler>=3.10"
            )
            return

        if not config.cache.download_strategy.enabled:
            logger.info("Download strategy disabled in config; scheduler idle.")
            return

        self._scheduler = AsyncIOScheduler()
        self._register_jobs()
        self._scheduler.start()
        logger.info(
            f"DownloadScheduler started with "
            f"{len(self._scheduler.get_jobs())} job(s)."
        )

    async def stop(self) -> None:
        """Shut down the scheduler."""
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("DownloadScheduler stopped.")

    # ------------------------------------------------------------------
    # Job registration
    # ------------------------------------------------------------------

    def _register_jobs(self) -> None:
        """Register all jobs from config and built-in maintenance tasks."""
        scheduler = self._scheduler
        assert scheduler is not None

        # ── User-configured downloads ──────────────────────────────────
        for job_conf in config.cache.download_strategy.scheduled_downloads:
            if not job_conf.get("enabled", True):
                continue
            url = job_conf.get("url", "")
            cron_str = job_conf.get("schedule", "0 2 * * *")
            fmt = job_conf.get(
                "format",
                config.cache.download_strategy.format_preference,
            )
            label = job_conf.get("label", url[:50])
            max_items = int(job_conf.get("max_items", 100))

            if not url:
                logger.warning(f"Scheduled download entry has no URL: {job_conf}")
                continue

            try:
                cron_kwargs = _parse_cron(cron_str)
            except ValueError as exc:
                logger.error(f"Bad cron expression for job {label!r}: {exc}")
                continue

            # Detect source type from URL host
            parsed_url = urlparse(url)
            host = (parsed_url.hostname or "").lower()
            if (
                host == "youtube.com"
                or host.endswith(".youtube.com")
                or host == "youtu.be"
                or host.endswith(".youtu.be")
            ):
                func = self._run_youtube_job
            elif host == "archive.org" or host.endswith(".archive.org"):
                func = self._run_archive_item_job
            else:
                # Treat as Archive.org collection identifier
                func = self._run_archive_collection_job

            scheduler.add_job(
                func,
                trigger=CronTrigger(**cron_kwargs),
                kwargs={"url": url, "format_preference": fmt, "max_items": max_items},
                id=f"dl_{label[:30]}",
                replace_existing=True,
                max_instances=1,
                coalesce=True,
            )
            logger.info(
                f"Scheduled download: {label!r} cron={cron_str!r} fmt={fmt}"
            )

        # ── Maintenance: evict expired + reconcile ─────────────────────
        scheduler.add_job(
            self._run_eviction,
            trigger=CronTrigger(hour=3, minute=0),
            id="cache_evict_expired",
            replace_existing=True,
            max_instances=1,
        )
        scheduler.add_job(
            self._run_reconcile,
            trigger=CronTrigger(hour=3, minute=5),
            id="cache_reconcile",
            replace_existing=True,
            max_instances=1,
        )

    # ------------------------------------------------------------------
    # Job handlers
    # ------------------------------------------------------------------

    async def _run_youtube_job(
        self, url: str, format_preference: str, max_items: int
    ) -> None:
        logger.info(f"Scheduled YouTube download starting: {url}")
        if "playlist" in url or "list=" in url:
            paths = await self._youtube_dl.download_playlist(
                url, format_preference, max_items
            )
            logger.info(
                f"Scheduled YouTube download complete: {len(paths)} files"
            )
        else:
            path = await self._youtube_dl.download_video(url, format_preference)
            logger.info(
                f"Scheduled YouTube download: "
                f"{'OK' if path else 'FAILED'} → {path}"
            )

    async def _run_archive_item_job(
        self, url: str, format_preference: str, max_items: int  # noqa: ARG002
    ) -> None:
        # Extract identifier from URL
        from ..streaming.archive_org_adapter import ArchiveOrgAdapter

        adapter = ArchiveOrgAdapter()
        identifier = adapter.extract_identifier(url) or url.rstrip("/").split("/")[-1]
        logger.info(f"Scheduled Archive.org download: {identifier}")
        path = await self._archive_dl.download_item(identifier, format_preference)
        logger.info(
            f"Scheduled Archive.org download: "
            f"{'OK' if path else 'FAILED'} → {path}"
        )

    async def _run_archive_collection_job(
        self, url: str, format_preference: str, max_items: int
    ) -> None:
        # Treat raw string as collection identifier
        collection_id = url.strip()
        logger.info(
            f"Scheduled Archive.org collection download: {collection_id}"
        )
        paths = await self._archive_dl.download_collection(
            collection_id,
            format_preference=format_preference,
            max_items=max_items,
        )
        logger.info(
            f"Collection download complete: {len(paths)} files from {collection_id}"
        )

    async def _run_eviction(self) -> None:
        count = self.cache_manager.evict_expired()
        logger.info(f"Scheduled eviction: removed {count} expired entries.")

    async def _run_reconcile(self) -> None:
        self.cache_manager.reconcile()
        logger.info("Scheduled reconciliation: manifest vs disk synced.")

    # ------------------------------------------------------------------
    # On-demand trigger (for testing / UI-triggered downloads)
    # ------------------------------------------------------------------

    async def trigger_now(self, job_id: str) -> bool:
        """Immediately execute a scheduled job by its ID."""
        if not self._scheduler:
            return False
        job = self._scheduler.get_job(job_id)
        if not job:
            logger.warning(f"Job {job_id!r} not found in scheduler.")
            return False
        job.modify(next_run_time=__import__("datetime").datetime.utcnow())
        return True

    def list_jobs(self) -> list[dict]:
        """Return a summary of all registered jobs."""
        if not self._scheduler:
            return []
        jobs = []
        for job in self._scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "next_run": (
                    job.next_run_time.isoformat()
                    if job.next_run_time
                    else None
                ),
                "trigger": str(job.trigger),
            })
        return jobs
