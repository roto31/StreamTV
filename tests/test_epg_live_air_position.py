"""EPG must follow on-air index when playout lags wall-clock guide."""

from __future__ import annotations

from datetime import datetime, timedelta

from streamtv.scheduling.playout_timeline import (
    assign_schedule_times_from_playout,
    clear_epg_timeline_cache,
    resolve_live_epg_air_position,
    stabilize_epg_timeline_for_plex,
)


def _item(title: str, duration: int) -> dict:
    class _Media:
        def __init__(self, t: str, d: int) -> None:
            self.title = t
            self.duration = d

    return {"media_item": _Media(title, duration), "cached_duration": duration}


def test_resolve_live_epg_air_position_prefers_lagging_air_index() -> None:
    items = [_item("A", 100), _item("B", 100), _item("C", 100)]
    anchor = datetime(2026, 7, 11, 8, 0, 0)
    now = anchor + timedelta(seconds=250)  # wall-clock guide at index 2

    position = resolve_live_epg_air_position(
        items,
        anchor,
        now,
        live_item_index=1,
        live_item_start_time=anchor + timedelta(seconds=120),
    )

    assert position["guide_item_index"] == 2
    assert position["item_index"] == 1


def test_assign_schedule_times_uses_live_air_index() -> None:
    items = [_item("A", 100), _item("B", 100), _item("C", 100)]
    anchor = datetime(2026, 7, 11, 8, 0, 0)
    now = anchor + timedelta(seconds=250)
    live_start = anchor + timedelta(seconds=120)

    reassigned = assign_schedule_times_from_playout(
        items,
        anchor,
        now,
        live_item_index=1,
        live_item_start_time=live_start,
    )

    assert reassigned[0]["media_item"].title == "B"
    assert reassigned[0]["start_time"] == live_start


def test_resolve_live_epg_stale_start_pins_on_air_item() -> None:
    """When DB start is hours old, EPG must not walk forward past the on-air item."""
    items = [_item("Queen", 353)] + [_item(f"Filler{i}", 240) for i in range(15)]
    anchor = datetime(2026, 7, 11, 8, 0, 0)
    live_start = anchor + timedelta(seconds=100)
    now = anchor + timedelta(seconds=3700)

    position = resolve_live_epg_air_position(
        items,
        anchor,
        now,
        live_item_index=0,
        live_item_start_time=live_start,
    )
    assert position["item_index"] == 0

    reassigned = assign_schedule_times_from_playout(
        items,
        anchor,
        now,
        live_item_index=0,
        live_item_start_time=live_start,
    )
    covering = None
    for it in reassigned:
        st = it["start_time"]
        en = st + timedelta(seconds=it["cached_duration"])
        if st <= now < en:
            covering = it["media_item"].title
            break
    assert covering == "Queen"


def test_assign_schedule_stretches_live_row_when_playout_lags() -> None:
    """EPG must keep the on-air title in 'now' until playout advances past it."""
    items = [_item("A", 100), _item("B", 100), _item("C", 100)]
    anchor = datetime(2026, 7, 11, 8, 0, 0)
    live_start = anchor + timedelta(seconds=100)
    now = live_start + timedelta(seconds=150)  # past B's scheduled end, still on-air

    reassigned = assign_schedule_times_from_playout(
        items,
        anchor,
        now,
        live_item_index=1,
        live_item_start_time=live_start,
    )

    covering = None
    for it in reassigned:
        st = it["start_time"]
        en = st + timedelta(seconds=it["cached_duration"])
        if st <= now < en:
            covering = it["media_item"].title
            break
    assert covering == "B"


def test_stabilize_epg_timeline_reuses_starts_until_item_changes() -> None:
    """Repeated EPG builds for the same on-air item must emit identical start times."""
    clear_epg_timeline_cache()
    items = [_item("A", 100), _item("B", 246), _item("C", 100)]
    anchor = datetime(2026, 7, 11, 8, 0, 37)
    live_start = anchor + timedelta(seconds=100)
    now = live_start + timedelta(seconds=10)

    first = assign_schedule_times_from_playout(
        items,
        anchor,
        now,
        live_item_index=1,
        live_item_start_time=live_start,
    )
    stable_a, state_a = stabilize_epg_timeline_for_plex("1991", 1, first, now)
    assert state_a == "miss"
    assert stable_a[0]["start_time"].second == 0

    now2 = live_start + timedelta(seconds=45)
    second = assign_schedule_times_from_playout(
        items,
        anchor,
        now2,
        live_item_index=1,
        live_item_start_time=live_start + timedelta(seconds=3),
    )
    stable_b, state_b = stabilize_epg_timeline_for_plex("1991", 1, second, now2)
    assert state_b == "hit"
    assert [r["start_time"] for r in stable_b[:3]] == [r["start_time"] for r in stable_a[:3]]

    third = assign_schedule_times_from_playout(
        items,
        anchor,
        now2,
        live_item_index=2,
        live_item_start_time=live_start + timedelta(seconds=400),
    )
    stable_c, state_c = stabilize_epg_timeline_for_plex("1991", 2, third, now2)
    assert state_c == "miss"
    clear_epg_timeline_cache()
