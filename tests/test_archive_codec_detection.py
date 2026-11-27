"""Archive.org codec detection regression tests."""

import json
import time
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from streamtv.streaming import mpegts_streamer
from streamtv.streaming.mpegts_streamer import MPEGTSStreamer
from streamtv.utils import archive_probe_cache


ARCHIVE_MP4 = "https://archive.org/download/test-item/video.mp4"
CDN_MP4 = "https://dn800205.us.archive.org/0/items/test-item/video.mp4"
H264_INFO = {
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


@pytest.fixture(autouse=True)
def _isolated_probe_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "probe_cache"
    monkeypatch.setattr(
        archive_probe_cache,
        "sidecar_path",
        lambda identifier, filename: root / identifier / f"{filename}.probe.json",
    )
    return root


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


@pytest.mark.asyncio
async def test_probe_success_writes_sidecar_and_next_tune_skips_ffprobe() -> None:
    streamer = _streamer()
    streamer._quick_ffprobe_codec = AsyncMock(return_value=dict(H264_INFO))
    await streamer._detect_input_codec(ARCHIVE_MP4)
    assert archive_probe_cache.load(CDN_MP4)["video_codec"] == "h264"

    second = _streamer()
    second._quick_ffprobe_codec = AsyncMock(return_value=None)
    codec_info = await second._detect_input_codec(CDN_MP4)

    assert codec_info["can_copy_video"] is True
    assert second._quick_ffprobe_codec.await_count == 0


@pytest.mark.asyncio
async def test_inferred_fallback_never_written_to_sidecar() -> None:
    streamer = _streamer()
    streamer._quick_ffprobe_codec = AsyncMock(return_value=None)
    streamer._archive_org_ring_part_path = lambda _url: None  # type: ignore[method-assign]

    codec_info = await streamer._detect_input_codec(ARCHIVE_MP4)

    assert codec_info["probe_inferred"] is True
    assert archive_probe_cache.load(ARCHIVE_MP4) is None


def test_expired_sidecar_ignored(_isolated_probe_cache: Path) -> None:
    assert archive_probe_cache.save(ARCHIVE_MP4, dict(H264_INFO))
    path = _isolated_probe_cache / "test-item" / "video.mp4.probe.json"
    payload = json.loads(path.read_text())
    payload["probed_at"] = time.time() - archive_probe_cache.PROBE_CACHE_TTL_SEC - 1
    path.write_text(json.dumps(payload))
    assert archive_probe_cache.load(ARCHIVE_MP4) is None


def test_first_chunk_budget_archive_vs_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STREAMTV_ARCHIVE_FIRST_CHUNK_SEC", raising=False)
    extended = mpegts_streamer.FIRST_CHUNK_EXTENDED_SEC
    assert mpegts_streamer._first_chunk_timeout_sec(CDN_MP4) + extended == 60.0
    assert mpegts_streamer._first_chunk_timeout_sec("https://youtube.com/x") == 15.0
    assert mpegts_streamer._first_chunk_timeout_sec(("a", "b")) == 15.0
    monkeypatch.setenv("STREAMTV_ARCHIVE_FIRST_CHUNK_SEC", "5")
    assert mpegts_streamer._first_chunk_timeout_sec(CDN_MP4) + extended == 25.0
