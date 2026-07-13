"""Playout reset anchor helpers."""

from datetime import datetime, timedelta

from streamtv.scheduling.playout_timeline import (
    cumulative_offset_seconds,
    find_item_index_by_title,
    playout_anchor_for_item_index,
)


def _items(durations):
    return [{"media_item": object(), "cached_duration": d} for d in durations]


def test_cumulative_offset_sums_prior_slots():
    items = _items([200, 201, 218])
    assert cumulative_offset_seconds(items, 0) == 0
    assert cumulative_offset_seconds(items, 2) == 401
    assert cumulative_offset_seconds(items, 3) == 619


def test_playout_anchor_for_item_index_rewinds_start_time():
    anchor = datetime(2026, 7, 11, 12, 0, 0)
    items = _items([200, 201])
    start, idx = playout_anchor_for_item_index(items, 1, anchor=anchor)
    assert idx == 1
    assert start == anchor - timedelta(seconds=200)


def test_find_item_index_by_title_unique_match():
    class _Media:
        def __init__(self, title):
            self.title = title

    items = [
        {"media_item": _Media("Rodney Crowell - I Couldn't Leave You If I Tried")},
        {"media_item": _Media("Randy Travis - Promises (Video)")},
    ]
    assert find_item_index_by_title(items, "Promises") == 1
