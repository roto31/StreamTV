"""Playout API endpoints for schedule metadata and time blocks"""

from datetime import datetime, timedelta
import json
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db, Channel
from ..scheduling import ScheduleParser, ScheduleEngine
from ..config import config

router = APIRouter(prefix="/playouts", tags=["Playouts"])


SCHEDULE_HIGHLIGHTS: Dict[str, Dict[str, Any]] = {
    "1980": {
        "highlights": [
            "Opening and closing ceremonies presented in full",
            "Custom WCCO pre-roll, mid-roll, and post-roll blocks",
            "Local Minnesota news segments sourced from TC Media Now"
        ]
    },
    "1984": {
        "highlights": [
            "Lake Placid throwback packaging",
            "Rotating filler pods to align hour breaks",
            "Localized sign-offs and promos"
        ]
    },
    "1988": {
        "highlights": [
            "Miracle on Ice retrospectives",
            "Custom halftime features",
            "Balanced ad pods for hour and half-hour slots"
        ]
    },
    "1992": {
        "highlights": [
            "Opening & closing ceremonies remastered",
            "Letterman wrap segments",
            "Local WCCO newscast inserts"
        ]
    },
    "1994": {
        "highlights": [
            "Lillehammer opening & closing ceremonies",
            "Rotating MN commercial pods (2–5 minutes)",
            "Letterman “Mom to Lillehammer” segments"
        ]
    }
}


@router.get("/{channel_number}")
def get_playout_detail(channel_number: str, db: Session = Depends(get_db)):
    channel = (
        db.query(Channel)
        .filter(Channel.number == channel_number)
        .first()
    )
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    response: Dict[str, Any] = {
        "channel_number": channel.number,
        "channel_name": channel.name,
        "enabled": bool(channel.enabled),
        "schedule": None,
        "metadata": SCHEDULE_HIGHLIGHTS.get(channel.number, {}),
        "time_blocks": []
    }

    schedule_file = ScheduleParser.find_schedule_file(channel_number)
    if not schedule_file:
        return response

    parsed_schedule = ScheduleParser.parse_file(schedule_file, schedule_file.parent)
    response["schedule"] = {
        "name": parsed_schedule.name,
        "description": parsed_schedule.description,
        "file": schedule_file.name,
        "content_items": len(parsed_schedule.content_map),
        "sequences": len(parsed_schedule.sequences),
        "playout_instructions": parsed_schedule.playout,
    }

    engine = ScheduleEngine(db)
    # Calculate max_items based on build_days (estimate ~30 items per day)
    build_days = config.playout.build_days
    max_items = max(30, build_days * 30)  # At least 30 items, or build_days * 30
    playlist_items = engine.generate_playlist_from_schedule(
        channel, parsed_schedule, max_items=max_items
    )

    current_time = datetime.utcnow().replace(microsecond=0)
    for item in playlist_items:
        media_item = item.get("media_item")
        if not media_item:
            continue

        start_time = item.get("start_time") or current_time
        duration = media_item.duration or 0
        end_time = start_time + timedelta(seconds=duration)

        block: Dict[str, Any] = {
            "title": item.get("custom_title") or media_item.title,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration": duration,
            "description": media_item.description,
            "filler_kind": item.get("filler_kind"),
            "source": media_item.source.value,
            "metadata": None
        }

        if media_item.meta_data:
            try:
                block["metadata"] = json.loads(media_item.meta_data)
            except json.JSONDecodeError:
                block["metadata"] = {"raw": media_item.meta_data}

        response["time_blocks"].append(block)
        current_time = end_time

    return response

