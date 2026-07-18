"""Shared continuous-playout timeline math for streaming and EPG."""

from __future__ import annotations

import re
import zoneinfo
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .parser import ParsedSchedule

_EPG_TIMELINE_CACHE: Dict[str, Dict[str, Any]] = {}
_PLEX_EPG_TZ = zoneinfo.ZoneInfo("America/Chicago")


def item_duration(schedule_item: Dict[str, Any], default: int = 1800) -> int:
    """Return seconds for one schedule row (matches channel_manager)."""
    cached = schedule_item.get("cached_duration")
    if cached:
        return int(cached)

    media_item = schedule_item.get("media_item")
    if media_item is not None:
        duration = getattr(media_item, "__dict__", {}).get("duration")
        if duration is None:
            duration = getattr(media_item, "duration", None)
        if duration:
            return int(duration)

    return default


def epg_xml_duration(
    schedule_item: Dict[str, Any],
    *,
    pad_seconds: int = 0,
    default: int = 1800,
) -> int:
    """XMLTV-only duration (optional pad for future grid slots; does not affect playout)."""
    base = item_duration(schedule_item, default=default)
    if pad_seconds > 0:
        return base + int(pad_seconds)
    return base


def stamp_cached_durations(schedule_items: List[Dict[str, Any]]) -> None:
    """Attach cached_duration on each item for stable timeline math."""
    for item in schedule_items:
        if item.get("cached_duration"):
            continue
        media = item.get("media_item")
        if media is not None:
            duration = getattr(media, "__dict__", {}).get("duration") or getattr(
                media, "duration", None
            )
            if duration:
                item["cached_duration"] = int(duration)


