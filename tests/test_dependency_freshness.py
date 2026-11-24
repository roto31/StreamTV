"""Unit tests for core dependency freshness (Issue 73)."""

from __future__ import annotations

from streamtv.ffmpeg.constants import YOUTUBE_PLAYER_CLIENTS, YTDLP_MIN_VERSION
from streamtv.utils import dependency_freshness as df


def test_calver_older() -> None:
    assert df._version_older("2026.07.04", "2026.08.19") is True
    assert df._version_older("2026.08.19", "2026.08.19") is False
    assert df._version_older("2026.11.23", "2026.08.19") is False


def test_player_clients_have_no_banned() -> None:
    finding = df.check_youtube_player_clients()
    assert finding.status == "ok", finding.detail
    assert YOUTUBE_PLAYER_CLIENTS[0] == df.PREFERRED_PRIMARY_CLIENT
    banned = set(YOUTUBE_PLAYER_CLIENTS) & df.BANNED_YOUTUBE_PLAYER_CLIENTS
    assert not banned


def test_floor_constant_synced_shape() -> None:
    # CalVer with zero-padded month/day as used in constants.
    assert YTDLP_MIN_VERSION.count(".") == 2
    assert not df._version_older(YTDLP_MIN_VERSION, "2026.08.19")


def test_run_freshness_checks_no_pypi() -> None:
    report = df.run_freshness_checks(check_pypi=False)
    assert report.findings
    components = {f.component for f in report.findings}
    assert "yt-dlp" in components
    assert "youtube-player-clients" in components
    assert report.ok or any(f.status == "fail" for f in report.findings)


def test_ensure_yt_dlp_current_no_upgrade_when_ok(monkeypatch) -> None:
    monkeypatch.setattr(
        df,
        "run_freshness_checks",
        lambda check_pypi=True: df.FreshnessReport(
            findings=[
                df.FreshnessFinding("yt-dlp", "ok", "meets floor"),
                df.FreshnessFinding("yt-dlp-pypi", "ok", "current"),
            ]
        ),
    )
    result = df.ensure_yt_dlp_current(check_pypi=True, upgrade=True)
    assert result["ok"] is True
    assert result["needs_upgrade"] is False
    assert result["upgraded"] is False
