"""Trigger Plex reloadGuide when StreamTV playout lags the wall-clock EPG."""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)

_reload_lock = asyncio.Lock()
_reload_done = False
_last_reload_at: Optional[float] = None


def _resolve_plex_base_url() -> Optional[str]:
    from streamtv.config import config

    host = os.getenv("PLEX_HOST")
    port = os.getenv("PLEX_PORT", "32400")
    if host:
        return f"http://{host}:{port}"
    if config.plex.base_url:
        return config.plex.base_url.rstrip("/")
    return None


def _resolve_plex_token() -> Optional[str]:
    from streamtv.config import config

    if config.plex.token:
        return config.plex.token
    env_token = os.getenv("STREAMTV_PLEX_TOKEN") or os.getenv("PLEX_TOKEN")
    if env_token:
        return env_token
    try:
        out = subprocess.run(
            [
                "plutil",
                "-extract",
                "PlexOnlineToken",
                "raw",
                os.path.expanduser("~/Library/Preferences/com.plexapp.plexmediaserver.plist"),
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        token = (out.stdout or "").strip()
        return token or None
    except Exception:
        return None


async def _resolve_dvr_id(client) -> Optional[str]:
    from streamtv.config import config

    if config.plex.dvr_id:
        return str(config.plex.dvr_id)
    env_id = os.getenv("PLEX_DVR_ID")
    if env_id:
        return env_id
    dvrs = await client.get_dvrs()
    for dvr in dvrs:
        if dvr.get("enabled") and dvr.get("id"):
            return str(dvr["id"])
    if dvrs and dvrs[0].get("id"):
        return str(dvrs[0]["id"])
    return None


async def maybe_reload_plex_guide_on_lag(
    *,
    lag_items: int,
    channel_number: str,
    wall_index: int,
    air_index: int,
    min_lag: int = 1,
) -> None:
    """Ask Plex to reload guide when playout lags wall-clock (cooldown between calls)."""
    global _reload_done
    from streamtv.config import config

    if lag_items < min_lag:
        return
    if not config.plex.enabled:
        return
    base_url = _resolve_plex_base_url()
    if not base_url:
        return
    if not config.plex.auto_reload_guide:
        return
    token = _resolve_plex_token()
    if not token:
        logger.debug("Plex guide reload skipped: no token")
        return

    import time as _time

    cooldown_s = 900  # 15 min — avoid hammering Plex during slow guide rebuilds
    async with _reload_lock:
        global _last_reload_at
        now = _time.time()
        if _last_reload_at and (now - _last_reload_at) < cooldown_s:
            logger.debug(
                "Plex guide reload skipped (cooldown): channel %s lag %s",
                channel_number,
                lag_items,
            )
            return
        _last_reload_at = now

    from streamtv.streaming.plex_api_client import PlexAPIClient

    try:
        async with PlexAPIClient(base_url, token) as client:
            dvr_id = await _resolve_dvr_id(client)
            if not dvr_id:
                logger.warning("Plex guide reload skipped: no DVR id")
                return
            ok = await client.reload_dvr_guide(dvr_id)
            if ok:
                logger.info(
                    "Channel %s: Plex reloadGuide triggered (lag %s items: air %s, wall %s)",
                    channel_number,
                    lag_items,
                    air_index,
                    wall_index,
                )
    except Exception as exc:
        logger.warning("Plex guide reload failed: %s", exc)


async def force_plex_guide_reload(*, reason: str = "manual") -> bool:
    """POST Plex reloadGuide (startup, operator script, or lag recovery)."""
    from streamtv.config import config

    if not config.plex.enabled or not config.plex.auto_reload_guide:
        return False
    base_url = _resolve_plex_base_url()
    token = _resolve_plex_token()
    if not base_url or not token:
        logger.debug("Plex guide reload skipped (%s): missing base_url or token", reason)
        return False

    import time as _time

    global _last_reload_at
    async with _reload_lock:
        now = _time.time()
        if _last_reload_at and (now - _last_reload_at) < 60:
            return False
        _last_reload_at = now

    from streamtv.streaming.plex_api_client import PlexAPIClient

    try:
        async with PlexAPIClient(base_url, token) as client:
            dvr_id = await _resolve_dvr_id(client)
            if not dvr_id:
                return False
            ok = await client.reload_dvr_guide(dvr_id)
            if ok:
                logger.info("Plex reloadGuide succeeded (%s)", reason)
            return ok
    except Exception as exc:
        logger.warning("Plex guide reload failed (%s): %s", reason, exc)
        return False


def schedule_startup_plex_guide_reload() -> None:
    """After StreamTV boot, ask Plex to re-fetch merged XMLTV (Plex caches across restarts)."""

    async def _run() -> None:
        await asyncio.sleep(45)
        await force_plex_guide_reload(reason="startup")

    try:
        asyncio.create_task(_run())
    except RuntimeError:
        pass
