"""Playback buffer wait caps for Plex tuner sessions."""

from __future__ import annotations

import pytest

from streamtv.cache.playback_buffer import resolve_buffer_max_wait_seconds


def test_youtube_full_cache_uses_short_wait_when_tuner_connected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from streamtv import config as cfg

    monkeypatch.setattr(cfg.config.cache, "tune_buffer_max_wait_seconds", 5.0)
    monkeypatch.setattr(cfg.config.cache, "youtube_cache_wait_seconds", 120.0)
    assert resolve_buffer_max_wait_seconds(on_tune=True, yt_full=True) == 5.0


def test_youtube_full_cache_uses_long_wait_for_background_playout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from streamtv import config as cfg

    monkeypatch.setattr(cfg.config.cache, "tune_buffer_max_wait_seconds", 5.0)
    monkeypatch.setattr(cfg.config.cache, "youtube_cache_wait_seconds", 120.0)
    assert resolve_buffer_max_wait_seconds(on_tune=False, yt_full=True) == 120.0


def test_non_youtube_tune_uses_tune_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from streamtv import config as cfg

    monkeypatch.setattr(cfg.config.cache, "tune_buffer_max_wait_seconds", 8.0)
    assert resolve_buffer_max_wait_seconds(on_tune=True, yt_full=False) == 8.0
