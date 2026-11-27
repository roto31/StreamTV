#!/usr/bin/env python3
"""Probe HDHomeRun hang: tune sizes + stuck ffmpeg (0% CPU) → debug NDJSON log.

Does not modify streaming bedrock. Safe to run while StreamTV is up.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / ".cursor" / "debug-aded3c.log"
CHANNELS = (80, 11, 1929, 1985)
TUNE_SEC = 18
BASE = os.environ.get("STREAMTV_BASE", "http://127.0.0.1:8410")


def log(hypothesis_id: str, message: str, data: dict) -> None:
    # #region agent log
    LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "sessionId": "aded3c",
        "runId": "hang-repro",
        "hypothesisId": hypothesis_id,
        "location": "probe_hdhr_hang.py",
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    # #endregion
    print(json.dumps({"hypothesisId": hypothesis_id, "message": message, **data}))


def tune(channel: int) -> dict:
    url = f"{BASE}/hdhomerun/auto/v{channel}"
    out = Path(f"/tmp/streamtv_hang_ch{channel}.ts")
    try:
        out.unlink(missing_ok=True)
    except TypeError:
        if out.exists():
            out.unlink()
    cmd = [
        "curl",
        "-s",
        "-m",
        str(TUNE_SEC),
        "-o",
        str(out),
        "-w",
        "%{http_code} %{size_download}",
        url,
    ]
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - t0
    parts = (proc.stdout or "").strip().split()
    http = int(parts[0]) if parts else 0
    size = int(parts[1]) if len(parts) > 1 else (out.stat().st_size if out.exists() else 0)
    codecs = ""
    if size > 50_000:
        probe = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "stream=codec_name",
                "-of",
                "csv=p=0",
                str(out),
            ],
            capture_output=True,
            text=True,
        )
        codecs = (probe.stdout or "").replace("\n", ",")
    return {
        "channel": channel,
        "http": http,
        "bytes": size,
        "elapsed": round(elapsed, 2),
        "curl_rc": proc.returncode,
        "codecs": codecs,
        "keepalive_only": size <= 8192,
    }


def ffmpeg_snapshot() -> list[dict]:
    rows = []
    try:
        out = subprocess.check_output(
            ["ps", "-axo", "pid=,pcpu=,etime=,state=,command="],
            text=True,
        )
    except subprocess.CalledProcessError:
        return rows
    for line in out.splitlines():
        if "ffmpeg" not in line or ("external HLS" in line.lower() and "streamtv" not in line.lower()):
            # keep StreamTV archive ffmpeg; skip pure external HLS if clearly separate
            pass
        if "/opt/homebrew/bin/ffmpeg" not in line and "Cellar/ffmpeg" not in line:
            continue
        if "Bedknobs" in line or "TunarrRAM/stream_" in line:
            continue
        parts = line.strip().split(None, 4)
        if len(parts) < 5:
            continue
        pid, pcpu, etime, state, cmd = parts
        src = ""
        if " -i " in cmd:
            src = cmd.split(" -i ", 1)[1][:120]
        rows.append(
            {
                "pid": int(pid),
                "pcpu": float(pcpu),
                "etime": etime,
                "state": state,
                "src": src,
                "stuck_zero_cpu": float(pcpu) == 0.0 and "archive.org" in cmd,
            }
        )
    return rows


def main() -> int:
    tunes = [tune(c) for c in CHANNELS]
    ff = ffmpeg_snapshot()
    stuck = [r for r in ff if r.get("stuck_zero_cpu")]
    log(
        "H1",
        "tune + ffmpeg snapshot",
        {
            "tunes": tunes,
            "ffmpeg_streamtvish": ff,
            "stuck_archive_ffmpeg": stuck,
            "any_keepalive_only": any(t["keepalive_only"] for t in tunes),
        },
    )
    # TunarrRAM free
    try:
        st = os.statvfs("/Volumes/TunarrRAM")
        free_mi = (st.f_bavail * st.f_frsize) / (1024 * 1024)
    except OSError:
        free_mi = None
    log("H2", "TunarrRAM free MiB", {"free_mi": free_mi})
    # stale pilot pid
    pilot = ROOT / ".streamtv-pilot.pid"
    if pilot.exists():
        pid = int(pilot.read_text().strip() or "0")
        try:
            cmd = subprocess.check_output(["ps", "-p", str(pid), "-o", "command="], text=True).strip()
        except subprocess.CalledProcessError:
            cmd = "DEAD"
        log(
            "H3",
            "pilot pidfile check",
            {"pid": pid, "command": cmd[:160], "stale_non_streamtv": "streamtv" not in cmd.lower()},
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
