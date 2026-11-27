"""SSD cache healer must never trim Archive probe sidecars (Lesson 41c)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "heal_streamtv_ssd_cache.py"


@pytest.fixture(scope="module")
def heal() -> ModuleType:
    spec = importlib.util.spec_from_file_location("heal_streamtv_ssd_cache", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_list_cache_files_excludes_probe_sidecars(heal: ModuleType, tmp_path: Path) -> None:
    sidecar = tmp_path / "archive_probe" / "tape-1" / "Tape 1.mp4.probe.json"
    media = tmp_path / "archive_org" / "tape-1.mp4"
    for path in (sidecar, media):
        path.parent.mkdir(parents=True)
        path.write_bytes(b"x")
    assert heal.list_cache_files(tmp_path) == [media]
