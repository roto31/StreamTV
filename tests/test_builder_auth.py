"""Tests for Channel Builder authentication helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from streamtv.builder.auth_service import auth_status
from streamtv.builder.cookie_io import (
    cookies_path_for_scope,
    import_pbs_cookies_from_downloads,
    write_netscape_cookies,
)
from streamtv.builder.models import BuilderDraft, ChannelInfo
from streamtv.builder.pbs_defaults import apply_pbs_source_defaults
from streamtv.builder.playwright_auth import PLAYWRIGHT_INSTALL_HINT, PlaywrightAuthError


def test_cookies_path_for_scope() -> None:
    assert cookies_path_for_scope("youtube") == Path("data/cookies/youtube_cookies.txt")
    assert cookies_path_for_scope("custom_site") == Path("data/cookies/custom_site_cookies.txt")


def test_write_netscape_cookies(tmp_path: Path) -> None:
    path = tmp_path / "cookies.txt"
    write_netscape_cookies(
        path,
        [
            {
                "domain": ".pbs.org",
                "path": "/",
                "secure": True,
                "expires": 9999999999,
                "name": "session",
                "value": "abc",
            }
        ],
    )
    text = path.read_text(encoding="utf-8")
    assert "Netscape HTTP Cookie File" in text
    assert "session" in text


def test_import_pbs_cookies_from_downloads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    src = tmp_path / "downloads" / "cookies.txt"
    src.parent.mkdir(parents=True)
    src.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
    dest = tmp_path / "pbs_cookies.txt"
    out = import_pbs_cookies_from_downloads(source=src, dest=dest, backup=False)
    assert out == dest
    assert dest.read_text(encoding="utf-8").startswith("# Netscape")


def test_apply_pbs_source_defaults() -> None:
    draft = BuilderDraft(channel=ChannelInfo(number="2319", name="Nature"))
    updated = apply_pbs_source_defaults(draft)
    assert updated.pbs_filter_full_episodes is True
    assert updated.pbs_min_episode_seconds == 300
    assert updated.channel.playout_mode == "continuous"


def test_auth_status_defaults() -> None:
    status = auth_status()
    assert "archive_org" in status
    assert "youtube" in status
    assert "pbs" in status
    assert "plex" in status
    assert "tvdb" in status
    assert "tvmaze" in status
    assert isinstance(status["youtube"]["configured"], bool)
    assert isinstance(status["tvdb"]["configured"], bool)
    assert isinstance(status["tvmaze"]["configured"], bool)


def test_apply_tvdb_api_key_rejects_empty() -> None:
    from streamtv.builder.auth_service import apply_tvdb_api_key

    with pytest.raises(ValueError, match="required"):
        apply_tvdb_api_key("  ")


def test_apply_tvdb_api_key_persists(monkeypatch: pytest.MonkeyPatch) -> None:
    from streamtv.builder import auth_service

    seen: dict = {}

    def _update(section: str, values: dict) -> None:
        seen["section"] = section
        seen["values"] = values

    monkeypatch.setattr(auth_service.config, "update_section", _update)
    out = auth_service.apply_tvdb_api_key("test-key-abc")
    assert out["scope"] == "tvdb"
    assert seen["section"] == "metadata"
    assert seen["values"]["tvdb_api_key"] == "test-key-abc"
    assert seen["values"]["enabled"] is True
    assert seen["values"]["enable_tvdb"] is True


def test_apply_tvmaze_credentials_persists(monkeypatch: pytest.MonkeyPatch) -> None:
    from streamtv.builder import auth_service

    seen: dict = {}

    def _update(section: str, values: dict) -> None:
        seen["section"] = section
        seen["values"] = values

    monkeypatch.setattr(auth_service.config, "update_section", _update)
    out = auth_service.apply_tvmaze_credentials("demo_user", "demo-key")
    assert out["scope"] == "tvmaze"
    assert seen["section"] == "metadata"
    assert seen["values"]["tvmaze_username"] == "demo_user"
    assert seen["values"]["tvmaze_api_key"] == "demo-key"
    assert seen["values"]["enable_tvmaze"] is True


def test_apply_tvmaze_credentials_rejects_incomplete() -> None:
    from streamtv.builder.auth_service import apply_tvmaze_credentials

    with pytest.raises(ValueError, match="username"):
        apply_tvmaze_credentials("", "key")
    with pytest.raises(ValueError, match="API key"):
        apply_tvmaze_credentials("user", "  ")


def test_series_provider_flags() -> None:
    from streamtv.builder.enrichment import series_provider_flags

    assert series_provider_flags("tvmaze") == (False, True)
    assert series_provider_flags("tvdb") == (True, False)
    assert series_provider_flags("both") == (True, True)
    assert series_provider_flags(None) == (False, True)


def test_providers_ready_for_series_matrix(monkeypatch: pytest.MonkeyPatch) -> None:
    from streamtv.builder import enrichment as enrich_mod
    from streamtv.config import config

    monkeypatch.setattr(config.metadata, "enabled", True)
    monkeypatch.setattr(config.metadata, "tvdb_api_key", None)
    monkeypatch.setattr(config.metadata, "tvdb_read_token", None)
    monkeypatch.setattr(config.metadata, "enable_tvdb", True)
    monkeypatch.setattr(config.metadata, "enable_tvmaze", True)

    ok, reason = enrich_mod.providers_ready_for("series", enable_tvdb=True, enable_tvmaze=False)
    assert ok is False
    assert reason and "TVDB" in reason

    ok, reason = enrich_mod.providers_ready_for("series", enable_tvdb=False, enable_tvmaze=True)
    assert ok is True
    assert reason is None

    ok, reason = enrich_mod.providers_ready_for("series", enable_tvdb=True, enable_tvmaze=True)
    assert ok is True
    assert reason is None

    ok, reason = enrich_mod.providers_ready_for("series", enable_tvdb=False, enable_tvmaze=False)
    assert ok is False
    assert reason and "provider" in reason.lower()

    monkeypatch.setattr(config.metadata, "tvdb_api_key", "fake-tvdb-key")
    ok, reason = enrich_mod.providers_ready_for("series", enable_tvdb=True, enable_tvmaze=False)
    assert ok is True
    assert reason is None


def test_providers_ready_for_disabled_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    from streamtv.builder.enrichment import providers_ready_for
    from streamtv.config import config

    monkeypatch.setattr(config.metadata, "enabled", False)
    ok, reason = providers_ready_for("series")
    assert ok is False
    assert reason and "disabled" in reason.lower()


def test_providers_ready_for_movie_needs_tmdb(monkeypatch: pytest.MonkeyPatch) -> None:
    from streamtv.builder.enrichment import providers_ready_for
    from streamtv.config import config

    monkeypatch.setattr(config.metadata, "enabled", True)
    monkeypatch.setattr(config.metadata, "enable_tmdb", True)
    monkeypatch.setattr(config.metadata, "tmdb_api_key", None)
    ok, reason = providers_ready_for("movie")
    assert ok is False
    assert reason and "TMDB" in reason

    monkeypatch.setattr(config.metadata, "tmdb_api_key", "fake-tmdb")
    ok, reason = providers_ready_for("movie")
    assert ok is True
    assert reason is None


@pytest.mark.asyncio
async def test_capture_cookies_youtube_playwright_error() -> None:
    from streamtv.builder import playwright_auth

    with patch.object(
        playwright_auth,
        "_run_login",
        new=AsyncMock(side_effect=PlaywrightAuthError(PLAYWRIGHT_INSTALL_HINT)),
    ):
        with pytest.raises(PlaywrightAuthError, match="Playwright is required"):
            await playwright_auth.capture_cookies_youtube("a@b.com", "secret")


@pytest.mark.asyncio
async def test_capture_cookies_youtube_success(tmp_path: Path) -> None:
    from streamtv.builder import playwright_auth

    fake_path = tmp_path / "youtube_cookies.txt"
    with patch.object(playwright_auth, "cookies_path_for_scope", return_value=fake_path):
        with patch.object(
            playwright_auth,
            "_run_login",
            new=AsyncMock(return_value=[{"domain": ".youtube.com", "name": "SID", "value": "x"}]),
        ):
            path = await playwright_auth.capture_cookies_youtube("a@b.com", "secret")
            assert path == fake_path
            assert fake_path.exists()
