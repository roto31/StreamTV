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


def test_enforce_on_air_epg_coverage_blocks_next_slot_as_now() -> None:
    """iptv enforce must stretch on-air row so only row 0 covers `now`."""
    from streamtv.api.iptv import _enforce_on_air_epg_coverage, _epg_item_covers_now

    items = [_item("For Those", 353), _item("Thunderstruck", 292)]
    anchor = datetime(2026, 7, 13, 22, 0, 0)
    live_start = anchor
    now = anchor + timedelta(seconds=400)  # past scheduled end of row 0

    rows = [
        {**items[0], "start_time": live_start},
        {**items[1], "start_time": live_start + timedelta(seconds=353)},
    ]
    enforced = _enforce_on_air_epg_coverage(
        rows, now, live_item_index=0, live_item_start_time=live_start
    )

    assert _epg_item_covers_now(enforced[0], now)
    assert not any(_epg_item_covers_now(row, now) for row in enforced[1:])
    assert enforced[0]["media_item"].title == "For Those"


def test_enforce_on_air_epg_anchors_to_live_start_and_grace() -> None:
    """Stale stabilize starts must not end the on-air row before playout finishes."""
    from streamtv.api.iptv import _enforce_on_air_epg_coverage, _epg_item_covers_now

    items = [_item("For Those", 353), _item("Thunderstruck", 292)]
    stale_start = datetime(2026, 7, 13, 23, 2, 0)
    live_start = datetime(2026, 7, 13, 23, 8, 0)
    now = live_start + timedelta(seconds=150)

    rows = [
        {**items[0], "start_time": stale_start},
        {**items[1], "start_time": stale_start + timedelta(seconds=353)},
    ]
    enforced = _enforce_on_air_epg_coverage(
        rows, now, live_item_index=7, live_item_start_time=live_start
    )

    assert enforced[0]["start_time"] == live_start
    assert _epg_item_covers_now(enforced[0], now)
    assert not _epg_item_covers_now(enforced[1], now)


def test_epg_live_air_anchor_prefers_memory_over_stale_saved() -> None:
    """When playout advanced to idx 8, EPG must not pin to stale saved idx 7."""

    class _Mgr:
        def get_live_playout_state(self, _channel: str) -> dict:
            return {"item_index": 8, "item_start_time": datetime(2026, 7, 13, 23, 2, 0)}

    class _Pos:
        last_item_index = 7
        last_position_update = datetime(2026, 7, 13, 22, 48, 0)

    from streamtv.api.iptv import _epg_live_air_anchor

    idx, _ = _epg_live_air_anchor(_Mgr(), _Pos(), "1986", guide_index=15)
    assert idx == 8


def test_epg_live_air_anchor_db_fallback_omits_stale_position_update() -> None:
    """After restart (no memory), item start must come from playout_timeline — not DB touch time."""

    class _Pos:
        last_item_index = 7
        last_position_update = datetime(2026, 7, 13, 22, 0, 0)

    from streamtv.api.iptv import _epg_live_air_anchor

    idx, start = _epg_live_air_anchor(None, _Pos(), "1986", guide_index=18)
    assert idx == 7
    assert start is None


def test_authoritative_enforce_when_air_equals_guide() -> None:
    """Class-A playout-authoritative path stretches row 0 even when not lagging."""
    from streamtv.api.iptv import _enforce_on_air_epg_coverage, _epg_item_covers_now

    items = [_item("A", 100), _item("B", 100)]
    anchor = datetime(2026, 7, 11, 8, 0, 0)
    live_start = anchor + timedelta(seconds=10)
    now = live_start + timedelta(seconds=50)

    enforced = _enforce_on_air_epg_coverage(
        items,
        now,
        live_item_index=0,
        live_item_start_time=live_start,
    )
    assert _epg_item_covers_now(enforced[0], now)


def test_epg_xml_duration_pad_future_rows_only() -> None:
    from streamtv.scheduling.playout_timeline import epg_xml_duration, item_duration

    row = _item("A", 200)
    assert epg_xml_duration(row, pad_seconds=5) == item_duration(row) + 5
    assert epg_xml_duration(row, pad_seconds=0) == item_duration(row)


def test_resolve_epg_sync_class_defaults() -> None:
    from streamtv.epg_sync_class import resolve_epg_sync_class

    assert resolve_epg_sync_class("1986") == "A"
    assert resolve_epg_sync_class("80") == "B"
    assert resolve_epg_sync_class("1929") == "C"


def test_enforce_on_air_epg_caps_stretch_for_archive_channels() -> None:
    """Class B/C lagging rows must not grow into multi-hour Plex guide blocks."""
    from streamtv.api.iptv import _enforce_on_air_epg_coverage, _epg_item_covers_now

    items = [_item("Magnum", 2800), _item("Next", 2800)]
    anchor = datetime(2026, 7, 14, 12, 0, 0)
    now = anchor + timedelta(hours=6)

    rows = [
        {**items[0], "start_time": anchor, "cached_duration": 6 * 3600},
        {**items[1], "start_time": anchor + timedelta(hours=6)},
    ]
    enforced = _enforce_on_air_epg_coverage(
        rows,
        now,
        live_item_index=0,
        live_item_start_time=anchor,
        cap_stretch_to_media=True,
    )

    max_dur = items[0]["media_item"].duration + 120
    assert enforced[0]["cached_duration"] <= max_dur
