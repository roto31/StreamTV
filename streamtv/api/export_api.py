"""Export API endpoints"""

from __future__ import annotations

from pathlib import Path

import yaml
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from ..database import Channel, get_db
from ..exporters.channel_yaml import build_channel_inventory_yaml
from ..scheduling.yaml_export import write_schedule_yaml_for_channel

router = APIRouter(prefix="/export", tags=["Export"])

ROOT = Path(__file__).resolve().parents[2]
SCHEDULES_DIR = ROOT / "schedules"


@router.get("/channels/{channel_id}/yaml")
def export_channel_yaml(channel_id: int, db: Session = Depends(get_db)) -> PlainTextResponse:
    """Export a channel inventory YAML document from database state."""
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")

    payload = build_channel_inventory_yaml(db, channel)
    schedule_path = SCHEDULES_DIR / f"{channel.number}.yml"
    if schedule_path.exists():
        payload["_schedule_file_note"] = (
            f"Companion playout schedule exists at schedules/{channel.number}.yml "
            "(not embedded; download separately or use schedule export)."
        )

    text = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, default_flow_style=False)
    filename = f"channel_{channel.number}.yaml"
    return PlainTextResponse(
        content=text,
        media_type="application/x-yaml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/schedules/{channel_number}/write")
async def write_schedule_yaml(
    channel_number: str,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """Compile DB schedule items to schedules/{number}.yml on disk."""
    channel = db.query(Channel).filter(Channel.number == str(channel_number)).first()
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
    try:
        path = write_schedule_yaml_for_channel(db, str(channel_number))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    restarted = False
    mgr = getattr(request.app.state, "channel_manager", None)
    if mgr is not None and channel.enabled:
        try:
            await mgr.restart_channel(str(channel.number))
            restarted = True
        except Exception:
            restarted = False

    return {
        "status": "success",
        "path": str(path.relative_to(ROOT)),
        "stream_restarted": restarted,
        "message": "Schedule YAML written to disk.",
    }


@router.post("/channels/{channel_id}/yaml/write")
def write_channel_yaml(channel_id: int, db: Session = Depends(get_db)):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="YAML write-back to original source files is not implemented. Use GET export and manual edit, or schedule write endpoint.",
    )


@router.get("/channels/yaml/bulk")
def export_all_channels_yaml(db: Session = Depends(get_db)):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Bulk YAML export is not yet implemented. Export channels individually.",
    )
