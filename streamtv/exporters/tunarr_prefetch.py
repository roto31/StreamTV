"""Prefetch full Archive.org MP4s into tunarr_library.export_directory.

StreamTV-driven (channel playlist inventory), not Tunarr lineup — Tunarr Local
Media only sees real files after an operator library scan.

Does not modify live MPEG-TS playout, TunarrRAM cache, or frozen scheduling.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from streamtv.config import config
from streamtv.database.models import (
    CachedMedia,
    CacheStatus,
    Channel,
    MediaItem,
    Playlist,
    PlaylistItem,
    PlayoutMode,
    StreamSource,
)
from streamtv.exporters.tunarr_library import (
    _movie_nfo,
    _safe_basename,
    assert_export_outside_cache,
    export_ready_archive_org,
    resolve_cache_directory,
    resolve_export_directory,
)
from streamtv.utils.download_errors import is_terminal_failure

logger = logging.getLogger(__name__)

_TUNARRAM_MARKERS = ("/Volumes/TunarrRAM", "/TunarrRAM/")


@dataclass
class PrefetchCandidate:
    source_id: str
    url: str
    title: str
    description: Optional[str]
    duration_seconds: int
    channel_number: str
    media_item_id: Optional[int] = None


@dataclass
class PrefetchResult:
    source_id: str
    status: str  # dry_run | skipped | downloaded | exported | error
    dest: Optional[str] = None
    detail: Optional[str] = None


def assert_export_not_tunarr_ram(export_dir: Path) -> None:
    """Refuse writing under the live TunarrRAM volume."""
    resolved = str(export_dir.resolve())
    for marker in _TUNARRAM_MARKERS:
        if resolved == marker.rstrip("/") or marker in resolved:
            raise ValueError(
                f"tunarr_library.export_directory ({export_dir}) must not be under "
                f"TunarrRAM. Use a durable path (e.g. data/tunarr_library)."
            )


def _playout_is_continuous(channel: Channel) -> bool:
    mode = getattr(channel, "playout_mode", None)
    if mode is None:
        return True
    if isinstance(mode, PlayoutMode):
        return mode == PlayoutMode.CONTINUOUS
    return str(mode).lower() in {"continuous", PlayoutMode.CONTINUOUS.value}


def _export_mp4_path(export_dir: Path, source_id: str, naming: str) -> Path:
    # Prefer matching existing file by stem; otherwise predicted basename.
    stem = _safe_basename(source_id, Path(f"{source_id}.mp4"), naming)
    candidate = export_dir / stem
    if candidate.is_file():
        return candidate
    for path in export_dir.glob(f"{Path(stem).stem}.*"):
        if path.suffix.lower() in {".mp4", ".m4v", ".mov"} and path.is_file():
            return path
    return candidate


def _export_dir_bytes(export_dir: Path) -> int:
    if not export_dir.is_dir():
        return 0
    total = 0
    for path in export_dir.rglob("*"):
        if path.is_file() and ".prefetch_work" not in path.parts:
            try:
                total += path.stat().st_size
            except OSError:
                continue
    return total


def _terminal_cached_failure(db: Session, source_id: str) -> Optional[str]:
    row = (
        db.query(CachedMedia)
        .filter(CachedMedia.source == StreamSource.ARCHIVE_ORG)
        .filter(CachedMedia.source_id == source_id)
        .first()
    )
    if row is None:
        return None
    fc = getattr(row, "failure_class", None)
    if is_terminal_failure(fc):
        return str(fc)
    return None


def _ready_cache_path(db: Session, source_id: str) -> Optional[Path]:
    row = (
        db.query(CachedMedia)
        .filter(CachedMedia.source == StreamSource.ARCHIVE_ORG)
        .filter(CachedMedia.source_id == source_id)
        .filter(CachedMedia.status == CacheStatus.READY)
        .first()
    )
    if row is None or not row.local_path:
        return None
    path = Path(row.local_path)
    if path.is_file() and path.suffix.lower() != ".part":
        return path
    return None


def select_prefetch_candidates(
    db: Session,
    *,
    channel_numbers: Optional[Iterable[str]] = None,
    prefetch_hours: Optional[float] = None,
    prefetch_max_items: Optional[int] = None,
    source_ids: Optional[Iterable[str]] = None,
) -> list[PrefetchCandidate]:
    """Select Archive.org playlist items for continuous enabled channels.

    Walks playlist order per channel, accumulating duration until the hours
    horizon or max_items cap. Deduplicates by source_id (first wins).
    """
    cfg = config.tunarr_library
    hours = float(prefetch_hours if prefetch_hours is not None else cfg.prefetch_hours)
    max_items = int(
        prefetch_max_items
        if prefetch_max_items is not None
        else cfg.prefetch_max_items
    )
    horizon_seconds = max(0.0, hours) * 3600.0
    numbers = list(channel_numbers) if channel_numbers is not None else list(
        cfg.channel_numbers or []
    )
    allow_ids = set(source_ids) if source_ids is not None else None

    q = db.query(Channel).filter(Channel.enabled.is_(True))
    if numbers:
        q = q.filter(Channel.number.in_([str(n) for n in numbers]))
    channels = [c for c in q.order_by(Channel.number).all() if _playout_is_continuous(c)]

    selected: list[PrefetchCandidate] = []
    seen: set[str] = set()
    cumulative = 0.0

    for channel in channels:
        if len(selected) >= max_items:
            break
        if horizon_seconds > 0 and cumulative >= horizon_seconds:
            break

        playlists = (
            db.query(Playlist)
            .filter(Playlist.channel_id == channel.id)
            .order_by(Playlist.id)
            .all()
        )
        for playlist in playlists:
            items = (
                db.query(PlaylistItem)
                .filter(PlaylistItem.playlist_id == playlist.id)
                .order_by(PlaylistItem.order, PlaylistItem.id)
                .all()
            )
            for item in items:
                if len(selected) >= max_items:
                    break
                if horizon_seconds > 0 and cumulative >= horizon_seconds:
                    break
                media = (
                    db.query(MediaItem)
                    .filter(MediaItem.id == item.media_item_id)
                    .first()
                )
                if media is None or media.source != StreamSource.ARCHIVE_ORG:
                    continue
                sid = str(media.source_id)
                if allow_ids is not None and sid not in allow_ids:
                    continue
                if sid in seen:
                    continue
                seen.add(sid)
                dur = int(media.duration or 0)
                selected.append(
                    PrefetchCandidate(
                        source_id=sid,
                        url=str(media.url or sid),
                        title=str(media.title or sid),
                        description=media.description,
                        duration_seconds=dur,
                        channel_number=str(channel.number),
                        media_item_id=media.id,
                    )
                )
                cumulative += float(dur) if dur > 0 else 0.0

    return selected


def _build_archive_org_adapter():
    """Construct ArchiveOrgAdapter from config (read-only use of streaming adapter)."""
    from streamtv.streaming.archive_org_adapter import ArchiveOrgAdapter

    if not config.archive_org.enabled:
        raise RuntimeError("archive_org is disabled in config")

    cookies = getattr(config.archive_org, "cookies_file", None)
    return ArchiveOrgAdapter(
        preferred_format=config.archive_org.preferred_format,
        username=config.archive_org.username or None,
        password=config.archive_org.password or None,
        use_authentication=bool(config.archive_org.use_authentication),
        cookies_file=cookies,
    )


async def _download_to_export(
    candidate: PrefetchCandidate,
    export_dir: Path,
    naming: str,
) -> Path:
    """Download straight under export_dir/.prefetch_work then promote to flat name."""
    from streamtv.cache.archive_org_http_downloader import ArchiveOrgHttpDownloader

    work_root = export_dir / ".prefetch_work"
    work_root.mkdir(parents=True, exist_ok=True)
    adapter = _build_archive_org_adapter()
    downloader = ArchiveOrgHttpDownloader(work_root, adapter)
    downloaded = await downloader.download_item(candidate.url)
    if downloaded is None or not downloaded.is_file():
        raise RuntimeError("download returned no file")

    dest_name = _safe_basename(candidate.source_id, downloaded, naming)
    dest = export_dir / dest_name
    if dest.exists() and dest.resolve() == downloaded.resolve():
        return dest
    if dest.exists():
        return dest
    shutil.move(str(downloaded), str(dest))
    nfo = dest.with_suffix(".nfo")
    nfo.write_text(
        _movie_nfo(candidate.title, candidate.description),
        encoding="utf-8",
    )
    return dest


def run_prefetch(
    db: Session,
    *,
    dry_run: bool = True,
    export_directory: Optional[str] = None,
    channel_numbers: Optional[Iterable[str]] = None,
    prefetch_hours: Optional[float] = None,
    prefetch_max_items: Optional[int] = None,
    prefetch_max_gb: Optional[float] = None,
    source_ids: Optional[Iterable[str]] = None,
) -> list[PrefetchResult]:
    """Select and optionally download Archive.org items into the Tunarr export folder."""
    export_dir = resolve_export_directory(export_directory)
    assert_export_outside_cache(export_dir, cache_dir=resolve_cache_directory())
    assert_export_not_tunarr_ram(export_dir)

    cfg = config.tunarr_library
    naming = getattr(cfg, "naming", "source_id") or "source_id"
    max_gb = float(
        prefetch_max_gb if prefetch_max_gb is not None else cfg.prefetch_max_gb
    )
    max_bytes = max(0.0, max_gb) * (1024**3)

    candidates = select_prefetch_candidates(
        db,
        channel_numbers=channel_numbers,
        prefetch_hours=prefetch_hours,
        prefetch_max_items=prefetch_max_items,
        source_ids=source_ids,
    )
    results: list[PrefetchResult] = []
    used_bytes = float(_export_dir_bytes(export_dir))

    for cand in candidates:
        dest_guess = _export_mp4_path(export_dir, cand.source_id, naming)
        if dest_guess.is_file() and dest_guess.stat().st_size > 0:
            results.append(
                PrefetchResult(
                    source_id=cand.source_id,
                    status="skipped",
                    dest=str(dest_guess),
                    detail="already in export",
                )
            )
            continue

        terminal = _terminal_cached_failure(db, cand.source_id)
        if terminal:
            results.append(
                PrefetchResult(
                    source_id=cand.source_id,
                    status="skipped",
                    detail=f"sticky failure: {terminal}",
                )
            )
            continue

        if max_bytes > 0 and used_bytes >= max_bytes:
            results.append(
                PrefetchResult(
                    source_id=cand.source_id,
                    status="skipped",
                    detail=f"prefetch_max_gb ({max_gb}) reached",
                )
            )
            continue

        if dry_run:
            results.append(
                PrefetchResult(
                    source_id=cand.source_id,
                    status="dry_run",
                    dest=str(dest_guess),
                    detail=(
                        f"ch={cand.channel_number} dur={cand.duration_seconds}s "
                        f"title={cand.title!r}"
                    ),
                )
            )
            continue

        ready = _ready_cache_path(db, cand.source_id)
        try:
            if ready is not None:
                export_ready_archive_org(
                    db,
                    dry_run=False,
                    export_directory=str(export_dir),
                    source_ids=[cand.source_id],
                )
                dest = _export_mp4_path(export_dir, cand.source_id, naming)
                results.append(
                    PrefetchResult(
                        source_id=cand.source_id,
                        status="exported",
                        dest=str(dest) if dest.is_file() else None,
                        detail="from READY cache",
                    )
                )
                if dest.is_file():
                    used_bytes += float(dest.stat().st_size)
                continue

            dest = asyncio.run(_download_to_export(cand, export_dir, naming))
            size = dest.stat().st_size if dest.is_file() else 0
            used_bytes += float(size)
            results.append(
                PrefetchResult(
                    source_id=cand.source_id,
                    status="downloaded",
                    dest=str(dest),
                    detail=f"{size} bytes",
                )
            )
        except Exception as exc:
            logger.error("Prefetch failed for %s: %s", cand.source_id, exc)
            results.append(
                PrefetchResult(
                    source_id=cand.source_id,
                    status="error",
                    detail=str(exc),
                )
            )

    return results
