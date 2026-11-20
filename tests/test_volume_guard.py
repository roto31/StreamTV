"""Issue 48 — pause / cap downloads before TunarrRAM hits 100% (no live yt-dlp)."""

from __future__ import annotations

from streamtv.cache.volume_guard import (
    can_start_download,
    download_dispatch_limit,
    effective_download_concurrency,
    should_pause_new_downloads,
)


def test_pause_at_or_above_50_used_pct() -> None:
    free_ok = 900 * 1024 * 1024
    assert should_pause_new_downloads(50.0, free_ok) is True
    assert should_pause_new_downloads(80.0, free_ok) is True
    assert should_pause_new_downloads(49.9, free_ok) is False


def test_pause_when_free_below_400_mi() -> None:
    assert should_pause_new_downloads(10.0, 399 * 1024 * 1024) is True
    assert should_pause_new_downloads(10.0, 400 * 1024 * 1024) is False


def test_youtube_full_cache_caps_concurrency_at_one() -> None:
    assert effective_download_concurrency(2, youtube_full_cache=True) == 1
    assert effective_download_concurrency(4, youtube_full_cache=True) == 1
    assert effective_download_concurrency(2, youtube_full_cache=False) == 2


def test_dispatch_limit_zero_when_paused() -> None:
    assert (
        download_dispatch_limit(
            configured_max=2,
            youtube_full_cache=True,
            used_pct=55.0,
            free_bytes=200 * 1024 * 1024,
        )
        == 0
    )


def test_dispatch_limit_one_when_full_cache_and_headroom() -> None:
    assert (
        download_dispatch_limit(
            configured_max=2,
            youtube_full_cache=True,
            used_pct=20.0,
            free_bytes=900 * 1024 * 1024,
        )
        == 1
    )


def test_cannot_start_when_in_flight_at_limit() -> None:
    assert (
        can_start_download(
            in_flight_count=1,
            configured_max=2,
            youtube_full_cache=True,
            used_pct=20.0,
            free_bytes=900 * 1024 * 1024,
        )
        is False
    )
    assert (
        can_start_download(
            in_flight_count=0,
            configured_max=2,
            youtube_full_cache=True,
            used_pct=20.0,
            free_bytes=900 * 1024 * 1024,
        )
        is True
    )
