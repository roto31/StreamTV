"""YouTube FFmpeg path behavior tests — remediation 2026-07.

Asserts the YouTube-scoped fixes (RC-1..RC-4, dual-input DASH) hold and that
banned flags can never reach a YouTube command. Mocking mirrors
tests/test_ffmpeg_command_golden.py.
"""
from unittest.mock import MagicMock

import pytest


def _streamer():
    from streamtv.streaming.mpegts_streamer import MPEGTSStreamer

    streamer = MPEGTSStreamer.__new__(MPEGTSStreamer)  # skip __init__/db
    streamer._ffmpeg_path = "ffmpeg"
    streamer._ffmpeg_profile = None
    streamer._channel_profile = None
    streamer._watermark = None
    sm = MagicMock()
    sm.archive_org_adapter.ffmpeg_cookie_header.return_value = ""
    sm.youtube_adapter.ffmpeg_cookie_header.return_value = ""
    streamer._stream_manager = sm
    return streamer


def _youtube_source():
    from streamtv.streaming.stream_manager import StreamSource
    return StreamSource.YOUTUBE


YT_URL = "https://rr3---sn-example.googlevideo.com/videoplayback?x=1"

COPY_INFO = {
    "video_codec": "h264",
    "audio_codec": "aac",
    "can_copy_video": True,
    "can_copy_audio": True,
}


def _build(codec_info, url=YT_URL, source=None):
    streamer = _streamer()
    return streamer._build_ffmpeg_command(
        url, codec_info, source=source or _youtube_source()
    )


def test_hls_probe_skips_annexb_filter():
    cmd = _build({**COPY_INFO, "container": "hls", "needs_annexb": False})
    joined = " ".join(cmd)
    assert "-bsf:v" in cmd and "dump_extra" in joined
    assert "h264_mp4toannexb" not in joined


def test_mp4_probe_applies_annexb_filter():
    cmd = _build({**COPY_INFO, "container": "mp4", "needs_annexb": True})
    assert "h264_mp4toannexb" in " ".join(cmd)


def test_youtube_flags_hygiene():
    cmd = " ".join(_build({**COPY_INFO, "container": "mp4", "needs_annexb": True}))
    assert "+igndts" in cmd
    for banned in ("fastseek", "low_delay", "reconnect_at_eof", "muxrate"):
        assert banned not in cmd, f"banned flag present: {banned}"


def test_db_stream_source_enum_uses_youtube_path():
    """database.models.StreamSource must not fall through to legacy FFmpeg flags."""
    from streamtv.database.models import StreamSource as DBSource

    cmd = _build(
        {**COPY_INFO, "container": "mp4", "needs_annexb": True},
        source=DBSource.YOUTUBE,
    )
    assert "-re" in cmd
    assert "reconnect_at_eof" not in cmd
    assert "muxrate" not in " ".join(cmd)
    assert "+igndts" in " ".join(cmd)


def test_direct_vod_input_is_real_time_paced():
    cmd = _build({**COPY_INFO, "container": "mp4", "needs_annexb": True})
    input_position = cmd.index("-i")
    assert "-re" in cmd[:input_position]


def test_youtube_vod_hls_is_real_time_paced():
    """VOD HLS must use -re; without it FFmpeg dumps the item in seconds."""
    cmd = _build(
        {**COPY_INFO, "container": "hls", "needs_annexb": False},
        url="https://manifest.googlevideo.com/api/manifest/hls_playlist/x.m3u8",
    )
    assert "-re" in cmd


def test_youtube_live_hls_is_not_artificially_paced():
    cmd = _build(
        {**COPY_INFO, "container": "hls", "needs_annexb": False},
        url="https://example.com/live/master.m3u8",
    )
    assert "-re" not in cmd


def test_missing_probe_defaults_to_annexb():
    # needs_annexb absent -> defaults True -> behaves like the MP4 case
    cmd = _build(dict(COPY_INFO))
    assert "h264_mp4toannexb" in " ".join(cmd)


