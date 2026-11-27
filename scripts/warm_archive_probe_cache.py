#!/usr/bin/env python3
"""Seed Archive.org probe sidecars for a channel (Lesson 41c).

Runs a long ffprobe (default 90s) on each Archive URL in
data/unified/<channel>.channel.yaml that lacks a fresh sidecar, and stores real
codec results via streamtv.utils.archive_probe_cache. Live tunes then skip the
5s/15s/15s probe chain that non-faststart multi-GB MP4s always miss.

Read-only toward the running server; safe with StreamTV running.

Usage:
  ./venv/bin/python3 scripts/warm_archive_probe_cache.py --channel 1984.2
  ./venv/bin/python3 scripts/warm_archive_probe_cache.py --channel 1984.2 --apply
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path
from typing import Any, Iterator

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from streamtv.streaming.mpegts_streamer import MPEGTSStreamer  # noqa: E402
from streamtv.utils import archive_probe_cache  # noqa: E402

DEFAULT_PROBE_TIMEOUT_SEC = 90.0


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


async def _warm(urls: list[str], *, apply: bool, timeout: float) -> int:
    streamer = MPEGTSStreamer.__new__(MPEGTSStreamer)
    failures = 0
    for url in urls:
        name = url.rsplit("/", 1)[-1][:70]
        if archive_probe_cache.load(url):
            print(f"  cached  {name}")
            continue
        if not apply:
            print(f"  WOULD_PROBE {name}")
            continue
        t0 = time.monotonic()
        info = await streamer._quick_ffprobe_codec(url, timeout=timeout)
        elapsed = time.monotonic() - t0
        if not info or not archive_probe_cache.save(url, info):
            failures += 1
            print(f"  MISS    {name} ({elapsed:.1f}s)")
            continue
        print(
            f"  saved   {name} video={info.get('video_codec')} "
            f"audio={info.get('audio_codec')} copy_v={info.get('can_copy_video')} "
            f"({elapsed:.1f}s)"
        )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--channel", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--timeout", type=float, default=DEFAULT_PROBE_TIMEOUT_SEC)
    args = parser.parse_args()

    urls = channel_archive_urls(args.channel)
    print(f"warm archive probe cache channel={args.channel} urls={len(urls)} apply={args.apply}")
    failures = asyncio.run(_warm(urls, apply=args.apply, timeout=args.timeout))
    print(f"done failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
