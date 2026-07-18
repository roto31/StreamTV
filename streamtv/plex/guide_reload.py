"""Trigger Plex reloadGuide when StreamTV playout lags the wall-clock EPG."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import time as _time
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_reload_lock = asyncio.Lock()
_reload_done = False
_last_reload_at: Optional[float] = None
_last_boundary_reload_by_channel: Dict[str, float] = {}

# #region agent log
_DEBUG_LOG_PATH = "/home/streamtv/XCode Projects/StreamTV/.cursor/debug-247576.log"


def _agent_dbg_log(
    hypothesis_id: str,
    location: str,
    message: str,
    data: dict,
    *,
    run_id: str = "post-fix",
) -> None:
    try:
        payload = {
            "sessionId": "247576",
            "runId": run_id,
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(_time.time() * 1000),
        }
        with open(_DEBUG_LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, default=str) + "\n")
    except Exception:
        pass


# #endregion


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


def _configured_dvr_id() -> Optional[str]:
    from streamtv.config import config

    if config.plex.dvr_id:
        return str(config.plex.dvr_id)
    env_id = os.getenv("PLEX_DVR_ID")
    if env_id:
        return str(env_id)
    return None


def _dvr_prefers_streamtv(lineup: str, lineup_title: str) -> bool:
    blob = f"{lineup} {lineup_title}".lower()
    return "xmltv" in blob or "streamtv" in blob or ":8410" in blob


async def _list_dvr_candidates(base_url: str, token: str) -> List[Tuple[str, str, str]]:
    """Return (dvr_id, lineup, lineup_title), StreamTV XMLTV lineups first."""
    import httpx

    url = f"{base_url.rstrip('/')}/livetv/dvrs"
    headers = {"X-Plex-Token": token, "Accept": "application/xml"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            root = ET.fromstring(response.text)
    except Exception as exc:
        logger.warning("Plex DVR list failed: %s", exc)
        return []

    rows: List[Tuple[str, str, str, int]] = []
    for dvr_elem in root.findall(".//Dvr"):
        dvr_id = (dvr_elem.get("key") or "").strip()
        if not dvr_id:
            continue
        lineup = dvr_elem.get("lineup") or ""
        lineup_title = dvr_elem.get("lineupTitle") or dvr_elem.get("title") or ""
        rank = 0 if _dvr_prefers_streamtv(lineup, lineup_title) else 1
        rows.append((dvr_id, lineup, lineup_title, rank))
    rows.sort(key=lambda r: (r[3], r[0]))
    return [(r[0], r[1], r[2]) for r in rows]


async def _resolve_dvr_id(client) -> Optional[str]:
    """Prefer configured DVR id; else discover StreamTV XMLTV DVR."""
    configured = _configured_dvr_id()
    if configured:
        return configured

    base_url = _resolve_plex_base_url()
    token = _resolve_plex_token()
    if base_url and token:
        discovered = await _list_dvr_candidates(base_url, token)
        if discovered:
            return discovered[0][0]

    dvrs = await client.get_dvrs()
    for dvr in dvrs:
        if dvr.get("enabled") and dvr.get("id"):
            return str(dvr["id"])
    if dvrs and dvrs[0].get("id"):
        return str(dvrs[0]["id"])
    return None


async def _post_reload_guide(*, reason: str, channel_number: str = "") -> bool:
    from streamtv.config import config

    if not config.plex.enabled or not config.plex.auto_reload_guide:
        return False
    base_url = _resolve_plex_base_url()
    token = _resolve_plex_token()
    if not base_url or not token:
        logger.debug("Plex guide reload skipped (%s): missing base_url or token", reason)
        return False

    from streamtv.streaming.plex_api_client import PlexAPIClient

    try:
        async with PlexAPIClient(base_url, token) as client:
            primary = await _resolve_dvr_id(client)
            candidates: List[str] = []
            if primary:
                candidates.append(primary)
            for dvr_id, _lineup, _title in await _list_dvr_candidates(base_url, token):
                if dvr_id not in candidates:
                    candidates.append(dvr_id)

            if not candidates:
                logger.warning("Plex guide reload skipped: no DVR id")
                # #region agent log
                _agent_dbg_log(
                    "H-dvr",
                    "guide_reload.py:_post_reload_guide",
                    "no DVR candidates",
                    {"reason": reason, "channel": channel_number, "base_url": base_url},
                )
                # #endregion
                return False

            for dvr_id in candidates:
                ok = await client.reload_dvr_guide(dvr_id)
                if ok:
                    if primary and dvr_id != primary:
                        logger.warning(
                            "Plex reloadGuide: configured DVR %s failed; fell back to %s (%s)",
                            primary,
                            dvr_id,
                            reason,
                        )
                    # #region agent log
                    _agent_dbg_log(
                        "H-dvr",
                        "guide_reload.py:_post_reload_guide",
                        "reloadGuide succeeded",
                        {
                            "reason": reason,
                            "channel": channel_number,
                            "dvr_id": dvr_id,
                            "configured": primary,
                            "fallback": bool(primary and dvr_id != primary),
                            "candidates": candidates,
                        },
                    )
                    # #endregion
                    if channel_number:
                        logger.info(
                            "Channel %s: Plex reloadGuide triggered (%s)",
                            channel_number,
                            reason,
                        )
                    else:
                        logger.info("Plex reloadGuide succeeded (%s)", reason)
                    return True

            # #region agent log
            _agent_dbg_log(
                "H-dvr",
                "guide_reload.py:_post_reload_guide",
                "reloadGuide failed all candidates",
                {
                    "reason": reason,
                    "channel": channel_number,
                    "candidates": candidates,
                    "configured": primary,
                },
            )
            # #endregion
            logger.warning(
                "Plex guide reload failed (%s): all DVR candidates exhausted %s",
                reason,
                candidates,
            )
            return False
    except Exception as exc:
        logger.warning("Plex guide reload failed (%s): %s", reason, exc)
        return False


async def maybe_reload_plex_guide_on_lag(
    *,
    lag_items: int,
    channel_number: str,
    wall_index: int,
    air_index: int,
    min_lag: int = 1,
) -> None:
    """Ask Plex to reload guide when playout lags wall-clock (global cooldown)."""
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

    cooldown_s = int(getattr(config.plex, "global_reload_cooldown_s", 900) or 900)
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

    await _post_reload_guide(
        reason=f"lag {lag_items} items: air {air_index}, wall {wall_index}",
        channel_number=channel_number,
    )


async def maybe_reload_plex_guide_on_item_boundary(
    *,
    channel_number: str,
    air_index: int,
    guide_index: int,
) -> None:
    """Reload Plex guide on playout item boundary (per-channel cooldown)."""
    from streamtv.config import config

    if guide_index <= air_index:
        return
    if not config.plex.enabled or not config.plex.auto_reload_guide:
        return
    if not config.plex.reload_on_item_boundary:
        return
    if not _resolve_plex_token():
        return

    cooldown_s = int(getattr(config.plex, "item_boundary_cooldown_s", 90) or 90)
    ch_key = str(channel_number)
    now = _time.time()
    last = _last_boundary_reload_by_channel.get(ch_key)
    if last and (now - last) < cooldown_s:
        logger.debug(
            "Plex boundary reload skipped (cooldown %ss): channel %s",
            cooldown_s,
            channel_number,
        )
        return

    async with _reload_lock:
        last = _last_boundary_reload_by_channel.get(ch_key)
        if last and (_time.time() - last) < cooldown_s:
            return
        _last_boundary_reload_by_channel[ch_key] = _time.time()
        global _last_reload_at
        _last_reload_at = _time.time()

    await _post_reload_guide(
        reason=f"item boundary air {air_index}, guide {guide_index}",
        channel_number=channel_number,
    )


async def force_plex_guide_reload(*, reason: str = "manual") -> bool:
    """POST Plex reloadGuide (startup, operator script, or lag recovery)."""
    from streamtv.config import config

    if not config.plex.enabled or not config.plex.auto_reload_guide:
        return False
    if not _resolve_plex_base_url() or not _resolve_plex_token():
        logger.debug("Plex guide reload skipped (%s): missing base_url or token", reason)
        return False

    global _last_reload_at
    async with _reload_lock:
        now = _time.time()
        if _last_reload_at and (now - _last_reload_at) < 60:
            return False
        _last_reload_at = now

    return await _post_reload_guide(reason=reason)


def schedule_startup_plex_guide_reload() -> None:
    """After StreamTV boot, ask Plex to re-fetch merged XMLTV (Plex caches across restarts)."""

    async def _run() -> None:
        await asyncio.sleep(45)
        await force_plex_guide_reload(reason="startup")

    try:
        asyncio.create_task(_run())
    except RuntimeError:
        pass
