"""Plex DVR id normalize + candidate ordering (reloadGuide 404 self-heal)."""

from __future__ import annotations

from streamtv.plex.guide_reload import normalize_dvr_id, _prefer_streamtv_dvr


def test_normalize_dvr_id_numeric() -> None:
    assert normalize_dvr_id("119") == "119"
    assert normalize_dvr_id(" 119 ") == "119"


def test_normalize_dvr_id_path() -> None:
    assert normalize_dvr_id("/livetv/dvrs/119") == "119"
    assert normalize_dvr_id("/livetv/dvrs/119/") == "119"


def test_normalize_dvr_id_empty() -> None:
    assert normalize_dvr_id(None) is None
    assert normalize_dvr_id("") is None
    assert normalize_dvr_id("   ") is None


def test_prefer_streamtv_dvr_orders_title_then_enabled() -> None:
    dvrs = [
        {"id": "10", "title": "Other", "enabled": True},
        {"id": "119", "title": "StreamTV", "enabled": True},
        {"id": "11", "title": "Tunarr", "enabled": False},
        {"id": "/livetv/dvrs/120", "title": "stream tv backup", "enabled": False},
    ]
    assert _prefer_streamtv_dvr(dvrs) == ["119", "120", "10", "11"]
