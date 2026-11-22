"""Offline discovery query-builder tests (no network)."""

from __future__ import annotations

from streamtv.builder.discovery.archive import build_archive_queries, post_filter_docs
from streamtv.builder.discovery.youtube import build_youtube_queries


def test_archive_query_families_include_networks_and_stations() -> None:
    qs = build_archive_queries(
        {
            "theme": "christmas",
            "theme_terms": ["christmas", "xmas"],
            "networks": ["CBS", "ABC"],
            "stations_for_breaks": ["WCCO", "KSTP"],
            "era": {"from": 1980, "to": 1999},
        }
    )
    assert any("CBS" in q and "commercials" in q for q in qs)
    assert any("WCCO" in q and "KSTP" in q for q in qs)
    assert any("complete broadcast" in q for q in qs)
    assert len(qs) == len(set(qs))


def test_post_filter_drops_deny_and_dedupes() -> None:
    docs = [
        {"identifier": "a", "title": "CBS Christmas special with commercials"},
        {"identifier": "a", "title": "dup"},
        {"identifier": "b", "title": "ABC Family Christmas"},
        {"identifier": "c", "title": "Summer picnic"},
    ]
    out = post_filter_docs(docs)
    ids = [d["identifier"] for d in out]
    assert ids == ["a"]


def test_youtube_query_families() -> None:
    qs = build_youtube_queries(
        {
            "theme": "Christmas",
            "networks": ["CBS"],
            "stations_for_breaks": ["WCCO"],
            "known_titles": ["Rudolph"],
        }
    )
    assert any("Rudolph CBS commercials" == q for q in qs)
    assert any("WCCO" in q for q in qs)
