"""Tests for sticky terminal cache failures (queue_for_download behavior)."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from streamtv.cache.cache_manager import CacheManager
from streamtv.database.models import CacheStatus, CachedMedia, MediaItem, StreamSource


@pytest.fixture()
def cache_mgr(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> CacheManager:
    monkeypatch.setattr(
        "streamtv.cache.cache_manager.config.cache.cache_directory",
        str(tmp_path / "cache"),
    )
    monkeypatch.setattr(
        "streamtv.cache.cache_manager.config.cache.default_ttl_hours",
        72,
    )
    sessions: list[MagicMock] = []

    def factory() -> MagicMock:
        db = MagicMock()
        sessions.append(db)
        return db

    mgr = CacheManager(factory)
    mgr._sessions = sessions  # type: ignore[attr-defined]
    return mgr


def _media(source_id: str = "vid1") -> MediaItem:
    item = MagicMock(spec=MediaItem)
    item.source_id = source_id
    item.id = 1
    item.source = StreamSource.YOUTUBE
    return item


def test_queue_skips_terminal_failed(cache_mgr: CacheManager) -> None:
    row = MagicMock(spec=CachedMedia)
    row.status = CacheStatus.FAILED
    row.failure_class = "unavailable"
    row.retry_after = None

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = row
    cache_mgr.db_session_factory = lambda: db
    cache_mgr.is_download_pending = MagicMock(return_value=False)  # type: ignore[method-assign]

    cache_mgr.queue_for_download(_media())
    db.commit.assert_not_called()
    assert row.status == CacheStatus.FAILED


def test_queue_allows_rate_limited_after_cooldown(cache_mgr: CacheManager) -> None:
    row = MagicMock(spec=CachedMedia)
    row.status = CacheStatus.FAILED
    row.failure_class = "rate_limited"
    row.retry_after = datetime.utcnow() - timedelta(seconds=1)
    row.error_message = "429"

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = row
    cache_mgr.db_session_factory = lambda: db
    cache_mgr.is_download_pending = MagicMock(return_value=False)  # type: ignore[method-assign]

    cache_mgr.queue_for_download(_media())
    assert row.status == CacheStatus.QUEUED
    assert row.failure_class is None
    db.commit.assert_called_once()


def test_queue_blocks_rate_limited_before_cooldown(cache_mgr: CacheManager) -> None:
    row = MagicMock(spec=CachedMedia)
    row.status = CacheStatus.FAILED
    row.failure_class = "rate_limited"
    row.retry_after = datetime.utcnow() + timedelta(minutes=10)

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = row
    cache_mgr.db_session_factory = lambda: db
    cache_mgr.is_download_pending = MagicMock(return_value=False)  # type: ignore[method-assign]

    cache_mgr.queue_for_download(_media())
    assert row.status == CacheStatus.FAILED
    db.commit.assert_not_called()


def test_retry_failed_download_clears_terminal(cache_mgr: CacheManager) -> None:
    row = MagicMock(spec=CachedMedia)
    row.status = CacheStatus.FAILED
    row.failure_class = "auth_required"
    row.error_message = "403"
    row.retry_after = None

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = row
    cache_mgr.db_session_factory = lambda: db

    assert cache_mgr.retry_failed_download("vid1") is True
    assert row.status == CacheStatus.QUEUED
    assert row.failure_class is None
    db.commit.assert_called_once()
