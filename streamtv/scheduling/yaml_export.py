"""Compile DB schedule records into filesystem playout YAML."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.orm import Session

from streamtv.database import Channel, Collection, Schedule, ScheduleItem

ROOT = Path(__file__).resolve().parents[2]
SCHEDULES_DIR = ROOT / "schedules"


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", (value or "block").lower()).strip("_")
    return slug or "block"


def _playback_order_label(item: ScheduleItem) -> str:
    order = getattr(item.playback_order, "value", item.playback_order)
    if str(order) == "shuffle":
        return "shuffle"
    return "chronological"


def build_schedule_yaml_from_db(db: Session, channel: Channel) -> dict[str, Any]:
    """Map DB classic schedule items to minimal continuous-playout YAML."""
    schedule = (
        db.query(Schedule)
        .filter(Schedule.channel_id == channel.id)
        .order_by(Schedule.id)
        .first()
    )
    if not schedule:
        raise ValueError(f"No DB schedule found for channel {channel.number}")

    items = (
        db.query(ScheduleItem)
        .filter(ScheduleItem.schedule_id == schedule.id)
        .order_by(ScheduleItem.index)
        .all()
    )
    if not items:
        raise ValueError(f"Schedule {schedule.id} has no items to export")

    content: list[dict[str, Any]] = []
    sequence_items: list[dict[str, Any]] = []
    seen_keys: set[str] = set()

    for item in items:
        collection_type = getattr(item.collection_type, "value", item.collection_type)
        if str(collection_type) != "collection" or not item.collection_id:
            continue
        collection = db.query(Collection).filter(Collection.id == item.collection_id).first()
        if not collection:
            continue
        key = _slug(collection.name)
        if key in seen_keys:
            key = f"{key}_{item.id}"
        seen_keys.add(key)
        content.append(
            {
                "key": key,
                "collection": collection.name,
                "order": _playback_order_label(item),
            }
        )
        block: dict[str, Any] = {"all": key}
        if item.custom_title:
            block["custom_title"] = item.custom_title
        sequence_items.append(block)

    if not content:
        raise ValueError(
            "No exportable collection items found (only manual collection items are supported)"
        )

    seq_key = _slug(schedule.name or f"channel_{channel.number}")
    return {
        "name": schedule.name or channel.name,
        "description": getattr(channel, "description", None)
        or f"Exported from DB schedule {schedule.id}",
        "content": content,
        "sequence": [{"key": seq_key, "items": sequence_items}],
        "playout": [{"sequence": seq_key}, {"repeat": True}],
    }


def write_schedule_yaml_for_channel(db: Session, channel_number: str) -> Path:
    channel = db.query(Channel).filter(Channel.number == str(channel_number)).first()
    if not channel:
        raise ValueError(f"Channel {channel_number} not found")
    payload = build_schedule_yaml_from_db(db, channel)
    path = SCHEDULES_DIR / f"{channel.number}.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )
    return path
