"""Tests for portable backup snapshot creation."""

from __future__ import annotations

import json
import time
import zipfile
from pathlib import Path

import yaml

from streamtv.backup.paths import FORMAT_VERSION, LATEST_NAME
from streamtv.backup.scheduler import BackupScheduler
from streamtv.backup.snapshot import create_snapshot


def _seed_tree(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    cfg = {
        "server": {"host": "0.0.0.0", "port": 8410},
        "database": {"url": f"sqlite:///{(root / 'streamtv.db').as_posix()}"},
        "ffmpeg": {"ffmpeg_path": "/opt/homebrew/bin/ffmpeg"},
        "cache": {"cache_directory": "/tmp/streamtv-cache"},
        "backup": {"enabled": True, "retain_count": 2, "include_secrets": False},
    }
    (root / "config.yaml").write_text(yaml.safe_dump(cfg), encoding="utf-8")
    import sqlite3

    conn = sqlite3.connect(str(root / "streamtv.db"))
    conn.execute("CREATE TABLE channels (id INTEGER PRIMARY KEY, number TEXT)")
    conn.execute("INSERT INTO channels (number) VALUES ('80')")
    conn.commit()
    conn.close()
    data = root / "data"
    data.mkdir()
    (data / "channels_80.yaml").write_text("channels: []\n", encoding="utf-8")
    icons = data / "channel_icons"
    icons.mkdir()
    (icons / "channel_80.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    schedules = root / "schedules"
    schedules.mkdir()
    (schedules / "80.yml").write_text("items: []\n", encoding="utf-8")


def test_create_snapshot_members(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "install"
    _seed_tree(root)
    backup_dir = tmp_path / "backups"

    monkeypatch.setattr("streamtv.backup.snapshot.config_path", lambda: root / "config.yaml")
    monkeypatch.setattr("streamtv.backup.snapshot.sqlite_db_path", lambda: root / "streamtv.db")
    monkeypatch.setattr("streamtv.backup.snapshot.data_dir", lambda: root / "data")
    monkeypatch.setattr("streamtv.backup.snapshot.schedules_dir", lambda: root / "schedules")
    monkeypatch.setattr("streamtv.backup.snapshot.project_root", lambda: root)

    # Avoid touching global config.backup for retain/secrets — pass explicitly
    stamped = create_snapshot(
        backup_dir=backup_dir,
        include_secrets=False,
        retain_count=7,
    )
    assert stamped.is_file()
    latest = backup_dir / LATEST_NAME
    assert latest.is_file()

    with zipfile.ZipFile(latest, "r") as zf:
        names = set(zf.namelist())
        assert "manifest.json" in names
        assert "config.yaml" in names
        assert "streamtv.db" in names
        assert "data/channels_80.yaml" in names
        assert "data/channel_icons/channel_80.png" in names
        assert "schedules/80.yml" in names
        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["format_version"] == FORMAT_VERSION
        assert isinstance(manifest["members"], list)
        assert len(manifest["members"]) >= 4


def test_retain_count_rotation(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "install"
    _seed_tree(root)
    backup_dir = tmp_path / "backups"

    monkeypatch.setattr("streamtv.backup.snapshot.config_path", lambda: root / "config.yaml")
    monkeypatch.setattr("streamtv.backup.snapshot.sqlite_db_path", lambda: root / "streamtv.db")
    monkeypatch.setattr("streamtv.backup.snapshot.data_dir", lambda: root / "data")
    monkeypatch.setattr("streamtv.backup.snapshot.schedules_dir", lambda: root / "schedules")
    monkeypatch.setattr("streamtv.backup.snapshot.project_root", lambda: root)

    for _ in range(4):
        create_snapshot(backup_dir=backup_dir, include_secrets=False, retain_count=2)
        time.sleep(1.05)  # ensure distinct timestamps in filename second resolution

    stamped = sorted(backup_dir.glob("streamtv-backup-*.zip"))
    stamped = [p for p in stamped if p.name != LATEST_NAME]
    assert len(stamped) == 2
    assert (backup_dir / LATEST_NAME).is_file()


def test_debounce_coalesces() -> None:
    calls: list[str] = []
    sched = BackupScheduler(debounce_seconds=0.25, enabled=True)

    def _run(reason: str):
        calls.append(reason)
        return "/tmp/fake.zip"

    sched._run = _run  # type: ignore[method-assign]
    sched.schedule(reason="a")
    sched.schedule(reason="b")
    time.sleep(0.5)
    assert len(calls) == 1
