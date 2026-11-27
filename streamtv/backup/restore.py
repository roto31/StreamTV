"""Restore StreamTV from a portable backup zip."""

from __future__ import annotations

import logging
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .manifest import read_manifest
from .paths import (
    FORMAT_VERSION,
    HOST_LOCAL_KEYS,
    config_path,
    data_dir,
    project_root,
    restore_pending_paths,
    schedules_dir,
    secrets_env_path,
    sqlite_db_path,
)

logger = logging.getLogger(__name__)

REQUIRED_MEMBERS = {"manifest.json", "streamtv.db"}


class BackupValidationError(ValueError):
    """Raised when a backup zip is invalid."""


def validate_backup_zip(zip_path: Path) -> Dict[str, Any]:
    """Open and validate a backup zip; return the manifest."""
    if not zip_path.is_file():
        raise BackupValidationError(f"Backup file not found: {zip_path}")
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = set(zf.namelist())
            # Reject absolute / path-traversal members
            for name in names:
                if name.startswith("/") or ".." in Path(name).parts:
                    raise BackupValidationError(f"Unsafe zip member: {name}")
            missing = REQUIRED_MEMBERS - names
            if missing:
                raise BackupValidationError(f"Missing required members: {sorted(missing)}")
            with tempfile.TemporaryDirectory(prefix="streamtv-validate-") as tmp:
                zf.extract("manifest.json", tmp)
                manifest = read_manifest(Path(tmp) / "manifest.json")
    except zipfile.BadZipFile as exc:
        raise BackupValidationError("Not a valid zip file") from exc

    version = manifest.get("format_version")
    if version != FORMAT_VERSION:
        raise BackupValidationError(
            f"Unsupported format_version: {version!r} (expected {FORMAT_VERSION})"
        )
    return manifest


def _strip_host_local(config_data: Dict[str, Any]) -> Dict[str, Any]:
    for section, key in HOST_LOCAL_KEYS:
        section_data = config_data.get(section)
        if isinstance(section_data, dict) and key in section_data:
            section_data.pop(key, None)
    return config_data


def _rewrite_cookie_paths(config_data: Dict[str, Any], cookies_dir: Path) -> Dict[str, Any]:
    """Point cookie paths at the restored cookies directory when present."""
    mapping = {
        ("youtube", "cookies_file"): "youtube_cookies.txt",
        ("youtube", "cookies_json_file"): None,
        ("archive_org", "cookies_file"): "archive_cookies.txt",
        ("pbs", "cookies_file"): "pbs_cookies.txt",
    }
    for (section, key), default_name in mapping.items():
        section_data = config_data.get(section)
        if not isinstance(section_data, dict):
            continue
        raw = section_data.get(key)
        if not raw:
            continue
        name = Path(str(raw)).name
        candidate = cookies_dir / name
        if candidate.is_file():
            section_data[key] = str(candidate.resolve())
        elif default_name and (cookies_dir / default_name).is_file():
            section_data[key] = str((cookies_dir / default_name).resolve())
    return config_data


def _safety_copy(dest: Path, safety_root: Path) -> None:
    if not dest.exists():
        return
    target = safety_root / dest.name
    if dest.is_dir():
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(dest, target)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dest, target)


