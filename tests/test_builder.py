"""Tests for Channel Builder resolver and compiler."""

from __future__ import annotations

import pytest

from streamtv.builder.compiler import compile_draft_to_unified
from streamtv.builder.models import BuilderDraft, ChannelInfo, LinkItem, LinkStatus, OrderingMode
from streamtv.builder.resolver import detect_url_kind, expand_url, resolve_single_url


def test_detect_archive_collection() -> None:
    kind = detect_url_kind("https://archive.org/details/JHiggens")
    assert kind == "archive_collection"


def test_archive_file_url_title_is_humanized(monkeypatch: pytest.MonkeyPatch) -> None:
    url = (
        "https://archive.org/download/winnie-the-pooh-christmas-too-flintstone-"
        "family-christmas-the-wish-that-changed-christmas-1993/"
        "Winnie%20The%20Pooh%20%26%20Christmas%20Too%2C%20Flintstone%20Family%"
        "20Christmas%2C%20The%20Wish%20That%20Changed%20Christmas%201993.mp4"
    )
    filename = (
        "Winnie The Pooh & Christmas Too, Flintstone Family Christmas, "
        "The Wish That Changed Christmas 1993.mp4"
    )

    def fake_meta(_identifier: str) -> dict:
        return {
            "metadata": {"date": "1993"},
            "files": [{"name": filename, "length": "5385.2"}],
        }

    monkeypatch.setattr(
        "streamtv.builder.resolver.fetch_archive_metadata", fake_meta
    )
    item = resolve_single_url(url)
    assert "%" not in item["title"]
    assert "Winnie The Pooh & Christmas Too" in item["title"]
    assert "Flintstone Family Christmas" in item["title"]
    assert item["duration"] == 5385
    assert item["upload_date"] == "1993"


def test_lookup_archive_file_duration_matches_basename() -> None:
    from streamtv.builder.resolver import lookup_archive_file_duration

    meta = {
        "files": [
            {"name": "path/WGGB ABC 40 Ernest Saves Xmas 12-11-1993.mp4", "length": "5581"},
            {"name": "other.mp4", "length": "100"},
        ]
    }
    dur = lookup_archive_file_duration(
        "wggb-abc-40-ernest-saves-xmas-12-11-1993",
        "WGGB%20ABC%2040%20Ernest%20Saves%20Xmas%2012-11-1993.mp4",
        metadata=meta,
    )
    assert dur == 5581


def test_compile_archive_draft_emits_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "streamtv.builder.compiler.enrich_archive_stream_runtimes",
        lambda streams: [],
    )
    draft = BuilderDraft(
        channel=ChannelInfo(number="2011", name="Xmas", primary_collection="Xmas"),
        ordering=OrderingMode.AS_ADDED,
        links=[
            LinkItem(
                url=(
                    "https://archive.org/download/example/"
                    "Winnie%20the%20Pooh.mp4"
                ),
                status=LinkStatus.OK,
                source="archive_org",
                stream_id="example_winnie",
                title="Winnie the Pooh",
                duration=1653,
            )
        ],
    )
    unified = compile_draft_to_unified(draft)
    assert unified["streams"][0]["runtime"] == "PT27M33S"
    assert unified["schedule"]["content"]
    assert unified["schedule"]["playout"]
    assert unified["schedule"]["media"]["mp4_only"] is True


def test_build_rejects_archive_streams_without_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import asyncio

    from streamtv.builder.compiler import build_channel_from_draft

    draft = BuilderDraft(
        channel=ChannelInfo(number="9998", name="Bad", primary_collection="Bad"),
        ordering=OrderingMode.AS_ADDED,
        links=[
            LinkItem(
                url="https://archive.org/download/x/file.mp4",
                status=LinkStatus.OK,
                source="archive_org",
                stream_id="x_file",
                title="File",
                duration=None,
            )
        ],
    )
    monkeypatch.setattr(
        "streamtv.builder.compiler.enrich_archive_stream_runtimes",
        lambda streams: ["File: Archive metadata has no file length"],
    )
    monkeypatch.setattr(
        "streamtv.builder.compiler.validate_unified_channel",
        lambda unified: type("R", (), {"ok": True, "errors": [], "warnings": []})(),
    )

    async def _run() -> None:
        with pytest.raises(ValueError, match="missing runtime"):
            await build_channel_from_draft(draft, db_session=object())

    asyncio.run(_run())


def test_detect_youtube_playlist() -> None:
    kind = detect_url_kind("https://www.youtube.com/playlist?list=PLtest123")
    assert kind == "youtube_playlist"


