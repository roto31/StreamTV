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
    streamer._archive_org_ring_part_path = lambda _url: None  # type: ignore[method-assign]

    codec_info = await streamer._detect_input_codec(ARCHIVE_MP4)

    assert codec_info["can_copy_video"] is False
    assert codec_info["can_copy_audio"] is False
    assert codec_info["probe_inferred"] is True
    # initial 5s + CDN 15s retry
    assert streamer._quick_ffprobe_codec.await_count == 2


@pytest.mark.asyncio
async def test_probe_retry_recovers_h264_copy() -> None:
    streamer = _streamer()
    h264 = {
        "video_codec": "h264",
        "audio_codec": "aac",
        "container_format": "mov,mp4,m4a,3gp,3g2,mj2",
        "container": "mov,mp4,m4a,3gp,3g2,mj2",
        "can_copy_video": True,
        "can_copy_audio": True,
        "needs_annexb_filter": True,
        "needs_annexb": True,
        "subtitle_streams": [],
    }
    streamer._quick_ffprobe_codec = AsyncMock(side_effect=[None, h264])
    streamer._archive_org_ring_part_path = lambda _url: None  # type: ignore[method-assign]

    codec_info = await streamer._detect_input_codec(ARCHIVE_MP4)

    assert codec_info["video_codec"] == "h264"
    assert codec_info["can_copy_video"] is True
    assert codec_info["can_copy_audio"] is True
    assert streamer._quick_ffprobe_codec.await_count == 2
    retry_kwargs = streamer._quick_ffprobe_codec.await_args_list[1].kwargs
    assert retry_kwargs.get("timeout") == 15.0


@pytest.mark.asyncio
async def test_ring_miss_still_retries_cdn(tmp_path, monkeypatch) -> None:
    streamer = _streamer()
    h264 = {
        "video_codec": "h264",
        "audio_codec": "aac",
        "container_format": "mp4",
        "container": "mp4",
        "can_copy_video": True,
        "can_copy_audio": True,
        "needs_annexb_filter": True,
        "needs_annexb": True,
        "subtitle_streams": [],
    }
    part = tmp_path / "video.mp4.part"
    part.write_bytes(b"x" * 2_000_000)
    streamer._quick_ffprobe_codec = AsyncMock(side_effect=[None, None, h264])
    streamer._archive_org_ring_part_path = lambda _url: part  # type: ignore[method-assign]

    codec_info = await streamer._detect_input_codec(ARCHIVE_MP4)

    assert codec_info["can_copy_video"] is True
    assert streamer._quick_ffprobe_codec.await_count == 3
    assert streamer._quick_ffprobe_codec.await_args_list[1].args[0] == str(part)
    assert streamer._quick_ffprobe_codec.await_args_list[2].args[0] == ARCHIVE_MP4


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