def compute_continuous_playout_position(
    schedule_items: List[Dict[str, Any]],
    playout_start_time: datetime,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Mirror channel_manager._get_current_position() for EPG alignment."""
    if now is None:
        now = datetime.utcnow()

    if not schedule_items:
        return {
            "item_index": 0,
            "elapsed_seconds": 0.0,
            "current_item_start": 0.0,
            "cycle_position": 0.0,
            "total_duration": 0.0,
            "current_item_start_time": now,
            "playout_start_time": playout_start_time,
        }

    total_duration = sum(item_duration(item) for item in schedule_items if item.get("media_item"))
    if total_duration <= 0:
        return {
            "item_index": 0,
            "elapsed_seconds": 0.0,
            "current_item_start": 0.0,
            "cycle_position": 0.0,
            "total_duration": 0.0,
            "current_item_start_time": playout_start_time or now,
            "playout_start_time": playout_start_time,
        }

    elapsed = (now - playout_start_time).total_seconds()
    cycle_position = elapsed % total_duration
    cycles_completed = int(elapsed // total_duration)

    current_time = 0.0
    item_index = 0
    for idx, schedule_item in enumerate(schedule_items):
        if not schedule_item.get("media_item"):
            continue
        duration = item_duration(schedule_item)
        if current_time + duration > cycle_position:
            item_index = idx
            break
        current_time += duration
        item_index = idx + 1

    if item_index >= len(schedule_items):
        item_index = 0
        current_time = 0.0

    current_item_start_time = playout_start_time + timedelta(
        seconds=(cycles_completed * total_duration) + current_time
    )

    return {
        "item_index": item_index,
        "elapsed_seconds": elapsed,
        "current_item_start": current_time,
        "cycle_position": cycle_position,
        "total_duration": float(total_duration),
        "current_item_start_time": current_item_start_time,
        "playout_start_time": playout_start_time,
    }


def cumulative_offset_seconds(
    schedule_items: List[Dict[str, Any]],
    item_index: int,
) -> int:
    """Sum slot durations for items [0, item_index) — playout cycle offset."""
    if item_index <= 0:
        return 0
    total = 0
    for i in range(min(item_index, len(schedule_items))):
        if schedule_items[i].get("media_item"):
            total += item_duration(schedule_items[i])
    return total


def playout_anchor_for_item_index(
    schedule_items: List[Dict[str, Any]],
    item_index: int,
    *,
    anchor: Optional[datetime] = None,
) -> tuple[datetime, int]:
    """Return (playout_start_time, last_item_index) so the guide opens on item_index."""
    anchor = anchor or datetime.utcnow()
    if not schedule_items:
        return anchor, 0
    idx = max(0, min(int(item_index), len(schedule_items) - 1))
    offset = cumulative_offset_seconds(schedule_items, idx)
    return anchor - timedelta(seconds=offset), idx


def find_item_index_by_title(
    schedule_items: List[Dict[str, Any]],
    title_query: str,
) -> Optional[int]:
    """Return the sole matching playout index, or None / raise if ambiguous."""
    query = title_query.strip().lower()
    if not query:
        return None
    matches: List[int] = []
    for i, schedule_item in enumerate(schedule_items):
        media = schedule_item.get("media_item")
        if not media:
            continue
        custom = schedule_item.get("custom_title") or ""
        title = (custom or getattr(media, "title", None) or "").lower()
        if query in title:
            matches.append(i)
    if not matches:
        return None
    if len(matches) > 1:
        raise ValueError(
            f"Title {title_query!r} matches multiple items at indices {matches}"
        )
    return matches[0]


def load_channel_stream_schedule(channel: Any, db_session: Any) -> List[Dict[str, Any]]:
    """Build the continuous-playout item list (matches channel_manager source order)."""
    from streamtv.scheduling.engine import ScheduleEngine, playout_shuffle_seed
    from streamtv.scheduling.parser import ScheduleParser

    schedule_file = ScheduleParser.find_schedule_file(channel.number)
    if not schedule_file:
        raise ValueError(f"No schedule file for channel {channel.number}")

    parsed = ScheduleParser.parse_file(schedule_file, schedule_file.parent)
    anchor = datetime.utcnow()
    engine = ScheduleEngine(
        db_session,
        seed=playout_shuffle_seed(str(channel.number), anchor, 0),
    )
    items = engine.generate_playlist_from_schedule(channel, parsed, max_items=None)
    stamp_cached_durations(items)
    return items


def archive_tune_seek_enabled() -> bool:
    """Return True when archive-only tune-in intra-episode seek is enabled.

    Environment variable STREAMTV_PLAYOUT_ARCHIVE_TUNE_SEEK wins over config.yaml
    so operators can enable/disable without editing YAML.
    """
    import os

    env_val = os.environ.get("STREAMTV_PLAYOUT_ARCHIVE_TUNE_SEEK")
    if env_val is not None:
        return env_val.strip().lower() in ("1", "true", "yes", "on")
    from streamtv.config import config

    return bool(getattr(config.playout, "archive_tune_seek", False))


def compute_intra_item_tune_offset(
    position: Dict[str, Any],
    schedule_item: Dict[str, Any],
    *,
    min_seek_seconds: float = 5.0,
) -> float:
    """Seconds into the current item for guide-aligned archive tune-in."""
    cycle_position = float(position.get("cycle_position", 0))
    current_item_start = float(position.get("current_item_start", 0))
    offset = max(0.0, cycle_position - current_item_start)
    duration = float(item_duration(schedule_item))
    if duration > 0:
        offset = min(offset, max(0.0, duration - 1.0))
    if offset < min_seek_seconds:
        return 0.0
    return offset


def episode_identity_key(title: Optional[str]) -> Optional[str]:
    """Normalize season/episode from a media title (e.g. S03E08)."""
    if not title:
        return None
    match = re.search(r"(\d+)x(\d+)", title, re.IGNORECASE)
    if match:
        return f"S{int(match.group(1)):02d}E{int(match.group(2)):02d}"
    match = re.search(r"S(\d+)E(\d+)", title, re.IGNORECASE)
    if match:
        return f"S{int(match.group(1)):02d}E{int(match.group(2)):02d}"
    return None


def map_timeline_index_to_stream_index(
    stream_items: List[Dict[str, Any]],
    timeline_items: List[Dict[str, Any]],
    timeline_index: int,
) -> int:
    """Map a canonical timeline row to the matching playable (e.g. MP4) playlist index."""
    if not stream_items:
        return 0
    if timeline_index >= len(timeline_items):
        return min(timeline_index, len(stream_items) - 1)
    if len(stream_items) == len(timeline_items):
        return timeline_index

    timeline_media = timeline_items[timeline_index].get("media_item")
    if timeline_media is None:
        return min(timeline_index, len(stream_items) - 1)

    media_id = getattr(timeline_media, "id", None)
    if media_id is not None:
        for idx, item in enumerate(stream_items):
            media = item.get("media_item")
            if media is not None and getattr(media, "id", None) == media_id:
                return idx

    episode_key = episode_identity_key(getattr(timeline_media, "title", None))
    if episode_key:
        timeline_occurrence = 0
        timeline_total = 0
        stream_total = 0
        for idx, item in enumerate(timeline_items):
            media = item.get("media_item")
            if media is not None and episode_identity_key(media.title) == episode_key:
                timeline_total += 1
                if idx <= timeline_index:
                    timeline_occurrence += 1
        for item in stream_items:
            media = item.get("media_item")
            if media is not None and episode_identity_key(media.title) == episode_key:
                stream_total += 1
        if timeline_total > 0 and stream_total > 0:
            target_occurrence = max(1, round(timeline_occurrence * stream_total / timeline_total))
            seen = 0
            for idx, item in enumerate(stream_items):
                media = item.get("media_item")
                if media is not None and episode_identity_key(media.title) == episode_key:
                    seen += 1
                    if seen == target_occurrence:
                        return idx

    return min(timeline_index, len(stream_items) - 1)


def resolve_stream_playout_position(
    stream_items: List[Dict[str, Any]],
    timeline_items: List[Dict[str, Any]],
    playout_start_time: datetime,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Compute playout on canonical timeline; return stream playlist index."""
    if not timeline_items or timeline_items is stream_items:
        return compute_continuous_playout_position(stream_items, playout_start_time, now)

    timeline_position = compute_continuous_playout_position(
        timeline_items, playout_start_time, now
    )
    stream_index = map_timeline_index_to_stream_index(
        stream_items,
        timeline_items,
        timeline_position["item_index"],
    )
    return {
        **timeline_position,
        "item_index": stream_index,
        "timeline_item_index": timeline_position["item_index"],
    }


def generate_canonical_timeline_playlist(
    engine: Any,
    channel: Any,
    schedule: "ParsedSchedule",
) -> List[Dict[str, Any]]:
    """Build unfiltered schedule rows for stable playout clock (MP4 filter changes length).

    Resets the engine RNG to its original seed so shuffle picks match a prior
    ``generate_playlist_from_schedule`` call on the same engine (EPG + playout).
    """
    import random
    from streamtv.scheduling import media_format

    original = media_format.mp4_only_for_content
    media_format.mp4_only_for_content = lambda _schedule, _content_key: False
    # Same seed as stream playlist — callers build stream then timeline on one engine.
    seed = getattr(engine, "_seed", None)
    if seed is not None:
        engine._random = random.Random(seed)
    if hasattr(engine, "_shuffled_sequences"):
        engine._shuffled_sequences.clear()
    engine._collection_cache.clear()
    try:
        return engine.generate_playlist_from_schedule(channel, schedule, max_items=None)
    finally:
        media_format.mp4_only_for_content = original
        engine._collection_cache.clear()


def resolve_live_epg_air_position(
    schedule_items: List[Dict[str, Any]],
    playout_start_time: datetime,
    now: Optional[datetime] = None,
    timeline_items: Optional[List[Dict[str, Any]]] = None,
    *,
    live_item_index: Optional[int] = None,
    live_item_start_time: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Wall-clock guide position, adjusted to the item actually on-air when playout lags."""
    if now is None:
        now = datetime.utcnow()
    if timeline_items:
        position = resolve_stream_playout_position(
            schedule_items, timeline_items, playout_start_time, now
        )
    else:
        position = compute_continuous_playout_position(
            schedule_items, playout_start_time, now
        )
    guide_index = int(position["item_index"])
    air_index = guide_index
    air_start = position["current_item_start_time"]
    if (
        live_item_index is not None
        and 0 <= int(live_item_index) < len(schedule_items)
    ):
        air_index = int(live_item_index)
        if live_item_start_time is not None:
            air_start = live_item_start_time
        elif int(live_item_index) < guide_index:
            air_start = live_item_start_time or air_start

    if 0 <= air_index < len(schedule_items) and air_start is not None:
        dur = float(item_duration(schedule_items[air_index]))
        if dur > 0:
            end = air_start + timedelta(seconds=dur)
            overdue = (now - end).total_seconds()
            if overdue > dur:
                # Stale DB start — walk-forward would skip past the on-air item.
                pin = max(1.0, min(dur - 1.0, dur * 0.5))
                air_start = now - timedelta(seconds=pin)
            elif air_start > now:
                air_start = now

    return {
        **position,
        "item_index": air_index,
        "guide_item_index": guide_index,
        "current_item_start_time": air_start,
    }


def assign_schedule_times_from_playout(
    schedule_items: List[Dict[str, Any]],
    playout_start_time: datetime,
    now: Optional[datetime] = None,
    timeline_items: Optional[List[Dict[str, Any]]] = None,
    *,
    live_item_index: Optional[int] = None,
    live_item_start_time: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """Build EPG rows starting at the item that is on-air for continuous playout."""
    if not schedule_items:
        return []

    stamp_cached_durations(schedule_items)
    if timeline_items:
        stamp_cached_durations(timeline_items)
    position = resolve_live_epg_air_position(
        schedule_items,
        playout_start_time,
        now,
        timeline_items,
        live_item_index=live_item_index,
        live_item_start_time=live_item_start_time,
    )
    start_index = position["item_index"]
    current_time = position["current_item_start_time"]

    reassigned: List[Dict[str, Any]] = []
    for offset in range(len(schedule_items)):
        idx = (start_index + offset) % len(schedule_items)
        src = schedule_items[idx]
        item = dict(src)
        item["start_time"] = current_time
        reassigned.append(item)
        current_time = current_time + timedelta(seconds=item_duration(item))

    # When playout lags, wall-clock may pass the on-air slot before FFmpeg advances.
    # Stretch the live row so EPG "now" matches the stream Plex is showing.
    if (
        now is not None
        and live_item_index is not None
        and reassigned
        and start_index == int(live_item_index)
    ):
        live_row = reassigned[0]
        live_start = live_row["start_time"]
        live_dur = item_duration(live_row)
        live_end = live_start + timedelta(seconds=live_dur)
        if now >= live_end:
            extra = int((now - live_end).total_seconds()) + 1
            live_row["cached_duration"] = live_dur + extra
            push_from = live_start + timedelta(seconds=live_row["cached_duration"])
            for row in reassigned[1:]:
                row["start_time"] = push_from
                push_from = push_from + timedelta(seconds=item_duration(row))

    return reassigned


def _aware_dt(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _naive_utc(dt: datetime) -> datetime:
    """Normalize to naive UTC (matches datetime.utcnow() in EPG builder)."""
    return _aware_dt(dt).astimezone(timezone.utc).replace(tzinfo=None)


def _floor_to_epg_minute(dt: datetime) -> datetime:
    """Floor to whole-minute wall clock for stable Plex XMLTV ingest."""
    aware = _aware_dt(dt)
    local = aware.astimezone(_PLEX_EPG_TZ)
    floored = local.replace(second=0, microsecond=0)
    return _naive_utc(floored)


def clear_epg_timeline_cache(channel_key: Optional[str] = None) -> None:
    """Clear cached EPG start times (all channels or one)."""
    if channel_key is None:
        _EPG_TIMELINE_CACHE.clear()
    else:
        _EPG_TIMELINE_CACHE.pop(str(channel_key), None)


def stabilize_epg_timeline_for_plex(
    channel_key: str,
    live_item_index: Optional[int],
    reassigned: List[Dict[str, Any]],
    now: Optional[datetime] = None,
) -> Tuple[List[Dict[str, Any]], str]:
    """Reuse per-channel start times until on-air item changes (prevents Plex duplicate airings)."""
    if not reassigned or live_item_index is None:
        return reassigned, "skip"

    key = str(channel_key)
    idx = int(live_item_index)
    cache = _EPG_TIMELINE_CACHE.get(key)

    if cache and cache.get("live_item_index") == idx and cache.get("start_times"):
        starts: List[datetime] = list(cache["start_times"])
        out: List[Dict[str, Any]] = []
        for i, row in enumerate(reassigned):
            item = dict(row)
            if i < len(starts):
                item["start_time"] = _naive_utc(starts[i])
            if i == 0 and cache.get("row0_duration") is not None:
                item["cached_duration"] = cache["row0_duration"]
            out.append(item)

        if now is not None and out:
            st0 = _aware_dt(out[0]["start_time"])
            cmp_now = _aware_dt(now)
            dur0 = item_duration(out[0])
            end0 = st0 + timedelta(seconds=dur0)
            if cmp_now >= end0:
                extra = int((cmp_now - end0).total_seconds()) + 60
                out[0] = dict(out[0])
                out[0]["cached_duration"] = dur0 + extra
                cache["row0_duration"] = out[0]["cached_duration"]
                cur = _naive_utc(st0 + timedelta(seconds=out[0]["cached_duration"]))
                new_starts = [_naive_utc(st0)]
                for i in range(1, len(out)):
                    out[i] = dict(out[i])
                    out[i]["start_time"] = cur
                    new_starts.append(cur)
                    cur = cur + timedelta(seconds=item_duration(out[i]))
                cache["start_times"] = new_starts

        return out, "hit"

    anchor = _floor_to_epg_minute(reassigned[0]["start_time"])
    out = []
    cur = anchor
    for row in reassigned:
        item = dict(row)
        item["start_time"] = _naive_utc(cur)
        out.append(item)
        cur = cur + timedelta(seconds=item_duration(item))

    row0_dur = out[0].get("cached_duration") if out else None
    _EPG_TIMELINE_CACHE[key] = {
        "live_item_index": idx,
        "start_times": [r["start_time"] for r in out],
        "row0_duration": row0_dur,
    }
    return out, "miss"
