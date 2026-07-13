"""Archive.org codec detection regression tests."""

from unittest.mock import AsyncMock

import pytest

from streamtv.streaming.mpegts_streamer import MPEGTSStreamer


ARCHIVE_MP4 = "https://archive.org/download/test-item/video.mp4"


def _streamer() -> MPEGTSStreamer:
    return MPEGTSStreamer.__new__(MPEGTSStreamer)


@pytest.mark.asyncio
async def test_mpeg4_probe_forces_video_transcode() -> None:
    streamer = _streamer()
    streamer._quick_ffprobe_codec = AsyncMock(
        return_value={
            "video_codec": "mpeg4",
            "audio_codec": "aac",
            "container_format": "mov,mp4,m4a,3gp,3g2,mj2",
            "container": "mov,mp4,m4a,3gp,3g2,mj2",
            "can_copy_video": False,
            "can_copy_audio": True,
            "needs_annexb_filter": False,
            "needs_annexb": True,
        }
    )

    codec_info = await streamer._detect_input_codec(ARCHIVE_MP4)

    assert codec_info["video_codec"] == "mpeg4"
    assert codec_info["can_copy_video"] is False


@pytest.mark.asyncio
async def test_probe_timeout_uses_safe_transcode_fallback() -> None:
    streamer = _streamer()
    streamer._quick_ffprobe_codec = AsyncMock(return_value=None)

    codec_info = await streamer._detect_input_codec(ARCHIVE_MP4)

    assert codec_info["can_copy_video"] is False
    assert codec_info["can_copy_audio"] is False
    assert codec_info["probe_inferred"] is True


@pytest.mark.asyncio
async def test_h264_probe_preserves_video_copy() -> None:
    streamer = _streamer()
    streamer._quick_ffprobe_codec = AsyncMock(
        return_value={
            "video_codec": "h264",
            "audio_codec": "aac",
            "container_format": "mov,mp4,m4a,3gp,3g2,mj2",
            "container": "mov,mp4,m4a,3gp,3g2,mj2",
            "can_copy_video": True,
            "can_copy_audio": True,
            "needs_annexb_filter": True,
            "needs_annexb": True,
        }
    )

    codec_info = await streamer._detect_input_codec(ARCHIVE_MP4)

    assert codec_info["video_codec"] == "h264"
    assert codec_info["can_copy_video"] is True