def test_tuple_input_dual_ffmpeg():
    video = "https://rr3---sn-example.googlevideo.com/videoplayback?v=1"
    audio = "https://rr3---sn-example.googlevideo.com/videoplayback?a=1"
    cmd = _build(
        {**COPY_INFO, "container": "mp4", "needs_annexb": True},
        url=(video, audio),
    )
    assert video in cmd and audio in cmd
    i_positions = [i for i, tok in enumerate(cmd) if tok == "-i"]
    assert len(i_positions) == 2
    assert cmd[i_positions[0] + 1] == video
    assert cmd[i_positions[1] + 1] == audio
    assert cmd.count("-re") == 2
    joined = " ".join(cmd)
    assert "-map 0:v:0 -map 1:a:0" in joined


def test_tuple_input_non_youtube_raises():
    from streamtv.streaming.stream_manager import StreamSource

    streamer = _streamer()
    with pytest.raises(ValueError):
        streamer._build_ffmpeg_command(
            ("https://v.example/v", "https://a.example/a"),
            dict(COPY_INFO),
            source=StreamSource.ARCHIVE_ORG,
        )


@pytest.mark.asyncio
async def test_force_refresh_bypasses_signed_url_cache():
    from streamtv.streaming.youtube_adapter import YouTubeAdapter

    adapter = YouTubeAdapter(request_delay=0)
    video_id = "abcdefghijk"
    source_url = f"https://www.youtube.com/watch?v={video_id}"
    stale_url = "https://rr3---sn-example.googlevideo.com/videoplayback?stale=1"
    fresh_url = "https://rr3---sn-example.googlevideo.com/videoplayback?fresh=1"
    adapter._cached_url_set(video_id, stale_url)
    adapter._get_stream_url_sync = MagicMock(return_value=fresh_url)

    try:
        result = await adapter.get_stream_url(
            source_url,
            tune_priority=True,
            force_refresh=True,
        )
    finally:
        adapter._executor.shutdown(wait=False)
        adapter._tune_executor.shutdown(wait=False)

    assert result == fresh_url
    adapter._get_stream_url_sync.assert_called_once()


def test_youtube_expiry_reresolve_budget_scales_with_duration():
    from streamtv.streaming.mpegts_streamer import youtube_expiry_reresolve_budget

    assert youtube_expiry_reresolve_budget(None) == 4
    assert youtube_expiry_reresolve_budget(300) == 4  # short VOD floor
    assert youtube_expiry_reresolve_budget(8220) == 34


def test_youtube_resume_seek_before_input():
    """403 mid-stream refresh must resume with -ss, not restart from t=0."""
    streamer = _streamer()
    cmd = streamer._build_ffmpeg_command(
        YT_URL,
        {**COPY_INFO, "container": "mp4", "needs_annexb": True},
        source=_youtube_source(),
        youtube_resume_seek_seconds=45.5,
    )
    ss_idx = cmd.index("-ss")
    i_idx = cmd.index("-i")
    assert ss_idx < i_idx
    assert cmd[ss_idx + 1] == "45.500"


def test_youtube_resume_seek_on_dual_input():
    video = "https://rr3---sn-example.googlevideo.com/videoplayback?v=1"
    audio = "https://rr3---sn-example.googlevideo.com/videoplayback?a=1"
    streamer = _streamer()
    cmd = streamer._build_ffmpeg_command(
        (video, audio),
        {**COPY_INFO, "container": "mp4", "needs_annexb": True},
        source=_youtube_source(),
        youtube_resume_seek_seconds=30.0,
    )
    i_positions = [i for i, tok in enumerate(cmd) if tok == "-i"]
    ss_positions = [i for i, tok in enumerate(cmd) if tok == "-ss"]
    assert len(ss_positions) == 2
    assert ss_positions[0] < i_positions[0]
    assert ss_positions[1] < i_positions[1]


