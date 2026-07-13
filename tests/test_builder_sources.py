"""Tests for Channel Builder source registry."""

from __future__ import annotations

from pathlib import Path

import pytest

from streamtv.builder.sources import get_source, list_sources, reload_sources
from streamtv.builder.sources.community_loader import load_community_sources, parse_manifest
from streamtv.builder.sources.registry import detect_source_for_url

FIXTURES = Path(__file__).parent / "fixtures"


def test_builtin_sources_include_vimeo_coming_soon() -> None:
    reload_sources()
    vimeo = get_source("vimeo")
    assert vimeo is not None
    assert vimeo.status == "coming_soon"
    assert vimeo.playout_ready is False


def test_builtin_sources_playable() -> None:
    reload_sources()
    for source_id in ("archive_org", "youtube", "pbs", "plex"):
        spec = get_source(source_id)
        assert spec is not None
        assert spec.status == "active"
        assert spec.playout_ready is True


def test_list_sources_includes_builtins() -> None:
    specs = list_sources()
    ids = {spec.id for spec in specs}
    assert "youtube" in ids
    assert "vimeo" in ids


def test_parse_valid_community_manifest() -> None:
    raw = (FIXTURES / "builder_source_valid.yaml").read_text(encoding="utf-8")
    import yaml

    spec = parse_manifest(yaml.safe_load(raw))
    assert spec.id == "community:example_stream"
    assert spec.status == "community"
    assert spec.playout_ready is False
    assert "stream.example.com" in spec.hosts[0]


def test_invalid_community_manifest_raises() -> None:
    raw = (FIXTURES / "builder_source_invalid.yaml").read_text(encoding="utf-8")
    import yaml

    with pytest.raises(ValueError, match="missing id"):
        parse_manifest(yaml.safe_load(raw))


def test_load_community_sources_from_directory(tmp_path: Path) -> None:
    dest = tmp_path / "example.yaml"
    dest.write_text((FIXTURES / "builder_source_valid.yaml").read_text(encoding="utf-8"))
    specs = load_community_sources(tmp_path)
    assert len(specs) == 1
    assert specs[0].label == "Example Stream Site"


def test_detect_source_for_url_youtube() -> None:
    reload_sources()
    spec = detect_source_for_url("https://www.youtube.com/watch?v=abc123")
    assert spec is not None
    assert spec.id == "youtube"


def test_detect_source_skips_coming_soon() -> None:
    reload_sources()
    spec = detect_source_for_url("https://vimeo.com/123456")
    assert spec is None
