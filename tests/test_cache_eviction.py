"""Tunarr-style cache eviction (after play + off-schedule window)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from streamtv.cache.cache_manager import CacheManager
from streamtv.database.models import CachedMedia, CacheStatus, StreamSource
from streamtv.utils.clock import utc_now_naive


@pytest.fixture()
def cache_manager(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> CacheManager:
    from streamtv import config as cfg

    monkeypatch.setattr(cfg.config.cache, "cache_directory", str(tmp_path))
    monkeypatch.setattr(cfg.config.cache, "max_size_gb", 1.0)
    monkeypatch.setattr(cfg.config.cache, "enabled", True)

    engine = create_engine("sqlite:///:memory:")
    CachedMedia.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    return CacheManager(factory)


def _add_ready_row(
    cm: CacheManager,
    source_id: str,
    *,
    status: CacheStatus = CacheStatus.READY,
) -> Path:
    path = cm.cache_dir / f"{source_id}.mp4"
    path.write_bytes(b"fake")
    db = cm.db_session_factory()
    try:
        db.add(
            CachedMedia(
                source_id=source_id,
                source=StreamSource.YOUTUBE,
                local_path=str(path),
                size_bytes=path.stat().st_size,
                status=status,
                accessed_at=utc_now_naive(),
            )
        )
        db.commit()
    finally:
        db.close()
    return path


def test_evict_source_deletes_file_and_manifest(
    cache_manager: CacheManager,
) -> None:
    path = _add_ready_row(cache_manager, "yt-keep-evict")
    assert path.exists()
    assert cache_manager.evict_source("yt-keep-evict", reason="after_play")
    assert not path.exists()
    assert cache_manager.get_cached_path("yt-keep-evict") is None


def test_evict_sources_not_in_keeps_window(
    cache_manager: CacheManager,
) -> None:
    keep_path = _add_ready_row(cache_manager, "in-window")
    drop_path = _add_ready_row(cache_manager, "off-window")
    removed = cache_manager.evict_sources_not_in({"in-window"})
    assert removed == 1
    assert keep_path.exists()
    assert not drop_path.exists()
    assert cache_manager.get_cached_path("in-window") is not None
    assert cache_manager.get_cached_path("off-window") is None


def test_evict_sources_not_in_scoped_to_channel_candidates(
    cache_manager: CacheManager,
) -> None:
    ch1991_playing = _add_ready_row(cache_manager, "1991-playing")
    ch1986_other = _add_ready_row(cache_manager, "1986-other")
    ch1991_stale = _add_ready_row(cache_manager, "1991-stale")

    removed = cache_manager.evict_sources_not_in(
        {"1991-playing", "1991-next"},
        candidate_source_ids={"1991-playing", "1991-stale", "1991-next"},
    )
    assert removed == 1
    assert ch1991_playing.exists()
    assert ch1986_other.exists()
    assert not ch1991_stale.exists()
    assert cache_manager.get_cached_path("1986-other") is not None


def test_evict_after_play_enabled_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    from streamtv import config as cfg
    from streamtv.cache.playback_mode import evict_after_play_enabled

    monkeypatch.setattr(cfg.config.cache, "enabled", True)
    monkeypatch.setattr(cfg.config.cache, "evict_after_play", True)
    assert evict_after_play_enabled()

    monkeypatch.setattr(cfg.config.cache, "evict_after_play", False)
    assert not evict_after_play_enabled()


def test_schedule_keep_source_ids_window() -> None:
    from streamtv.streaming.channel_manager import _schedule_keep_source_ids

    media_a = SimpleNamespace(source_id="a")
    media_b = SimpleNamespace(source_id="b")
    media_c = SimpleNamespace(source_id="c")
    items = [
        {"media_item": media_a},
        {"media_item": media_b},
        {"media_item": media_c},
    ]
    keep = _schedule_keep_source_ids(
        items,
        start_index=1,
        prefetch_count=2,
        extra_keep_source_ids={"on-air"},
    )
    assert keep == {"a", "b", "c", "on-air"}


def test_evict_lru_skips_pinned_on_air(
    cache_manager: CacheManager, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pinned on-air/window source_ids must survive LRU even past access grace."""
    from datetime import timedelta

    monkeypatch.setattr(cache_manager, "max_size_bytes", 10)

    pinned_path = _add_ready_row(cache_manager, "on-air-yt")
    victim_path = _add_ready_row(cache_manager, "cold-other")
    db = cache_manager.db_session_factory()
    try:
        old = utc_now_naive() - timedelta(hours=2)
        for row in db.query(CachedMedia).all():
            row.size_bytes = 8
            row.accessed_at = old
            path = Path(row.local_path)
            path.write_bytes(b"x" * 8)
        db.commit()
    finally:
        db.close()

    cache_manager.set_pin_group("on_air:1988.2", {"on-air-yt"})
    cache_manager.evict_lru_to_fit(8)

    assert pinned_path.exists()
    assert cache_manager.get_cached_path("on-air-yt") is not None
    assert not victim_path.exists()
    assert cache_manager.get_cached_path("cold-other") is None


def test_set_pin_group_replace_and_clear(cache_manager: CacheManager) -> None:
    cache_manager.set_pin_group("yt_window:1996.2", {"a", "b"})
    assert cache_manager.pinned_source_ids() == {"a", "b"}
    cache_manager.set_pin_group("yt_window:1996.2", {"b", "c"})
    assert cache_manager.pinned_source_ids() == {"b", "c"}
    cache_manager.clear_pin_group("yt_window:1996.2")
    assert cache_manager.pinned_source_ids() == set()
