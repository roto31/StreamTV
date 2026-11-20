"""Tests for TunarrRAM/cache volume readiness helpers."""

from __future__ import annotations

from pathlib import Path

from streamtv.utils.cache_startup import cache_volume_status, ensure_cache_dir


def test_cache_volume_status_local_writable(tmp_path: Path) -> None:
    cache = tmp_path / "streamtv-cache"
    cache.mkdir()
    ok, reason = cache_volume_status(str(cache))
    assert ok
    assert reason == "ok"


def test_cache_volume_status_missing_parent(tmp_path: Path) -> None:
    missing = tmp_path / "nope" / "streamtv-cache"
    ok, reason = cache_volume_status(str(missing))
    assert not ok
    assert "parent missing" in reason or "volume not mounted" in reason


def test_ensure_cache_dir_creates(tmp_path: Path) -> None:
    cache = tmp_path / "new-cache"
    path = ensure_cache_dir(str(cache))
    assert path.is_dir()
