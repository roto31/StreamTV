"""Public-safe troubleshooting / playback scripts catalog.

Shown in WebUI Settings → Troubleshooting and the macOS Settings panel.
Descriptions are written for hover/help tooltips. No lab IPs, home paths,
or private tokens — scripts use localhost / env overrides only.
"""

from __future__ import annotations

from typing import Any

# Keys:
#   name, description (short list blurb), hover (full tooltip),
#   script (path under scripts/), type, category,
#   runnable (API may execute), args (extra argv), timeout_sec,
#   shell (use bash for .sh), confirm (UI should confirm before run)
TROUBLESHOOTING_SCRIPTS: dict[str, dict[str, Any]] = {
    # --- Built-in diagnostics (inline fallbacks in api/scripts.py if file missing) ---
    "check_python": {
        "name": "Check Python",
        "description": "Verify the Python interpreter StreamTV is using.",
        "hover": "Reports Python version and executable path. Use when imports fail or the wrong venv is active.",
        "script": "check_python.py",
        "type": "diagnostic",
        "category": "diagnostics",
        "runnable": True,
        "timeout_sec": 30,
    },
    "check_ffmpeg": {
        "name": "Check FFmpeg",
        "description": "Verify FFmpeg is installed and on PATH.",
        "hover": "Confirms ffmpeg is findable and prints its version line. Required for HDHomeRun MPEG-TS playout.",
        "script": "check_ffmpeg.py",
        "type": "diagnostic",
        "category": "diagnostics",
        "runnable": True,
        "timeout_sec": 30,
    },
    "check_database": {
        "name": "Check Database",
        "description": "Open the SQLite DB and count channels.",
        "hover": "Validates DB connectivity. Use after restore, migration, or 'database is locked' errors.",
        "script": "check_database.py",
        "type": "diagnostic",
        "category": "diagnostics",
        "runnable": True,
        "timeout_sec": 30,
    },
    "check_ports": {
        "name": "Check Ports",
        "description": "See whether StreamTV / HDHomeRun ports are in use.",
        "hover": "Checks the configured StreamTV port (usually 8410). In use usually means the server is already running.",
        "script": "check_ports.py",
        "type": "diagnostic",
        "category": "diagnostics",
        "runnable": True,
        "timeout_sec": 30,
    },
    "test_connectivity": {
        "name": "Test Source Connectivity",
        "description": "DNS and HTTPS reachability for YouTube / Archive.org.",
        "hover": "Resolves youtube.com, googlevideo.com, and archive.org and probes HTTPS. Use for black screens caused by network/DNS, not FFmpeg.",
        "script": "test_connectivity.py",
        "type": "diagnostic",
        "category": "diagnostics",
        "runnable": True,
        "timeout_sec": 60,
    },
    "repair_database": {
        "name": "Repair Database",
        "description": "Attempt SQLite integrity repair.",
        "hover": "Last-resort repair for a corrupted streamtv.db. Back up first. Prefer restore from Backup & Restore when possible.",
        "script": "repair_database.py",
        "type": "repair",
        "category": "maintenance",
        "runnable": True,
        "confirm": True,
        "timeout_sec": 120,
    },
    "clear_cache": {
        "name": "Clear Cache",
        "description": "Clear application cache entries (maintenance).",
        "hover": "Clears StreamTV application cache state. Does not delete your channel YAML. May force YouTube re-downloads on next tune.",
        "script": "clear_cache.py",
        "type": "maintenance",
        "category": "maintenance",
        "runnable": True,
        "confirm": True,
        "timeout_sec": 120,
    },
    # --- Playback / playout aids (public-safe repo scripts) ---
    "health_check": {
        "name": "Platform Health Check",
        "description": "Broad health report (API, components, recent issues).",
        "hover": "Runs scripts/health_check.py against the local server. Start here when several channels misbehave at once.",
        "script": "health_check.py",
        "type": "diagnostic",
        "category": "playback",
        "runnable": True,
        "timeout_sec": 120,
    },
    "probe_hdhr_hang": {
        "name": "Probe HDHomeRun Hang",
        "description": "Sample /auto/v* sizes and look for stalled FFmpeg.",
        "hover": "Detects keepalive-only tunes (HTTP 200 but tiny payload) and 0% CPU FFmpeg wedges (Lesson 41). Safe read-only probe while StreamTV is running.",
        "script": "probe_hdhr_hang.py",
        "type": "diagnostic",
        "category": "playback",
        "runnable": True,
        "timeout_sec": 180,
    },
    "heal_stalled_ffmpeg_dry": {
        "name": "Heal Stalled FFmpeg (dry-run)",
        "description": "List Archive.org FFmpeg processes that look stalled.",
        "hover": "Dry-run of heal_stalled_ffmpeg.py — reports candidates that match the keepalive wedge criteria without killing processes.",
        "script": "heal_stalled_ffmpeg.py",
        "args": ["--dry-run"],
        "type": "diagnostic",
        "category": "playback",
        "runnable": True,
        "timeout_sec": 60,
    },
    "heal_stalled_ffmpeg_apply": {
        "name": "Heal Stalled FFmpeg (apply)",
        "description": "Kill stalled Archive.org FFmpeg so playout can advance.",
        "hover": "Applies Lesson 41 heal: terminates matching stalled archive.org ffmpeg processes so ChannelManager can respawn. Confirm before running. Skips overlay/DVD burn encodes.",
        "script": "heal_stalled_ffmpeg.py",
        "args": ["--apply"],
        "type": "repair",
        "category": "playback",
        "runnable": True,
        "confirm": True,
        "timeout_sec": 60,
    },
    "heal_keepalive_tunes_dry": {
        "name": "Heal Keepalive Tunes (dry-run)",
        "description": "Sample HDHR channels for keepalive-only wedges without killing.",
        "hover": "Samples /auto/v* (~12s). If only ~8192 B null keepalive, reports stalled archive ffmpeg kill candidates and would soft-restart the channel (1984.2 class).",
        "script": "heal_keepalive_tunes.py",
        "args": ["--dry-run"],
        "type": "diagnostic",
        "category": "playback",
        "runnable": True,
        "timeout_sec": 180,
    },
    "heal_keepalive_tunes_apply": {
        "name": "Heal Keepalive Tunes (apply)",
        "description": "Kill stalled Archive FFmpeg and soft-restart keepalive-only channels.",
        "hover": "When a sampled channel is keepalive-only, SIGKILLs matching stalled archive.org ffmpeg (etime≥90s) and POSTs stream-restart. Confirm before running.",
        "script": "heal_keepalive_tunes.py",
        "args": ["--apply"],
        "type": "repair",
        "category": "playback",
        "runnable": True,
        "confirm": True,
        "timeout_sec": 180,
    },
    "prewarm_youtube_cache": {
        "name": "Pre-warm YouTube Cache",
        "description": "Pull a few YouTube channels so SSD cache is warm before Plex.",
        "hover": "Sequentially tunes sample YouTube-primary channels via localhost HDHomeRun so full-cache downloads finish before evening Live TV. Do not run many at once; waits per channel. Uses --seconds 25 on a short channel list when launched from the UI.",
        "script": "prewarm_youtube_cache.py",
        "args": ["--seconds", "25", "--channels", "1986,1987,1991", "--min-bytes", "500000"],
        "type": "maintenance",
        "category": "playback",
        "runnable": True,
        "confirm": True,
        "timeout_sec": 300,
    },
    "deploy_soft": {
        "name": "Soft Deploy (restart streams)",
        "description": "Restart channel streams inside the running server.",
        "hover": "Runs deploy_soft.sh — recycles ChannelManager streams without reloading Python. Use after schedule/YAML import. Full kickstart is still required after streamtv/ code or LaunchAgent env changes.",
        "script": "deploy_soft.sh",
        "shell": True,
        "type": "repair",
        "category": "playback",
        "runnable": True,
        "confirm": True,
        "timeout_sec": 180,
    },
    "check_core_dependency_freshness": {
        "name": "Check yt-dlp / Dependency Floors",
        "description": "Verify yt-dlp version and YouTube player-client policy.",
        "hover": "Issue 73 freshness gate: yt-dlp floor, banned player clients, optional PyPI lag. Run after YouTube 403 storms or dependency upgrades.",
        "script": "check_core_dependency_freshness.py",
        "type": "diagnostic",
        "category": "playback",
        "runnable": True,
        "timeout_sec": 90,
    },
    "verify_plex_aac_codecs": {
        "name": "Verify Plex AAC Codecs",
        "description": "Check PMS has the AAC decoder needed for Live TV.",
        "hover": "Looks for libaac_decoder.dylib under Plex Media Server. Missing AAC often shows as Playback Error even when StreamTV MPEG-TS is healthy (Issue 72).",
        "script": "verify_plex_aac_codecs.sh",
        "shell": True,
        "type": "diagnostic",
        "category": "playback",
        "runnable": True,
        "timeout_sec": 60,
    },
    "kickstart_with_prewarm": {
        "name": "Kickstart + Pre-warm (Terminal)",
        "description": "Full LaunchAgent kickstart then YouTube pre-warm.",
        "hover": "bash scripts/kickstart_streamtv_with_prewarm.sh — restarts com.streamtv then pre-warms YouTube cache. Not runnable from the WebUI (would kill this request). Run in Terminal after config/module changes.",
        "script": "kickstart_streamtv_with_prewarm.sh",
        "shell": True,
        "type": "maintenance",
        "category": "playback",
        "runnable": False,
        "timeout_sec": 600,
    },
}


def get_script(script_id: str) -> dict[str, Any] | None:
    entry = TROUBLESHOOTING_SCRIPTS.get(script_id)
    if entry is None:
        return None
    return {"id": script_id, **entry}


def list_scripts_public() -> dict[str, dict[str, Any]]:
    """Return catalog entries safe to expose in API/UI (all current entries are public-safe)."""
    out: dict[str, dict[str, Any]] = {}
    for script_id, meta in TROUBLESHOOTING_SCRIPTS.items():
        out[script_id] = {
            "id": script_id,
            "name": meta["name"],
            "description": meta["description"],
            "hover": meta.get("hover") or meta["description"],
            "script": meta["script"],
            "type": meta.get("type", "diagnostic"),
            "category": meta.get("category", "diagnostics"),
            "runnable": bool(meta.get("runnable", True)),
            "confirm": bool(meta.get("confirm", False)),
            "timeout_sec": int(meta.get("timeout_sec", 60)),
        }
    return out
