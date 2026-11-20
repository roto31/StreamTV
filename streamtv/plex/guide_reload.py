"""Trigger Plex reloadGuide when StreamTV playout lags the wall-clock EPG."""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import time as _time
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_reload_lock = asyncio.Lock()
_reload_done = False
_last_reload_at: Optional[float] = None
_last_boundary_reload_by_channel: Dict[str, float] = {}


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


def normalize_dvr_id(raw: Optional[str]) -> Optional[str]:
    """Normalize Plex DVR id from ratingKey or /livetv/dvrs/{id} key path."""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    if "/" in text:
        text = text.rstrip("/").split("/")[-1]
    return text or None


def _prefer_streamtv_dvr(dvrs: List[Dict]) -> List[str]:
    """Order discovered DVR ids: StreamTV-titled first, then enabled, then rest."""
    scored: List[tuple[int, str]] = []
    for dvr in dvrs:
        nid = normalize_dvr_id(dvr.get("id") or dvr.get("ratingKey") or dvr.get("key"))
        if not nid:
            continue
        title = str(dvr.get("title") or "").lower()
        enabled = bool(dvr.get("enabled"))
        score = 0
        if "streamtv" in title or "stream tv" in title:
            score += 20
        if enabled:
            score += 10
        scored.append((score, nid))
    scored.sort(key=lambda item: (-item[0], item[1]))
    ordered: List[str] = []
    for _, nid in scored:
        if nid not in ordered:
            ordered.append(nid)
    return ordered


async def _candidate_dvr_ids(client) -> List[str]:
    """Config/env first, then live PMS discovery (Plex DVR ids rotate on re-add)."""
    from streamtv.config import config

    candidates: List[str] = []
    for raw in (getattr(config.plex, "dvr_id", None), os.getenv("PLEX_DVR_ID")):
        nid = normalize_dvr_id(raw if raw is None else str(raw))
        if nid and nid not in candidates:
            candidates.append(nid)

    try:
        dvrs = await client.get_dvrs()
    except Exception as exc:
        logger.warning("Plex get_dvrs failed during DVR resolve: %s", exc)
        dvrs = []

    for nid in _prefer_streamtv_dvr(dvrs or []):
        if nid not in candidates:
            candidates.append(nid)
    return candidates


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
            candidates = await _candidate_dvr_ids(client)
            if not candidates:
                logger.warning("Plex guide reload skipped: no DVR id candidates")
                return False

            preferred = normalize_dvr_id(
                str(getattr(config.plex, "dvr_id", "") or "")
            ) or normalize_dvr_id(os.getenv("PLEX_DVR_ID"))

            for dvr_id in candidates:
                ok = await client.reload_dvr_guide(dvr_id)
                if not ok:
                    continue
                if preferred and dvr_id != preferred:
                    logger.warning(
                        "Plex reloadGuide: configured/env DVR id %s failed; "
                        "succeeded with live DVR %s — update config.plex.dvr_id "
                        "and PLEX_DVR_ID / epg-health LaunchAgent",
                        preferred,
                        dvr_id,
                    )
                if channel_number:
                    logger.info(
                        "Channel %s: Plex reloadGuide triggered (%s) dvr=%s",
                        channel_number,
                        reason,
                        dvr_id,
                    )
                else:
                    logger.info(
                        "Plex reloadGuide succeeded (%s) dvr=%s", reason, dvr_id
                    )
                return True

            logger.warning(
                "Plex guide reload failed (%s): tried DVR ids %s",
                reason,
                ",".join(candidates),
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
