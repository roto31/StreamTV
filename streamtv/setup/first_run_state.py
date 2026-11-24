"""AppleSetupDone-style marker for StreamTV first-run completion."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

SETUP_DONE_FILENAME = ".StreamTVSetupDone"
REPO_SETUP_DONE_FILENAME = ".streamtv-setup-done"
SETUP_SCHEMA_VERSION = 1


def _app_support_dir() -> Path:
    override = os.environ.get("STREAMTV_DATA_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / "Library" / "Application Support" / "StreamTV"


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _app_version() -> str:
    version_file = _repo_root() / "VERSION"
    try:
        return version_file.read_text(encoding="utf-8").strip() or "0.0.0"
    except OSError:
        return "0.0.0"


def setup_done_paths() -> list[Path]:
    """Canonical + repo-cwd marker locations (first existing wins for read)."""
    paths = [
        _app_support_dir() / SETUP_DONE_FILENAME,
        Path.cwd() / REPO_SETUP_DONE_FILENAME,
        _repo_root() / REPO_SETUP_DONE_FILENAME,
    ]
    # Dedupe while preserving order
    seen: set[str] = set()
    out: list[Path] = []
    for p in paths:
        key = str(p.resolve()) if p.parent.exists() else str(p)
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def is_setup_done() -> bool:
    return read_setup_done() is not None


def read_setup_done() -> Optional[dict[str, Any]]:
    for path in setup_done_paths():
        if not path.is_file():
            continue
        try:
            raw = path.read_text(encoding="utf-8").strip()
            if not raw:
                return {"path": str(path), "completed_at": None, "app_version": None}
            if raw.startswith("{"):
                data = json.loads(raw)
                data["path"] = str(path)
                return data
            return {
                "path": str(path),
                "completed_at": raw,
                "app_version": None,
                "setup_schema_version": SETUP_SCHEMA_VERSION,
            }
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Failed reading SetupDone %s: %s", path, exc)
    return None


def write_setup_done(*, extra: Optional[dict[str, Any]] = None) -> Path:
    """Write SetupDone to Application Support (and repo marker when cwd is repo)."""
    payload: dict[str, Any] = {
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "app_version": _app_version(),
        "setup_schema_version": SETUP_SCHEMA_VERSION,
    }
    if extra:
        payload.update(extra)

    primary = _app_support_dir() / SETUP_DONE_FILENAME
    primary.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2) + "\n"
    primary.write_text(text, encoding="utf-8")

    # Mirror next to cwd for LaunchAgent/repo installs
    try:
        repo_marker = Path.cwd() / REPO_SETUP_DONE_FILENAME
        if repo_marker.parent.resolve() != primary.parent.resolve():
            repo_marker.write_text(text, encoding="utf-8")
    except OSError as exc:
        logger.debug("Could not write repo SetupDone mirror: %s", exc)

    logger.info("Wrote SetupDone marker at %s", primary)
    return primary


def clear_setup_done() -> list[str]:
    """Remove all known SetupDone markers. Returns paths removed."""
    removed: list[str] = []
    for path in setup_done_paths():
        try:
            if path.is_file():
                path.unlink()
                removed.append(str(path))
        except OSError as exc:
            logger.warning("Failed removing SetupDone %s: %s", path, exc)
    return removed
