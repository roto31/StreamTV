"""Opt-in Archive.org English DVD-subtitle burn-in (Plex Live TV overlay).

Default path must stay byte-identical to frozen Archive.org goldens.
Overlay only when the channel opts in, audio is not English, and a bitmap
English subtitle stream exists.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from tests.test_ffmpeg_command_golden import CASES, _build as _golden_build

ARCHIVE_URL = "https://archive.org/download/test-item/test.mp4"

JPN_WITH_ENG_DVD = {
    "video_codec": "h264",
    "audio_codec": "aac",
    "audio_language": "jpn",
    "can_copy_video": True,
    "can_copy_audio": True,
    "subtitle_streams": [
        {"codec": "dvd_subtitle", "language": "eng"},
    ],
}

ENG_WITH_ENG_DVD = {
    **JPN_WITH_ENG_DVD,
    "audio_language": "eng",
}

JPN_NO_SUBS = {
    "video_codec": "h264",
    "audio_codec": "aac",
    "audio_language": "jpn",
    "can_copy_video": True,
    "can_copy_audio": True,
    "subtitle_streams": [],
}


def _archive_source():
    from streamtv.streaming.stream_manager import StreamSource

    return StreamSource.ARCHIVE_ORG


def _youtube_source():
    from streamtv.streaming.stream_manager import StreamSource

    return StreamSource.YOUTUBE


def _streamer(*, burn: bool = False, lang: str = "eng"):
    from streamtv.streaming.mpegts_streamer import MPEGTSStreamer

    streamer = MPEGTSStreamer.__new__(MPEGTSStreamer)
    streamer._ffmpeg_path = "ffmpeg"
    streamer._ffmpeg_profile = None
    streamer._channel_profile = None
    streamer._watermark = None
    streamer._burn_embedded_subtitles = burn
    streamer._preferred_subtitle_language = lang
    sm = MagicMock()
    sm.archive_org_adapter.ffmpeg_cookie_header.return_value = ""
    sm.youtube_adapter.ffmpeg_cookie_header.return_value = ""
    streamer._stream_manager = sm
    return streamer


def _build(codec_info, *, burn: bool = False, source=None, lang: str = "eng"):
    streamer = _streamer(burn=burn, lang=lang)
    return streamer._build_ffmpeg_command(
        ARCHIVE_URL if source is None or getattr(source, "name", "") == "ARCHIVE_ORG"
        else "https://rr3---sn-example.googlevideo.com/videoplayback?x=1",
        codec_info,
        source=source or _archive_source(),
    )


def test_default_archive_copy_golden_unchanged() -> None:
    """Burn-in must not leak into the frozen Archive.org copy command."""
    cmd = _golden_build(CASES["archive_org_copy"])
    joined = " ".join(cmd)
    assert "overlay" not in joined
    assert "-filter_complex" not in cmd
    assert cmd[cmd.index("-c:v") + 1] == "copy"


def test_opt_out_with_jpn_and_subs_still_copies() -> None:
    cmd = _build(JPN_WITH_ENG_DVD, burn=False)
    joined = " ".join(cmd)
    assert "overlay" not in joined
    assert cmd[cmd.index("-c:v") + 1] == "copy"


def test_burnin_overlays_first_eng_dvd_sub_when_audio_is_jpn() -> None:
    cmd = _build(JPN_WITH_ENG_DVD, burn=True)
    joined = " ".join(cmd)
    assert "-filter_complex" in cmd
    fc = cmd[cmd.index("-filter_complex") + 1]
    assert "[0:s:0]" in fc
    assert "overlay" in fc
    assert "-map" in cmd
    assert "[vout]" in cmd
    assert "0:a:0" in cmd
    assert cmd[cmd.index("-c:v") + 1] != "copy"
    assert "libx264" in cmd
    for banned in ("fastseek", "low_delay", "reconnect_at_eof"):
        assert banned not in joined


def test_burnin_skips_when_audio_already_english() -> None:
    cmd = _build(ENG_WITH_ENG_DVD, burn=True)
    assert "overlay" not in " ".join(cmd)
    assert cmd[cmd.index("-c:v") + 1] == "copy"


def test_burnin_skips_when_no_subtitle_stream() -> None:
    cmd = _build(JPN_NO_SUBS, burn=True)
    assert "overlay" not in " ".join(cmd)
    assert cmd[cmd.index("-c:v") + 1] == "copy"


def test_burnin_skips_text_subtitles() -> None:
    info = {
        **JPN_NO_SUBS,
        "subtitle_streams": [{"codec": "mov_text", "language": "eng"}],
    }
    cmd = _build(info, burn=True)
    assert "overlay" not in " ".join(cmd)


def test_select_second_subtitle_stream_when_first_is_wrong_language() -> None:
    from streamtv.streaming.mpegts_streamer import select_embedded_dvd_subtitle_index

    info = {
        "audio_language": "jpn",
        "subtitle_streams": [
            {"codec": "dvd_subtitle", "language": "jpn"},
            {"codec": "dvd_subtitle", "language": "eng"},
        ],
    }
    assert (
        select_embedded_dvd_subtitle_index(
            info, burn_enabled=True, preferred_language="eng"
        )
        == 1
    )


def test_bind_channel_policy_none_disables_burn() -> None:
    from streamtv.database.models import ChannelSubtitleMode
    from streamtv.streaming.mpegts_streamer import bind_embedded_subtitle_policy

    streamer = _streamer(burn=True)
    channel = MagicMock()
    channel.subtitle_mode = ChannelSubtitleMode.NONE
    channel.preferred_subtitle_language_code = "en"
    bind_embedded_subtitle_policy(streamer, channel)
    assert streamer._burn_embedded_subtitles is False


def test_bind_channel_policy_default_enables_burn() -> None:
    from streamtv.database.models import ChannelSubtitleMode
    from streamtv.streaming.mpegts_streamer import bind_embedded_subtitle_policy

    streamer = _streamer(burn=False)
    channel = MagicMock()
    channel.subtitle_mode = ChannelSubtitleMode.DEFAULT
    channel.preferred_subtitle_language_code = "en"
    bind_embedded_subtitle_policy(streamer, channel)
    assert streamer._burn_embedded_subtitles is True
    assert streamer._preferred_subtitle_language == "en"


def test_parse_ffprobe_skips_attached_pic_mjpeg_cover() -> None:
    streamer = _streamer()
    info = streamer._parse_ffprobe_json(
        {
            "format": {"format_name": "mov,mp4,m4a,3gp,3g2,mj2"},
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "mjpeg",
                    "disposition": {"attached_pic": 1},
                },
                {"codec_type": "video", "codec_name": "h264"},
                {
                    "codec_type": "audio",
                    "codec_name": "aac",
                    "tags": {"language": "jpn"},
                },
                {
                    "codec_type": "subtitle",
                    "codec_name": "dvd_subtitle",
                    "tags": {"language": "eng"},
                },
            ],
        },
        "https://archive.org/download/BigGMovies/godzilla.mp4",
    )
    assert info is not None
    assert info["video_codec"] == "h264"
    assert info["can_copy_video"] is True
    assert info["audio_language"] == "jpn"


def test_parse_ffprobe_records_audio_lang_and_subs() -> None:
    streamer = _streamer()
    info = streamer._parse_ffprobe_json(
        {
            "format": {"format_name": "mov,mp4,m4a,3gp,3g2,mj2"},
            "streams": [
                {"codec_type": "video", "codec_name": "h264"},
                {
                    "codec_type": "audio",
                    "codec_name": "aac",
                    "tags": {"language": "jpn"},
                },
                {
                    "codec_type": "subtitle",
                    "codec_name": "dvd_subtitle",
                    "tags": {"language": "eng"},
                },
            ],
        },
        "https://archive.org/download/BigGMovies/godzilla.mp4",
    )
    assert info is not None
    assert info["audio_language"] == "jpn"
    assert info["subtitle_streams"] == [
        {"codec": "dvd_subtitle", "language": "eng"}
    ]
    assert info["can_copy_video"] is True


def test_burnin_does_not_alter_youtube_commands() -> None:
    cmd = _build(
        {
            **JPN_WITH_ENG_DVD,
            "container": "mp4",
            "needs_annexb": True,
        },
        burn=True,
        source=_youtube_source(),
    )
    joined = " ".join(cmd)
    assert "overlay" not in joined
    assert "-re" in cmd


def test_burnin_skips_profile_builder(monkeypatch: pytest.MonkeyPatch) -> None:
    marker = ["PROFILE_CMD"]

    def _profile_cmd(**kwargs):
        return marker

    monkeypatch.setattr(
        "streamtv.transcoding.ffmpeg_builder.build_ffmpeg_command",
        _profile_cmd,
    )
    streamer = _streamer(burn=True)
    streamer._ffmpeg_profile = MagicMock(name="Software")
    cmd = streamer._build_ffmpeg_command(
        ARCHIVE_URL, JPN_WITH_ENG_DVD, source=_archive_source()
    )
    assert cmd != marker
    assert "overlay" in " ".join(cmd)


def test_profile_builder_still_used_when_burn_not_applicable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker = ["PROFILE_CMD"]
    monkeypatch.setattr(
        "streamtv.transcoding.ffmpeg_builder.build_ffmpeg_command",
        lambda **kwargs: marker,
    )
    streamer = _streamer(burn=True)
    streamer._ffmpeg_profile = MagicMock(name="Software")
    cmd = streamer._build_ffmpeg_command(
        ARCHIVE_URL, ENG_WITH_ENG_DVD, source=_archive_source()
    )
    assert cmd == marker
