"""SQLAlchemy and config hooks that schedule automatic backups."""

from __future__ import annotations

import logging
from typing import Set

from sqlalchemy import event
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Tables whose commits should trigger a backup. Playback positions are excluded
# so continuous playout never storms the disk.
_BACKUP_TABLES: Set[str] = {
    "channels",
    "media_items",
    "collections",
    "collection_items",
    "playlists",
    "playlist_items",
    "schedules",
    "schedule_items",
    "ffmpeg_profiles",
    "watermarks",
    "resolutions",
}

_listeners_registered = False


def _session_has_backup_changes(session: Session) -> bool:
    for obj in list(session.new) + list(session.dirty) + list(session.deleted):
        table = getattr(getattr(obj, "__table__", None), "name", None)
        if table in _BACKUP_TABLES:
            return True
    return False


def _after_commit(session: Session) -> None:
    # Flag set in before_commit because after_commit has cleared the identity sets.
    if not getattr(session, "_streamtv_backup_pending", False):
        return
    try:
        session._streamtv_backup_pending = False  # type: ignore[attr-defined]
    except Exception:
        pass
    try:
        from .scheduler import schedule_backup

        schedule_backup(reason="db_commit")
    except Exception as exc:
        logger.debug("backup: after_commit schedule failed: %s", exc)


def _before_commit(session: Session) -> None:
    try:
        session._streamtv_backup_pending = _session_has_backup_changes(session)  # type: ignore[attr-defined]
    except Exception:
        session._streamtv_backup_pending = False  # type: ignore[attr-defined]


def register_db_hooks() -> None:
    """Register Session before_commit / after_commit listeners (idempotent)."""
    global _listeners_registered
    if _listeners_registered:
        return
    event.listen(Session, "before_commit", _before_commit)
    event.listen(Session, "after_commit", _after_commit)
    _listeners_registered = True
    logger.debug("backup: SQLAlchemy commit hooks registered")
