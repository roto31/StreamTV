"""Path helpers for StreamTV backup packages."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

FORMAT_VERSION = 1
LATEST_NAME = "streamtv-backup-latest.zip"
TIMESTAMP_PREFIX = "streamtv-backup-"
RESTORE_PENDING_MARKER = ".streamtv-restore-pending"
RESTORE_PENDING_ZIP = "streamtv-restore-pending.zip"

# Host-local config keys stripped on restore (kept in manifest notes only).
HOST_LOCAL_KEYS = (
    ("ffmpeg", "ffmpeg_path"),
    ("ffmpeg", "ffprobe_path"),
    ("cache", "cache_directory"),
)

COOKIE_CONFIG_KEYS = (
    ("youtube", "cookies_file"),
    ("youtube", "cookies_json_file"),
    ("archive_org", "cookies_file"),
    ("pbs", "cookies_file"),
    ("pbs", "cookies_import_path"),
)


def project_root() -> Path:
    """Repository / Application Support root (parent of the streamtv package)."""
    return Path(__file__).resolve().parents[2]


def config_path() -> Path:
    from streamtv.config import config

    return Path(config._config_path).resolve()


def backup_root(override: Optional[Path] = None) -> Path:
    """Directory that holds backup zips."""
    if override is not None:
        root = Path(override)
    else:
        env = os.getenv("STREAMTV_BACKUP_DIR")
        if env:
            root = Path(env)
        else:
            # Prefer Application Support when the server cwd is that directory.
            cfg_parent = config_path().parent
            support = Path.home() / "Library" / "Application Support" / "StreamTV"
            try:
                if cfg_parent.resolve() == support.resolve() or Path.cwd().resolve() == support.resolve():
                    root = support / "backups"
                else:
                    root = cfg_parent / "backups"
            except OSError:
                root = cfg_parent / "backups"
    root.mkdir(parents=True, exist_ok=True)
    return root


def latest_zip_path(root: Optional[Path] = None) -> Path:
    return (root or backup_root()) / LATEST_NAME


def secrets_env_path() -> Path:
    candidate = os.getenv("STREAMTV_SECRETS_FILE") or str(
        Path.home() / ".streamtv" / "secrets.env"
    )
    return Path(candidate)


def sqlite_db_path() -> Path:
    """Resolve SQLite file path from database.url."""
    from streamtv.config import config

    url = config.database.url or "sqlite:///./streamtv.db"
    if url.startswith("sqlite:///"):
        raw = url[len("sqlite:///") :]
        path = Path(raw)
        if not path.is_absolute():
            # Relative to config parent (macOS Application Support cwd).
            path = config_path().parent / path
        return path.resolve()
    raise ValueError(f"Unsupported database URL for backup: {url!r}")


def data_dir() -> Path:
    return project_root() / "data"


def schedules_dir() -> Path:
    return project_root() / "schedules"


def restore_pending_paths(data_directory: Optional[Path] = None) -> tuple[Path, Path]:
    """Marker + staged zip used by macOS onboarding / Settings restore."""
    base = data_directory or config_path().parent
    return base / RESTORE_PENDING_MARKER, base / RESTORE_PENDING_ZIP
