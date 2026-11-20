"""TunarrRAM / cache-volume download gates (Issue 48).

`cache.max_size_gb` is a manifest cap, not `df`. Concurrent yt-dlp can fill a 2 Gi
RAM disk inside the healer interval. Pause new prefetch before the 55% heal,
and cap youtube_full_cache concurrency to 1.

On-air `download_now` is not gated here (caller still needs the current item).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Union

# Pause *before* healer STREAMTV_TUNARRAM_MAX_USED_PCT=55 / MIN_FREE_MB=300.
DEFAULT_PAUSE_USED_PCT = 50.0
DEFAULT_PAUSE_MIN_FREE_MB = 400.0

PathLike = Union[str, Path]


def should_pause_new_downloads(
    used_pct: float,
    free_bytes: int,
    *,
    max_used_pct: float = DEFAULT_PAUSE_USED_PCT,
    min_free_mb: float = DEFAULT_PAUSE_MIN_FREE_MB,
) -> bool:
    """True when a new prefetch download would race the 2 Gi volume."""
    if used_pct >= max_used_pct:
        return True
    return int(free_bytes) < int(min_free_mb * 1024 * 1024)


def effective_download_concurrency(
    configured_max: int,
    *,
    youtube_full_cache: bool,
) -> int:
    """youtube_full_cache: at most one yt-dlp so a single file cannot race N-wide."""
    configured = max(0, int(configured_max))
    if youtube_full_cache:
        return 0 if configured == 0 else min(configured, 1)
    return configured


def download_dispatch_limit(
    *,
    configured_max: int,
    youtube_full_cache: bool,
    used_pct: float,
    free_bytes: int,
) -> int:
    if should_pause_new_downloads(used_pct, free_bytes):
        return 0
    return effective_download_concurrency(
        configured_max, youtube_full_cache=youtube_full_cache
    )


def can_start_download(
    *,
    in_flight_count: int,
    configured_max: int,
    youtube_full_cache: bool,
    used_pct: float,
    free_bytes: int,
) -> bool:
    limit = download_dispatch_limit(
        configured_max=configured_max,
        youtube_full_cache=youtube_full_cache,
        used_pct=used_pct,
        free_bytes=free_bytes,
    )
    return limit > 0 and int(in_flight_count) < limit


def cache_volume_pressure(cache_directory: PathLike) -> tuple[float, int]:
    """Return (used_pct, free_bytes). Missing/unreadable → no pressure."""
    path = Path(cache_directory)
    probe = path if path.exists() else path.parent
    try:
        st = os.statvfs(probe)
    except OSError:
        return 0.0, 10**18
    total = int(st.f_blocks * st.f_frsize)
    free = int(st.f_bavail * st.f_frsize)
    if total <= 0:
        return 0.0, free
    used_pct = 100.0 * (total - free) / total
    return used_pct, free
