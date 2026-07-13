"""Compile builder drafts into unified channel YAML and deploy artifacts."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

import yaml

from streamtv.importers import import_channels_from_yaml
from streamtv.validation.playout_guards import validate_unified_channel

from .models import BuilderDraft, FillerCollection, LinkStatus, OrderingMode, PaddingMode
from .store import FillerStore

ROOT = Path(__file__).resolve().parents[2]
UNIFIED_DIR = ROOT / "data" / "unified"
DATA_DIR = ROOT / "data"
SCHEDULES_DIR = ROOT / "schedules"


def _iso_duration(seconds: Optional[int]) -> Optional[str]:
    if seconds is None or seconds <= 0:
        return None
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"PT{h}H{m}M{s}S"
    if m:
        return f"PT{m}M{s}S"
    return f"PT{s}S"


def _sort_links(draft: BuilderDraft) -> list:
    ok_links = [link for link in draft.links if link.status == LinkStatus.OK]
    if draft.ordering == OrderingMode.CHRONOLOGICAL:
        return sorted(
            ok_links,
            key=lambda link: link.upload_date or "",
        )
    return ok_links


def _next_channel_number(existing: set[str]) -> str:
    nums = []
    for val in existing:
        try:
            nums.append(int(val))
        except ValueError:
            continue
    return str(max(nums, default=1999) + 1)


def _collection_name(draft: BuilderDraft) -> str:
    if draft.channel.primary_collection:
        return draft.channel.primary_collection
    name = draft.channel.name or f"Channel {draft.channel.number}"
    return name


def _streams_from_draft(
    draft: BuilderDraft,
    filler_store: FillerStore,
) -> list[dict[str, Any]]:
    collection = _collection_name(draft)
    streams: list[dict[str, Any]] = []
    for link in _sort_links(draft):
        if not link.stream_id:
            continue
        stream: dict[str, Any] = {
            "id": link.stream_id,
            "collection": collection,
            "type": "event",
            "source": link.source or "youtube",
            "url": link.url,
            "title": link.title or link.stream_id,
        }
        runtime = _iso_duration(link.duration)
        if runtime:
            stream["runtime"] = runtime
        if link.upload_date:
            stream["broadcast_date"] = link.upload_date
        streams.append(stream)

    for attachment in draft.filler_attachments:
        filler = filler_store.get(attachment.filler_id)
        if not filler:
            continue
        for idx, flink in enumerate(filler.links):
            sid = flink.stream_id or f"filler_{filler.id}_{idx}"
            stream = {
                "id": sid,
                "collection": filler.name,
                "type": flink.clip_type,
                "source": flink.source or "youtube",
                "url": flink.url,
                "title": flink.title or sid,
            }
            runtime = _iso_duration(flink.duration)
            if runtime:
                stream["runtime"] = runtime
            streams.append(stream)
    return streams


def _schedule_from_draft(
    draft: BuilderDraft,
    filler_store: FillerStore,
) -> dict[str, Any]:
    collection = _collection_name(draft)
    channel_name = draft.channel.name or f"Channel {draft.channel.number}"
    primary_key = re.sub(r"[^\w]+", "_", collection.lower()).strip("_") or "primary"

    content: list[dict[str, Any]] = [
        {
            "key": primary_key,
            "collection": collection,
            "order": "shuffle" if draft.ordering == OrderingMode.SHUFFLE else "chronological",
        }
    ]

    filler_keys: list[tuple[str, str, int]] = []
    for attachment in draft.filler_attachments:
        filler = filler_store.get(attachment.filler_id)
        if not filler or not filler.links:
            continue
        fkey = re.sub(r"[^\w]+", "_", filler.name.lower()).strip("_") or f"filler_{filler.id}"
        content.append(
            {
                "key": fkey,
                "collection": filler.name,
                "order": "shuffle",
            }
        )
        filler_keys.append((fkey, filler.name, attachment.break_duration_seconds))

    sequence_items: list[dict[str, Any]] = []
    if filler_keys and draft.filler_attachments:
        attachment = draft.filler_attachments[0]
        if attachment.padding_mode == PaddingMode.BETWEEN_ITEMS:
            for _ in _sort_links(draft):
                sequence_items.append({"all": primary_key})
                fkey, _, break_secs = filler_keys[0]
                sequence_items.append(
                    {
                        "duration": break_secs,
                        "content": fkey,
                        "custom_title": "Commercial Break",
                    }
                )
        else:
            sequence_items.append({"all": primary_key})
    else:
        sequence_items.append({"all": primary_key})

    seq_key = f"{primary_key}_playlist"
    schedule: dict[str, Any] = {
        "name": channel_name,
        "description": draft.channel.description
        or f"Channel built with StreamTV Channel Builder ({len(draft.links)} items)",
        "content": content,
        "sequence": [{"key": seq_key, "items": sequence_items}],
        "playout": [{"sequence": seq_key}, {"repeat": True}],
    }
    if any(link.source in ("archive", "archive_org") for link in draft.links):
        schedule["media"] = {"preferred_extension": "mp4", "mp4_only": True}
    return schedule


def compile_draft_to_unified(
    draft: BuilderDraft,
    filler_store: Optional[FillerStore] = None,
) -> dict[str, Any]:
    store = filler_store or FillerStore()
    streams = _streams_from_draft(draft, store)
    if not streams:
        raise ValueError("No resolved streams to compile")

    number = draft.channel.number
    if not number:
        raise ValueError("Channel number is required before build")

    unified = {
        "config_revision": 1,
        "channel": {
            "number": str(number),
            "name": draft.channel.name or f"Channel {number}",
            "group": draft.channel.group or "Custom",
            "description": draft.channel.description,
            "enabled": True,
            "playout_mode": draft.channel.playout_mode,
        },
        "streams": streams,
        "schedule": _schedule_from_draft(draft, store),
    }
    unified["channel"] = {k: v for k, v in unified["channel"].items() if v is not None}
    return unified


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )


async def build_channel_from_draft(
    draft: BuilderDraft,
    db_session: Any,
    *,
    filler_store: Optional[FillerStore] = None,
) -> dict[str, Any]:
    """Compile, write artifacts, import inventory, return paths."""
    store = filler_store or FillerStore()
    unified = compile_draft_to_unified(draft, store)
    number = str(draft.channel.number)

    report = validate_unified_channel(unified)
    if not report.ok:
        raise ValueError("; ".join(report.errors))

    unified_path = UNIFIED_DIR / f"{number}.channel.yaml"
    inventory_path = DATA_DIR / f"channels_generated_{number}.yaml"
    schedule_path = SCHEDULES_DIR / f"{number}.yml"

    _write_yaml(unified_path, unified)

    inventory = {
        "channels": [
            {
                **unified["channel"],
                "streams": unified["streams"],
            }
        ]
    }
    _write_yaml(inventory_path, inventory)
    _write_yaml(schedule_path, unified["schedule"])

    await import_channels_from_yaml(inventory_path, db_session=db_session)

    warnings = list(report.warnings)
    return {
        "channel_number": number,
        "unified_path": str(unified_path),
        "inventory_path": str(inventory_path),
        "schedule_path": str(schedule_path),
        "stream_count": len(unified["streams"]),
        "warnings": warnings,
    }
