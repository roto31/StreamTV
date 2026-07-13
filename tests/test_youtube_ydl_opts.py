"""Tests for shared YouTube yt-dlp option builder (EJS/Deno wiring)."""

from __future__ import annotations

from streamtv.ffmpeg.constants import YOUTUBE_EXTRACTOR_ARGS
from streamtv.youtube.ydl_opts import youtube_ydl_opts


def test_youtube_ydl_opts_always_includes_extractor_args() -> None:
    opts = youtube_ydl_opts(quiet=True)
    assert opts["extractor_args"] == YOUTUBE_EXTRACTOR_ARGS


def test_youtube_ydl_opts_merges_overrides() -> None:
    opts = youtube_ydl_opts(quiet=True, skip_download=True, socket_timeout=20)
    assert opts["quiet"] is True
    assert opts["skip_download"] is True
    assert opts["socket_timeout"] == 20
    assert "extractor_args" in opts


def test_youtube_ydl_opts_includes_ejs_from_config(monkeypatch: pytest.MonkeyPatch) -> None:
    from streamtv.config import config

    monkeypatch.setattr(config.youtube, "remote_components", "ejs:github")
    monkeypatch.setattr(config.youtube, "js_runtime", "deno:/opt/homebrew/bin/deno")
    opts = youtube_ydl_opts()
    assert "remote_components" in opts
    assert "ejs:github" in opts["remote_components"]
    assert "js_runtimes" in opts
    assert "deno" in opts["js_runtimes"]
