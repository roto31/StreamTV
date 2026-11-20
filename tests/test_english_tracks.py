"""Tests for offline English-track classification (no live tune path)."""

from __future__ import annotations

from streamtv.utils.english_tracks import (
    ProbeResult,
    StreamTrack,
    classify_title,
    is_english_lang,
    looks_like_us_or_hardcoded_title,
    normalize_media_lang,
    parse_ffprobe_json,
)


def test_normalize_english_variants() -> None:
    assert normalize_media_lang("en") == "eng"
    assert normalize_media_lang("ENG") == "eng"
    assert normalize_media_lang("english") == "eng"
    assert is_english_lang("en-US")


def test_classify_english_audio_wins_over_bitmap() -> None:
    probe = ProbeResult(
        path_or_url="x",
        audio_tracks=[StreamTrack(0, "aac", "eng")],
        subtitle_tracks=[StreamTrack(1, "dvd_subtitle", "eng")],
    )
    assert classify_title(probe, title="Godzilla") == "has_english_audio"


def test_classify_dual_audio_english_second() -> None:
    probe = ProbeResult(
        path_or_url="x",
        audio_tracks=[
            StreamTrack(0, "aac", "jpn"),
            StreamTrack(1, "aac", "eng"),
        ],
        subtitle_tracks=[StreamTrack(2, "dvd_subtitle", "eng")],
    )
    assert classify_title(probe) == "dual_audio_needs_map"
    assert probe.has_english_audio is True


def test_classify_offline_burn_foreign_plus_bitmap() -> None:
    probe = ProbeResult(
        path_or_url="x",
        audio_tracks=[StreamTrack(0, "aac", "jpn")],
        subtitle_tracks=[StreamTrack(1, "dvd_subtitle", "eng")],
    )
    assert classify_title(probe, title="Godzilla") == "offline_burn"


def test_classify_skip_hardcoded_us_unlabeled() -> None:
    probe = ProbeResult(
        path_or_url="x",
        audio_tracks=[StreamTrack(0, "aac", "")],
        subtitle_tracks=[],
    )
    assert (
        classify_title(
            probe,
            title="Godzilla, King of the Monsters (US Version)",
            stream_id="BigGMovies/(1955a) Godzilla, King of the Monsters (US Vesion).mp4",
        )
        == "skip_hardcoded"
    )
    assert looks_like_us_or_hardcoded_title(
        "Godzilla, King of the Monsters (US Version)"
    )


def test_classify_unlabeled_with_bitmap_needs_review() -> None:
    probe = ProbeResult(
        path_or_url="x",
        audio_tracks=[StreamTrack(0, "aac", "und")],
        subtitle_tracks=[StreamTrack(1, "dvd_subtitle", "eng")],
    )
    assert classify_title(probe, title="Mystery Film") == "unlabeled_needs_review"


def test_classify_youtube_skipped() -> None:
    probe = ProbeResult(path_or_url="x")
    assert classify_title(probe, source="youtube") == "n/a_youtube"


def test_parse_ffprobe_json_all_audio_langs() -> None:
    data = {
        "streams": [
            {"index": 0, "codec_type": "video", "codec_name": "h264"},
            {
                "index": 1,
                "codec_type": "audio",
                "codec_name": "aac",
                "tags": {"language": "jpn"},
            },
            {
                "index": 2,
                "codec_type": "audio",
                "codec_name": "aac",
                "tags": {"language": "eng"},
            },
            {
                "index": 3,
                "codec_type": "subtitle",
                "codec_name": "dvd_subtitle",
                "tags": {"language": "eng"},
            },
        ]
    }
    probe = parse_ffprobe_json(data, "file.mp4")
    assert probe.has_english_audio is True
    assert probe.dual_audio_english_not_first is True
    assert probe.english_bitmap_index == 0
    assert probe.video_codec == "h264"
