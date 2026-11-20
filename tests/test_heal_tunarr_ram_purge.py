"""Unit tests for TunarrRAM purge classification (no live deletes)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "heal_tunarr_ram_purge.py"


def _load():
    spec = importlib.util.spec_from_file_location("heal_tunarr_ram_purge", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def purge():
    return _load()


def test_should_purge_at_45_pct(purge) -> None:
    assert purge.should_purge(45.0, 900 * 1024 * 1024, max_used_pct=45.0, min_free_mb=300)
    assert purge.should_purge(60.0, 900 * 1024 * 1024, max_used_pct=45.0, min_free_mb=300)
    assert not purge.should_purge(40.0, 900 * 1024 * 1024, max_used_pct=45.0, min_free_mb=300)


def test_should_purge_legacy_min_free(purge) -> None:
    # Low used% but free below floor still purges
    assert purge.should_purge(10.0, 100 * 1024 * 1024, max_used_pct=45.0, min_free_mb=300)
    assert not purge.should_purge(10.0, 400 * 1024 * 1024, max_used_pct=45.0, min_free_mb=300)


def test_should_purge_at_1_7_gib_hard_ceiling(purge) -> None:
    """2 GiB volume: used >= 1.7 GiB must purge even if % and free look OK."""
    total = 2 * purge.GIB
    used = int(1.7 * purge.GIB)
    free = total - used
    # used_pct ~85%, but set max_used_pct high so only GiB ceiling fires
    used_pct = 100.0 * used / total
    assert purge.should_purge(
        used_pct,
        free,
        max_used_pct=95.0,
        min_free_mb=100,
        total_bytes=total,
        max_used_gb=1.7,
    )
    # Just under ceiling
    used2 = int(1.69 * purge.GIB)
    free2 = total - used2
    used_pct2 = 100.0 * used2 / total
    assert not purge.should_purge(
        used_pct2,
        free2,
        max_used_pct=95.0,
        min_free_mb=100,
        total_bytes=total,
        max_used_gb=1.7,
    )


def test_expand_keep_with_parts(purge, tmp_path: Path) -> None:
    cache = tmp_path / "streamtv-cache"
    cache.mkdir()
    ready = cache / "abc123.mp4"
    part = cache / "abc123.mp4.part"
    other = cache / "other.mp4"
    ready.write_bytes(b"x")
    part.write_bytes(b"y")
    other.write_bytes(b"z")
    kept = purge.expand_keep_with_parts({ready.resolve()}, cache)
    assert ready.resolve() in kept
    assert part.resolve() in kept
    assert other.resolve() not in kept
