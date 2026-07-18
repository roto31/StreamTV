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


def test_pbs_prefers_pbs_cs_over_drm_cmaf() -> None:
    adapter = _adapter()
    drm = (
        "https://ga.pbs-video.pbs.org/p/-/sid/abc/videos/downton-abbey/"
        "asset/2000523214/hd-16x9-mezzanine-1080p/cbc/mast4102_2026-AABR-AVC-720p_983.m3u8"
    )
    plain = (
        "https://ga.pbs-video.pbs.org/p/pbs-cs/sid/67c12857b53a47eb8cdb2f677add81b0/"
        "videos/nature/f445478f-7900-42bc-aebf-66398ab/manifest.m3u8"
    )
    chosen = adapter._select_preferred_stream_url([drm, plain])
    assert chosen == plain
    assert not adapter._is_drm_pbs_stream_url(chosen)


def test_pbs_drm_url_detection() -> None:
    adapter = _adapter()
    drm = (
        "https://ga.pbs-video.pbs.org/p/-/sid/x/videos/downton-abbey/y/"
        "z/cbc/mast4101_2026-AABR-AVC-720p_345.m3u8"
    )
    assert adapter._is_drm_pbs_stream_url(drm)
    assert not adapter._is_drm_pbs_stream_url(
        "https://ga.pbs-video.pbs.org/p/pbs-cs/sid/x/videos/nature/y/manifest.m3u8"
    )


def test_pbs_rejects_placeholder_drm_static_url() -> None:
    adapter = _adapter()
    drm = (
        "https://ga.pbs-video.pbs.org/p/-/sid/abc/videos/downton-abbey/"
        "asset/cbc/mast4102_2026-AABR-AVC-720p_983.m3u8"
    )
    placeholder = (
        "https://static.drm.pbs.org/v1/channel/livestream-update-needed-ga/index.m3u8"
    )
    plain = (
        "https://ga.pbs-video.pbs.org/p/pbs-cs/sid/67c12857b53a47eb8cdb2f677add81b0/"
        "videos/downton-abbey/81a6bff1/manifest.m3u8"
    )
    chosen = adapter._select_preferred_stream_url([drm, placeholder, plain])
    assert chosen == plain
    assert adapter._is_bad_pbs_stream_url(placeholder)
