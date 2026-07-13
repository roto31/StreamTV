"""Build import-compatible channel inventory YAML from database state."""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from sqlalchemy.orm import Session

from streamtv.database import Channel, Collection, CollectionItem, MediaItem, Playlist, PlaylistItem


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", (value or "item").lower()).strip("_")
    return slug or "item"


def _seconds_to_iso(duration: Optional[int]) -> Optional[str]:
    if not duration or duration <= 0:
        return None
    hours, rem = divmod(int(duration), 3600)
    minutes, seconds = divmod(rem, 60)
    if hours:
        return f"PT{hours}H{minutes}M{seconds}S"
    if minutes:
        return f"PT{minutes}M{seconds}S"
    return f"PT{seconds}S"


def _source_label(media: MediaItem) -> str:
    raw = getattr(media.source, "value", str(media.source))
    if raw == "archive_org":
        return "archive"
    return raw


def _collection_for_media(db: Session, media_id: int) -> Optional[str]:
    row = (
        db.query(Collection)
        .join(CollectionItem, CollectionItem.collection_id == Collection.id)
        .filter(CollectionItem.media_item_id == media_id)
        .order_by(CollectionItem.order)
        .first()
    )
    return row.name if row else None


def _stream_from_media(db: Session, media: MediaItem, *, channel_name: str) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    if media.meta_data:
        try:
            meta = json.loads(media.meta_data)
        except json.JSONDecodeError:
            meta = {}

    stream_id = media.source_id or f"media_{media.id}"
    collection = _collection_for_media(db, media.id) or channel_name

    slot_parts: list[str] = []
    if meta.get("season") is not None and meta.get("episode") is not None:
        ep_title = meta.get("episode_title") or media.title
        slot_parts.append(
            f"S{int(meta['season']):02d}E{int(meta['episode']):02d} - {ep_title}"
        )
    elif meta.get("slot"):
        slot_parts.append(str(meta["slot"]))

    stream: dict[str, Any] = {
        "id": stream_id,
        "collection": collection,
        "source": _source_label(media),
        "url": media.url,
    }
    runtime = _seconds_to_iso(media.duration)
    if runtime:
        stream["runtime"] = runtime
    if slot_parts:
        stream["slot"] = slot_parts[0]
    if media.description:
        stream["notes"] = media.description
    if meta.get("broadcast_date"):
        stream["broadcast_date"] = meta["broadcast_date"]
    if meta.get("network"):
        stream["network"] = meta["network"]
    if media.title and media.title not in (stream_id, collection):
        stream["title"] = media.title
    return stream


def build_channel_inventory_yaml(db: Session, channel: Channel) -> dict[str, Any]:
    """Return a dict matching the `channels:` import YAML shape."""
    playlist_name = f"{channel.name} - Main Playlist"
    playlist = (
        db.query(Playlist)
        .filter(Playlist.channel_id == channel.id, Playlist.name == playlist_name)
        .first()
    )
    streams: list[dict[str, Any]] = []
    if playlist:
        items = (
            db.query(PlaylistItem)
            .filter(PlaylistItem.playlist_id == playlist.id)
            .order_by(PlaylistItem.order)
            .all()
        )
        for item in items:
            media = db.query(MediaItem).filter(MediaItem.id == item.media_item_id).first()
            if media:
                streams.append(_stream_from_media(db, media, channel_name=channel.name))

    channel_entry: dict[str, Any] = {
        "number": str(channel.number),
        "name": channel.name,
        "enabled": bool(channel.enabled),
    }
    if channel.group:
        channel_entry["group"] = channel.group
    if getattr(channel, "description", None):
        channel_entry["description"] = channel.description
    if streams:
        channel_entry["streams"] = streams
    playout_mode = getattr(channel.playout_mode, "value", channel.playout_mode)
    if playout_mode:
        channel_entry["playout_mode"] = str(playout_mode)
    return {"channels": [channel_entry]}
