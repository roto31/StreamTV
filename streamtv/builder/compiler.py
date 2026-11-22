"""Compile builder drafts into unified channel YAML and deploy artifacts."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

import yaml

from streamtv.importers import import_channels_from_yaml
from streamtv.validation.playout_guards import validate_unified_channel

from streamtv.builder.titles import humanize_media_title

from .models import BuilderDraft, FillerCollection, LinkStatus, OrderingMode, PaddingMode
from .store import FillerStore

ROOT = Path(__file__).resolve().parents[2]
UNIFIED_DIR = ROOT / "data" / "unified"
DATA_DIR = ROOT / "data"
SCHEDULES_DIR = ROOT / "schedules"


def _humanize_title(raw: Optional[str]) -> str:
    return humanize_media_title(raw or "")


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


def _parse_iso_runtime(runtime: Optional[str]) -> Optional[int]:
    if not runtime:
        return None
    text = str(runtime).strip().upper().replace("PT", "")
    if not text:
        return None
    hours = minutes = seconds = 0
    match_h = re.search(r"(\d+)H", text)
    match_m = re.search(r"(\d+)M", text)
    match_s = re.search(r"(\d+)S", text)
    if match_h:
        hours = int(match_h.group(1))
    if match_m:
        minutes = int(match_m.group(1))
    if match_s:
        seconds = int(match_s.group(1))
    total = hours * 3600 + minutes * 60 + seconds
    return total if total > 0 else None


def enrich_archive_stream_runtimes(streams: list[dict[str, Any]]) -> list[str]:
    """Fill missing Archive ``runtime`` from metadata API. Returns warning strings."""
    from streamtv.builder.resolver import (
        _extract_archive_identifier,
        _is_archive_file_url,
        lookup_archive_file_duration,
    )
    from urllib.parse import unquote, urlparse

    warnings: list[str] = []
    for stream in streams:
        if _parse_iso_runtime(stream.get("runtime")):
            continue
        src = (stream.get("source") or "").lower()
        url = (stream.get("url") or "").replace("\n", " ").strip()
        if src not in ("archive", "archive_org") and "archive.org" not in url.lower():
            continue
        if not url or not _is_archive_file_url(url):
            warnings.append(
                f"{stream.get('title') or stream.get('id') or url}: "
                "Archive stream missing file URL; cannot resolve duration"
            )
            continue
        identifier = _extract_archive_identifier(url)
        filename = unquote(urlparse(url).path.rsplit("/", 1)[-1])
        if not identifier:
            warnings.append(
                f"{stream.get('title') or filename}: cannot parse Archive identifier"
            )
            continue
        try:
            seconds = lookup_archive_file_duration(identifier, filename)
        except Exception as exc:
            warnings.append(
                f"{stream.get('title') or filename}: Archive metadata duration "
                f"lookup failed ({exc})"
            )
            continue
        if not seconds:
            warnings.append(
                f"{stream.get('title') or filename}: Archive metadata has no "
                "file length — EPG slots require a real duration"
            )
            continue
        stream["runtime"] = _iso_duration(seconds)
    return warnings


def archive_streams_missing_runtime(streams: list[dict[str, Any]]) -> list[str]:
    """Labels of Archive file streams that still lack a usable runtime."""
    missing: list[str] = []
    for stream in streams:
        src = (stream.get("source") or "").lower()
        url = (stream.get("url") or "").lower()
        if src not in ("archive", "archive_org") and "archive.org" not in url:
            continue
        if not _parse_iso_runtime(stream.get("runtime")):
            missing.append(str(stream.get("title") or stream.get("id") or stream.get("url")))
    return missing


def _sort_links(draft: BuilderDraft) -> list:
    ok_links = [link for link in draft.links if link.status == LinkStatus.OK]
    if draft.ordering in (OrderingMode.CHRONOLOGICAL, OrderingMode.AIR_DATE):
        # D4: air_date first, then upload_date, then insertion order (stable).
        return sorted(
            ok_links,
            key=lambda link: (
                getattr(link, "air_date", None) or "9999-99-99",
                link.upload_date or "9999-99-99",
            ),
        )
    return ok_links


def _program_collection_name(draft: BuilderDraft, link: Any) -> str:
    """One collection per program (D1/D3); name includes stream id in [brackets]."""
    base = _collection_name(draft)
    title = _humanize_title(link.title) or link.stream_id or "item"
    sid = link.stream_id or "item"
    return f"{base} - {title} [{sid}]"


def _content_key(stream_id: str) -> str:
    return re.sub(r"[^\w]+", "_", (stream_id or "item").lower()).strip("_") or "item"


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


def _epg_sync_class_for_draft(draft: BuilderDraft) -> Optional[str]:
    if draft.channel.epg_sync_class:
        return draft.channel.epg_sync_class
    ok_links = [link for link in draft.links if link.status == LinkStatus.OK]
    if not ok_links:
        return None
    if draft.channel.playout_mode != "continuous":
        return None
    if all((link.source or "") == "pbs" for link in ok_links):
        return "C"
    if any(link.expanded_from and "pbs.org/show/" in link.expanded_from.lower() for link in ok_links):
        return "C"
    return None


def _streams_from_draft(
    draft: BuilderDraft,
    filler_store: FillerStore,
) -> list[dict[str, Any]]:
    streams: list[dict[str, Any]] = []
    for link in _sort_links(draft):
        if not link.stream_id:
            continue
        stream: dict[str, Any] = {
            "id": link.stream_id,
            "collection": _program_collection_name(draft, link),
            "type": "event",
            "source": link.source or "youtube",
            "url": link.url,
            "title": _humanize_title(link.title) or link.stream_id,
        }
        runtime = _iso_duration(link.duration)
        if runtime:
            stream["runtime"] = runtime
        # D4: never write upload_date into broadcast_date.
        air = getattr(link, "air_date", None)
        if air:
            stream["broadcast_date"] = air
        streams.append(stream)

    for attachment in draft.filler_attachments:
        filler = filler_store.get(attachment.filler_id)
        if not filler:
            continue
        for idx, flink in enumerate(filler.links):
            sid = flink.stream_id or f"filler_{filler.id}_{idx}"
            title = _humanize_title(flink.title) or sid
            stream = {
                "id": sid,
                "collection": f"{filler.name} - {title} [{sid}]",
                "type": flink.clip_type,
                "source": flink.source or "youtube",
                "url": flink.url,
                "title": title,
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
    """Emit one collection per program/break and only ``all:`` sequence items (D1)."""
    channel_name = draft.channel.name or f"Channel {draft.channel.number}"
    order = "shuffle" if draft.ordering == OrderingMode.SHUFFLE else "chronological"
    ok_links = [link for link in _sort_links(draft) if link.stream_id]

    content: list[dict[str, Any]] = []
    for link in ok_links:
        key = _content_key(link.stream_id or "")
        content.append(
            {
                "key": key,
                "collection": _program_collection_name(draft, link),
                "order": order,
            }
        )

    break_entries: list[tuple[str, str]] = []
    for attachment in draft.filler_attachments:
        filler = filler_store.get(attachment.filler_id)
        if not filler or not filler.links:
            continue
        for idx, flink in enumerate(filler.links):
            sid = flink.stream_id or f"filler_{filler.id}_{idx}"
            fkey = _content_key(sid)
            title = _humanize_title(flink.title) or sid
            content.append(
                {
                    "key": fkey,
                    "collection": f"{filler.name} - {title} [{sid}]",
                    "order": "shuffle",
                }
            )
            break_entries.append((fkey, title))

    sequence_items: list[dict[str, Any]] = []
    between = False
    if draft.filler_attachments and break_entries:
        between = draft.filler_attachments[0].padding_mode == PaddingMode.BETWEEN_ITEMS

    if between and break_entries:
        # Rotate break reels between programs; never emit duration: (D1).
        for i, link in enumerate(ok_links):
            sequence_items.append(
                {
                    "all": _content_key(link.stream_id or ""),
                    "custom_title": _humanize_title(link.title) or link.stream_id,
                }
            )
            fkey, btitle = break_entries[i % len(break_entries)]
            sequence_items.append(
                {
                    "all": fkey,
                    "custom_title": f"Station Break: {btitle}",
                    "filler_kind": "Commercial",
                }
            )
    else:
        for link in ok_links:
            sequence_items.append({"all": _content_key(link.stream_id or "")})

    base = _collection_name(draft)
    primary_key = re.sub(r"[^\w]+", "_", base.lower()).strip("_") or "primary"
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

    enrich_archive_stream_runtimes(streams)
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
    epg_class = _epg_sync_class_for_draft(draft)
    if epg_class:
        unified["channel"]["epg_sync_class"] = epg_class
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

    # Second-chance metadata fill (in case resolve left duration unset).
    runtime_warnings = enrich_archive_stream_runtimes(unified["streams"])
    missing_runtime = archive_streams_missing_runtime(unified["streams"])
    if missing_runtime:
        raise ValueError(
            "Archive streams missing runtime — cannot build a correct XMLTV/schedule. "
            "Re-run resolve or fix metadata lengths for: "
            + "; ".join(missing_runtime[:8])
            + ("…" if len(missing_runtime) > 8 else "")
        )

    report = validate_unified_channel(unified)
    if not report.ok:
        raise ValueError("; ".join(report.errors))

    schedule = unified.get("schedule") or {}
    if not schedule.get("content") or not schedule.get("playout"):
        raise ValueError(
            "Compiled schedule is incomplete (need content + playout); "
            "refusing to write channel artifacts"
        )

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
    _write_yaml(schedule_path, schedule)

    if not schedule_path.is_file() or schedule_path.stat().st_size < 32:
        raise ValueError(f"Schedule file was not written correctly: {schedule_path}")

    await import_channels_from_yaml(inventory_path, db_session=db_session)

    warnings = list(report.warnings) + runtime_warnings
    return {
        "channel_number": number,
        "unified_path": str(unified_path),
        "inventory_path": str(inventory_path),
        "schedule_path": str(schedule_path),
        "stream_count": len(unified["streams"]),
        "warnings": warnings,
    }
