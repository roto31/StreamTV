"""Backup and restore API endpoints."""

from __future__ import annotations

import logging
import secrets
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse

from ..config import config
from ..backup.paths import FORMAT_VERSION, latest_zip_path
from ..backup.restore import (
    BackupValidationError,
    stage_restore_pending,
    validate_backup_zip,
)
from ..backup.scheduler import get_scheduler
from ..backup.snapshot import create_snapshot, snapshot_status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/backup", tags=["Backup"])

MAX_UPLOAD_BYTES = 512 * 1024 * 1024  # 512 MiB


def _require_backup_download_auth(request: Request) -> None:
    """GET is not gated by APIKeyMiddleware — enforce token when required."""
    if not config.security.api_key_required:
        return
    expected = config.security.access_token
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: access_token not configured",
        )
    provided = None
    auth = request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        provided = auth.split(" ", 1)[1].strip()
    if not provided:
        provided = (request.headers.get("X-API-Key") or "").strip() or None
    if not provided or not secrets.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: valid API key or bearer token required",
        )


@router.get("/status")
def backup_status():
    """Return backup directory status and scheduler state."""
    snap = snapshot_status()
    sched = get_scheduler().status()
    return {
        **snap,
        "scheduler": sched,
        "include_secrets": bool(config.backup.include_secrets),
        "debounce_seconds": float(config.backup.debounce_seconds),
        "retain_count": int(config.backup.retain_count),
        "enabled": bool(config.backup.enabled),
        "format_version": FORMAT_VERSION,
        "warning": (
            "Backup zips may contain API tokens, cookies, and secrets.env. "
            "Treat them as credentials."
        ),
    }


@router.post("/now")
def backup_now():
    """Create a backup snapshot immediately."""
    if not config.backup.enabled:
        # Still allow manual snapshot when auto is disabled
        pass
    try:
        path = create_snapshot()
    except Exception as exc:
        logger.exception("backup now failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backup failed: {exc}",
        ) from exc
    return {
        "status": "ok",
        "path": str(path),
        "latest": str(latest_zip_path()),
    }


@router.get("/latest")
def download_latest(request: Request):
    """Download streamtv-backup-latest.zip (auth required when API key is on)."""
    _require_backup_download_auth(request)
    latest = latest_zip_path()
    if not latest.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No backup exists yet. Use POST /api/backup/now first.",
        )
    return FileResponse(
        path=str(latest),
        media_type="application/zip",
        filename="streamtv-backup-latest.zip",
    )


@router.post("/restore")
async def restore_backup(
    file: UploadFile = File(...),
    dry_run: bool = False,
):
    """Upload a backup zip. Stages a pending restore and asks the client to restart.

    The actual file replacement runs on the next server start (lifespan) so
    live tuners are not mid-write. Set dry_run=true to validate only.
    """
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload must be a .zip backup package",
        )

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        total = 0
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_UPLOAD_BYTES:
                tmp_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Upload too large (max {MAX_UPLOAD_BYTES} bytes)",
                )
            tmp.write(chunk)

    try:
        manifest = validate_backup_zip(tmp_path)
        if dry_run:
            return {
                "status": "validated",
                "dry_run": True,
                "manifest": {
                    "format_version": manifest.get("format_version"),
                    "app_version": manifest.get("app_version"),
                    "created_at": manifest.get("created_at"),
                    "member_count": len(manifest.get("members") or []),
                },
                "restart_required": False,
            }
        staged = stage_restore_pending(tmp_path)
        return {
            "status": "staged",
            "dry_run": False,
            "manifest": {
                "format_version": manifest.get("format_version"),
                "app_version": manifest.get("app_version"),
                "created_at": manifest.get("created_at"),
                "member_count": len(manifest.get("members") or []),
            },
            "pending": staged,
            "restart_required": True,
            "message": (
                "Restore staged. Stop and start the StreamTV server to apply. "
                "The previous config/DB will be copied aside under .streamtv-pre-restore-*."
            ),
        }
    except BackupValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
