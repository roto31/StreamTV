"""Phase 3 soft-deploy / isolation helpers (no live fleet restart)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
async def test_restart_all_channels_collects_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    from streamtv.streaming.channel_manager import ChannelManager

    mgr = ChannelManager(MagicMock())

    ch_a = MagicMock()
    ch_a.number = "80"
    ch_b = MagicMock()
    ch_b.number = "1991"

    db = MagicMock()
    q = MagicMock()
    q.filter.return_value.order_by.return_value.all.return_value = [ch_a, ch_b]
    db.query.return_value = q
    mgr.db_session_factory = MagicMock(return_value=db)

    async def _restart(num: str) -> dict:
        if num == "1991":
            raise RuntimeError("boom")
        return {"channel_number": num, "restarted": True}

    mgr.restart_channel = AsyncMock(side_effect=_restart)  # type: ignore[method-assign]

    out = await mgr.restart_all_channels()
    assert out["restarted"] == 1
    assert out["failed"] == 1
    assert out["errors"][0]["channel_number"] == "1991"


@pytest.mark.asyncio
async def test_supervised_respects_stop_requested() -> None:
    from streamtv.streaming.channel_manager import ChannelStream

    ch = MagicMock()
    ch.id = 1
    ch.number = "80"
    ch.name = "Test"
    stream = ChannelStream(ch, MagicMock())
    stream._stop_requested = True
    stream._epg_sync_class = "C"

    async def _never() -> None:
        raise AssertionError("should not run continuous stream")

    stream._run_continuous_stream = _never  # type: ignore[method-assign]
    await stream._supervised_continuous_stream()
