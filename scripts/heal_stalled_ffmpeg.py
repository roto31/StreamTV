#!/usr/bin/env python3
"""Kill StreamTV Archive.org FFmpeg processes that have stalled (keepalive wedge).

Lesson 41 (2026-07-21): Mid-stream Archive.org FFmpeg can sit at ~0% CPU for hours
with no TCP while ChannelManager still believes the item is playing. HDHomeRun then
serves only MPEG-TS null keepalives (~8192 B) and Plex/Apple TV drops to the guide.

This healer is the external belt for the in-process stall timeout in
mpegts_streamer.py (STREAMTV_FFMPEG_STALL_SEC).

Criteria (all must match):
  - Command is Homebrew ffmpeg with archive.org / ia*.archive.org input
  - Not external HLS (TunarrRAM/stream_*, Bedknobs, ffmpeg@7 path)
  - Not DVD/PGS burn or overlay encodes (-filter_complex / overlay / subtitles=)
  - etime >= --min-etime-sec (default 90; was 300 — Plex dies ~25s on keepalive)
  - pcpu <= --max-pcpu (default 0.15)

Usage:
  ./venv/bin/python3 scripts/heal_stalled_ffmpeg.py --dry-run
  ./venv/bin/python3 scripts/heal_stalled_ffmpeg.py --apply
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEBUG_LOG = ROOT / ".cursor" / "debug-aded3c.log"

ETIME_RE = re.compile(
    r"^(?:(?:(\d+)-)?(\d+):)?(\d+):(\d+)$"  # [[dd-]hh:]mm:ss
)


def _agent_log(message: str, data: dict[str, Any]) -> None:
    # #region agent log
    try:
        DEBUG_LOG.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "sessionId": "aded3c",
            "runId": "stalled-ffmpeg-heal",
            "hypothesisId": "H1",
            "location": "heal_stalled_ffmpeg.py",
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        with DEBUG_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload) + "\n")
    except Exception:
        pass
    # #endregion


def parse_etime_seconds(etime: str) -> int:
    etime = (etime or "").strip()
    m = ETIME_RE.match(etime)
    if not m:
        return 0
    days = int(m.group(1) or 0)
    hours = int(m.group(2) or 0)
    mins = int(m.group(3) or 0)
    secs = int(m.group(4) or 0)
    return days * 86400 + hours * 3600 + mins * 60 + secs


def is_streamtv_archive_ffmpeg(cmd: str) -> bool:
    if "ffmpeg" not in cmd:
        return False
    if "TunarrRAM/stream_" in cmd or "Bedknobs" in cmd or "Cellar/ffmpeg@7" in cmd:
        return False
    if "archive.org" in cmd or "us.archive.org" in cmd:
        return True
    # ia601007.us.archive.org style already matched; also plain iaNNNNN hosts
    if re.search(r"\bia\d+\.", cmd):
        return True
    return False


def is_realtime_copy(cmd: str) -> bool:
    """True for `-re` + video copy. That path sits near 0% CPU while playing.

    2026-11-27: pid 86829 (Tape 1, pcpu 0.1, etime 18:46) was SIGKILLed during a
    healthy Apple TV session (60633 chunks). Low CPU is the pacing, not a wedge.
    """
    if not cmd:
        return False
    if not re.search(r"(?:^|\s)-re(?:\s|$)", cmd):
        return False
    return "-c:v copy" in cmd or "-c copy" in cmd


def is_overlay_or_burn_encode(cmd: str) -> bool:
    """True for DVD/PGS burn / filter overlay — low CPU is normal; never SIGKILL.

    Live English overlay (channel subtitle_mode default) uses -filter_complex with
    overlay/subtitles=; quiet periods are not keepalive wedges (Lesson 41 false positive).
    """
    lower = (cmd or "").lower()
    if "-filter_complex" in lower:
        return True
    if "overlay" in lower:
        return True
    if "subtitles=" in lower:
        return True
    return False


def classify_candidate(
    cmd: str,
    *,
    min_etime_sec: int,
    max_pcpu: float,
    etime_sec: int,
    pcpu: float,
) -> str:
    """Return 'kill', 'skip_overlay', 'skip_live_copy', 'skip_not_archive', or 'skip_criteria'."""
    if not is_streamtv_archive_ffmpeg(cmd):
        return "skip_not_archive"
    if is_overlay_or_burn_encode(cmd):
        return "skip_overlay"
    if is_realtime_copy(cmd):
        return "skip_live_copy"
    if etime_sec < min_etime_sec or pcpu > max_pcpu:
        return "skip_criteria"
    return "kill"


def list_candidates(min_etime_sec: int, max_pcpu: float) -> list[dict[str, Any]]:
    out = subprocess.check_output(
        ["ps", "-axo", "pid=,pcpu=,etime=,command="],
        text=True,
    )
    found: list[dict[str, Any]] = []
    skipped_overlay = 0
    skipped_live = 0
    for line in out.splitlines():
        line = line.strip()
        if not line or "ffmpeg" not in line:
            continue
        parts = line.split(None, 3)
        if len(parts) < 4:
            continue
        pid_s, pcpu_s, etime, cmd = parts
        try:
            pid = int(pid_s)
            pcpu = float(pcpu_s)
        except ValueError:
            continue
        et_sec = parse_etime_seconds(etime)
        verdict = classify_candidate(
            cmd,
            min_etime_sec=min_etime_sec,
            max_pcpu=max_pcpu,
            etime_sec=et_sec,
            pcpu=pcpu,
        )
        if verdict == "skip_overlay":
            skipped_overlay += 1
            continue
        if verdict == "skip_live_copy":
            skipped_live += 1
            continue
        if verdict != "kill":
            continue
        src = ""
        if " -i " in cmd:
            src = cmd.split(" -i ", 1)[1][:140]
        found.append(
            {
                "pid": pid,
                "pcpu": pcpu,
                "etime": etime,
                "etime_sec": et_sec,
                "src": src,
            }
        )
    if skipped_overlay:
        print(f"skipped {skipped_overlay} overlay/burn ffmpeg (not kill candidates)")
    if skipped_live:
        print(f"skipped {skipped_live} live -re copy ffmpeg (low CPU is normal)")
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--min-etime-sec", type=int, default=int(os.environ.get("STREAMTV_STALL_HEAL_MIN_ETIME", "90")))
    parser.add_argument("--max-pcpu", type=float, default=float(os.environ.get("STREAMTV_STALL_HEAL_MAX_PCPU", "0.15")))
    args = parser.parse_args()
    if not args.dry_run and not args.apply:
        args.dry_run = True

    cands = list_candidates(args.min_etime_sec, args.max_pcpu)
    _agent_log(
        "stalled ffmpeg scan",
        {
            "count": len(cands),
            "dry_run": args.dry_run,
            "min_etime_sec": args.min_etime_sec,
            "max_pcpu": args.max_pcpu,
            "candidates": cands,
        },
    )
    if not cands:
        print("no stalled archive ffmpeg")
        return 0

    for c in cands:
        action = "WOULD_KILL" if args.dry_run else "KILL"
        print(f"{action} pid={c['pid']} pcpu={c['pcpu']} etime={c['etime']} src={c['src'][:90]}")
        if args.apply:
            try:
                os.kill(c["pid"], 9)
            except ProcessLookupError:
                print(f"  already gone pid={c['pid']}")
    _agent_log(
        "stalled ffmpeg heal done",
        {"killed": 0 if args.dry_run else len(cands), "dry_run": args.dry_run},
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
