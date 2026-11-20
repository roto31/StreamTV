"""Tests for stream metadata resolution."""

from __future__ import annotations

from streamtv.importers.stream_metadata import (
    build_stream_meta_data,
    parse_slot,
    resolve_media_title,
    resolve_show_name,
)


def test_parse_slot() -> None:
    p = parse_slot("S01E03 - China Doll")
    assert p["season"] == 1
    assert p["episode"] == 3
    assert p["episode_title"] == "China Doll"


def test_resolve_title_from_slot() -> None:
    t = resolve_media_title(
        {"slot": "S01E03 - China Doll", "collection": "Magnum P.I. - Season 1"}
    )
    assert t == "S01E03 - China Doll"


def test_resolve_title_from_yaml_title() -> None:
    t = resolve_media_title(
        {
            "title": "Disney Animated Shorts - 1929x01 - The Barn Dance",
            "collection": "Disney Animated Shorts (MP4)",
        }
    )
    assert "Barn Dance" in t


def test_show_name_from_collection() -> None:
    show = resolve_show_name(
        {"collection": "Magnum P.I. - Season 1"},
        channel_name="Magnum P.I. Complete Series",
    )
    assert show == "Magnum P.I."


def test_meta_json_includes_season() -> None:
    meta = build_stream_meta_data(
        {"slot": "S02E05 - Test", "collection": "Show - Season 2"},
        channel_name="Show Complete",
    )
    assert meta is not None
    assert '"season": 2' in meta


def test_movie_meta_omits_series_fields() -> None:
    import json

    meta = build_stream_meta_data(
        {
            "type": "movie",
            "title": "Godzilla",
            "year": 1954,
            "slot": "S1954E01 - Godzilla",
            "collection": "Godzilla Movies",
        },
        channel_name="Godzilla Movies",
    )
    assert meta is not None
    data = json.loads(meta)
    assert "show_name" not in data
    assert "season" not in data
    assert "episode" not in data
    assert data.get("year") == 1954
    title = resolve_media_title(
        {
            "type": "movie",
            "title": "Godzilla",
            "slot": "S1954E01 - Godzilla",
            "collection": "Godzilla Movies",
        }
    )
    assert title == "Godzilla"
