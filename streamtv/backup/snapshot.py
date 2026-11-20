"""Create StreamTV portable backup zip packages."""

from __future__ import annotations

import logging
import os
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import yaml

from .manifest import build_manifest, sha256_file, write_manifest
from .paths import (
    COOKIE_CONFIG_KEYS,
    FORMAT_VERSION,
    HOST_LOCAL_KEYS,
    LATEST_NAME,
    TIMESTAMP_PREFIX,
    backup_root,
    config_path,
    data_dir,
    latest_zip_path,
    project_root,
    schedules_dir,
    secrets_env_path,
    sqlite_db_path,
)

logger = logging.getLogger(__name__)


def _member_entry(arcname: str, path: Path) -> Dict[str, Any]:
    return {
        "path": arcname,
        "size": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def _add_file(
    zf: zipfile.ZipFile,
    src: Path,
    arcname: str,
    members: List[Dict[str, Any]],
) -> None:
    if not src.is_file():
        return
    zf.write(src, arcname)
    members.append(_member_entry(arcname, src))


def _add_tree(
    zf: zipfile.ZipFile,
    src_dir: Path,
    arc_prefix: str,
    members: List[Dict[str, Any]],
    *,
    pattern: str = "**/*",
) -> None:
    if not src_dir.is_dir():
        return
    for path in sorted(src_dir.glob(pattern)):
        if not path.is_file():
            continue
        # Skip cache media and large runtime trees under data/
        rel = path.relative_to(src_dir)
        parts = rel.parts
        if parts and parts[0] in {"cache", "enrichment"}:
            continue
        arcname = f"{arc_prefix}/{rel.as_posix()}"
        _add_file(zf, path, arcname, members)


def _vacuum_sqlite(db_path: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    if not db_path.is_file():
        # Empty placeholder DB so restore always has a member.
        conn = sqlite3.connect(str(dest))
        conn.close()
        return
    src = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        src.execute(f"VACUUM INTO '{dest.as_posix()}'")
    finally:
        src.close()


def _cookie_paths_from_config(config_data: Dict[str, Any]) -> List[Tuple[str, Path]]:
    found: List[Tuple[str, Path]] = []
    for section, key in COOKIE_CONFIG_KEYS:
        section_data = config_data.get(section) or {}
        raw = section_data.get(key)
        if not raw:
            continue
        path = Path(str(raw)).expanduser()
        if path.is_file():
            arc = f"cookies/{path.name}"
            found.append((arc, path))
    return found


def _watermark_images() -> List[Tuple[str, Path]]:
    """Collect watermark image files if they live under the project."""
    results: List[Tuple[str, Path]] = []
    root = project_root()
    for candidate_dir in (root / "data" / "watermarks", root / "watermarks"):
        if not candidate_dir.is_dir():
            continue
        for path in sorted(candidate_dir.rglob("*")):
            if path.is_file():
                rel = path.relative_to(root)
                results.append((rel.as_posix(), path))
    return results


def _host_local_notes(config_data: Dict[str, Any]) -> List[str]:
    notes: List[str] = []
    for section, key in HOST_LOCAL_KEYS:
        section_data = config_data.get(section) or {}
        if key in section_data and section_data[key] is not None:
            notes.append(f"host_local:{section}.{key}={section_data[key]!r}")
    return notes


def create_snapshot(
    *,
    backup_dir: Optional[Path] = None,
    include_secrets: Optional[bool] = None,
    retain_count: Optional[int] = None,
) -> Path:
    """Write a timestamped backup zip and update streamtv-backup-latest.zip.

    Returns the path to the timestamped zip.
    """
    from streamtv.config import config

    root = backup_root(backup_dir)
    if include_secrets is None:
        include_secrets = bool(getattr(config.backup, "include_secrets", True))
    if retain_count is None:
        retain_count = int(getattr(config.backup, "retain_count", 7))

    cfg_path = config_path()
    config_data: Dict[str, Any] = {}
    if cfg_path.is_file():
        with cfg_path.open("r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f) or {}

    stamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d-%H%M%S")
    timestamped = root / f"{TIMESTAMP_PREFIX}{stamp}.zip"
    latest = root / LATEST_NAME

    with tempfile.TemporaryDirectory(prefix="streamtv-backup-") as tmp:
        tmp_path = Path(tmp)
        members: List[Dict[str, Any]] = []
        staging_zip = tmp_path / "package.zip"
        db_copy = tmp_path / "streamtv.db"

        try:
            _vacuum_sqlite(sqlite_db_path(), db_copy)
        except Exception as exc:
            logger.warning("VACUUM INTO failed (%s); copying DB file", exc)
            src_db = sqlite_db_path()
            if src_db.is_file():
                shutil.copy2(src_db, db_copy)
            else:
                sqlite3.connect(str(db_copy)).close()

        with zipfile.ZipFile(staging_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            if cfg_path.is_file():
                _add_file(zf, cfg_path, "config.yaml", members)
            _add_file(zf, db_copy, "streamtv.db", members)

            data = data_dir()
            # Channel YAML inventories at data/*.yaml (not recursive cache)
            if data.is_dir():
                for path in sorted(data.glob("*.yaml")):
                    if path.is_file():
                        _add_file(zf, path, f"data/{path.name}", members)
                for sub in ("channel_icons", "builder_drafts", "tuner_device_ids"):
                    _add_tree(zf, data / sub, f"data/{sub}", members)

            schedules = schedules_dir()
            if schedules.is_dir():
                for path in sorted(schedules.glob("*.yml")) + sorted(schedules.glob("*.yaml")):
                    if path.is_file():
                        _add_file(zf, path, f"schedules/{path.name}", members)

            for arc, path in _watermark_images():
                _add_file(zf, path, arc, members)

            for arc, path in _cookie_paths_from_config(config_data):
                _add_file(zf, path, arc, members)

            if include_secrets:
                secrets = secrets_env_path()
                if secrets.is_file():
                    _add_file(zf, secrets, "secrets.env", members)

            notes = _host_local_notes(config_data)
            notes.append("exclude:venv,cache_media,logs")
            if not include_secrets:
                notes.append("secrets:omitted")

            manifest = build_manifest(
                format_version=FORMAT_VERSION,
                members=members,
                notes=notes,
            )
            manifest_path = tmp_path / "manifest.json"
            write_manifest(manifest_path, manifest)
            zf.write(manifest_path, "manifest.json")

        # Atomic publish: copy to timestamped, then rename onto latest
        shutil.copy2(staging_zip, timestamped)
        os.chmod(timestamped, 0o600)
        latest_tmp = root / f".{LATEST_NAME}.tmp"
        shutil.copy2(staging_zip, latest_tmp)
        os.chmod(latest_tmp, 0o600)
        latest_tmp.replace(latest)

    _rotate_backups(root, retain_count=retain_count)
    logger.info("backup: wrote %s (latest=%s)", timestamped, latest)
    return timestamped


def _rotate_backups(root: Path, *, retain_count: int) -> None:
    if retain_count < 1:
        return
    stamped = sorted(
        (
            p
            for p in root.glob(f"{TIMESTAMP_PREFIX}*.zip")
            if p.name != LATEST_NAME and not p.name.startswith(".")
        ),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for old in stamped[retain_count:]:
        try:
            old.unlink()
        except OSError as exc:
            logger.warning("Could not remove old backup %s: %s", old, exc)


def snapshot_status(*, backup_dir: Optional[Path] = None) -> Dict[str, Any]:
    root = backup_root(backup_dir)
    latest = latest_zip_path(root)
    stamped = sorted(
        (p for p in root.glob(f"{TIMESTAMP_PREFIX}*.zip") if p.name != LATEST_NAME),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return {
        "enabled": True,
        "backup_dir": str(root),
        "latest_path": str(latest) if latest.is_file() else None,
        "latest_exists": latest.is_file(),
        "latest_mtime": latest.stat().st_mtime if latest.is_file() else None,
        "latest_size": latest.stat().st_size if latest.is_file() else None,
        "retained_count": len(stamped),
        "retained": [p.name for p in stamped[:20]],
        "format_version": FORMAT_VERSION,
    }