@pytest.mark.asyncio
async def test_youtube_near_complete_403_does_not_restart():
    import asyncio
    import time
    from unittest.mock import AsyncMock, MagicMock

    from streamtv.database.models import StreamSource
    from streamtv.streaming.mpegts_streamer import (
        MPEGTSStreamer,
        StreamURLExpiredError,
    )

    streamer = MPEGTSStreamer.__new__(MPEGTSStreamer)
    media_item = MagicMock()
    media_item.source = StreamSource.YOUTUBE
    media_item.duration = 200
    media_item.title = "Rodney Crowell - I Couldn't Leave You If I Tried"
    media_item.url = "https://www.youtube.com/watch?v=testvid01"

    async def expire_only(url, codec_info, source=None, **kwargs):
        raise StreamURLExpiredError("expired")
        yield b""  # pragma: no cover

    streamer._transcode_to_mpegts = expire_only
    stream_manager = MagicMock()
    stream_manager.get_stream_url = AsyncMock()

    original_monotonic = time.monotonic
    base = original_monotonic()
    call_n = [0]

    def fake_monotonic():
        call_n[0] += 1
        if call_n[0] == 1:
            return base
        return base + 170.0

    time.monotonic = fake_monotonic
    chunks = []
    try:
        async for chunk in streamer._transcode_with_youtube_expiry_retries(
            "https://stale.example/v",
            None,
            item_source=None,
            media_item=media_item,
            stream_manager=stream_manager,
            channel_name="1991",
            tune_priority=True,
        ):
            chunks.append(chunk)
    finally:
        time.monotonic = original_monotonic

    assert chunks == []
    stream_manager.get_stream_url.assert_not_awaited()


@pytest.mark.asyncio
async def test_youtube_expiry_retry_loops_until_success():
    from unittest.mock import AsyncMock, MagicMock

    from streamtv.database.models import StreamSource
    from streamtv.streaming.mpegts_streamer import (
        MPEGTSStreamer,
        StreamURLExpiredError,
    )

    streamer = MPEGTSStreamer.__new__(MPEGTSStreamer)
    media_item = MagicMock()
    media_item.source = StreamSource.YOUTUBE
    media_item.duration = 600
    media_item.title = "Short test clip"
    media_item.url = "https://www.youtube.com/watch?v=testvid01"

    calls = {"n": 0}

    async def fake_transcode(url, codec_info, source=None, **kwargs):
        calls["n"] += 1
        if calls["n"] < 3:
            raise StreamURLExpiredError("expired")
        yield b"chunk"

    streamer._transcode_to_mpegts = fake_transcode
    stream_manager = MagicMock()
    stream_manager.get_stream_url = AsyncMock(
        side_effect=[
            "https://fresh1.example/v",
            "https://fresh2.example/v",
        ]
    )

    chunks = []
    async for chunk in streamer._transcode_with_youtube_expiry_retries(
        "https://stale.example/v",
        None,
        item_source=None,
        media_item=media_item,
        stream_manager=stream_manager,
        channel_name="1988",
        tune_priority=True,
    ):
        chunks.append(chunk)

    assert chunks == [b"chunk"]
    assert calls["n"] == 3
    assert stream_manager.get_stream_url.await_count == 2
    for call in stream_manager.get_stream_url.await_args_list:
        assert call.kwargs.get("force_refresh") is True


def test_cached_youtube_local_path_uses_re_and_copy():
    """RAM-cache .mp4 must pace with -re; H.264/AAC should stream-copy."""
    streamer = _streamer()
    codec_info = {
        "video_codec": "h264",
        "audio_codec": "aac",
        "container_format": "mp4",
        "container": "mp4",
        "can_copy_video": True,
        "can_copy_audio": True,
        "needs_annexb_filter": True,
        "needs_annexb": True,
    }
    local = "/Volumes/TunarrRAM/streamtv-cache/youtube/sgJXbIP83A8.mp4"
    cmd = streamer._build_ffmpeg_command(
        local, codec_info, source=_youtube_source()
    )
    assert "-re" in cmd
    assert "-c:v" in cmd
    assert "copy" in cmd[cmd.index("-c:v") + 1]
    assert "-c:a" in cmd
    assert "copy" in cmd[cmd.index("-c:a") + 1]
