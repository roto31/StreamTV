"""Tests for Tunarr library prefetch selection and skip-if-exists."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from streamtv.database.models import (
    Channel,
    MediaItem,
    Playlist,
    PlaylistItem,
    PlayoutMode,
    StreamSource,
)
from streamtv.exporters.tunarr_prefetch import (
    PrefetchCandidate,
    assert_export_not_tunarr_ram,
    run_prefetch,
    select_prefetch_candidates,
)


def test_assert_export_not_tunarr_ram_rejects() -> None:
    bad = Path("/Volumes/TunarrRAM/streamtv-cache/export")
    with pytest.raises(ValueError, match="TunarrRAM"):
        assert_export_not_tunarr_ram(bad)


def test_assert_export_not_tunarr_ram_allows_durable(tmp_path: Path) -> None:
    export = tmp_path / "tunarr_library"
    export.mkdir()
    assert_export_not_tunarr_ram(export)


class _Query:
    def __init__(self, rows=None, first_row=None):
        self._rows = list(rows or [])
        self._first = first_row

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return list(self._rows)

    def first(self):
        if self._first is not None:
            return self._first
        return self._rows[0] if self._rows else None


def test_select_respects_max_items(monkeypatch: pytest.MonkeyPatch) -> None:
    ch = SimpleNamespace(
        id=1,
        number="42",
        enabled=True,
        playout_mode=PlayoutMode.CONTINUOUS,
    )
    pl = SimpleNamespace(id=10, channel_id=1)
    items = [
        SimpleNamespace(id=i, playlist_id=10, media_item_id=100 + i, order=i)
        for i in range(5)
    ]
    media = {
        100 + i: SimpleNamespace(
            id=100 + i,
            source=StreamSource.ARCHIVE_ORG,
            source_id=f"ia-{i}",
            url=f"https://archive.org/details/ia-{i}",
            title=f"Title {i}",
            description=None,
            duration=1800,
        )
        for i in range(5)
    }

    media_queue = [media[100 + i] for i in range(5)]

    def query(model):
        if model is Channel:
            return _Query(rows=[ch])
        if model is Playlist:
            return _Query(rows=[pl])
        if model is PlaylistItem:
            return _Query(rows=items)
        if model is MediaItem:
            q = _Query()

            def filter_media(*args, **kwargs):
                row = media_queue.pop(0) if media_queue else None
                return _Query(first_row=row)

            q.filter = filter_media  # type: ignore[method-assign]
            return q
        return _Query()

    db = MagicMock()
    db.query.side_effect = query
    monkeypatch.setattr(
        "streamtv.exporters.tunarr_prefetch.config.tunarr_library",
        SimpleNamespace(
            prefetch_hours=24,
            prefetch_max_items=2,
            channel_numbers=[],
        ),
    )

    selected = select_prefetch_candidates(db, prefetch_max_items=2)
    assert len(selected) == 2
    assert selected[0].source_id == "ia-0"
    assert selected[1].source_id == "ia-1"


def test_dry_run_lists_and_skip_existing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = tmp_path / "cache"
    export = tmp_path / "library"
    cache.mkdir()
    export.mkdir()
    existing = export / "already.mp4"
    existing.write_bytes(b"x" * 100)

    monkeypatch.setattr(
        "streamtv.exporters.tunarr_prefetch.config.cache.cache_directory",
        str(cache),
    )
    monkeypatch.setattr(
        "streamtv.exporters.tunarr_prefetch.config.tunarr_library",
        SimpleNamespace(
            export_directory=str(export),
            naming="source_id",
            prefetch_hours=6,
            prefetch_max_items=5,
            prefetch_max_gb=20,
            channel_numbers=[],
        ),
    )
    monkeypatch.setattr(
        "streamtv.exporters.tunarr_library.config.cache.cache_directory",
        str(cache),
    )
    monkeypatch.setattr(
        "streamtv.exporters.tunarr_library.config.tunarr_library.export_directory",
        str(export),
    )

    cands = [
        PrefetchCandidate(
            source_id="already",
            url="https://archive.org/details/already",
            title="Already",
            description=None,
            duration_seconds=60,
            channel_number="1",
        ),
        PrefetchCandidate(
            source_id="need-me",
            url="https://archive.org/details/need-me",
            title="Need Me",
            description=None,
            duration_seconds=120,
            channel_number="1",
        ),
    ]
    monkeypatch.setattr(
        "streamtv.exporters.tunarr_prefetch.select_prefetch_candidates",
        lambda *a, **k: cands,
    )
    monkeypatch.setattr(
        "streamtv.exporters.tunarr_prefetch._terminal_cached_failure",
        lambda db, sid: None,
    )
    monkeypatch.setattr(
        "streamtv.exporters.tunarr_prefetch._ready_cache_path",
        lambda db, sid: None,
    )

    results = run_prefetch(MagicMock(), dry_run=True, export_directory=str(export))
    by_id = {r.source_id: r for r in results}
    assert by_id["already"].status == "skipped"
    assert by_id["already"].detail == "already in export"
    assert by_id["need-me"].status == "dry_run"
    assert "Need Me" in (by_id["need-me"].detail or "")


def test_skip_sticky_terminal_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = tmp_path / "cache"
    export = tmp_path / "library"
    cache.mkdir()
    export.mkdir()

    monkeypatch.setattr(
        "streamtv.exporters.tunarr_prefetch.config.cache.cache_directory",
        str(cache),
    )
    monkeypatch.setattr(
        "streamtv.exporters.tunarr_prefetch.config.tunarr_library",
        SimpleNamespace(
            export_directory=str(export),
            naming="source_id",
            prefetch_hours=6,
            prefetch_max_items=5,
            prefetch_max_gb=20,
            channel_numbers=[],
        ),
    )
    monkeypatch.setattr(
        "streamtv.exporters.tunarr_library.config.cache.cache_directory",
        str(cache),
    )

    cands = [
        PrefetchCandidate(
            source_id="dead",
            url="https://archive.org/details/dead",
            title="Dead",
            description=None,
            duration_seconds=60,
            channel_number="1",
        ),
    ]
    monkeypatch.setattr(
        "streamtv.exporters.tunarr_prefetch.select_prefetch_candidates",
        lambda *a, **k: cands,
    )
    monkeypatch.setattr(
        "streamtv.exporters.tunarr_prefetch._terminal_cached_failure",
        lambda db, sid: "unavailable",
    )

    results = run_prefetch(MagicMock(), dry_run=True, export_directory=str(export))
    assert len(results) == 1
    assert results[0].status == "skipped"
    assert "unavailable" in (results[0].detail or "")
