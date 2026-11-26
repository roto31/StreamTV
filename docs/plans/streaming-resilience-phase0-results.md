# Streaming Resilience — Phase 0 Results

**Date:** 2026-11-25 (~11:49–11:52 CST)  
**Host:** Mac Studio (production)  
**Charter:** [streaming-resilience-scope.md](streaming-resilience-scope.md)

## Listener / log anchor

| Field | Value |
|-------|-------|
| PID | 69417 |
| LaunchAgent | `com.streamtv` running |
| cwd | `/Volumes/SSD Storage/XCode Projects/StreamTV` |
| Started | 2026-11-24 20:52:48 / log marker `Started server process [69417]` at 20:52:59 |
| Log file | `~/Library/Logs/StreamTV/streamtv-2026-11-24.log` |
| Health | `GET /health` 200 |

## Healers installed

| Agent | Result |
|-------|--------|
| `com.streamtv.stalled-ffmpeg-heal` | **Installed** — every 120s + RunAtLoad; criteria archive.org ffmpeg, etime≥300s, pcpu≤0.15 |
| Dry-run `heal_stalled_ffmpeg.py` | `no stalled archive ffmpeg` (at install time; later soak found a young 0% CPU process under 300s etime) |
| `com.streamtv.tunarr-ram-heal` | **Refreshed/running** — 60s; max_used_pct=45, max_used_gb=1.7, min_free_mb=300 |
| `verify_tunarr_ram.sh` | **PASSED** — TunarrRAM 2.0 GiB, ~11 Mi used, ~99% free, part_files=1 |

## ERROR classes (post-kickstart slice)

From `streamtv-2026-11-24.log` after `2026-11-24 20:52:59` (29 ERROR lines):

| Class | Count |
|-------|------:|
| ffmpeg_stall | 9 |
| youtube_rename | 4 |
| youtube_enospace | 4 |
| youtube_other (incl. postprocess) | 4 |
| youtube_unavailable | 4 |
| other | 4 |

Confirms taxonomy **C** (stalls) and **D** (TunarrRAM / YouTube cache pressure earlier in the process lifetime).

## Soak baseline (1225 / 1128)

| Channel | Window | HTTP | Bytes | Codecs | Approx bitrate | Notes |
|---------|--------|------|------:|--------|----------------|-------|
| **1225** | 20 s | 200 | **8192** | — | — | **KEEPALIVE_ONLY** |
| **1225** | 45 s | 200 | **8192** | — | — | Still keepalive-only |
| **1128** | 20 s | 200 | 9 934 968 | h264 + aac | ~3.96 Mbps | Healthy |
| probe fleet (80/11/1929/1985) | 18 s | 200 | ≫8192 | h264+aac | — | `any_keepalive_only=false` |

Live FFmpeg at soak time:

- **1128** path: long-running Macy’s parade transcoder (pid 80830, ~50% CPU, etime ~1h49m) — healthy.
- **1225** path: new FFmpeg on `80s-christmas-specials-with-commercials` (pid 2951) flagged `stuck_zero_cpu: true` at etime ~1m34s — too young for external healer (≥300s); HDHR clients saw keepalive-only.

## Phase 0 exit criteria

| Criterion | Status |
|-----------|--------|
| Stall healer installed | Met |
| TunarrRAM verified / heal running | Met |
| Baseline numbers recorded | Met |
| No Studio `streamtv/` bedrock edits | Met |

## Implications for Phase 1+

- Phase 0 ops address **C** going forward; **1225 keepalive-only during item start** is live evidence of **A** (tune gap / stalled start) and must be measured on Mini.
- TunarrRAM is healthy **now** but 2 GiB + full-cache remains a **D** risk (ENOSPC earlier same process).
- Do not enable `STREAMTV_PLEX_VIDEO_HOLD_NATIVE` on Studio without Mini A/B.

---

*End Phase 0 results.*
