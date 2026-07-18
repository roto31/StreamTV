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
    assert updated.pbs_exclude_passport_drm is True
    assert updated.channel.playout_mode == "continuous"


def test_auth_status_defaults() -> None:
    status = auth_status()
    assert "archive_org" in status
    assert "youtube" in status
    assert "pbs" in status
    assert "plex" in status
    assert isinstance(status["youtube"]["configured"], bool)


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
