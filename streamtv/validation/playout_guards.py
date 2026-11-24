"""Compile-time guards that block known playout failure patterns.

See LESSONS_LEARNED.md Issues 22–25 and rule `playout-reliability-guards.mdc`.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
from urllib.parse import unquote, urlparse

IA_MP4_RE = re.compile(r"\.ia\.mp4(?:\?|#|$)", re.IGNORECASE)
ARCHIVE_URL_RE = re.compile(r"archive\.org/download/[^/]+/.+", re.IGNORECASE)


@dataclass
class GuardReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


def _content_keys(schedule: dict[str, Any]) -> set[str]:
    return {c.get("key") for c in (schedule.get("content") or []) if c.get("key")}


def validate_schedule_sequence(
    schedule: dict[str, Any], *, channel_label: str = ""
) -> GuardReport:
    """Reject duplicate `all:` blocks (Issue 22 — channel 80 marathon blow-up)."""
    report = GuardReport()
    prefix = f"{channel_label}: " if channel_label else ""
    valid_keys = _content_keys(schedule)
    for seq in schedule.get("sequence") or []:
        items = seq.get("items") or []
        all_keys = [it.get("all") for it in items if it.get("all")]
        counts = Counter(all_keys)
        dups = {k: n for k, n in counts.items() if n > 1}
        if dups:
            worst = max(dups.values())
            report.error(
                f"{prefix}schedule sequence '{seq.get('key', '?')}' repeats "
                f"`all:` keys {dups} — use each content key once (had {worst}x duplicate)"
            )
        unknown = [k for k in all_keys if k not in valid_keys]
        if unknown:
            report.error(
                f"{prefix}schedule references unknown content keys: {unknown}"
            )
        if len(all_keys) > len(valid_keys) * 3:
            report.warn(
                f"{prefix}sequence has {len(all_keys)} `all:` entries but only "
                f"{len(valid_keys)} content blocks — check for accidental duplication"
            )
    return report


def validate_archive_stream_urls(
    streams: list[dict[str, Any]], *, channel_label: str = ""
) -> GuardReport:
    """Block .ia.mp4 derivatives and collection-only URLs (Issues 24–25)."""
    report = GuardReport()
    prefix = f"{channel_label}: " if channel_label else ""
    for i, stream in enumerate(streams):
        src = (stream.get("source") or "").lower()
        if src not in ("archive", "archive_org"):
            continue
        url = (stream.get("url") or "").replace("\n", " ").strip()
        sid = stream.get("id") or ""
        label = stream.get("title") or sid or f"stream[{i}]"
        if not url:
            report.error(f"{prefix}{label}: archive stream missing url")
            continue
        if IA_MP4_RE.search(url):
            report.error(
                f"{prefix}{label}: uses Archive.org `.ia.mp4` derivative URL — "
                "use canonical `.mp4` from metadata"
            )
        if "archive.org" in url.lower() and not ARCHIVE_URL_RE.search(url):
            report.error(
                f"{prefix}{label}: archive url has no filename path after identifier"
            )
        path = unquote(urlparse(url).path)
        if path.endswith("/") or path.rstrip("/").endswith("/download"):
            report.error(f"{prefix}{label}: archive url ends at collection, not file")
        runtime = stream.get("runtime")
        if not runtime:
            report.warn(
                f"{prefix}{label}: archive stream missing runtime — "
                "XMLTV/guide slots will collapse without MediaItem.duration"
            )
    return report


def _is_filler_schedule_key(key: str, title: str = "") -> bool:
    """Commercial / pad rows are allowed to repeat; program rows are not adjacent."""
    k = (key or "").lower()
    t = (title or "").lower()
    return (
        k.startswith("brk_")
        or k.startswith("pad_")
        or "station break" in t
        or "late-night programming" in t
        or "filler" in t
    )


def validate_schedule_program_diversity(
    schedule: dict[str, Any],
    *,
    channel_label: str = "",
    max_program_share: float = 0.20,
    max_consecutive_same: int = 1,
) -> GuardReport:
    """Block tiny fill-pool loops and consecutive program repeats (Issue 69).

    Daypart loops may reuse program keys across the cycle, but must not:
      - schedule the same non-filler program key back-to-back
      - let one non-filler key dominate (>max_program_share of program slots)
    """
    report = GuardReport()
    prefix = f"{channel_label}: " if channel_label else ""
    for seq in schedule.get("sequence") or []:
        items = seq.get("items") or []
        program_keys: list[str] = []
        for it in items:
            key = str(it.get("all") or it.get("content") or "")
            title = str(it.get("custom_title") or "")
            if not key or _is_filler_schedule_key(key, title):
                continue
            program_keys.append(key)
        if len(program_keys) < 2:
            continue
        # Consecutive identical program keys (always — even on short sequences)
        streak = 1
        worst_streak = 1
        worst_key = program_keys[0]
        for a, b in zip(program_keys, program_keys[1:]):
            if a == b:
                streak += 1
                if streak > worst_streak:
                    worst_streak = streak
                    worst_key = a
            else:
                streak = 1
        if worst_streak > max_consecutive_same:
            report.error(
                f"{prefix}schedule sequence '{seq.get('key', '?')}' repeats "
                f"program key '{worst_key}' {worst_streak}x consecutively "
                f"(max {max_consecutive_same}) — Issue 69: use a larger fill pool "
                "and LRU / no-adjacent selection"
            )
        # Monopoly share needs enough slots to be meaningful
        if len(program_keys) < 4:
            continue
        counts = Counter(program_keys)
        top_key, top_n = counts.most_common(1)[0]
        share = top_n / len(program_keys)
        if share > max_program_share and top_n >= 8:
            report.error(
                f"{prefix}schedule sequence '{seq.get('key', '?')}' overuses "
                f"program key '{top_key}' ({top_n}/{len(program_keys)} = "
                f"{share:.0%} > {max_program_share:.0%}) — Issue 69: do not loop a "
                "1-item prog/fill pool for overnight or afternoon pads; rotate "
                "real inventory and reserve commercial pads for short remainders"
            )
    return report


def validate_stream_schedule_ratio(
    streams: list[dict[str, Any]],
    schedule: dict[str, Any],
    *,
    channel_label: str = "",
    max_multiplier: float = 2.5,
) -> GuardReport:
    """Warn when schedule expansion would dwarf stream count (Issue 22)."""
    report = GuardReport()
    prefix = f"{channel_label}: " if channel_label else ""
    stream_count = len(streams)
    if stream_count == 0:
        return report
    by_collection: dict[str, int] = {}
    for s in streams:
        coll = s.get("collection") or "?"
        by_collection[coll] = by_collection.get(coll, 0) + 1
    estimated = 0
    for seq in schedule.get("sequence") or []:
        for it in seq.get("items") or []:
            key = it.get("all")
            if not key:
                continue
            coll = next(
                (
                    c.get("collection")
                    for c in (schedule.get("content") or [])
                    if c.get("key") == key
                ),
                None,
            )
            if coll:
                estimated += by_collection.get(coll, 0)
            else:
                estimated += stream_count
    if estimated > stream_count * max_multiplier:
        report.warn(
            f"{prefix}estimated schedule items ~{estimated} from {stream_count} streams "
            f"(>{max_multiplier}x) — duplicate `all:` blocks likely"
        )
    return report


def validate_logo_path(
    channel: dict[str, Any],
    *,
    project_root: Path,
    channel_label: str = "",
) -> GuardReport:
    report = GuardReport()
    prefix = f"{channel_label}: " if channel_label else ""
    logo = channel.get("logo_path")
    if not logo:
        return report
    if logo.startswith("http"):
        return report
    rel = logo.lstrip("/")
    if rel.startswith("static/channel_icons/"):
        rel = "data/channel_icons/" + rel.split("channel_icons/", 1)[-1]
    path = project_root / rel
    if not path.exists():
        report.warn(f"{prefix}logo_path {logo} — file not found at {path}")
    return report


def validate_duplicate_stream_ids(
    streams: list[dict[str, Any]],
    *,
    channel_label: str = "?",
) -> GuardReport:
    """D2: duplicate stream ids inside one channel file are a hard error."""
    report = GuardReport()
    seen: dict[str, int] = {}
    for stream in streams or []:
        sid = stream.get("id")
        if not sid:
            continue
        key = str(sid)
        seen[key] = seen.get(key, 0) + 1
    for sid, count in sorted(seen.items()):
        if count > 1:
            report.error(
                f"Channel {channel_label}: duplicate stream id '{sid}' "
                f"appears {count} times (D2)"
            )
    return report


def validate_unified_channel(
    data: dict[str, Any],
    *,
    src: Optional[Path] = None,
    project_root: Optional[Path] = None,
) -> GuardReport:
    """Run all compile-time playout guards on unified channel YAML data."""
    ch = data.get("channel") or {}
    streams = data.get("streams") or []
    schedule = data.get("schedule") or {}
    label = str(ch.get("number") or (src.stem.replace(".channel", "") if src else "?"))
    root = project_root or (src.resolve().parents[2] if src else Path.cwd())

    merged = GuardReport()
    for part in (
        validate_schedule_sequence(schedule, channel_label=label),
        validate_schedule_program_diversity(schedule, channel_label=label),
        validate_archive_stream_urls(streams, channel_label=label),
        validate_stream_schedule_ratio(streams, schedule, channel_label=label),
        validate_logo_path(ch, project_root=root, channel_label=label),
        validate_duplicate_stream_ids(streams, channel_label=label),
    ):
        merged.errors.extend(part.errors)
        merged.warnings.extend(part.warnings)
    return merged


def assert_unified_channel_ok(
    data: dict[str, Any],
    *,
    src: Optional[Path] = None,
    project_root: Optional[Path] = None,
    strict_warnings: bool = False,
) -> GuardReport:
    report = validate_unified_channel(data, src=src, project_root=project_root)
    if strict_warnings and report.warnings:
        report.errors.extend([f"WARN-as-ERROR: {w}" for w in report.warnings])
    if not report.ok:
        raise ValueError("\n".join(report.errors))
    return report
