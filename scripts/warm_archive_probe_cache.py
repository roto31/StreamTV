#!/usr/bin/env python3
"""Seed Archive.org probe sidecars for a channel (Lesson 41c).

Runs a long ffprobe (default 90s) on each Archive URL in
data/unified/<channel>.channel.yaml that lacks a fresh sidecar, and stores real
codec results via streamtv.utils.archive_probe_cache. Live tunes then skip the
5s/15s/15s probe chain that non-faststart multi-GB MP4s always miss.

Also stores video width/height/profile so the Archive wait-phase hold can
match program geometry (tuners/video_hold). Fresh sidecars without geometry
are re-probed.

Read-only toward the running server; safe with StreamTV running.

Usage:
  ./venv/bin/python3 scripts/warm_archive_probe_cache.py --channel 1984.2
  ./venv/bin/python3 scripts/warm_archive_probe_cache.py --channel 1984.2 --apply
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any, Iterator, Optional

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from streamtv.config import config  # noqa: E402
from streamtv.streaming.mpegts_streamer import MPEGTSStreamer  # noqa: E402
from streamtv.utils import archive_probe_cache  # noqa: E402

DEFAULT_PROBE_TIMEOUT_SEC = 90.0
# Same input options as MPEGTSStreamer._quick_ffprobe_codec (default probe size).
FFPROBE_SOCKET_TIMEOUT_US = "3000000"
FFPROBE_PROBESIZE = "500000"
FFPROBE_ANALYZEDURATION = "500000"
FFPROBE_USER_AGENT = "Mozilla/5.0 (compatible; StreamTV/1.0)"


def _iter_archive_urls(node: Any) -> Iterator[str]:
    if isinstance(node, dict):
        url = node.get("url")
        if isinstance(url, str) and "archive.org" in url.lower():
            yield url
        for value in node.values():
            yield from _iter_archive_urls(value)
    elif isinstance(node, list):
        for value in node:
            yield from _iter_archive_urls(value)


def channel_archive_urls(channel: str) -> list[str]:
    path = ROOT / "data" / "unified" / f"{channel}.channel.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return list(dict.fromkeys(_iter_archive_urls(data)))


def video_geometry_fields(probe_data: dict[str, Any]) -> dict[str, Any]:
    """width/height/profile of the first video stream in ffprobe JSON."""
    for stream in probe_data.get("streams") or []:
        if stream.get("codec_type") != "video":
            continue
        fields: dict[str, Any] = {}
        width, height = stream.get("width"), stream.get("height")
        if isinstance(width, int) and isinstance(height, int) and width > 0 and height > 0:
            fields["width"] = width
            fields["height"] = height
        if stream.get("profile"):
            fields["profile"] = str(stream["profile"])
        return fields
    return {}


def _archive_cookie_header() -> Optional[str]:
    """Archive.org login cookies for gated/inappropriate items (CDN 401 without them)."""
    try:
        from streamtv.streaming.stream_manager import StreamManager

        adapter = StreamManager().archive_org_adapter
        return adapter.ffmpeg_cookie_header() if adapter else None
    except Exception as exc:
        print(f"    archive cookies unavailable: {exc}")
        return None


async def probe_with_geometry(
    streamer: MPEGTSStreamer, url: str, *, timeout: float
) -> Optional[dict[str, Any]]:
    """One ffprobe: streamer codec parsing plus video geometry fields."""
    cmd = [
        config.ffmpeg.ffprobe_path or "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        "-timeout", FFPROBE_SOCKET_TIMEOUT_US,
        "-probesize", FFPROBE_PROBESIZE,
        "-analyzeduration", FFPROBE_ANALYZEDURATION,
        "-user_agent", FFPROBE_USER_AGENT,
    ]
    # Same Cookie -headers path as mpegts_streamer Archive inputs — required for
    # adult/inappropriate-gated IA items (unauthenticated probe looks like 401).
    if "archive.org" in url.lower():
        cookie_header = _archive_cookie_header()
        if cookie_header:
            cmd.extend(["-headers", f"Cookie: {cookie_header}\r\n"])
    cmd.append(url)
    process = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        print(f"    ffprobe timeout after {timeout:.0f}s")
        return None
    if process.returncode != 0 or not stdout:
        print(f"    ffprobe rc={process.returncode} {stderr.decode(errors='replace')[:200]}")
        return None
    try:
        probe_data = json.loads(stdout.decode())
    except json.JSONDecodeError as exc:
        print(f"    ffprobe JSON invalid: {exc}")
        return None
    info = streamer._parse_ffprobe_json(probe_data, url)
    if not info:
        return None
    info.update(video_geometry_fields(probe_data))
    return info


def filter_urls_by_identifier(urls: list[str], identifiers: list[str]) -> list[str]:
    """Keep URLs whose Archive identifier is in identifiers (empty = no filter)."""
    if not identifiers:
        return urls
    wanted = set(identifiers)
    kept: list[str] = []
    for url in urls:
        key = archive_probe_cache.archive_item_key(url)
        if key and key[0] in wanted:
            kept.append(url)
    return kept


async def _warm_one(
    streamer: MPEGTSStreamer,
    url: str,
    *,
    apply: bool,
    timeout: float,
    sem: asyncio.Semaphore,
) -> int:
    """Probe/save one URL. Returns 1 on failure, 0 otherwise."""
    name = url.rsplit("/", 1)[-1][:70]
    async with sem:
        cached = archive_probe_cache.load(url)
        geometry = archive_probe_cache.video_geometry(cached)
        if cached and geometry:
            print(f"  cached  {name} {geometry[0]}x{geometry[1]}", flush=True)
            return 0
        reason = "no geometry" if cached else "no sidecar"
        if not apply:
            print(f"  WOULD_PROBE {name} ({reason})", flush=True)
            return 0
        t0 = time.monotonic()
        info = await probe_with_geometry(streamer, url, timeout=timeout)
        elapsed = time.monotonic() - t0
        if not info or not archive_probe_cache.save(url, info):
            print(f"  MISS    {name} ({elapsed:.1f}s)", flush=True)
            return 1
        print(
            f"  saved   {name} video={info.get('video_codec')} "
            f"{info.get('width', '?')}x{info.get('height', '?')} "
            f"profile={info.get('profile')} "
            f"audio={info.get('audio_codec')} copy_v={info.get('can_copy_video')} "
            f"({elapsed:.1f}s)",
            flush=True,
        )
        return 0


async def _warm(
    urls: list[str], *, apply: bool, timeout: float, concurrency: int
) -> int:
    streamer = MPEGTSStreamer.__new__(MPEGTSStreamer)
    sem = asyncio.Semaphore(max(1, concurrency))
    results = await asyncio.gather(
        *[
            _warm_one(streamer, url, apply=apply, timeout=timeout, sem=sem)
            for url in urls
        ]
    )
    return sum(results)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--channel", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--timeout", type=float, default=DEFAULT_PROBE_TIMEOUT_SEC)
    parser.add_argument(
        "--identifier",
        action="append",
        default=[],
        help="Only warm this Archive identifier (repeatable)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Parallel ffprobe workers (default 1)",
    )
    args = parser.parse_args()

    urls = filter_urls_by_identifier(
        channel_archive_urls(args.channel), args.identifier
    )
    print(
        f"warm archive probe cache channel={args.channel} urls={len(urls)} "
        f"apply={args.apply} identifiers={args.identifier or 'ALL'} "
        f"concurrency={args.concurrency}"
    )
    failures = asyncio.run(
        _warm(
            urls,
            apply=args.apply,
            timeout=args.timeout,
            concurrency=args.concurrency,
        )
    )
    print(f"done failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
