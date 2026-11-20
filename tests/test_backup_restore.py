"""Tests for backup restore validation and path remapping."""

from __future__ import annotations

import json
import sqlite3
import zipfile
from pathlib import Path

import pytest
import yaml

from streamtv.backup.manifest import build_manifest
from streamtv.backup.paths import FORMAT_VERSION
from streamtv.backup.restore import (
    BackupValidationError,
    restore_from_zip,
    stage_restore_pending,
    validate_backup_zip,
)


def _make_backup_zip(path: Path, *, format_version: int = FORMAT_VERSION) -> Path:
    with zipfile.ZipFile(path, "w") as zf:
        cfg = {
            "server": {"port": 8410},
            "ffmpeg": {
                "ffmpeg_path": "/old/machine/ffmpeg",
                "ffprobe_path": "/old/machine/ffprobe",
            },
            "cache": {"cache_directory": "/old/cache"},
            "youtube": {"cookies_file": "/old/youtube_cookies.txt"},
        }
        zf.writestr("config.yaml", yaml.safe_dump(cfg))
        db_tmp = path.parent / "_tmp.db"
        conn = sqlite3.connect(str(db_tmp))
        conn.execute("CREATE TABLE channels (id INTEGER PRIMARY KEY, number TEXT)")
        conn.execute("INSERT INTO channels (number) VALUES ('99')")
        conn.commit()
        conn.close()
        zf.write(db_tmp, "streamtv.db")
        db_tmp.unlink()
        zf.writestr("data/channels_99.yaml", "channels: []\n")
        zf.writestr("schedules/99.yml", "items: []\n")
        zf.writestr("cookies/youtube_cookies.txt", "# Netscape\n")
        members = [
            {"path": "config.yaml", "size": 1, "sha256": "x"},
            {"path": "streamtv.db", "size": 1, "sha256": "y"},
        ]
        manifest = build_manifest(format_version=format_version, members=members)
        zf.writestr("manifest.json", json.dumps(manifest))
    return path


def test_validate_rejects_garbage(tmp_path: Path) -> None:
    junk = tmp_path / "not-a-backup.zip"
    junk.write_bytes(b"not a zip")
    with pytest.raises(BackupValidationError):
        validate_backup_zip(junk)


def test_validate_rejects_wrong_version(tmp_path: Path) -> None:
    zpath = tmp_path / "bad-version.zip"
    _make_backup_zip(zpath, format_version=999)
    with pytest.raises(BackupValidationError, match="format_version"):
        validate_backup_zip(zpath)


def test_restore_strips_host_local_and_rewrites_cookies(tmp_path: Path) -> None:
    zpath = tmp_path / "good.zip"
    _make_backup_zip(zpath)
    target = tmp_path / "new-install"
    target.mkdir()

    report = restore_from_zip(zpath, target_root=target, dry_run=False)
    assert report["status"] == "restored"
    assert (target / "config.yaml").is_file()
    assert (target / "streamtv.db").is_file()
    assert (target / "data" / "channels_99.yaml").is_file()
    assert (target / "schedules" / "99.yml").is_file()
    assert (target / "cookies" / "youtube_cookies.txt").is_file()

    with (target / "config.yaml").open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    assert "ffmpeg_path" not in (cfg.get("ffmpeg") or {})
    assert "ffprobe_path" not in (cfg.get("ffmpeg") or {})
    assert "cache_directory" not in (cfg.get("cache") or {})
    cookies = cfg["youtube"]["cookies_file"]
    assert cookies.endswith("youtube_cookies.txt")
    assert Path(cookies).is_file()


def test_dry_run_does_not_write(tmp_path: Path) -> None:
    zpath = tmp_path / "good.zip"
    _make_backup_zip(zpath)
    target = tmp_path / "empty"
    target.mkdir()
    report = restore_from_zip(zpath, target_root=target, dry_run=True)
    assert report["status"] == "validated"
    assert not (target / "config.yaml").exists()


def test_stage_restore_pending(tmp_path: Path) -> None:
    zpath = tmp_path / "good.zip"
    _make_backup_zip(zpath)
    support = tmp_path / "Application Support" / "StreamTV"
    support.mkdir(parents=True)
    staged = stage_restore_pending(zpath, data_directory=support)
    assert Path(staged["marker"]).is_file()
    assert Path(staged["zip"]).is_file()
