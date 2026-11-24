"""Background first-run checks with progress events."""

from __future__ import annotations

import logging
import shutil
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class JobState:
    jobs: List[Dict[str, Any]] = field(default_factory=list)
    running: bool = False
    finished: bool = False
    error: Optional[str] = None


_lock = threading.Lock()
_state = JobState()


def get_progress() -> Dict[str, Any]:
    with _lock:
        return {
            "running": _state.running,
            "finished": _state.finished,
            "error": _state.error,
            "jobs": list(_state.jobs),
        }


def _set_job(name: str, status: str, detail: str = "") -> None:
    with _lock:
        for job in _state.jobs:
            if job["id"] == name:
                job["status"] = status
                job["detail"] = detail
                return
        _state.jobs.append({"id": name, "status": status, "detail": detail})


def _run_jobs() -> None:
    global _state
    try:
        _set_job("config", "running", "Ensuring config.yaml")
        from .apply_port import ensure_config_exists

        path = ensure_config_exists()
        _set_job("config", "done", str(path))

        _set_job("ffmpeg", "running", "Checking FFmpeg")
        ffmpeg = shutil.which("ffmpeg") or (
            "/opt/homebrew/bin/ffmpeg" if Path("/opt/homebrew/bin/ffmpeg").is_file() else None
        )
        if ffmpeg:
            _set_job("ffmpeg", "done", ffmpeg)
        else:
            _set_job("ffmpeg", "warn", "FFmpeg not found (recommended: brew install ffmpeg)")

        _set_job("ffprobe", "running", "Checking ffprobe")
        ffprobe = shutil.which("ffprobe") or (
            "/opt/homebrew/bin/ffprobe" if Path("/opt/homebrew/bin/ffprobe").is_file() else None
        )
        if ffprobe:
            _set_job("ffprobe", "done", ffprobe)
        else:
            _set_job("ffprobe", "warn", "ffprobe not found")

        _set_job("yt_dlp", "running", "Ensuring yt-dlp meets floor / tip")
        try:
            from streamtv.utils.dependency_freshness import ensure_yt_dlp_current

            yt = ensure_yt_dlp_current(check_pypi=True, upgrade=True)
            if yt.get("ok"):
                detail = yt.get("detail", "ok")
                if yt.get("upgraded"):
                    detail = f"upgraded — {detail}"
                _set_job("yt_dlp", "done", detail)
            else:
                _set_job(
                    "yt_dlp",
                    "fail",
                    yt.get("detail") or yt.get("pip_detail") or "yt-dlp below floor",
                )
        except Exception as exc:
            _set_job("yt_dlp", "warn", str(exc))

        _set_job("plex_codecs", "running", "Checking / installing Plex AAC codecs")
        try:
            from streamtv.setup.plex_codecs import install_aac_codecs, verify_aac_codecs

            before = verify_aac_codecs()
            if before.skipped:
                _set_job("plex_codecs", "done", before.detail)
            elif before.ok:
                _set_job("plex_codecs", "done", before.detail)
            else:
                after = install_aac_codecs()
                if after.ok:
                    _set_job("plex_codecs", "done", after.detail)
                else:
                    _set_job("plex_codecs", "fail", after.detail)
        except Exception as exc:
            _set_job("plex_codecs", "warn", str(exc))

        _set_job("database", "running", "Database ready on server start")
        _set_job("database", "done", "SQLite initializes on first API use")

        _set_job("youtube_auth", "running", "YouTube auth status")
        try:
            from ..config import config

            yt_ok = bool(getattr(config.youtube, "cookies_file", None))
            _set_job(
                "youtube_auth",
                "done" if yt_ok else "pending",
                "cookies configured" if yt_ok else "sign-in recommended",
            )
        except Exception as exc:
            _set_job("youtube_auth", "warn", str(exc))

        _set_job("archive_auth", "running", "Archive.org auth status")
        try:
            from ..config import config
            from ..utils.macos_credentials import get_credentials_from_keychain

            ao_ok = bool(getattr(config.archive_org, "cookies_file", None)) or bool(
                get_credentials_from_keychain("archive.org")
            )
            _set_job(
                "archive_auth",
                "done" if ao_ok else "pending",
                "credentials present" if ao_ok else "sign-in recommended",
            )
        except Exception as exc:
            _set_job("archive_auth", "warn", str(exc))

        with _lock:
            _state.finished = True
            _state.running = False
    except Exception as exc:
        logger.exception("First-run background jobs failed")
        with _lock:
            _state.error = str(exc)
            _state.finished = True
            _state.running = False


def start_jobs() -> Dict[str, Any]:
    global _state
    with _lock:
        if _state.running:
            return get_progress()
        _state = JobState(running=True, finished=False, error=None, jobs=[])
    thread = threading.Thread(target=_run_jobs, name="streamtv-setup-jobs", daemon=True)
    thread.start()
    return get_progress()