def test_compile_draft_minimal() -> None:
    draft = BuilderDraft(
        channel=ChannelInfo(number="9999", name="Test Channel", primary_collection="Test"),
        ordering=OrderingMode.AS_ADDED,
        links=[
            LinkItem(
                url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                status=LinkStatus.OK,
                source="youtube",
                stream_id="dQw4w9WgXcQ",
                title="Test Video",
                duration=212,
            )
        ],
    )
    unified = compile_draft_to_unified(draft)
    assert unified["channel"]["number"] == "9999"
    assert len(unified["streams"]) == 1
    assert unified["schedule"]["content"][0]["order"] == "chronological"


def test_detect_pbs_show() -> None:
    kind = detect_url_kind("https://www.pbs.org/show/nature/")
    assert kind == "pbs_show"


def test_pbs_show_html_harvest() -> None:
    from pathlib import Path

    from streamtv.builder.pbs_show import harvest_from_html, parse_show_slug

    html = (Path(__file__).parent / "fixtures" / "pbs_nature_show_snippet.html").read_text(
        encoding="utf-8"
    )
    assert parse_show_slug("https://www.pbs.org/show/nature/") == "nature"
    items = harvest_from_html(html, "https://www.pbs.org/show/nature/")
    assert len(items) >= 2
    assert any("nature-forest-ep1" in url for url in items)


def test_expand_pbs_show_without_network(monkeypatch: pytest.MonkeyPatch) -> None:
    from pathlib import Path

    from streamtv.builder import pbs_show

    html = (Path(__file__).parent / "fixtures" / "pbs_nature_show_snippet.html").read_text(
        encoding="utf-8"
    )

    class FakeResponse:
        text = html

        def raise_for_status(self) -> None:
            return None

    class FakeSession:
        def get(self, url: str, timeout: int = 60) -> FakeResponse:
            return FakeResponse()

    monkeypatch.setattr(pbs_show, "load_pbs_session", lambda: FakeSession())
    monkeypatch.setattr(pbs_show, "extract_season_ids", lambda _html: [])

    expanded = pbs_show.expand_pbs_show("https://www.pbs.org/show/nature/")
    assert len(expanded) >= 2
    assert all(item["source"] == "pbs" for item in expanded)


def test_channel_schema_allows_pbs_source() -> None:
    from streamtv.validation import YAMLValidator
    from pathlib import Path

    validator = YAMLValidator()
    sample = {
        "channels": [
            {
                "number": "9998",
                "name": "PBS Test",
                "streams": [
                    {
                        "id": "pbs_vid_1",
                        "collection": "Nature",
                        "type": "event",
                        "source": "pbs",
                        "url": "https://www.pbs.org/video/nature-ep1/",
                        "title": "Nature Ep 1",
                    }
                ],
            }
        ]
    }
    validator.validate_channel_data(sample)


def test_expand_url_pbs_show(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "streamtv.builder.resolver.expand_pbs_show",
        lambda url, **kwargs: [
            {
                "url": "https://www.pbs.org/video/nature-ep1/",
                "title": "Nature Ep 1",
                "source": "pbs",
                "stream_id": "nature_ep1",
            }
        ],
    )
    items = expand_url("https://www.pbs.org/show/nature/")
    assert len(items) == 1
    assert items[0]["source"] == "pbs"


def test_expand_url_youtube_single() -> None:
    items = expand_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert len(items) == 1
    assert items[0]["source"] == "youtube"


def test_pbs_episode_filter_skips_trailers() -> None:
    from streamtv.builder.pbs_episode_filter import filter_full_pbs_episodes, is_full_pbs_episode

    trailer = {"title": "Season 1 Trailer", "duration": 120, "source": "pbs"}
    episode = {"title": "Forest of the Lynx", "duration": 3200, "source": "pbs"}
    assert not is_full_pbs_episode(trailer)
    assert is_full_pbs_episode(episode)
    filtered = filter_full_pbs_episodes([trailer, episode])
    assert len(filtered) == 1
    assert filtered[0]["title"] == "Forest of the Lynx"


def test_compile_pbs_draft_defaults_epg_sync_class_c() -> None:
    draft = BuilderDraft(
        channel=ChannelInfo(number="2319", name="Nature", primary_collection="Nature"),
        links=[
            LinkItem(
                url="https://www.pbs.org/video/nature-ep1/",
                status=LinkStatus.OK,
                source="pbs",
                stream_id="nature_ep1",
                title="Nature Ep 1",
                expanded_from="https://www.pbs.org/show/nature/",
            )
        ],
    )
    unified = compile_draft_to_unified(draft)
    assert unified["channel"]["epg_sync_class"] == "C"


