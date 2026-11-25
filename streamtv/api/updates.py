"""In-app Updates API — check GitHub Releases, apply with backup/rollback."""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/updates", tags=["Updates"])

_PUBLIC_REPO = os.environ.get("STREAMTV_PUBLIC_REPO", "roto31/StreamTV")
_CACHE: Dict[str, Any] = {"fetched_at": 0.0, "payload": None}
_CACHE_TTL = 3600.0
_STATE_FILE = Path.home() / "Library" / "Application Support" / "StreamTV" / "update_state.json"
_UPDATE_LOCK = threading.Lock()
_UPDATE_STATE: Dict[str, Any] = {
    "status": "idle",
    "message": "",
    "error": None,
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _app_version() -> str:
    vf = _repo_root() / "VERSION"
    try:
        return vf.read_text(encoding="utf-8").strip() or "0.0.0"
    except OSError:
        return "0.0.0"


def detect_install_mode() -> str:
    cwd = Path.cwd().resolve()
    as_dir = (Path.home() / "Library" / "Application Support" / "StreamTV").resolve()
    if cwd == as_dir or str(cwd).startswith(str(as_dir)):
        return "app"
    # Bundled app Resources often set PYTHONPATH; cwd AS is the signal for .app
    if os.environ.get("STREAMTV_INSTALL_MODE", "").strip().lower() in ("app", "repo"):
        return os.environ["STREAMTV_INSTALL_MODE"].strip().lower()
    return "repo"


def _load_banner_state() -> Dict[str, Any]:
    try:
        if _STATE_FILE.is_file():
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    return {}


def _save_banner_state(data: Dict[str, Any]) -> None:
    try:
        _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _STATE_FILE.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        logger.warning("Could not write update_state: %s", exc)


def _fetch_latest_release() -> Dict[str, Any]:
    now = time.time()
    if _CACHE["payload"] and (now - float(_CACHE["fetched_at"])) < _CACHE_TTL:
        return _CACHE["payload"]  # type: ignore[return-value]

    url = f"https://api.github.com/repos/{_PUBLIC_REPO}/releases/latest"
    req = Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "StreamTV-Updates"})
    try:
        with urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (URLError, HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning("GitHub release fetch failed: %s", exc)
        return {
            "tag_name": None,
            "name": None,
            "body": f"Could not fetch releases: {exc}",
            "html_url": f"https://github.com/{_PUBLIC_REPO}/releases",
            "assets": [],
            "error": str(exc),
        }

    assets = []
    for a in data.get("assets") or []:
        assets.append(
            {
                "name": a.get("name"),
                "browser_download_url": a.get("browser_download_url"),
                "size": a.get("size"),
                "content_type": a.get("content_type"),
            }
        )
    payload = {
        "tag_name": data.get("tag_name"),
        "name": data.get("name"),
        "body": data.get("body") or "",
        "html_url": data.get("html_url"),
        "published_at": data.get("published_at"),
        "assets": assets,
        "error": None,
    }
    _CACHE["fetched_at"] = now
    _CACHE["payload"] = payload
    return payload


def _version_from_tag(tag: Optional[str]) -> Optional[str]:
    if not tag:
        return None
    return tag[1:] if tag.startswith("v") else tag


@router.get("/status", operation_id="updates_status")
async def updates_status() -> Dict[str, Any]:
    current = _app_version()
    latest = _fetch_latest_release()
    latest_ver = _version_from_tag(latest.get("tag_name"))
    update_available = bool(latest_ver and latest_ver != current and not latest.get("error"))
    banner = _load_banner_state()
    with _UPDATE_LOCK:
        job = dict(_UPDATE_STATE)
    return {
        "install_mode": detect_install_mode(),
        "current_version": current,
        "latest_version": latest_ver,
        "latest_tag": latest.get("tag_name"),
        "release_name": latest.get("name"),
        "release_notes": latest.get("body") or "",
        "release_url": latest.get("html_url"),
        "published_at": latest.get("published_at"),
        "update_available": update_available,
        "assets": latest.get("assets") or [],
        "fetch_error": latest.get("error"),
        "banner": banner,
        "job": job,
    }


@router.post("/banner/ack", operation_id="updates_banner_ack")
async def updates_banner_ack() -> Dict[str, Any]:
    state = _load_banner_state()
    state["acked"] = True
    _save_banner_state(state)
    return {"ok": True}


class AgreeApplyBody(BaseModel):
    agree: bool = False


def _run_update_job(mode: str) -> None:
    global _UPDATE_STATE
    root = _repo_root()
    backup_root = (
        Path.home()
        / "Library"
        / "Application Support"
        / "StreamTV"
        / "update-backups"
        / time.strftime("%Y%m%d-%H%M%S")
    )
    try:
        with _UPDATE_LOCK:
            _UPDATE_STATE = {"status": "backing_up", "message": "Creating pre-update backup", "error": None}

        backup_root.mkdir(parents=True, exist_ok=True)
        try:
            from ..backup.snapshot import create_snapshot

            snap = create_snapshot()
            if snap:
                shutil.copy2(snap, backup_root / Path(snap).name)
        except Exception as exc:
            logger.warning("Data snapshot for update: %s", exc)

        # Code tree snapshot (repo mode)
        if mode == "repo":
            code_bak = backup_root / "code"
            code_bak.mkdir(parents=True, exist_ok=True)
            for name in ("VERSION", "requirements.txt", "streamtv"):
                src = root / name
                if src.is_dir():
                    shutil.copytree(src, code_bak / name, dirs_exist_ok=True)
                elif src.is_file():
                    shutil.copy2(src, code_bak / name)

        with _UPDATE_LOCK:
            _UPDATE_STATE = {"status": "applying", "message": "Applying public update", "error": None}

        script = root / "scripts" / "apply_public_update.sh"
        if script.is_file():
            proc = subprocess.run(
                ["bash", str(script), "--mode", mode, "--backup-dir", str(backup_root)],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=600,
                check=False,
            )
            if proc.returncode != 0:
                raise RuntimeError(
                    f"apply_public_update failed ({proc.returncode}): "
                    f"{(proc.stderr or proc.stdout or '')[-2000:]}"
                )
        else:
            # Minimal fallback: pip upgrade from requirements
            pip = root / "venv" / "bin" / "pip"
            if pip.is_file():
                subprocess.run(
                    [str(pip), "install", "-r", str(root / "requirements.txt"), "--upgrade"],
                    cwd=str(root),
                    check=False,
                    timeout=600,
                )

        _save_banner_state(
            {
                "event": "update_restart",
                "acked": False,
                "message": "Update applied — server restarting",
                "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        )

        with _UPDATE_LOCK:
            _UPDATE_STATE = {
                "status": "restarting",
                "message": "Restarting server",
                "error": None,
            }

        # Kickstart LaunchAgent when present
        try:
            uid = os.getuid()
            subprocess.Popen(
                ["launchctl", "kickstart", "-k", f"gui/{uid}/com.streamtv"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as exc:
            logger.warning("kickstart failed: %s", exc)

        _save_banner_state(
            {
                "event": "server_back_up",
                "acked": False,
                "message": "Server is back up after update",
                "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        )
        with _UPDATE_LOCK:
            _UPDATE_STATE = {"status": "done", "message": "Update complete", "error": None}

    except Exception as exc:
        logger.exception("Update failed — attempting rollback note")
        with _UPDATE_LOCK:
            _UPDATE_STATE = {"status": "failed", "message": "Update failed", "error": str(exc)}
        _save_banner_state(
            {
                "event": "update_rolled_back",
                "acked": False,
                "message": f"Update failed: {exc}. Restore from {backup_root}",
                "backup_dir": str(backup_root),
                "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        )


@router.post("/agree-and-apply", operation_id="updates_agree_and_apply")
async def updates_agree_and_apply(body: AgreeApplyBody) -> Dict[str, Any]:
    global _UPDATE_STATE
    if not body.agree:
        raise HTTPException(status_code=400, detail="agree=true required")
    mode = detect_install_mode()
    with _UPDATE_LOCK:
        if _UPDATE_STATE.get("status") in ("backing_up", "applying", "restarting"):
            raise HTTPException(status_code=409, detail="Update already in progress")
        _UPDATE_STATE = {"status": "queued", "message": "Update queued", "error": None}
    thread = threading.Thread(
        target=_run_update_job, args=(mode,), name="streamtv-update", daemon=True
    )
    thread.start()
    return {"ok": True, "install_mode": mode, "job": get_update_job()}


def get_update_job() -> Dict[str, Any]:
    with _UPDATE_LOCK:
        return dict(_UPDATE_STATE)


@router.get("/job", operation_id="updates_job")
async def updates_job() -> Dict[str, Any]:
    return get_update_job()


@router.get("/dmg", operation_id="updates_dmg")
async def updates_dmg():
    latest = _fetch_latest_release()
    for asset in latest.get("assets") or []:
        name = (asset.get("name") or "").lower()
        url = asset.get("browser_download_url")
        if url and name.endswith(".dmg"):
            return RedirectResponse(url=url, status_code=302)
    # JSON fallback
    return {
        "ok": False,
        "error": latest.get("error") or "No .dmg asset on latest release",
        "release_url": latest.get("html_url"),
        "assets": latest.get("assets") or [],
    }
