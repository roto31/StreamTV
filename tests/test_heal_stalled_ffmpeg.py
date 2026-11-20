"""Unit tests for stalled-ffmpeg healer classification (no live SIGKILL)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "heal_stalled_ffmpeg.py"


def _load_mod():
    spec = importlib.util.spec_from_file_location("heal_stalled_ffmpeg", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def heal():
    return _load_mod()


def test_copy_path_archive_is_kill(heal) -> None:
    cmd = (
        "/opt/homebrew/bin/ffmpeg -i https://ia601007.us.archive.org/foo.mp4 "
        "-c copy -f mpegts pipe:1"
    )
    assert (
        heal.classify_candidate(cmd, min_etime_sec=300, max_pcpu=0.15, etime_sec=400, pcpu=0.0)
        == "kill"
    )


def test_filter_complex_overlay_skipped(heal) -> None:
    cmd = (
        "/opt/homebrew/bin/ffmpeg -i https://archive.org/download/BigGMovies/godzilla.mp4 "
        "-filter_complex [0:v][0:s]overlay -c:v libx264 -f mpegts pipe:1"
    )
    assert (
        heal.classify_candidate(cmd, min_etime_sec=300, max_pcpu=0.15, etime_sec=900, pcpu=0.0)
        == "skip_overlay"
    )


def test_subtitles_burn_skipped(heal) -> None:
    cmd = (
        "/opt/homebrew/bin/ffmpeg -i https://archive.org/x.mkv "
        "-vf subtitles=/tmp/en.srt -c:v libx264 -f mpegts pipe:1"
    )
    assert (
        heal.classify_candidate(cmd, min_etime_sec=300, max_pcpu=0.15, etime_sec=600, pcpu=0.05)
        == "skip_overlay"
    )


def test_short_etime_skip_criteria(heal) -> None:
    cmd = "/opt/homebrew/bin/ffmpeg -i https://archive.org/x.mp4 -c copy -f mpegts pipe:1"
    assert (
        heal.classify_candidate(cmd, min_etime_sec=300, max_pcpu=0.15, etime_sec=60, pcpu=0.0)
        == "skip_criteria"
    )


def test_is_overlay_helpers(heal) -> None:
    assert heal.is_overlay_or_burn_encode("ffmpeg -filter_complex overlay")
    assert not heal.is_overlay_or_burn_encode("ffmpeg -c copy archive.org")
