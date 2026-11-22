"""Phase 1 red regressions for Channel Creator MCP v2 (D1, D2, D4).

These assert the *fixed* behavior from CURSOR_PROMPT_CHANNEL_CREATOR_MCP_V2.md.
They must fail on current HEAD for the documented defect reasons.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import pytest

from streamtv.builder.compiler import compile_draft_to_unified
from streamtv.builder.models import (
    BuilderDraft,
    ChannelInfo,
    FillerAttachment,
    FillerCollection,
    FillerLink,
    LinkItem,
    LinkStatus,
    OrderingMode,
    PaddingMode,
)
from streamtv.builder.resolver import _slugify, resolve_single_url
from streamtv.builder.store import FillerStore


def _ok_yt(stream_id: str, title: str, **extra: Any) -> LinkItem:
    return LinkItem(
        url=f"https://www.youtube.com/watch?v={stream_id}",
        status=LinkStatus.OK,
        source="youtube",
        stream_id=stream_id,
        title=title,
        duration=1800,
        **extra,
    )


def test_d1_between_items_emits_per_program_all_breaks_not_int_duration(
    tmp_path: Any,
) -> None:
    """D1: BETWEEN_ITEMS must not emit int ``duration:`` or replay the whole collection.

    Fixed shape: one content collection per program and per break reel; sequence
    uses only ``all:`` items. Never emit ``duration:`` from Builder.
    """
    store = FillerStore(base_dir=tmp_path / "fillers")
    filler = FillerCollection(
        id="brk1",
        name="Station Breaks",
        links=[
            FillerLink(
                url="https://www.youtube.com/watch?v=break01",
                title="Break reel",
                clip_type="commercial",
                source="youtube",
                stream_id="break01",
                duration=120,
            )
        ],
    )
    store.save(filler)

    draft = BuilderDraft(
        channel=ChannelInfo(
            number="9001",
            name="D1 Probe",
            primary_collection="D1 Probe",
        ),
        ordering=OrderingMode.AS_ADDED,
        links=[_ok_yt(f"v{i}", f"Show {i}") for i in range(3)],
        filler_attachments=[
            FillerAttachment(
                filler_id=filler.id,
                padding_mode=PaddingMode.BETWEEN_ITEMS,
                break_duration_seconds=120,
            )
        ],
    )
    unified = compile_draft_to_unified(draft, filler_store=store)
    items = unified["schedule"]["sequence"][0]["items"]

    duration_items = [item for item in items if "duration" in item]
    assert duration_items == [], (
        "D1: Builder must never emit duration: items "
        f"(got {duration_items!r}; parse_duration(int) silently skips breaks)"
    )

    all_keys = [item.get("all") for item in items if "all" in item]
    assert len(all_keys) >= 5, (
        "D1: expect per-program all: plus per-break all: "
        f"(got {len(all_keys)} all: items: {all_keys!r})"
    )
    # Whole-collection replay: same primary key repeated once per program.
    primary_hits = [k for k in all_keys if k == "d1_probe"]
    assert len(primary_hits) <= 1, (
        "D1: must not append {all: primary} once per program "
        f"(replayed {len(primary_hits)} times)"
    )


def test_d2_archive_multi_file_stream_ids_are_unique(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D2: multiple files of one archive.org item must not share a truncated id."""
    identifier = "winniethepoohandchristmastoo_201912"
    filenames = [
        "Winnie the Pooh and Christmas Too (Part 1).mp4",
        "Winnie the Pooh and Christmas Too (Part 2).mp4",
        "Winnie the Pooh and Christmas Too.mp4",
    ]

    def fake_meta(_identifier: str) -> dict:
        return {
            "metadata": {"date": "2019-12-01"},
            "files": [{"name": name, "length": "1800"} for name in filenames],
        }

    monkeypatch.setattr(
        "streamtv.builder.resolver.fetch_archive_metadata", fake_meta
    )

    stream_ids: list[str] = []
    for name in filenames:
        url = (
            f"https://archive.org/download/{identifier}/{quote(name, safe='/')}"
        )
        item = resolve_single_url(url)
        stream_ids.append(item["stream_id"])

    # Document the current colliding slug for diagnostics when the assert fails.
    colliding = _slugify(f"{identifier}_{filenames[0]}")
    assert len(set(stream_ids)) == 3, (
        "D2: three files of one archive item produced colliding stream_ids "
        f"{stream_ids!r} (truncated slug example: {colliding!r})"
    )
    for sid in stream_ids:
        assert sid != colliding or stream_ids.count(sid) == 1


def test_d4_chronological_sorts_by_air_date_not_upload_date() -> None:
    """D4: chronological order and broadcast_date must use air_date, not upload_date."""
    assert "air_date" in LinkItem.model_fields, (
        "D4: LinkItem.air_date field missing — upload_date is used as air date today"
    )

    draft = BuilderDraft(
        channel=ChannelInfo(number="9004", name="D4 Probe"),
        ordering=OrderingMode.CHRONOLOGICAL,
        links=[
            LinkItem(
                url="https://www.youtube.com/watch?v=lateup",
                status=LinkStatus.OK,
                source="youtube",
                stream_id="lateup",
                title="1984 special uploaded in 2023",
                duration=1800,
                upload_date="2023-06-01",
                air_date="1984-12-25",
            ),
            LinkItem(
                url="https://www.youtube.com/watch?v=earlyup",
                status=LinkStatus.OK,
                source="youtube",
                stream_id="earlyup",
                title="1990 special",
                duration=1800,
                upload_date="1990-01-15",
                air_date="1990-12-24",
            ),
        ],
    )
    unified = compile_draft_to_unified(draft)
    ids = [s["id"] for s in unified["streams"]]
    assert ids == ["lateup", "earlyup"], (
        "D4: chronological must sort by air_date (1984 before 1990); "
        f"got {ids!r} (upload_date order would put earlyup first)"
    )
    assert unified["streams"][0]["broadcast_date"] == "1984-12-25", (
        "D4: broadcast_date must be air_date, never upload_date "
        f"(got {unified['streams'][0].get('broadcast_date')!r})"
    )
