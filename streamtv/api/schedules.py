"""Schedules API endpoints"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import logging

import yaml
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db, Schedule, Channel
from ..api.schemas import ScheduleCreate, ScheduleResponse, ScheduleUpdate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/schedules", tags=["Schedules"])

ROOT = Path(__file__).resolve().parents[2]
SCHEDULES_DIR = ROOT / "schedules"

_CREATE_DISABLED = (
    "Web/API schedule creation is disabled. "
    "Edit schedules/{channel}.yml on disk (continuous playout + XMLTV authority)."
)


@router.get("/yaml-inventory")
def list_yaml_schedules(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Read-only inventory of on-disk schedules/{number}.yml files."""
    channels = {str(c.number): c for c in db.query(Channel).all()}
    rows: List[Dict[str, Any]] = []
    if not SCHEDULES_DIR.is_dir():
        return rows

    for path in sorted(SCHEDULES_DIR.glob("*.yml")) + sorted(SCHEDULES_DIR.glob("*.yaml")):
        if path.name.endswith(".orig") or path.name.endswith(".bak"):
            continue
        number = path.stem
        channel = channels.get(number)
        name = number
        description = ""
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if isinstance(data, dict):
                name = str(data.get("name") or name)
                description = str(data.get("description") or "")
        except Exception as exc:
            logger.warning("Failed to read schedule YAML %s: %s", path, exc)
            name = f"{number} (unreadable)"

        rows.append(
            {
                "channel_number": number,
                "channel_name": channel.name if channel else None,
                "channel_enabled": bool(channel.enabled) if channel else None,
                "schedule_name": name,
                "description": description,
                "file": f"schedules/{path.name}",
                "bytes": path.stat().st_size,
            }
        )
    return rows


@router.get("", response_model=List[ScheduleResponse])
def get_all_schedules(
    channel_id: int = None,
    db: Session = Depends(get_db),
):
    """Get all DB schedules (legacy; playout uses YAML on disk)."""
    query = db.query(Schedule)
    if channel_id:
        query = query.filter(Schedule.channel_id == channel_id)
    return query.all()


@router.get("/{schedule_id}", response_model=ScheduleResponse)
def get_schedule(schedule_id: int, db: Session = Depends(get_db)):
    """Get schedule by ID"""
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
def create_schedule(schedule: ScheduleCreate, db: Session = Depends(get_db)):
    """Disabled — continuous playout uses schedules/{n}.yml only."""
    raise HTTPException(status_code=status.HTTP_410_GONE, detail=_CREATE_DISABLED)


@router.put("/{schedule_id}", response_model=ScheduleResponse)
def update_schedule(schedule_id: int, schedule: ScheduleUpdate, db: Session = Depends(get_db)):
    """Disabled — edit schedules/{n}.yml on disk instead."""
    raise HTTPException(status_code=status.HTTP_410_GONE, detail=_CREATE_DISABLED)


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(schedule_id: int, db: Session = Depends(get_db)):
    """Delete a legacy DB schedule row (does not modify YAML on disk)."""
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    try:
        channel = db.query(Channel).filter(Channel.id == schedule.channel_id).first()
        from ..scheduling.parser import ScheduleParser

        has_yaml_file = False
        if channel and getattr(channel, "number", None):
            has_yaml_file = bool(ScheduleParser.find_schedule_file(channel.number))
    except Exception:
        has_yaml_file = False
    if getattr(schedule, "is_yaml_source", False) or has_yaml_file:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Schedule is defined in YAML. Edit the YAML file; DB delete refused while YAML exists.",
        )

    db.delete(schedule)
    db.commit()
    return None
