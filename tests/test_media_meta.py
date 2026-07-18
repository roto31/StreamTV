"""Tests for media_meta conflict / merge helpers."""

from __future__ import annotations

from streamtv.utils.media_meta import (
    descriptions_conflict,
    has_enrichment,
    merge_enrichment,
    normalize_cast,
    parse_meta_data,
    prefer_longest_description,
)


def test_prefer_longest_description_keeps_longer_and_flags_conflict() -> None:
    primary = {
        "source": "tvdb",
        "description": (
            "Magnum and TC track a missing necklace across Oahu while "
            "Higgins objects to the guest list at the estate."
        ),
        "title": "A",
        "genres": ["Drama"],
    }
    secondary = {
        "source": "tvmaze",
        "description": (
            "A much longer and substantially different plot summary that "
            "describes entirely different events and characters in detail "
            "so that jaccard similarity stays low enough to flag."
        ),
        "genres": ["Action"],
    }
    out = prefer_longest_description(primary, secondary)
    assert out["description"] == secondary["description"]
    assert out["unverified"] is True
    assert out["conflicts"]
    assert "tvdb" in out["sources_consulted"]
    assert "tvmaze" in out["sources_consulted"]
    assert "Action" in out["genres"]


def test_descriptions_conflict_superset_not_conflict() -> None:
    short = "Magnum investigates a case."
    long = "Magnum investigates a case. He finds more clues later."
    assert descriptions_conflict(short, long) is False


def test_merge_enrichment_preserves_archive() -> None:
    raw = merge_enrichment(
        '{"identifier": "foo", "description": "arch"}',
        {"source": "tmdb", "description": "plot"},
    )
    meta = parse_meta_data(raw)
    assert meta["archive"]["identifier"] == "foo"
    assert meta["enrichment"]["source"] == "tmdb"
    assert has_enrichment(raw)


def test_normalize_cast() -> None:
    credits = {
        "cast": [{"name": "A"}, {"name": "B"}],
        "crew": [{"name": "D", "job": "Director"}, {"name": "W", "job": "Writer"}],
    }
    cast = normalize_cast(credits)
    roles = {(c["name"], c["role"]) for c in cast}
    assert ("A", "actor") in roles
    assert ("D", "director") in roles
