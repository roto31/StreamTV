"""Tests for Tunarr library export isolation and hardlink/copy."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from streamtv.exporters.tunarr_library import (
    assert_export_outside_cache,
    export_ready_archive_org,
    _movie_nfo,
)


def test_assert_export_outside_cache_rejects_nested(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    cache.mkdir()
    nested = cache / "export"
    nested.mkdir()
    with pytest.raises(ValueError, match="must not be inside"):
        assert_export_outside_cache(nested, cache_dir=cache)


def test_assert_export_outside_cache_allows_sibling(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    export = tmp_path / "library"
    cache.mkdir()
    export.mkdir()
    assert_export_outside_cache(export, cache_dir=cache)


def test_movie_nfo_escapes() -> None:
    text = _movie_nfo('A & B <C>', 'plot "x"')
    assert "<title>A &amp; B &lt;C&gt;</title>" in text
    assert "<movie>" in text


def test_export_dry_run_lists_ready_mp4(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = tmp_path / "cache"
    export = tmp_path / "library"
    cache.mkdir()
    export.mkdir()
    src = cache / "archive_org" / "item1.mp4"
    src.parent.mkdir(parents=True)
    src.write_bytes(b"fake-mp4")

    monkeypatch.setattr(
        "streamtv.exporters.tunarr_library.config.cache.cache_directory",
        str(cache),
    )
    monkeypatch.setattr(
        "streamtv.exporters.tunarr_library.config.tunarr_library.export_directory",
        str(export),
    )
    monkeypatch.setattr(
        "streamtv.exporters.tunarr_library.config.tunarr_library.naming",
        "source_id",
    )

    row = MagicMock()
    row.source_id = "item1"
    row.local_path = str(src)
    row.media_item_id = None
    row.status = "ready"

    media = None
    db = MagicMock()

    def fake_iter(db_arg, source_ids=None):
        return [(row, media)]

    monkeypatch.setattr(
        "streamtv.exporters.tunarr_library.iter_ready_archive_rows",
        fake_iter,
    )

    results = export_ready_archive_org(db, dry_run=True, export_directory=str(export))
    assert len(results) == 1
    assert results[0].status == "dry_run"
    assert "item1.mp4" in (results[0].dest or "")

    results_apply = export_ready_archive_org(
        db, dry_run=False, export_directory=str(export)
    )
    assert results_apply[0].status in {"linked", "copied"}
    dest = Path(results_apply[0].dest or "")
    assert dest.is_file()
    assert dest.with_suffix(".nfo").is_file()
