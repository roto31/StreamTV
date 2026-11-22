"""source_meta helpers and category pass-through (§5.9)."""

from __future__ import annotations

import json

import pytest

from streamtv.builder.source_meta import (
    compose_guide_description,
    iso_runtime_from_exact,
    parse_archive_length,
    round_duration_seconds,
)
from streamtv.importers.stream_metadata import build_stream_meta_data


def test_parse_length_seconds_and_clock() -> None:
    assert parse_archive_length("3398.45") == pytest.approx(3398.45)
    assert parse_archive_length("0:56:38.45") == pytest.approx(3398.45)
    assert parse_archive_length("56:38") == pytest.approx(3398.0)
    assert parse_archive_length(1810) == 1810.0
    assert parse_archive_length(None) is None


def test_round_and_iso() -> None:
    assert round_duration_seconds(27.4) == 27
    assert round_duration_seconds(27.5) == 28
    assert iso_runtime_from_exact(1653) == "PT27M33S"
    assert iso_runtime_from_exact(0.4) == "PT1S"


def test_compose_description_exact_vs_placeholder() -> None:
    exact = compose_guide_description(
        air_date="1989-02-10",
        air_date_quality="exact",
        network="CBS",
        source_description="A special.",
        commercials_label="yes",
    )
    assert exact.startswith("Original air date: February 10, 1989.")
    assert "CBS." in exact
    assert "Commercials: yes." in exact

    placeholder = compose_guide_description(
        air_date="1993-12-15",
        air_date_quality="month",
        network="CBS",
        source_description="",
        commercials_label="yes",
    )
    assert placeholder.startswith(
        "Air date: about December 1993 (exact day not listed)."
    )


def test_categories_pass_through_and_unchanged_without() -> None:
    base = {
        "type": "event",
        "title": "Show",
        "broadcast_date": "1984-12-25",
        "network": "CBS",
    }
    without = build_stream_meta_data(base, channel_name="Ch")
    with_cats = build_stream_meta_data(
        {**base, "categories": ["Holiday", "Special", "Children"]},
        channel_name="Ch",
    )
    assert without is not None
    meta0 = json.loads(without)
    assert "categories" not in meta0
    meta1 = json.loads(with_cats or "{}")
    assert meta1.get("categories") == ["Holiday", "Special", "Children"]
    for key in ("broadcast_date", "network", "episode_title"):
        assert meta0.get(key) == meta1.get(key)
