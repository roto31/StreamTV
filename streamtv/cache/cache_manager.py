"""Central cache manager: LRU eviction, TTL, manifest tracking, cache-first lookup."""

import asyncio
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional

from sqlalchemy.orm import Session

from ..config import config
from ..database.models import CachedMedia, CacheStatus, MediaItem, StreamSource

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages the local media cache.

    Responsibilities:
    - Maintain a SQLite-backed manifest (CachedMedia model)
    - Enforce size limit via LRU eviction
    - Resolve cache-first lookups for StreamManager
    - Provide a single entry-point for all cache reads/writes
    """

    def __init__(self, db_session_factory: Callable[[], Session]):
        self.db_session_factory = db_session_factory
        self.cache_dir = Path(config.cache.cache_directory).expanduser().resolve()
        self.max_size_bytes = int(config.cache.max_size_gb * 1024 ** 3)
        self.default_ttl_hours = config.cache.default_ttl_hours
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(
            f"CacheManager initialized. dir={self.cache_dir} "
            f"max={config.cache.max_size_gb:.1f} GB ttl={self.default_ttl_hours}h"
        )

    # ------------------------------------------------------------------
    # Public read API (synchronous — safe to call from async context)
    # ------------------------------------------------------------------

    def get_cached_path(self, source_id: str) -> Optional[Path]:
        """Return local path for source_id if it is cached and still valid.

        Returns None when:
          - Not in the manifest
          - File was deleted externally
          - TTL expired
        Updates accessed_at and hit_count on a valid hit.
        """
        db = self.db_session_factory()
        try:
            row = (
                db.query(CachedMedia)
                .filter(
                    CachedMedia.source_id == source_id,
                    CachedMedia.status == CacheStatus.READY,
                )
                .first()
            )
            if row is None:
                return None

            path = Path(row.local_path)

            # Stale or missing file → remove manifest entry
            if not path.exists():
                logger.warning(f"Cache entry exists but file missing: {path}")
                db.delete(row)
                db.commit()
                return None

            path = self._resolve_playable_path(path)
            if path is None:
                logger.warning(
                    f"Cache entry not playable (empty or ambiguous directory): {row.local_path}"
                )
                db.delete(row)
                db.commit()
                return None

            # TTL check
            if row.expires_at and datetime.utcnow() > row.expires_at:
                logger.info(f"Cache TTL expired for {source_id}, removing.")
                self._evict_row(db, row)
                return None

            # Record hit
            row.accessed_at = datetime.utcnow()
            row.hit_count = (row.hit_count or 0) + 1
            if str(path) != row.local_path:
                row.local_path = str(path)
            db.commit()
            logger.debug(f"Cache HIT: {source_id} → {path}")
            return path

        finally:
            db.close()

    def get_playable_path(self, source_id: str) -> Optional[Path]:
        """Return a complete local file even if manifest status is stale."""
        ready = self.get_cached_path(source_id)
        if ready:
            return ready

        db = self.db_session_factory()
        try:
            row = (
                db.query(CachedMedia)
                .filter(CachedMedia.source_id == source_id)
                .first()
            )
            if row is None:
                return None
            path = Path(row.local_path)
            if path.suffix == ".part":
                return None
            resolved = self._resolve_playable_path(path)
            if resolved and resolved.is_file() and resolved.stat().st_size > 0:
                return resolved
            return None
        finally:
            db.close()

    @staticmethod
    def _resolve_playable_path(path: Path) -> Optional[Path]:
        """Return a concrete media file path; directories store one media file inside."""
        if path.is_file():
            return path
        if not path.is_dir():
            return None

        media_suffixes = {".mp4", ".mkv", ".webm", ".mov", ".m4v", ".ts", ".avi"}
        candidates = [
            child
            for child in path.iterdir()
            if child.is_file() and child.suffix.lower() in media_suffixes
        ]
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            return max(candidates, key=lambda p: p.stat().st_size)
        return None

    @staticmethod
    def _part_path_for(final_path: Path) -> Path:
        if final_path.suffix:
            return final_path.with_suffix(f"{final_path.suffix}.part")
        return Path(f"{final_path}.part")

    def _part_path_for_source(self, source_id: str) -> Optional[Path]:
        """Return the in-progress .part path for a source_id, if any."""
        db = self.db_session_factory()
        try:
            row = (
                db.query(CachedMedia)
                .filter(
                    CachedMedia.source_id == source_id,
                    CachedMedia.status.in_(
                        [CacheStatus.QUEUED, CacheStatus.DOWNLOADING]
                    ),
                )
                .first()
            )
            if row is None:
                return None
            manifest_path = Path(row.local_path)
            part_path = (
                manifest_path
                if manifest_path.suffix == ".part"
                else self._part_path_for(manifest_path)
            )
            if part_path.is_file():
                return part_path
            return None
        finally:
            db.close()

    def estimate_buffered_seconds(
        self, source_id: str, media_item: MediaItem
    ) -> float:
        """Estimate seconds of media available in cache or partial download."""
        if self.get_cached_path(source_id):
            duration = getattr(media_item, "duration", None) or 0
            return float(duration) if duration > 0 else 9999.0

        part_path = self._part_path_for_source(source_id)
        if part_path is None:
            return 0.0

        part_size = part_path.stat().st_size
        if part_size <= 0:
            return 0.0

        db = self.db_session_factory()
        try:
            row = (
                db.query(CachedMedia)
                .filter(CachedMedia.source_id == source_id)
                .first()
            )
            total_bytes = int(row.size_bytes or 0) if row else 0
        finally:
            db.close()

        duration = getattr(media_item, "duration", None) or 0
        if total_bytes > 0 and duration > 0:
            return min(float(duration), duration * (part_size / total_bytes))

        return (part_size * 8) / 2_500_000

    def get_buffer_path(
        self, source_id: str, min_bytes: int
    ) -> Optional[Path]:
        """Return a partial (.part) download path when enough data exists to start playback."""
        if min_bytes <= 0:
            return None
        db = self.db_session_factory()
        try:
            row = (
                db.query(CachedMedia)
                .filter(
                    CachedMedia.source_id == source_id,
                    CachedMedia.status.in_(
                        [CacheStatus.QUEUED, CacheStatus.DOWNLOADING]
                    ),
                )
                .first()
            )
            if row is None:
                return None

            manifest_path = Path(row.local_path)
            part_path = (
                manifest_path
                if manifest_path.suffix == ".part"
                else self._part_path_for(manifest_path)
            )
            if part_path.is_file():
                size = part_path.stat().st_size
                if size >= min_bytes:
                    logger.info(
                        f"Buffer ready: {source_id} → {part_path.name} "
                        f"({size / 1024 / 1024:.1f} MB)"
                    )
                    return part_path
            return None
        finally:
            db.close()

    def is_download_pending(self, source_id: str) -> bool:
        """Return True if source_id is already queued or downloading."""
        db = self.db_session_factory()
        try:
            row = (
                db.query(CachedMedia)
                .filter(
                    CachedMedia.source_id == source_id,
                    CachedMedia.status.in_(
                        [CacheStatus.QUEUED, CacheStatus.DOWNLOADING]
                    ),
                )
                .first()
            )
            return row is not None
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Public write API
    # ------------------------------------------------------------------

    def register_download_start(
        self,
        media_item: MediaItem,
        local_path: Path,
        ttl_hours: Optional[int] = None,
        ring_buffer: bool = False,
    ) -> None:
        """Create or update a manifest row marking a download as in-progress."""
        db = self.db_session_factory()
        try:
            row = (
                db.query(CachedMedia)
                .filter(CachedMedia.source_id == media_item.source_id)
                .first()
            )
            expires_at = datetime.utcnow() + timedelta(
                hours=ttl_hours or self.default_ttl_hours
            )
            if row is None:
                row = CachedMedia(
                    source_id=media_item.source_id,
                    source=media_item.source,
                    media_item_id=media_item.id,
                    local_path=str(local_path),
                    status=CacheStatus.DOWNLOADING,
                    expires_at=expires_at,
                    size_bytes=0,
                    error_message="ring_buffer" if ring_buffer else None,
                )
                db.add(row)
            else:
                row.local_path = str(local_path)
                row.status = CacheStatus.DOWNLOADING
                row.expires_at = expires_at
                if ring_buffer:
                    row.error_message = "ring_buffer"
            db.commit()
        finally:
            db.close()

    def release_ring_buffer(self, source_id: str) -> None:
        """Delete tune-time .part buffer; does not remove completed cache files."""
        db = self.db_session_factory()
        try:
            row = (
                db.query(CachedMedia)
                .filter(CachedMedia.source_id == source_id)
                .first()
            )
            if row is None:
                return
            if row.status == CacheStatus.READY:
                return
            path = Path(row.local_path)
            part = (
                path if path.suffix == ".part" else self._part_path_for(path)
            )
            if part.is_file():
                try:
                    part.unlink()
                except OSError as exc:
                    logger.debug(f"Could not delete ring buffer {part}: {exc}")
            if row.error_message == "ring_buffer" or row.status != CacheStatus.READY:
                db.delete(row)
                db.commit()
        finally:
            db.close()

    def register_download_complete(
        self, source_id: str, local_path: Path
    ) -> None:
        """Mark a download as READY and record file size."""
        db = self.db_session_factory()
        try:
            row = (
                db.query(CachedMedia)
                .filter(CachedMedia.source_id == source_id)
                .first()
            )
            if row is None:
                logger.error(
                    f"register_download_complete: no manifest row for {source_id}"
                )
                return
            size = local_path.stat().st_size if local_path.exists() else 0
            row.status = CacheStatus.READY
            row.size_bytes = size
            row.accessed_at = datetime.utcnow()
            db.commit()
            logger.info(
                f"Cache READY: {source_id} → {local_path} "
                f"({size / 1024 / 1024:.1f} MB)"
            )
        finally:
            db.close()

    def register_download_failed(self, source_id: str, error: str) -> None:
        """Mark a download as FAILED with an error message."""
        db = self.db_session_factory()
        try:
            row = (
                db.query(CachedMedia)
                .filter(CachedMedia.source_id == source_id)
                .first()
            )
            if row:
                row.status = CacheStatus.FAILED
                row.error_message = error[:1024]
                db.commit()
        finally:
            db.close()

    def queue_for_download(self, media_item: MediaItem) -> None:
        """Insert a QUEUED manifest row (idempotent)."""
        if self.is_download_pending(media_item.source_id):
            logger.debug(
                f"Already queued/downloading: {media_item.source_id}"
            )
            return
        db = self.db_session_factory()
        try:
            existing = (
                db.query(CachedMedia)
                .filter(CachedMedia.source_id == media_item.source_id)
                .first()
            )
            if existing and existing.status == CacheStatus.READY:
                logger.debug(
                    f"Already cached: {media_item.source_id}"
                )
                return
            if existing:
                existing.status = CacheStatus.QUEUED
                existing.error_message = None
            else:
                placeholder_path = (
                    self.cache_dir
                    / str(media_item.source.value)
                    / media_item.source_id
                )
                db.add(
                    CachedMedia(
                        source_id=media_item.source_id,
                        source=media_item.source,
                        media_item_id=media_item.id,
                        local_path=str(placeholder_path),
                        status=CacheStatus.QUEUED,
                        size_bytes=0,
                        expires_at=datetime.utcnow()
                        + timedelta(hours=self.default_ttl_hours),
                    )
                )
            db.commit()
            logger.info(f"Queued for download: {media_item.source_id}")
        finally:
            db.close()

    def suspend_queued_downloads(self) -> int:
        """Drop QUEUED/DOWNLOADING manifest rows when full downloads are disabled."""
        db = self.db_session_factory()
        try:
            rows = (
                db.query(CachedMedia)
                .filter(
                    CachedMedia.status.in_(
                        [CacheStatus.QUEUED, CacheStatus.DOWNLOADING]
                    )
                )
                .filter(
                    (CachedMedia.error_message.is_(None))
                    | (CachedMedia.error_message != "ring_buffer")
                )
                .all()
            )
            count = len(rows)
            for row in rows:
                db.delete(row)
            if count:
                db.commit()
            return count
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Eviction
    # ------------------------------------------------------------------

    def evict_expired(self) -> int:
        """Remove all expired cache entries. Returns number evicted."""
        db = self.db_session_factory()
        count = 0
        try:
            expired = (
                db.query(CachedMedia)
                .filter(
                    CachedMedia.expires_at < datetime.utcnow(),
                    CachedMedia.status == CacheStatus.READY,
                )
                .all()
            )
            for row in expired:
                self._evict_row(db, row)
                count += 1
            db.commit()
            if count:
                logger.info(f"Evicted {count} expired cache entries.")
        finally:
            db.close()
        return count

    def evict_source(self, source_id: str, *, reason: str = "after_play") -> bool:
        """Delete one manifest row and its file (Tunarr-style session teardown)."""
        db = self.db_session_factory()
        try:
            row = (
                db.query(CachedMedia)
                .filter(CachedMedia.source_id == source_id)
                .first()
            )
            if row is None:
                return False
            size_mb = (row.size_bytes or 0) / 1024 / 1024
            self._evict_row(db, row)
            db.commit()
            logger.info(
                f"Cache evicted ({reason}): {source_id} ({size_mb:.1f} MB)"
            )
            return True
        finally:
            db.close()

    def evict_sources_not_in(
        self,
        keep_source_ids: set[str],
        *,
        reason: str = "off_schedule",
        candidate_source_ids: Optional[set[str]] = None,
    ) -> int:
        """Remove READY/QUEUED entries outside keep set.

        When candidate_source_ids is set, only rows owned by that channel schedule
        are eligible — prevents one channel's prefetch from evicting another's cache.
        """
        db = self.db_session_factory()
        count = 0
        try:
            rows = (
                db.query(CachedMedia)
                .filter(
                    CachedMedia.status.in_(
                        [CacheStatus.READY, CacheStatus.QUEUED]
                    )
                )
                .all()
            )
            for row in rows:
                if row.source_id in keep_source_ids:
                    continue
                if (
                    candidate_source_ids is not None
                    and row.source_id not in candidate_source_ids
                ):
                    continue
                self._evict_row(db, row)
                count += 1
            if count:
                db.commit()
                logger.info(
                    f"Off-schedule cache eviction ({reason}): "
                    f"removed {count} entries "
                    f"(keeping {len(keep_source_ids)} source_id(s))"
                )
        finally:
            db.close()
        return count

    def evict_lru_to_fit(self, needed_bytes: int) -> None:
        """Free at least needed_bytes by evicting least-recently-used entries."""
        db = self.db_session_factory()
        try:
            current = self._total_size_bytes(db)
            if current + needed_bytes <= self.max_size_bytes:
                return
            to_free = (current + needed_bytes) - self.max_size_bytes
            freed = 0
            grace_cutoff = datetime.utcnow() - timedelta(minutes=20)
            rows = (
                db.query(CachedMedia)
                .filter(CachedMedia.status == CacheStatus.READY)
                .filter(CachedMedia.accessed_at < grace_cutoff)
                .order_by(CachedMedia.accessed_at.asc())
                .all()
            )
            for row in rows:
                if freed >= to_free:
                    break
                freed += row.size_bytes or 0
                self._evict_row(db, row)
                logger.info(
                    f"LRU evicted: {row.source_id} "
                    f"({(row.size_bytes or 0) / 1024 / 1024:.1f} MB)"
                )
            if freed < to_free:
                logger.warning(
                    "LRU eviction could not free %.1f MB (freed %.1f MB); "
                    "recently accessed entries are protected",
                    to_free / 1024 / 1024,
                    freed / 1024 / 1024,
                )
            db.commit()
        finally:
            db.close()

    def _evict_row(self, db: Session, row: CachedMedia) -> None:
        path = Path(row.local_path)
        if path.exists():
            try:
                if path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    path.unlink(missing_ok=True)
                # Remove empty parent dirs inside cache_dir
                parent = path.parent
                if (
                    parent != self.cache_dir
                    and parent.exists()
                    and not any(parent.iterdir())
                ):
                    parent.rmdir()
            except Exception as exc:
                logger.warning(f"Failed to delete {path}: {exc}")
        db.delete(row)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> dict:
        """Return a dict of cache statistics for the dashboard/API."""
        db = self.db_session_factory()
        try:
            total_bytes = self._total_size_bytes(db)
            ready = (
                db.query(CachedMedia)
                .filter(CachedMedia.status == CacheStatus.READY)
                .count()
            )
            queued = (
                db.query(CachedMedia)
                .filter(CachedMedia.status == CacheStatus.QUEUED)
                .count()
            )
            downloading = (
                db.query(CachedMedia)
                .filter(CachedMedia.status == CacheStatus.DOWNLOADING)
                .count()
            )
            failed = (
                db.query(CachedMedia)
                .filter(CachedMedia.status == CacheStatus.FAILED)
                .count()
            )
            total_hits = (
                db.query(
                    CachedMedia.hit_count
                )
                .filter(CachedMedia.status == CacheStatus.READY)
                .all()
            )
            hit_sum = sum(r[0] or 0 for r in total_hits)
            return {
                "cache_directory": str(self.cache_dir),
                "max_size_gb": config.cache.max_size_gb,
                "used_bytes": total_bytes,
                "used_gb": round(total_bytes / 1024 ** 3, 3),
                "used_pct": round(
                    total_bytes / self.max_size_bytes * 100, 1
                ) if self.max_size_bytes else 0,
                "items_ready": ready,
                "items_queued": queued,
                "items_downloading": downloading,
                "items_failed": failed,
                "total_hits": hit_sum,
            }
        finally:
            db.close()

    def _total_size_bytes(self, db: Session) -> int:
        rows = (
            db.query(CachedMedia.size_bytes)
            .filter(CachedMedia.status == CacheStatus.READY)
            .all()
        )
        return sum(r[0] or 0 for r in rows)

    # ------------------------------------------------------------------
    # Cleanup on disk vs manifest reconciliation
    # ------------------------------------------------------------------

    def reconcile(self) -> None:
        """Remove manifest rows whose files no longer exist on disk."""
        db = self.db_session_factory()
        try:
            rows = (
                db.query(CachedMedia)
                .filter(CachedMedia.status == CacheStatus.READY)
                .all()
            )
            removed = 0
            for row in rows:
                if not Path(row.local_path).exists():
                    db.delete(row)
                    removed += 1
            db.commit()
            if removed:
                logger.info(
                    f"Reconciliation removed {removed} stale manifest entries."
                )
        finally:
            db.close()
