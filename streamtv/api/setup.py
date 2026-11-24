"""First-run setup API (SetupDone, port, jobs, MCP, factory reset)."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from ..config import config
from ..setup.apply_port import apply_port, ensure_config_exists
from ..setup.background_jobs import get_progress, start_jobs
from ..setup.first_run_state import (
    clear_setup_done,
    is_setup_done,
    read_setup_done,
    write_setup_done,
)
from ..setup.mcp_offer import list_mcp_hosts
from ..setup.mcp_runner import apply_mcp_hosts
from ..setup.plex_codecs import install_aac_codecs, verify_aac_codecs
from ..setup.port_probe import probe_port
from ..setup.runtime_install import install_runtime, validate_workdir
from ..setup.starter_packs import install_starter_channels, list_catalog
from ..utils.dependency_freshness import run_freshness_checks

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/setup", tags=["Setup"])
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


class PortBody(BaseModel):
    port: int = Field(..., ge=1, le=65535)


class McpBody(BaseModel):
    enabled: bool = False
    hosts: List[str] = Field(default_factory=list)


class FactoryResetBody(BaseModel):
    confirm: bool = False
    reseed_config: bool = False
    clear_credentials: bool = False


class PlexCodecsInstallBody(BaseModel):
    from_dir: Optional[str] = None


class RuntimeInstallBody(BaseModel):
    mode: str = Field(default="app_support", description="app_support | repo")
    workdir: Optional[str] = None


class SampleChannelsBody(BaseModel):
    channels: List[str] = Field(default_factory=list)


@router.get("/status", operation_id="setup_status")
async def setup_status() -> Dict[str, Any]:
    current_port = int(getattr(config.server, "port", 8410) or 8410)
    probe = probe_port(current_port)
    # If we are already listening, treat preferred port as OK for this process
    listening_ok = True  # this process owns a port; conflict matters for *changing* to busy ports
    marker = read_setup_done()
    plex = verify_aac_codecs()
    yt_report = run_freshness_checks(check_pypi=False)
    yt_floor = next((f for f in yt_report.findings if f.component == "yt-dlp"), None)
    return {
        "setup_done": marker is not None,
        "setup_done_info": marker,
        "current_port": current_port,
        "base_url": getattr(config.server, "base_url", f"http://127.0.0.1:{current_port}"),
        "port_available": probe.available or listening_ok,
        "port_probe": {
            "port": probe.port,
            "available": probe.available,
            "suggestions": probe.suggestions,
            "message": probe.message,
        },
        "mcp_hosts": list_mcp_hosts(),
        "progress": get_progress(),
        "plex_codecs": plex.to_dict(),
        "yt_dlp": {
            "ok": bool(yt_floor and yt_floor.status == "ok"),
            "detail": yt_floor.detail if yt_floor else "unavailable",
        },
        "sample_channels": list_catalog(
            base_url=getattr(config.server, "base_url", f"http://127.0.0.1:{current_port}")
        ),
        "install_modes": {
            "default": "app_support",
            "advanced": "repo",
            "app_support_path": str(Path.home() / "Library/Application Support/StreamTV"),
        },
    }


@router.post("/port", operation_id="setup_set_port")
async def setup_set_port(body: PortBody) -> Dict[str, Any]:
    probe = probe_port(body.port)
    # Allow keeping current listening port even if bind check is false (SO_REUSE / self)
    current = int(getattr(config.server, "port", 8410) or 8410)
    if not probe.available and body.port != current:
        raise HTTPException(
            status_code=409,
            detail={
                "message": probe.message,
                "suggestions": probe.suggestions,
            },
        )
    try:
        result = apply_port(body.port)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"ok": True, **result}


@router.post("/start", operation_id="setup_start_jobs")
async def setup_start() -> Dict[str, Any]:
    try:
        ensure_config_exists()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return start_jobs()


@router.get("/progress", operation_id="setup_progress")
async def setup_progress() -> Dict[str, Any]:
    return get_progress()


@router.post("/mcp", operation_id="setup_mcp")
async def setup_mcp(body: McpBody) -> Dict[str, Any]:
    if not body.enabled:
        return {"ok": True, "skipped": True, "hosts": []}
    return apply_mcp_hosts(body.hosts)


@router.post("/install-runtime", operation_id="setup_install_runtime")
async def setup_install_runtime(body: RuntimeInstallBody) -> Dict[str, Any]:
    mode = (body.mode or "app_support").strip().lower()
    if mode not in {"app_support", "repo"}:
        raise HTTPException(status_code=400, detail="mode must be app_support or repo")
    if mode == "repo":
        if not body.workdir:
            raise HTTPException(
                status_code=400,
                detail="Advanced (repo) mode requires workdir — clone/build the repo and create venv first",
            )
        check = validate_workdir(body.workdir, mode="repo")
        if not check.ok:
            raise HTTPException(status_code=400, detail=check.to_dict())
    result = install_runtime(workdir=body.workdir, mode=mode)
    if not result.get("ok"):
        raise HTTPException(status_code=500, detail=result)
    return result


@router.get("/sample-channels", operation_id="setup_sample_channels_catalog")
async def setup_sample_channels_catalog() -> Dict[str, Any]:
    return {"channels": list_catalog(base_url=getattr(config.server, "base_url", "http://127.0.0.1:8410"))}


@router.post("/sample-channels", operation_id="setup_sample_channels_install")
async def setup_sample_channels_install(body: SampleChannelsBody) -> Dict[str, Any]:
    from ..database.session import SessionLocal

    db = SessionLocal()
    try:
        result = await install_starter_channels(body.channels or [], db_session=db)
    finally:
        db.close()
    if not result.ok and result.errors and not result.installed:
        raise HTTPException(status_code=400, detail=result.to_dict())
    return {"ok": result.ok, **result.to_dict()}


@router.get("/plex-codecs", operation_id="setup_plex_codecs_status")
async def setup_plex_codecs_status() -> Dict[str, Any]:
    return verify_aac_codecs().to_dict()


@router.post("/plex-codecs/install", operation_id="setup_plex_codecs_install")
async def setup_plex_codecs_install(body: Optional[PlexCodecsInstallBody] = None) -> Dict[str, Any]:
    payload = body or PlexCodecsInstallBody()
    status = install_aac_codecs(from_dir=payload.from_dir)
    return {"ok": status.ok, **status.to_dict()}


@router.post("/complete", operation_id="setup_complete")
async def setup_complete() -> Dict[str, Any]:
    plex = verify_aac_codecs()
    if plex.detected and not plex.ok:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "plex_codecs_missing",
                "message": (
                    "Plex AAC codecs are required before SetupDone. "
                    "Use Retry codec installation (or POST /api/setup/plex-codecs/install), "
                    "optionally with from_dir pointing at a healthy host Codecs folder."
                ),
                "plex_codecs": plex.to_dict(),
            },
        )
    path = write_setup_done()
    return {"ok": True, "setup_done": True, "path": str(path)}


@router.post("/factory-reset", operation_id="setup_factory_reset")
async def setup_factory_reset(body: FactoryResetBody) -> Dict[str, Any]:
    if not body.confirm:
        raise HTTPException(status_code=400, detail="confirm=true required")

    # Best-effort backup with a hard timeout — never block the macOS app reset path.
    import asyncio

    backup_info: Optional[Dict[str, Any]] = None
    try:
        from ..backup.snapshot import create_snapshot

        snap = await asyncio.wait_for(asyncio.to_thread(create_snapshot), timeout=5.0)
        backup_info = {"path": str(snap) if snap is not None else None}
    except asyncio.TimeoutError:
        logger.warning("Pre-factory-reset backup timed out after 5s; continuing")
        backup_info = {"error": "backup_timeout"}
    except Exception as exc:
        logger.warning("Pre-factory-reset backup skipped: %s", exc)
        backup_info = {"error": str(exc)}

    removed = clear_setup_done()
    reseeded = False
    if body.reseed_config:
        example = Path(__file__).resolve().parent.parent.parent / "config.example.yaml"
        target = Path(
            __import__("os").environ.get("STREAMTV_CONFIG", "config.yaml")
        ).expanduser()
        if example.is_file():
            shutil.copy2(example, target)
            reseeded = True

    cleared_creds_note = None
    if body.clear_credentials:
        cleared_creds_note = (
            "Clear YouTube cookies / Archive.org Keychain entries manually "
            "or via Source Authentication pages (no Keychain delete API)."
        )

    return {
        "ok": True,
        "removed_markers": removed,
        "backup": backup_info,
        "reseeded_config": reseeded,
        "cleared_credentials": False,
        "cleared_credentials_note": cleared_creds_note,
        "setup_done": is_setup_done(),
    }
