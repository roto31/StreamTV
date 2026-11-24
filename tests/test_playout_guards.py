"""Tests for playout reliability guards."""

from __future__ import annotations

from streamtv.validation.playout_guards import (
    validate_archive_stream_urls,
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
