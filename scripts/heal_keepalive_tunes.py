#!/usr/bin/env python3
"""Heal keepalive-only HDHomeRun tunes (Archive FFmpeg wedge → Plex Playback Error).

Samples /hdhomerun/auto/v{N} (never video-hold wrapped, so hold bytes cannot
mask a wedge) for a short window. When a channel returns only ~8192 B
(null keepalive), kill matching stalled Archive.org FFmpeg (same criteria as
heal_stalled_ffmpeg.py) and soft-restart that channel so ChannelManager respawns.

Does not modify streaming bedrock. Safe with StreamTV running.

Usage:
  ./venv/bin/python3 scripts/heal_keepalive_tunes.py --dry-run
  ./venv/bin/python3 scripts/heal_keepalive_tunes.py --apply
  STREAMTV_KEEPALIVE_HEAL_CHANNELS=1984.2,1992.2,80 ./venv/bin/python3 \\
    scripts/heal_keepalive_tunes.py --apply
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
# Short default set for LaunchAgent cadence (~120s interval).
DEFAULT_CHANNELS = (
    "80",
    "1984.2",
    "1985",
    "1992.2",
)
TUNE_SEC = 12
KEEPALIVE_MAX_BYTES = 8192


def _load_heal_mod():
    path = ROOT / "scripts" / "heal_stalled_ffmpeg.py"
    spec = importlib.util.spec_from_file_location("heal_stalled_ffmpeg", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _channels() -> list[str]:
    raw = os.environ.get("STREAMTV_KEEPALIVE_HEAL_CHANNELS", "").strip()
    if raw:
        return [c.strip() for c in raw.split(",") if c.strip()]
    return list(DEFAULT_CHANNELS)


def _base_url() -> str:
    return os.environ.get("STREAMTV_BASE_URL") or os.environ.get(
        "STREAMTV_BASE", "http://127.0.0.1:8410"
    )


def sample_tune(channel: str, *, tune_sec: int, base: str) -> dict[str, Any]:
    url = f"{base.rstrip('/')}/hdhomerun/auto/v{channel}"
    out = Path(f"/tmp/streamtv_keepalive_heal_ch{channel}.ts")
    try:
        out.unlink(missing_ok=True)
    except TypeError:
        if out.exists():
            out.unlink()
    cmd = [
        "curl",
        "-s",
        "-m",
        str(tune_sec),
        "-o",
        str(out),
        "-w",
        "%{http_code} %{size_download}",
        url,
    ]
    t0 = time.monotonic()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.monotonic() - t0
    parts = (proc.stdout or "").strip().split()
    http = int(parts[0]) if parts else 0
    size = int(parts[1]) if len(parts) > 1 else (out.stat().st_size if out.exists() else 0)
    return {
        "channel": channel,
        "http": http,
        "bytes": size,
        "elapsed": round(elapsed, 2),
        "keepalive_only": http == 200 and 0 < size <= KEEPALIVE_MAX_BYTES,
        "curl_rc": proc.returncode,
    }


def soft_restart_channel(channel: str, *, base: str) -> dict[str, Any]:
    url = f"{base.rstrip('/')}/api/channels/by-number/{channel}/stream-restart"
    req = urllib.request.Request(url, method="POST", data=b"")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(body) if body else {}
            except json.JSONDecodeError:
                payload = {"raw": body[:200]}
            return {"ok": True, "status": resp.status, "body": payload}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"ok": False, "error": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--tune-sec",
        type=int,
        default=int(os.environ.get("STREAMTV_KEEPALIVE_HEAL_TUNE_SEC", str(TUNE_SEC))),
    )
    parser.add_argument(
        "--min-etime-sec",
        type=int,
        default=int(os.environ.get("STREAMTV_STALL_HEAL_MIN_ETIME", "90")),
    )
    parser.add_argument(
        "--max-pcpu",
        type=float,
        default=float(os.environ.get("STREAMTV_STALL_HEAL_MAX_PCPU", "0.15")),
    )
    args = parser.parse_args()
    if not args.dry_run and not args.apply:
        args.dry_run = True

    heal = _load_heal_mod()
    base = _base_url()
    channels = _channels()
    print(
        f"keepalive heal base={base} channels={channels} "
        f"tune_sec={args.tune_sec} dry_run={args.dry_run}"
    )

    healed = 0
    for ch in channels:
        sample = sample_tune(ch, tune_sec=args.tune_sec, base=base)
        print(
            f"  sample ch={ch} http={sample['http']} bytes={sample['bytes']} "
            f"keepalive_only={sample['keepalive_only']}"
        )
        if not sample["keepalive_only"]:
            continue

        cands = heal.list_candidates(args.min_etime_sec, args.max_pcpu)
        if not cands:
            print(f"  ch={ch}: keepalive-only but no stalled archive ffmpeg candidates")
            if args.apply:
                result = soft_restart_channel(ch, base=base)
                print(f"  ch={ch}: soft-restart → {result}")
                healed += 1 if result.get("ok") else 0
            else:
                print(f"  ch={ch}: WOULD soft-restart (no ffmpeg kill candidates)")
            continue

        for c in cands:
            action = "WOULD_KILL" if args.dry_run else "KILL"
            print(
                f"  {action} pid={c['pid']} pcpu={c['pcpu']} "
                f"etime={c['etime']} src={c['src'][:90]}"
            )
            if args.apply:
                try:
                    os.kill(c["pid"], 9)
                except ProcessLookupError:
                    print(f"    already gone pid={c['pid']}")

        if args.apply:
            result = soft_restart_channel(ch, base=base)
            print(f"  ch={ch}: soft-restart → {result}")
            healed += 1
        else:
            print(f"  ch={ch}: WOULD soft-restart after kill")

    print(f"keepalive heal done healed={healed} dry_run={args.dry_run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
