"""Resolve per-stream titles and episode metadata from unified YAML fields."""

from __future__ import annotations

import json
import re
import urllib.parse
from pathlib import Path
from typing import Any, Optional

SLOT_RE = re.compile(r"^[Ss](\d+)[Ee](\d+)\s*-\s*(.+)$")


def parse_slot(slot: str) -> dict[str, Any]:
    """Parse 'S01E03 - Episode Title' into season/episode/episode_title."""
    if not slot:
        return {}
    m = SLOT_RE.match(slot.strip())
    if not m:
        return {"slot": slot.strip()}
    return {
        "season": int(m.group(1)),
        "episode": int(m.group(2)),
        "episode_title": m.group(3).strip(),
        "slot": slot.strip(),
    }


def title_from_url(url: str) -> str:
    try:
        path = urllib.parse.unquote(url or "")
        base = Path(path).name
        if base and "." in base:
            return base.rsplit(".", 1)[0]
    except Exception:
        pass
    return ""


def resolve_media_title(stream_data: dict[str, Any]) -> str:
    """Best display title for a stream: slot/title/url basename, not collection."""
    slot = (stream_data.get("slot") or "").strip()
    if slot:
        parsed = parse_slot(slot)
        if parsed.get("episode_title"):
            ep = parsed["episode"]
            sn = parsed["season"]
            return f"S{sn:02d}E{ep:02d} - {parsed['episode_title']}"
        return slot
    title = (stream_data.get("title") or "").strip()
    if title:
        return title
    from_url = title_from_url(stream_data.get("url") or "")
    if from_url:
        return from_url
    return (stream_data.get("collection") or stream_data.get("id") or "Untitled").strip()


def resolve_show_name(stream_data: dict[str, Any], channel_name: str = "") -> str:
    """Series-level name for EPG main title (sub-title holds episode detail)."""
    collection = (stream_data.get("collection") or "").strip()
    if collection:
        # "Magnum P.I. - Season 1" -> "Magnum P.I."
        if " - Season " in collection or " - Specials" in collection:
            return collection.split(" - ", 1)[0].strip()
        if collection.endswith(" (MP4)"):
            return collection[:-6].strip()
    if channel_name:
        # Strip suffix like " Complete Series"
        name = channel_name.strip()
        for suffix in (" Complete Series", " Marathon"):
            if name.endswith(suffix):
                return name[: -len(suffix)].strip()
        return name
    return resolve_media_title(stream_data)


def build_stream_meta_data(
    stream_data: dict[str, Any], *, channel_name: str = ""
) -> Optional[str]:
    """JSON blob for media_items.meta_data (EPG season/episode/sub-title)."""
    meta: dict[str, Any] = {}
    slot = (stream_data.get("slot") or "").strip()
    if slot:
        meta.update(parse_slot(slot))
    title = (stream_data.get("title") or "").strip()
    if title and "episode_title" not in meta:
        meta["episode_title"] = title
    show = resolve_show_name(stream_data, channel_name)
    if show:
        meta["show_name"] = show
    if stream_data.get("broadcast_date"):
        meta["broadcast_date"] = str(stream_data["broadcast_date"])
    if stream_data.get("network"):
        meta["network"] = stream_data["network"]
    return json.dumps(meta) if meta else None
