"""Tests for Channel Builder resolver and compiler."""

from __future__ import annotations

import pytest

from streamtv.builder.compiler import compile_draft_to_unified
from streamtv.builder.models import BuilderDraft, ChannelInfo, LinkItem, LinkStatus, OrderingMode
from streamtv.builder.resolver import detect_url_kind, expand_url, resolve_single_url


def test_detect_archive_collection() -> None:
    kind = detect_url_kind("https://archive.org/details/JHiggens")
    assert kind == "archive_collection"


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


def test_expand_url_pbs_show(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "streamtv.builder.resolver.expand_pbs_show",
        lambda url: [
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

    items = expand_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert len(items) == 1
    assert items[0]["source"] == "youtube"
