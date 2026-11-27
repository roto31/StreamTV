"""Tests for playout reliability guards."""

from __future__ import annotations

from streamtv.builder.gates import check_unique_ids_in_streams
from streamtv.builder.ids import apply_existing_url_ids, normalize_stream_url
from streamtv.validation.playout_guards import (
    URL_COLLAPSE_USER_WARNING,
    choose_url_twin_winner,
    normalize_stream_url_for_dedupe,
    validate_archive_stream_urls,
    validate_duplicate_stream_urls,
    validate_schedule_program_diversity,
    validate_schedule_sequence,
)


def test_rejects_duplicate_all_keys() -> None:
    schedule = {
        "content": [{"key": "season1", "collection": "S1"}],
        "sequence": [
            {
                "key": "main",
                "items": [{"all": "season1"}, {"all": "season1"}],
            }
        ],
    }
    report = validate_schedule_sequence(schedule, channel_label="80")
    assert not report.ok
    assert any("repeats" in e for e in report.errors)


def test_rejects_ia_mp4_url() -> None:
    streams = [
        {
            "source": "archive_org",
            "url": "https://archive.org/download/foo/bar.ia.mp4",
            "title": "bad",
        }
    ]
    report = validate_archive_stream_urls(streams, channel_label="2000")
    assert not report.ok
    assert any(".ia.mp4" in e for e in report.errors)


def test_accepts_canonical_mp4_url() -> None:
    streams = [
        {
            "source": "archive_org",
            "url": "https://archive.org/download/foo/bar.mp4",
            "title": "good",
            "runtime": "PT30M",
        }
    ]
    report = validate_archive_stream_urls(streams)
    assert report.ok
    assert not report.warnings


def test_rejects_consecutive_same_program_key() -> None:
    """Issue 69: adjacent identical program keys flood the Plex guide."""
    schedule = {
        "content": [
            {"key": "game_a", "collection": "A"},
            {"key": "game_b", "collection": "B"},
            {"key": "brk_x", "collection": "Break"},
        ],
        "sequence": [
            {
                "key": "main",
                "items": [
                    {"all": "game_a", "custom_title": "Game A"},
                    {"all": "game_a", "custom_title": "Game A again"},
                    {"all": "game_b", "custom_title": "Game B"},
                    {"all": "brk_x", "custom_title": "Station Break (brk_x)"},
                ],
            }
        ],
    }
    report = validate_schedule_program_diversity(schedule, channel_label="1965")
    assert not report.ok
    assert any("consecutively" in e for e in report.errors)


def test_rejects_monopoly_fill_program_key() -> None:
    """Issue 69: looping a 1-item prog pool for overnight pads."""
    items = [{"all": "lonely_news", "custom_title": f"News {i}"} for i in range(12)]
    items.append({"all": "brk_x", "custom_title": "Station Break (brk_x)"})
    schedule = {
        "content": [
            {"key": "lonely_news", "collection": "N"},
            {"key": "brk_x", "collection": "Break"},
        ],
        "sequence": [{"key": "main", "items": items}],
    }
    report = validate_schedule_program_diversity(schedule, channel_label="1965")
    assert not report.ok
    assert any("overuses" in e for e in report.errors)


def test_allows_diverse_daypart_reuse() -> None:
    """Daypart loops may reuse keys across the cycle if not adjacent/monopoly."""
    keys = [f"g{i}" for i in range(10)]
    content = [{"key": k, "collection": k} for k in keys]
    content.append({"key": "brk_x", "collection": "Break"})
    # Two days of rotating games (reuse ok) with breaks between
    items = []
    for day in range(3):
        for k in keys:
            items.append({"all": k, "custom_title": k})
            items.append({"all": "brk_x", "custom_title": "Station Break (brk_x)"})
    schedule = {
        "content": content,
        "sequence": [{"key": "loop", "items": items}],
    }
    report = validate_schedule_program_diversity(schedule, channel_label="1965")
    assert report.ok, report.errors


def test_warns_archive_stream_missing_runtime() -> None:
    streams = [
        {
            "source": "archive_org",
            "url": "https://archive.org/download/foo/bar.mp4",
            "title": "no-runtime",
        }
    ]
    report = validate_archive_stream_urls(streams)
    assert report.ok
    assert any("missing runtime" in w for w in report.warnings)


def test_duplicate_stream_urls_hard_error() -> None:
    url = "https://www.youtube.com/watch?v=abcdefghijk"
    streams = [
        {"id": "bare", "url": url, "title": "Library"},
        {"id": "bare__mn-block", "url": url, "title": "Block"},
    ]
    report = validate_duplicate_stream_urls(streams, channel_label="1998")
    assert not report.ok
    assert any("bare" in e and "bare__mn-block" in e for e in report.errors)
    assert any("collapses" in e for e in report.errors)


def test_distinct_stream_urls_ok() -> None:
    streams = [
        {"id": "a", "url": "https://www.youtube.com/watch?v=aaaaaaaaaaa"},
        {"id": "b", "url": "https://www.youtube.com/watch?v=bbbbbbbbbbb"},
    ]
    report = validate_duplicate_stream_urls(streams, channel_label="80")
    assert report.ok


def test_url_normalization_detects_equivalent_dupes() -> None:
    streams = [
        {
            "id": "one",
            "url": "https://archive.org/download/foo/Bar%20Baz.mp4",
            "title": "A",
        },
        {
            "id": "two",
            "url": "https://archive.org/download/foo/Bar Baz.mp4",
            "title": "B longer title here",
        },
    ]
    assert normalize_stream_url_for_dedupe(streams[0]["url"]) == normalize_stream_url(
        streams[1]["url"]
    )
    report = validate_duplicate_stream_urls(streams, channel_label="123")
    assert not report.ok


def test_choose_url_twin_prefers_block_id_and_richer_title() -> None:
    url = "https://www.youtube.com/watch?v=abcdefghijk"
    twins = [
        {"id": "abcdefghijk", "url": url, "title": "News"},
        {
            "id": "abcdefghijk__mn-1998-block",
            "url": url,
            "title": "News block",
        },
    ]
    winner = choose_url_twin_winner(twins)
    assert winner["id"] == "abcdefghijk__mn-1998-block"

    archive_twins = [
        {
            "id": "sesame_e0002",
            "url": "https://archive.org/download/x/a.mp4",
            "title": "Episode 2",
            "broadcast_date": "2009",
        },
        {
            "id": "sesame_e4188",
            "url": "https://archive.org/download/x/a.mp4",
            "title": "Sesame Street Episode 4188 (November 11, 2009)",
        },
    ]
    assert choose_url_twin_winner(archive_twins)["id"] == "sesame_e4188"


def test_builder_g2_fails_on_duplicate_urls() -> None:
    url = "https://www.youtube.com/watch?v=abcdefghijk"
    result = check_unique_ids_in_streams(
        [
            {"id": "a", "url": url},
            {"id": "b", "url": url},
        ]
    )
    assert not result.ok
    assert "duplicate stream URLs" in result.message
    assert URL_COLLAPSE_USER_WARNING in result.repair


def test_intra_draft_url_collapse(tmp_path) -> None:
    url = "https://www.youtube.com/watch?v=abcdefghijk"
    candidates = [
        {"id": "a", "url": url, "title": "Lib"},
        {"id": "a__mn-block", "url": url, "title": "Block"},
    ]
    out, log = apply_existing_url_ids(candidates, tmp_path)
    assert len(out) == 1
    assert out[0]["id"] == "a__mn-block"
    assert any(e.get("reason") == "intra_draft_url_dedupe" for e in log)
