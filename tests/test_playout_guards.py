"""Tests for playout reliability guards."""

from __future__ import annotations

from streamtv.validation.playout_guards import (
    validate_archive_stream_urls,
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
        }
    ]
    report = validate_archive_stream_urls(streams)
    assert report.ok
