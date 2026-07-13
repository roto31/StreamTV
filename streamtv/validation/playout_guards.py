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
        validate_archive_stream_urls(streams, channel_label=label),
        validate_stream_schedule_ratio(streams, schedule, channel_label=label),
        validate_logo_path(ch, project_root=root, channel_label=label),
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
