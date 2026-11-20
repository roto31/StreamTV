"""Export READY Archive.org cache files into a Tunarr Local Media directory.

Isolation rules:
- Reads CachedMedia READY rows only; never gates live MPEG-TS tune.
- Writes only under ``tunarr_library.export_directory`` (must not nest under cache_dir).
- Does not call Tunarr HTTP write APIs (operator points Tunarr at the export folder).
"""

from __future__ import annotations

import logging
import re
import shutil
import xml.sax.saxutils as xml_escape
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from streamtv.config import config
from streamtv.database.models import CachedMedia, CacheStatus, MediaItem, StreamSource

logger = logging.getLogger(__name__)

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._\-\[\]]+")


@dataclass
class ExportResult:
    source_id: str
    status: str  # linked | copied | skipped | dry_run | error
    dest: Optional[str] = None
    detail: Optional[str] = None


def resolve_export_directory(export_directory: Optional[str] = None) -> Path:
    raw = export_directory or config.tunarr_library.export_directory
    return Path(raw).expanduser().resolve()


def resolve_cache_directory() -> Path:
    return Path(config.cache.cache_directory).expanduser().resolve()


def assert_export_outside_cache(
    export_dir: Path,
    cache_dir: Optional[Path] = None,
) -> None:
    """Refuse export paths that nest inside (or equal) the live cache directory."""
    cache = (cache_dir or resolve_cache_directory()).resolve()
    export = export_dir.resolve()
    try:
        export.relative_to(cache)
    except ValueError:
        return
    raise ValueError(
        f"tunarr_library.export_directory ({export}) must not be inside or equal to "
        f"cache.cache_directory ({cache}). Point Tunarr at a separate library folder."
    )


def _safe_basename(source_id: str, local_path: Path, naming: str) -> str:
    if naming == "basename":
        stem = local_path.stem
    else:
        stem = source_id.replace("/", "_")
        for ext in (".mp4", ".m4v", ".mov", ".mkv", ".webm"):
            if stem.lower().endswith(ext):
                stem = stem[: -len(ext)]
                break
    stem = _SAFE_NAME.sub("_", stem).strip("._") or "item"
    suffix = local_path.suffix.lower() or ".mp4"
    if not suffix.startswith("."):
        suffix = f".{suffix}"
    if suffix not in {".mp4", ".m4v", ".mov", ".mkv", ".webm"}:
        suffix = ".mp4"
    return f"{stem}{suffix}"


def _movie_nfo(title: str, plot: Optional[str] = None) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        "<movie>",
        f"  <title>{xml_escape.escape(title)}</title>",
    ]
    if plot:
        lines.append(f"  <plot>{xml_escape.escape(plot)}</plot>")
    lines.append("</movie>")
    return "\n".join(lines) + "\n"


def _hardlink_or_copy(src: Path, dest: Path) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        if dest.stat().st_ino == src.stat().st_ino and dest.stat().st_dev == src.stat().st_dev:
            return "linked"
        return "skipped"
    try:
        dest.hardlink_to(src)
        return "linked"
    except OSError:
        shutil.copy2(src, dest)
        return "copied"


def iter_ready_archive_rows(
    db: Session,
    *,
    source_ids: Optional[Iterable[str]] = None,
) -> list[tuple[CachedMedia, Optional[MediaItem]]]:
    q = (
        db.query(CachedMedia)
        .filter(CachedMedia.status == CacheStatus.READY)
        .filter(CachedMedia.source == StreamSource.ARCHIVE_ORG)
    )
    if source_ids is not None:
        ids = list(source_ids)
        if not ids:
            return []
        q = q.filter(CachedMedia.source_id.in_(ids))
    rows = q.all()
    out: list[tuple[CachedMedia, Optional[MediaItem]]] = []
    for row in rows:
        media = None
        if row.media_item_id:
            media = db.query(MediaItem).filter(MediaItem.id == row.media_item_id).first()
        out.append((row, media))
    return out


def export_ready_archive_org(
    db: Session,
    *,
    dry_run: bool = True,
    export_directory: Optional[str] = None,
    source_ids: Optional[Iterable[str]] = None,
) -> list[ExportResult]:
    """Hardlink/copy READY archive_org cache MP4s + write Kodi movie NFOs."""
    export_dir = resolve_export_directory(export_directory)
    assert_export_outside_cache(export_dir)

    naming = getattr(config.tunarr_library, "naming", "source_id") or "source_id"
    results: list[ExportResult] = []

    for row, media in iter_ready_archive_rows(db, source_ids=source_ids):
        src = Path(row.local_path)
        if not src.is_file() or src.suffix.lower() == ".part":
            results.append(
                ExportResult(
                    source_id=row.source_id,
                    status="skipped",
                    detail="missing or partial file",
                )
            )
            continue
        if src.suffix.lower() not in {".mp4", ".m4v", ".mov"}:
            results.append(
                ExportResult(
                    source_id=row.source_id,
                    status="skipped",
                    detail=f"non-mp4 extension {src.suffix}",
                )
            )
            continue

        dest_name = _safe_basename(row.source_id, src, naming)
        dest = export_dir / dest_name
        nfo_path = dest.with_suffix(".nfo")
        title = (media.title if media else None) or row.source_id
        plot = media.description if media and getattr(media, "description", None) else None

        if dry_run:
            results.append(
                ExportResult(
                    source_id=row.source_id,
                    status="dry_run",
                    dest=str(dest),
                    detail=f"would export {src} → {dest}",
                )
            )
            continue

        try:
            action = _hardlink_or_copy(src, dest)
            if action != "skipped" or not nfo_path.exists():
                nfo_path.write_text(_movie_nfo(title, plot), encoding="utf-8")
            results.append(
                ExportResult(
                    source_id=row.source_id,
                    status=action,
                    dest=str(dest),
                )
            )
        except Exception as exc:
            logger.error("Export failed for %s: %s", row.source_id, exc)
            results.append(
                ExportResult(
                    source_id=row.source_id,
                    status="error",
                    detail=str(exc),
                )
            )

    return results