def test_expand_pbs_show_applies_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    from pathlib import Path

    from streamtv.builder import pbs_show

    html = (Path(__file__).parent / "fixtures" / "pbs_nature_show_snippet.html").read_text(
        encoding="utf-8"
    )

    class FakeResponse:
        text = html

        def raise_for_status(self) -> None:
            return None

    class FakeSession:
        def get(self, url: str, timeout: int = 60) -> FakeResponse:
            return FakeResponse()

    monkeypatch.setattr(pbs_show, "load_pbs_session", lambda: FakeSession())
    monkeypatch.setattr(pbs_show, "extract_season_ids", lambda _html: [])

    expanded = pbs_show.expand_pbs_show(
        "https://www.pbs.org/show/nature/",
        filter_full_episodes=True,
        min_episode_seconds=300,
    )
    assert expanded
    assert all(item.get("duration") is None or item["duration"] >= 300 for item in expanded)


def test_clean_channel_name_for_series() -> None:
    from streamtv.builder.enrichment import clean_channel_name_for_series

    assert (
        clean_channel_name_for_series("Saturday Night Live (Seasons 1–30)")
        == "Saturday Night Live"
    )
    assert clean_channel_name_for_series("Magnum P.I. Complete Series") == "Magnum P.I."


def test_detect_series_from_titles() -> None:
    from streamtv.builder.enrichment import detect_series_from_titles

    name, year = detect_series_from_titles(
        [
            "Saturday Night Live - S01E01 - George Carlin (1975)",
            "Saturday Night Live - S01E02 - Simon",
        ]
    )
    assert name == "Saturday Night Live"
    assert year == 1975


def test_resolve_enrichment_identity_explicit() -> None:
    from streamtv.builder.enrichment import resolve_enrichment_identity

    draft = BuilderDraft(
        channel=ChannelInfo(
            number="1975",
            name="SNL Marathon",
            enrichment_series_name="Saturday Night Live",
            enrichment_year=1975,
        ),
        links=[
            LinkItem(
                url="https://example.com/a",
                status=LinkStatus.OK,
                title="Wrong Show - S01E01",
            )
        ],
    )
    name, year, kind = resolve_enrichment_identity(draft)
    assert name == "Saturday Night Live"
    assert year == 1975
    assert kind == "series"


def test_resolve_enrichment_identity_auto_from_channel_name() -> None:
    from streamtv.builder.enrichment import resolve_enrichment_identity

    draft = BuilderDraft(
        channel=ChannelInfo(
            number="1975",
            name="Saturday Night Live (Seasons 1–30)",
        ),
        links=[],
    )
    name, year, kind = resolve_enrichment_identity(draft)
    assert name == "Saturday Night Live"
    assert kind == "series"


@pytest.mark.asyncio
async def test_enrich_built_draft_respects_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from streamtv.builder import enrichment as enrich_mod

    called = {"n": 0}

    async def _boom(*_a: object, **_k: object) -> dict:
        called["n"] += 1
        return {}

    monkeypatch.setattr(enrich_mod, "enrich_channel_media", _boom)
    draft = BuilderDraft(
        channel=ChannelInfo(
            number="1975",
            name="Saturday Night Live",
            enrich_metadata=False,
        )
    )
    summary = await enrich_mod.enrich_built_draft(draft)
    assert summary.get("skipped_enrichment") is True
    assert called["n"] == 0


@pytest.mark.asyncio
async def test_enrich_built_draft_calls_enricher(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from streamtv.builder import enrichment as enrich_mod

    seen: dict = {}

    async def _fake(
        channel_number: str,
        *,
        series_name: str,
        series_year: int | None = None,
        enrich_type: str = "series",
        series_provider: str | None = None,
        **_kwargs: object,
    ) -> dict:
        seen.update(
            {
                "channel_number": channel_number,
                "series_name": series_name,
                "series_year": series_year,
                "enrich_type": enrich_type,
                "series_provider": series_provider,
            }
        )
        return {
            "updated": 2,
            "failed": 0,
            "total": 2,
            "skipped": 0,
            "series_name": series_name,
        }

    monkeypatch.setattr(enrich_mod, "enrich_channel_media", _fake)
    draft = BuilderDraft(
        channel=ChannelInfo(
            number="1975",
            name="SNL",
            enrichment_series_name="Saturday Night Live",
            enrichment_year=1975,
            enrich_metadata=True,
            enrichment_series_provider="both",
        )
    )
    summary = await enrich_mod.enrich_built_draft(draft)
    assert seen["channel_number"] == "1975"
    assert seen["series_provider"] == "both"
    assert summary.get("series_provider") == "both"
    assert seen["series_name"] == "Saturday Night Live"
    assert seen["series_year"] == 1975
    assert summary["updated"] == 2
    assert summary.get("identity_source") == "explicit"
