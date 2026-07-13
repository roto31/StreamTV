"""Golden-file tests: non-YouTube FFmpeg commands must never change.

These snapshots were captured before the YouTube-path remediation of 2026-07.
If this test fails, a change has leaked outside the src_youtube gate. That is
a bug in the change, not in this test. Do not regenerate snapshots to make a
failure go away without explicit human sign-off.
"""
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

SNAPSHOT_DIR = Path(__file__).parent / "golden"
SNAPSHOT_DIR.mkdir(exist_ok=True)

# Snapshots were captured with operator ffmpeg settings (threads + extra_flags).
# CI has no gitignored config.yaml — pin these so golden tests are deterministic.
_GOLDEN_FFMPEG_THREADS = 2
_GOLDEN_FFMPEG_EXTRA_FLAGS = "-maxrate 3000k -bufsize 6000k -b:v 3000k"

CASES = {
    "archive_org_copy": {
        "url": "https://archive.org/download/test-item/test.mp4",
        "codec_info": {"video_codec": "h264", "audio_codec": "aac",
                       "can_copy_video": True, "can_copy_audio": True},
        "source": "ARCHIVE_ORG",
    },
    "archive_org_mpeg4": {
        "url": "https://archive.org/download/test-item/test.avi",
        "codec_info": {"video_codec": "mpeg4", "audio_codec": "mp3",
                       "can_copy_video": False, "can_copy_audio": True},
        "source": "ARCHIVE_ORG",
    },
    "pbs_drm_hls": {
        "url": "https://lls.pbs.org/live/stream.m3u8",
        "codec_info": {"video_codec": "h264", "audio_codec": "aac",
                       "can_copy_video": True, "can_copy_audio": True},
        "source": "PBS",
    },
    "plex_copy": {
        "url": "http://192.0.2.1:32400/library/metadata/1/file.mp4",
        "codec_info": {"video_codec": "h264", "audio_codec": "aac",
                       "can_copy_video": True, "can_copy_audio": True},
        "source": "PLEX",
    },
}


def _build(case) -> list[str]:
    from streamtv.config import config
    from streamtv.streaming.mpegts_streamer import MPEGTSStreamer
    from streamtv.streaming.stream_manager import StreamSource

    config.ffmpeg.threads = _GOLDEN_FFMPEG_THREADS
    config.ffmpeg.extra_flags = _GOLDEN_FFMPEG_EXTRA_FLAGS

    streamer = MPEGTSStreamer.__new__(MPEGTSStreamer)  # skip __init__/db
    streamer._ffmpeg_path = "ffmpeg"
    streamer._ffmpeg_profile = None
    streamer._channel_profile = None
    streamer._watermark = None
    # Deterministic stream manager stub: cookie headers must be empty strings,
    # never MagicMock reprs (they would leak into the command snapshot).
    sm = MagicMock()
    sm.archive_org_adapter.ffmpeg_cookie_header.return_value = ""
    sm.youtube_adapter.ffmpeg_cookie_header.return_value = ""
    streamer._stream_manager = sm
    return streamer._build_ffmpeg_command(
        case["url"], case["codec_info"],
        source=getattr(StreamSource, case["source"]),
    )


@pytest.mark.parametrize("name,case", CASES.items())
def test_non_youtube_command_is_frozen(name, case):
    cmd = _build(case)
    snap = SNAPSHOT_DIR / f"{name}.json"
    if not snap.exists():
        snap.write_text(json.dumps(cmd, indent=1))
        pytest.skip(f"snapshot created: {snap.name} — commit it")
    assert cmd == json.loads(snap.read_text()), (
        f"NON-YOUTUBE FFMPEG COMMAND DRIFTED for {name}. "
        "A change leaked outside the src_youtube gate."
    )
