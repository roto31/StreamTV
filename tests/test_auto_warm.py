"""Idle YouTube full-cache auto-warm selection + cadence."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from streamtv.cache.auto_warm import (
    auto_warm_enabled,
    select_youtube_warm_items,
    warm_idle_youtube_window,
)
from streamtv.database.models import StreamSource


def _yt(sid: str) -> SimpleNamespace:
    return SimpleNamespace(source=StreamSource.YOUTUBE, source_id=sid, id=1)


def _arc(sid: str) -> SimpleNamespace:
    return SimpleNamespace(source=StreamSource.ARCHIVE_ORG, source_id=sid, id=2)


def test_select_youtube_warm_items_skips_archive_and_bounds() -> None:
    schedule = [
        {"media_item": _arc("a1")},
        {"media_item": _yt("y1")},
        {"media_item": _yt("y2")},
        {"media_item": _arc("a2")},
    ]
    assert [m.source_id for m in select_youtube_warm_items(schedule, 0, 2)] == ["y1"]
    assert [m.source_id for m in select_youtube_warm_items(schedule, 1, 3)] == [
        "y1",
        "y2",
    ]
    assert select_youtube_warm_items(schedule, 99, 2) == []
    assert select_youtube_warm_items([], 0, 2) == []


def test_auto_warm_requires_youtube_full_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    from streamtv import config as cfg
    from streamtv.cache import playback_mode

    monkeypatch.setattr(cfg.config.cache, "enabled", True)
    monkeypatch.setattr(cfg.config.cache, "youtube_full_cache", False)
    monkeypatch.setattr(cfg.config.cache, "auto_warm_enabled", True)
    monkeypatch.setattr(playback_mode, "youtube_full_cache_enabled", lambda: False)
    assert auto_warm_enabled() is False

    monkeypatch.setattr(playback_mode, "youtube_full_cache_enabled", lambda: True)
    monkeypatch.setattr(cfg.config.cache, "youtube_full_cache", True)
    assert auto_warm_enabled() is True


@pytest.mark.asyncio
async def test_warm_idle_youtube_window_cadence_and_prioritize(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from streamtv import config as cfg
    from streamtv.cache import auto_warm as aw

    monkeypatch.setattr(aw, "auto_warm_enabled", lambda: True)
    monkeypatch.setattr(aw, "auto_warm_interval_seconds", lambda: 60.0)
    monkeypatch.setattr(cfg.config.cache, "prefetch_count", 2)

    queue = AsyncMock()
    schedule = [
        {"media_item": _yt("open")},
        {"media_item": _yt("next")},
    ]

    first = await warm_idle_youtube_window(
        channel_number="2026",
        schedule_items=schedule,
        guide_index=0,
        download_queue=queue,
        last_warm_mono=0.0,
        now_mono=100.0,
    )
    assert first == 100.0
    assert queue.enqueue.await_count == 2
    queue.ensure_download_started.assert_awaited_once()
    queue.prioritize.assert_awaited_once()

    # Within interval — no second pass.
    second = await warm_idle_youtube_window(
        channel_number="2026",
        schedule_items=schedule,
        guide_index=0,
        download_queue=queue,
        last_warm_mono=first,
        now_mono=130.0,
    )
    assert second == first
    assert queue.enqueue.await_count == 2
