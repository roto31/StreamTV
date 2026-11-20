"""Debounced automatic backup scheduler."""

from __future__ import annotations

import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

_scheduler: Optional["BackupScheduler"] = None
_scheduler_lock = threading.Lock()


class BackupScheduler:
    """Coalesce backup requests into a single snapshot after debounce_seconds."""

    def __init__(self, *, debounce_seconds: float = 30.0, enabled: bool = True) -> None:
        self.debounce_seconds = max(0.0, float(debounce_seconds))
        self.enabled = enabled
        self._timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()
        self._last_error: Optional[str] = None
        self._last_path: Optional[str] = None
        self._pending = False

    def schedule(self, *, reason: str = "change") -> None:
        if not self.enabled:
            return
        with self._lock:
            self._pending = True
            if self._timer is not None:
                self._timer.cancel()
            delay = self.debounce_seconds
            self._timer = threading.Timer(delay, self._run, args=(reason,))
            self._timer.daemon = True
            self._timer.start()
            logger.debug("backup: scheduled in %.1fs (reason=%s)", delay, reason)

    def run_now(self, *, reason: str = "manual") -> Optional[str]:
        """Create a snapshot immediately (cancels pending debounce)."""
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
            self._pending = False
        return self._run(reason)

    def _run(self, reason: str) -> Optional[str]:
        if not self.enabled:
            return None
        try:
            from .snapshot import create_snapshot

            path = create_snapshot()
            self._last_path = str(path)
            self._last_error = None
            self._pending = False
            logger.info("backup: snapshot complete (%s) reason=%s", path, reason)
            return self._last_path
        except Exception as exc:
            self._last_error = str(exc)
            logger.exception("backup: snapshot failed (reason=%s): %s", reason, exc)
            return None

    def status(self) -> dict:
        return {
            "enabled": self.enabled,
            "debounce_seconds": self.debounce_seconds,
            "pending": self._pending,
            "last_path": self._last_path,
            "last_error": self._last_error,
        }

    def stop(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None


def get_scheduler() -> BackupScheduler:
    global _scheduler
    with _scheduler_lock:
        if _scheduler is None:
            try:
                from streamtv.config import config

                enabled = bool(getattr(config.backup, "enabled", True))
                debounce = float(getattr(config.backup, "debounce_seconds", 30))
            except Exception:
                enabled = True
                debounce = 30.0
            _scheduler = BackupScheduler(debounce_seconds=debounce, enabled=enabled)
        return _scheduler


def schedule_backup(*, reason: str = "change") -> None:
    """Public hook used by config/DB/import/auth change sites."""
    try:
        get_scheduler().schedule(reason=reason)
    except Exception as exc:
        logger.debug("backup: schedule skipped: %s", exc)


def start_scheduler(*, take_initial_if_missing: bool = True) -> BackupScheduler:
    """Start (or return) the global scheduler; optionally snapshot if no latest."""
    sched = get_scheduler()
    if take_initial_if_missing and sched.enabled:
        try:
            from .paths import latest_zip_path

            if not latest_zip_path().is_file():
                sched.run_now(reason="startup_missing_latest")
        except Exception as exc:
            logger.warning("backup: initial snapshot skipped: %s", exc)
    return sched


def stop_scheduler() -> None:
    global _scheduler
    with _scheduler_lock:
        if _scheduler is not None:
            _scheduler.stop()
