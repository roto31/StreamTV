"""Archive-only tune-in seek: offset math, FFmpeg isolation, golden safety."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

SNAPSHOT_DIR = Path(__file__).parent / "golden"

ARCHIVE_COPY = {
    "url": "https://archive.org/download/test-item/test.mp4",
    "codec_info": {
        "video_codec": "h264",
        "audio_codec": "aac",
        "can_copy_video": True,
        "can_copy_audio": True,
    },
    "source": "ARCHIVE_ORG",
}

YOUTUBE_COPY = {
    "url": "https://rr3---sn-example.googlevideo.com/videoplayback?x=1",
    "codec_info": {
        "video_codec": "h264",
        "audio_codec": "aac",
        "can_copy_video": True,
        "can_copy_audio": True,
    },
    "source": "YOUTUBE",
}


def _streamer():
    from streamtv.streaming.mpegts_streamer import MPEGTSStreamer

    streamer = MPEGTSStreamer.__new__(MPEGTSStreamer)
    streamer._ffmpeg_path = "ffmpeg"
    streamer._ffmpeg_profile = None
    streamer._channel_profile = None
    streamer._watermark = None
    sm = MagicMock()
    sm.archive_org_adapter.ffmpeg_cookie_header.return_value = ""
    sm.youtube_adapter.ffmpeg_cookie_header.return_value = ""
    streamer._stream_manager = sm
    return streamer


def _build(case: dict, *, archive_tune_seek_seconds: float = 0.0) -> list[str]:
    from streamtv.streaming.mpegts_streamer import MPEGTSStreamer
    from streamtv.streaming.stream_manager import StreamSource

    streamer = _streamer()
    return streamer._build_ffmpeg_command(
        case["url"],
        case["codec_info"],
        source=getattr(StreamSource, case["source"]),
        archive_tune_seek_seconds=archive_tune_seek_seconds,
    )


def test_compute_intra_item_tune_offset_basic() -> None:
    from streamtv.scheduling.playout_timeline import compute_intra_item_tune_offset

    position = {"cycle_position": 226.0, "current_item_start": 0.0}
    item = {"cached_duration": 3000}
    assert compute_intra_item_tune_offset(position, item) == 226.0


def test_compute_intra_item_tune_offset_clamps_to_duration() -> None:
    from streamtv.scheduling.playout_timeline import compute_intra_item_tune_offset

    position = {"cycle_position": 5000.0, "current_item_start": 0.0}
    item = {"cached_duration": 3000}
    assert compute_intra_item_tune_offset(position, item) == 2999.0


def test_compute_intra_item_tune_offset_below_min_returns_zero() -> None:
    from streamtv.scheduling.playout_timeline import compute_intra_item_tune_offset

    position = {"cycle_position": 3.0, "current_item_start": 0.0}
    item = {"cached_duration": 3000}
    assert compute_intra_item_tune_offset(position, item) == 0.0


def test_archive_offset_zero_matches_golden_snapshot() -> None:
    cmd = _build(ARCHIVE_COPY, archive_tune_seek_seconds=0.0)
    snap = SNAPSHOT_DIR / "archive_org_copy.json"
    assert snap.exists(), "golden snapshot missing"
    assert cmd == json.loads(snap.read_text())
    assert "-ss" not in cmd


def test_archive_offset_positive_inserts_ss_before_input() -> None:
    cmd = _build(ARCHIVE_COPY, archive_tune_seek_seconds=226.0)
    ss_index = cmd.index("-ss")
    i_index = cmd.index("-i")
    assert ss_index < i_index
    assert cmd[ss_index + 1] == "226.000"
    assert "+fastseek" not in " ".join(cmd)


def test_archive_offset_with_database_stream_source_enum() -> None:
    from streamtv.database.models import StreamSource as DbStreamSource

    streamer = _streamer()
    cmd = streamer._build_ffmpeg_command(
        ARCHIVE_COPY["url"],
        ARCHIVE_COPY["codec_info"],
        source=DbStreamSource.ARCHIVE_ORG,
        archive_tune_seek_seconds=120.0,
    )
    assert "-ss" in cmd
    assert cmd[cmd.index("-ss") + 1] == "120.000"


def test_youtube_never_receives_ss_even_when_offset_passed() -> None:
    cmd = _build(YOUTUBE_COPY, archive_tune_seek_seconds=226.0)
    assert "-ss" not in cmd


def test_plex_never_receives_ss_even_when_offset_passed() -> None:
    case = {
        "url": "http://<your-plex-host>:32400/library/metadata/1/file.mp4",
        "codec_info": ARCHIVE_COPY["codec_info"],
        "source": "PLEX",
    }
    cmd = _build(case, archive_tune_seek_seconds=120.0)
    assert "-ss" not in cmd


def test_pbs_never_receives_ss_even_when_offset_passed() -> None:
    case = {
        "url": "https://lls.pbs.org/live/stream.m3u8",
        "codec_info": ARCHIVE_COPY["codec_info"],
        "source": "PBS",
    }
    cmd = _build(case, archive_tune_seek_seconds=120.0)
    assert "-ss" not in cmd


def test_archive_tune_seek_enabled_defaults_false(monkeypatch: pytest.MonkeyPatch) -> None:
    from streamtv.config import config
    from streamtv.scheduling.playout_timeline import archive_tune_seek_enabled

    monkeypatch.delenv("STREAMTV_PLAYOUT_ARCHIVE_TUNE_SEEK", raising=False)
    monkeypatch.setattr(config.playout, "archive_tune_seek", False)
    assert archive_tune_seek_enabled() is False

    monkeypatch.setattr(config.playout, "archive_tune_seek", True)
    assert archive_tune_seek_enabled() is True


def test_archive_tune_seek_env_overrides_yaml(monkeypatch: pytest.MonkeyPatch) -> None:
    from streamtv.config import config
    from streamtv.scheduling.playout_timeline import archive_tune_seek_enabled

    monkeypatch.setattr(config.playout, "archive_tune_seek", False)
    monkeypatch.setenv("STREAMTV_PLAYOUT_ARCHIVE_TUNE_SEEK", "true")
    assert archive_tune_seek_enabled() is True

    monkeypatch.setenv("STREAMTV_PLAYOUT_ARCHIVE_TUNE_SEEK", "0")
    assert archive_tune_seek_enabled() is False
