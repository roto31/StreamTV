"""PBS adapter URL classification (VOD vs live vs false positives)."""

from __future__ import annotations

from streamtv.streaming.pbs_adapter import PBSAdapter

LAKE_MEAD = (
    "https://www.pbs.org/video/lake-mead-mysteries-great-ev-road-chatper-one-niks4w/"
)
TITANOBOA = (
    "https://www.pbs.org/video/titanoboa-the-largest-snake-that-ever-lived-1sn2xp/"
)


def _adapter() -> PBSAdapter:
    return PBSAdapter(cookies_file="data/cookies/pbs_cookies.txt", use_authentication=False)


def test_pbs_vod_video_pages_are_valid() -> None:
    adapter = _adapter()
    assert adapter.is_valid_url(LAKE_MEAD)
    assert adapter.is_valid_url(TITANOBOA)


def test_pbs_show_landing_not_valid_for_streaming() -> None:
    adapter = _adapter()
    assert not adapter.is_valid_url("https://www.pbs.org/show/nature/")


def test_pbs_watch_live_valid() -> None:
    adapter = _adapter()
    assert adapter.is_valid_url("https://www.pbs.org/watch-live/kcts/")
