"""Cache playback mode helpers (direct / buffer / full)."""

from __future__ import annotations

from typing import Literal

from streamtv.config import config
from streamtv.database.models import StreamSource

PlaybackMode = Literal["direct", "buffer", "full"]


def playback_mode() -> PlaybackMode:
    raw = (getattr(config.cache, "playback_mode", None) or "full").lower()
    if raw in ("direct", "buffer", "full"):
        return raw  # type: ignore[return-value]
    return "full"


def direct_stream_first() -> bool:
    """Stream from CDN immediately; cache is optional acceleration only."""
    if not config.cache.enabled:
        return True
    return playback_mode() in ("direct", "buffer")


def background_downloads_enabled() -> bool:
    """Queue full-file background downloads (disk-heavy)."""
    if not config.cache.enabled:
        return False
    return playback_mode() == "full"


def prefetch_downloads_enabled() -> bool:
    """Idle background prefetch (full downloads while channel runs unattended)."""
    if not config.cache.enabled:
        return False
    return playback_mode() == "full"


def tune_only_buffering() -> bool:
    """RAM ring buffer only when a tuner is connected (Tunarr-style)."""
    if not config.cache.enabled or playback_mode() != "buffer":
        return False
    return bool(getattr(config.cache, "tune_only_buffer", True))


def youtube_full_cache_enabled() -> bool:
    """Buffer mode: full yt-dlp download for YouTube only (RAM disk cache)."""
    if not config.cache.enabled:
        return False
    return bool(getattr(config.cache, "youtube_full_cache", False))


def source_downloads_enabled(source: StreamSource) -> bool:
    """Whether background/full downloads are allowed for this source."""
    if background_downloads_enabled():
        return True
    return source == StreamSource.YOUTUBE and youtube_full_cache_enabled()


def youtube_prefetch_enabled() -> bool:
    """Prefetch upcoming YouTube items while channel plays (buffer + youtube_full_cache)."""
    return prefetch_downloads_enabled() or youtube_full_cache_enabled()


def evict_after_play_enabled() -> bool:
    """Tunarr-style: remove cached file when playback for that item ends."""
    if not config.cache.enabled:
        return False
    return bool(getattr(config.cache, "evict_after_play", True))


def evict_off_schedule_enabled() -> bool:
    """Remove READY cache files not in the upcoming playout prefetch window."""
    if not config.cache.enabled:
        return False
    return bool(getattr(config.cache, "evict_off_schedule", True))


def ring_buffer_max_bytes() -> int:
    """Max bytes to pull per item into RAM (not a full file download)."""
    mb = float(getattr(config.cache, "stream_buffer_max_mb", 48.0) or 48.0)
    sec = max(0.0, float(getattr(config.cache, "stream_buffer_seconds", 30.0) or 30.0))
    cap = int(mb * 1024 * 1024)
    from_bytes = int(sec * 2_500_000 / 8 * 1.25) if sec > 0 else 0
    floor = min(4 * 1024 * 1024, cap) if cap > 0 else 4 * 1024 * 1024
    need = max(from_bytes, floor)
    return min(cap, need) if cap > 0 else need