def restore_from_zip(
    zip_path: Path,
    *,
    target_root: Optional[Path] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Replace config/DB/data/schedules from a validated backup zip.

    Returns a report dict. When dry_run=True, no files are written.
    """
    manifest = validate_backup_zip(zip_path)
    root = Path(target_root) if target_root else project_root()
    cfg_dest = (root / "config.yaml") if target_root else config_path()
    db_dest = (root / "streamtv.db") if target_root else sqlite_db_path()
    data_dest = (root / "data") if target_root else data_dir()
    schedules_dest = (root / "schedules") if target_root else schedules_dir()
    cookies_dest = root / "cookies"

    report: Dict[str, Any] = {
        "format_version": manifest.get("format_version"),
        "app_version": manifest.get("app_version"),
        "dry_run": dry_run,
        "files": [],
        "target_root": str(root),
    }

    with tempfile.TemporaryDirectory(prefix="streamtv-restore-") as tmp:
        extract_dir = Path(tmp) / "extract"
        extract_dir.mkdir()
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)
            names = set(zf.namelist())

        report["files"] = sorted(names)

        if dry_run:
            report["status"] = "validated"
            report["would_replace"] = {
                "config": str(cfg_dest),
                "database": str(db_dest),
                "data": str(data_dest),
                "schedules": str(schedules_dest),
            }
            return report

        stamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
        safety = root / f".streamtv-pre-restore-{stamp}"
        safety.mkdir(parents=True, exist_ok=True)
        try:
            _safety_copy(cfg_dest, safety)
            _safety_copy(db_dest, safety)
            if data_dest.exists():
                # Only back up yaml/icons subsets we replace, not entire cache
                for sub in ("channel_icons", "builder_drafts"):
                    _safety_copy(data_dest / sub, safety / "data")
                for yaml_file in data_dest.glob("*.yaml"):
                    _safety_copy(yaml_file, safety / "data")
            _safety_copy(schedules_dest, safety)

            # Apply config with host-local strip + cookie rewrite
            restored_cfg = extract_dir / "config.yaml"
            if restored_cfg.is_file():
                with restored_cfg.open("r", encoding="utf-8") as f:
                    config_data = yaml.safe_load(f) or {}
                config_data = _strip_host_local(config_data)

                # Place cookies first so rewrite can see them
                cookies_src = extract_dir / "cookies"
                if cookies_src.is_dir():
                    cookies_dest.mkdir(parents=True, exist_ok=True)
                    for src in cookies_src.iterdir():
                        if src.is_file():
                            shutil.copy2(src, cookies_dest / src.name)
                config_data = _rewrite_cookie_paths(config_data, cookies_dest)

                cfg_dest.parent.mkdir(parents=True, exist_ok=True)
                with cfg_dest.open("w", encoding="utf-8") as f:
                    yaml.safe_dump(
                        config_data,
                        f,
                        sort_keys=False,
                        default_flow_style=False,
                        allow_unicode=True,
                    )

            restored_db = extract_dir / "streamtv.db"
            if restored_db.is_file():
                db_dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(restored_db, db_dest)

            # data/*.yaml and selected subdirs
            data_src = extract_dir / "data"
            if data_src.is_dir():
                data_dest.mkdir(parents=True, exist_ok=True)
                for path in data_src.glob("*.yaml"):
                    shutil.copy2(path, data_dest / path.name)
                for sub in ("channel_icons", "builder_drafts"):
                    src_sub = data_src / sub
                    if src_sub.is_dir():
                        dest_sub = data_dest / sub
                        if dest_sub.exists():
                            shutil.rmtree(dest_sub)
                        shutil.copytree(src_sub, dest_sub)

            schedules_src = extract_dir / "schedules"
            if schedules_src.is_dir():
                schedules_dest.mkdir(parents=True, exist_ok=True)
                for path in schedules_src.iterdir():
                    if path.is_file():
                        shutil.copy2(path, schedules_dest / path.name)

            # watermarks under data/watermarks or watermarks/
            for wm_name in ("data/watermarks", "watermarks"):
                wm_src = extract_dir / wm_name
                if wm_src.is_dir():
                    wm_dest = root / wm_name
                    wm_dest.parent.mkdir(parents=True, exist_ok=True)
                    if wm_dest.exists():
                        shutil.rmtree(wm_dest)
                    shutil.copytree(wm_src, wm_dest)

            secrets_src = extract_dir / "secrets.env"
            if secrets_src.is_file():
                secrets_dest = secrets_env_path()
                secrets_dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(secrets_src, secrets_dest)
                try:
                    secrets_dest.chmod(0o600)
                except OSError:
                    pass

            report["status"] = "restored"
            report["safety_copy"] = str(safety)
            logger.info("backup: restored from %s (safety=%s)", zip_path, safety)
            return report
        except Exception:
            logger.exception("backup: restore failed; safety copy at %s", safety)
            raise


def stage_restore_pending(zip_path: Path, data_directory: Optional[Path] = None) -> Dict[str, str]:
    """Validate zip, copy to pending path, write marker for next lifespan."""
    validate_backup_zip(zip_path)
    marker, pending_zip = restore_pending_paths(data_directory)
    pending_zip.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(zip_path, pending_zip)
    marker.write_text(
        datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z") + "\n",
        encoding="utf-8",
    )
    try:
        pending_zip.chmod(0o600)
        marker.chmod(0o600)
    except OSError:
        pass
    return {"marker": str(marker), "zip": str(pending_zip)}


def apply_pending_restore(data_directory: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """If a restore-pending marker exists, restore and clear the marker.

    Called from application lifespan before serving. Non-fatal on missing files.
    """
    marker, pending_zip = restore_pending_paths(data_directory)
    if not marker.is_file():
        return None
    if not pending_zip.is_file():
        logger.error("backup: restore marker present but zip missing: %s", pending_zip)
        try:
            marker.unlink()
        except OSError:
            pass
        return None
    try:
        report = restore_from_zip(pending_zip, target_root=None)
        report["pending_applied"] = True
        return report
    finally:
        for path in (marker, pending_zip):
            try:
                path.unlink(missing_ok=True)
            except OSError as exc:
                logger.warning("Could not remove pending restore file %s: %s", path, exc)
