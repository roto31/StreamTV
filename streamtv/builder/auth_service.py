"""Persist Builder authentication without storing passwords."""

from __future__ import annotations

import logging
import platform
from pathlib import Path
from typing import Optional

from streamtv.config import config
from streamtv.streaming.stream_manager import StreamManager

logger = logging.getLogger(__name__)


def apply_youtube_cookies(path: Path) -> None:
    config.update_section(
        "youtube",
        {
            "cookies_file": str(path.absolute()),
            "use_authentication": True,
        },
    )
    manager = StreamManager()
    if manager.youtube_adapter:
        manager.youtube_adapter.cookies_file = str(path.absolute())
        manager.youtube_adapter._ydl_opts["cookiefile"] = str(path.absolute())


def apply_pbs_cookies(path: Path) -> None:
    config.update_section(
        "pbs",
        {
            "cookies_file": str(path.absolute()),
            "use_authentication": True,
        },
    )
    manager = StreamManager()
    if manager.pbs_adapter:
        manager.pbs_adapter.cookies_file = str(path.absolute())
        manager.pbs_adapter._load_cookies_from_file()


def apply_archive_credentials(username: str, password: str) -> dict:
    if platform.system() == "Darwin":
        from streamtv.utils.macos_credentials import store_credentials_in_keychain

        store_credentials_in_keychain("archive.org", username, password)
    config.update_section(
        "archive_org",
        {
            "username": username,
            "password": None,
            "use_authentication": True,
        },
    )
    manager = StreamManager()
    manager.update_archive_org_credentials(username, password)
    return {"status": "success", "scope": "archive_org"}


def apply_plex_credentials(base_url: str, token: str) -> dict:
    config.update_section(
        "plex",
        {
            "enabled": True,
            "base_url": base_url.rstrip("/"),
            "token": token,
            "use_for_epg": config.plex.use_for_epg,
        },
    )
    manager = StreamManager()
    if manager.plex_adapter:
        manager.plex_adapter.base_url = base_url.rstrip("/")
        manager.plex_adapter.token = token
    return {"status": "success", "scope": "plex"}


def apply_tvdb_api_key(api_key: str) -> dict:
    """Persist TVDB API key for Builder / CLI metadata enrichment. Never log the key."""
    key = (api_key or "").strip()
    if not key:
        raise ValueError("TVDB API key is required")
    config.update_section(
        "metadata",
        {
            "enabled": True,
            "enable_tvdb": True,
            "tvdb_api_key": key,
        },
    )
    return {"status": "success", "scope": "tvdb"}


def apply_tvmaze_credentials(username: str, api_key: str) -> dict:
    """Persist TVMaze username + dashboard API key (HTTP Basic). Never log the key."""
    user = (username or "").strip()
    key = (api_key or "").strip()
    if not user:
        raise ValueError("TVMaze username is required")
    if not key:
        raise ValueError("TVMaze API key is required")
    config.update_section(
        "metadata",
        {
            "enabled": True,
            "enable_tvmaze": True,
            "tvmaze_username": user,
            "tvmaze_api_key": key,
        },
    )
    return {"status": "success", "scope": "tvmaze"}


def auth_status() -> dict[str, dict]:
    archive_cookies = Path("data/cookies/archive_cookies.txt").exists()
    archive_keychain = bool(config.archive_org.use_authentication and config.archive_org.username)
    youtube_ok = bool(config.youtube.cookies_file) or Path("data/cookies/youtube_cookies.txt").exists()
    pbs_ok = bool(getattr(config, "pbs", None) and config.pbs.cookies_file) or Path(
        "data/cookies/pbs_cookies.txt"
    ).exists()
    plex_ok = bool(config.plex.enabled and config.plex.base_url and config.plex.token)
    tvdb_ok = bool(config.metadata.tvdb_api_key or config.metadata.tvdb_read_token)
    tvmaze_ok = bool(config.metadata.tvmaze_api_key and config.metadata.tvmaze_username)
    return {
        "archive_org": {
            "configured": archive_cookies or archive_keychain,
            "method": "cookies" if archive_cookies else ("keychain" if archive_keychain else None),
        },
        "youtube": {
            "configured": youtube_ok,
            "method": "cookies" if youtube_ok else None,
        },
        "pbs": {
            "configured": pbs_ok,
            "method": "cookies" if pbs_ok else None,
        },
        "plex": {
            "configured": plex_ok,
            "method": "token" if plex_ok else None,
        },
        "tvdb": {
            "configured": tvdb_ok,
            "method": "api_key" if config.metadata.tvdb_api_key else ("read_token" if tvdb_ok else None),
        },
        "tvmaze": {
            "configured": tvmaze_ok,
            "method": "basic_auth" if tvmaze_ok else None,
        },
    }


def scope_configured(scope: str) -> bool:
    return bool(auth_status().get(scope, {}).get("configured"))
