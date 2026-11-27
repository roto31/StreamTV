# Streaming resilience ops

Phase **3** (frozen-path packages **3a–3f**) is **PARKED** as of 2026-11-25 for most
CDN-first experiments. Tip reliability still ships **ops + approved bedrock** for
cold YouTube auto-warm and **Archive probe retry / keepalive heal** (Lesson **41b**).

Full operator guide: [STREAMING_RESILIENCE_OPS.md](https://github.com/roto31/StreamTV/blob/main/docs/guides/STREAMING_RESILIENCE_OPS.md) ·
Archive probe feature: [ARCHIVE_PROBE_RETRY_KEEPALIVE.md](https://github.com/roto31/StreamTV/blob/main/docs/guides/ARCHIVE_PROBE_RETRY_KEEPALIVE.md) ·
Gate notes: [phase3-gate](https://github.com/roto31/StreamTV-source/blob/main/docs/plans/streaming-resilience-phase3-gate-20261125.md) (private plans may differ).

```mermaid
flowchart TD
  SSD["SSD youtube_full_cache"] --> Prefetch["prefetch_count + TTL"]
  Prefetch --> AutoWarm["idle auto-warm + LRU pin on-air"]
  AutoWarm --> Ready["Cache READY"]
  Ready --> Plex["Plex Live TV"]
  Dead["F-class quarantine"] --> Ready
  Probe["Archive probe 5s + 15s retry + cookie warm"] --> Copy["H.264/AAC copy when verified"]
  Copy --> Plex
  HEVC["HEVC Archive"] -->|"accept encode"| Xcode["libx264 path"]
  Xcode --> Plex
  Trickle["under-rate copy <16KiB/s"] --> Abort["abort FFmpeg"]
  Stall["heal_stalled_ffmpeg etime≥90 + keepalive bridge"] --> Soft["soft stream-restart"]
  Abort --> Soft
  Soft --> Plex
  P3["Phase 3a–3f bedrock"] -.->|"PARKED"| SSD
  DP["HEVC MPEG-TS Direct Play"] -.->|"Studio HOLD — Mini soak only"| Plex
```

## Archive probe miss → keepalive (Lesson 41b)

Multi-GB Archive CDN objects can miss the 5 s quick ffprobe → Issue 23 force-transcode
→ HDHomeRun **8192** keepalive until Plex drops. Tip retries probe once (ring `.part`
then CDN), and the stall LaunchAgent heals residual 0% CPU / keepalive-only tunes.

```mermaid
flowchart LR
  Miss["5s probe miss"] --> Retry["15s ring then CDN"]
  Retry -->|ok| Copy["copy MPEG-TS"]
  Retry -->|fail| Xcode["libx264 force"]
  Xcode --> Keep["keepalive risk"]
  Keep --> Heal["heal LA @ 120s"]
```

## Non-faststart Archive slow open (Lesson 41c)

Some multi-GB Archive MP4s keep the `moov` index at the file tail, so a cold open takes
~40–55 s. Allowlisted channels (`STREAMTV_PLEX_VIDEO_HOLD_ARCHIVE_CHANNELS`, e.g. `1984.2`)
show real hold video immediately and splice to the program once FFmpeg delivers. A probe
sidecar cache keeps copy mode consistent, and Archive inputs get a 60 s first-chunk budget.

```mermaid
flowchart LR
  Tune["Plex tune"] --> Hold["hold h264/aac < 1s"]
  Tune --> Side["probe sidecar → copy"]
  Side --> Open["FFmpeg opens tail moov ~40-55s"]
  Open --> Splice["splice to program (no re-hold)"]
  Hold --> Splice
```

Seed sidecars: `scripts/warm_archive_probe_cache.py --channel N --apply` (cookie-aware).
Details: [Layer C](https://github.com/roto31/StreamTV/blob/main/docs/guides/ARCHIVE_PROBE_RETRY_KEEPALIVE.md#layer-c--non-faststart-slow-open-lesson-41c) ·
[Layer B2 under-rate](https://github.com/roto31/StreamTV/blob/main/docs/guides/ARCHIVE_PROBE_RETRY_KEEPALIVE.md#layer-b2--under-rate-copy-trickle-plex-black) ·
[Layer D auth inventory](https://github.com/roto31/StreamTV/blob/main/docs/guides/ARCHIVE_PROBE_RETRY_KEEPALIVE.md#layer-d--inventory-vs-playback-auth-lesson-75).

## HEVC / Direct Play (decision)

Production **accepts encode** for HEVC Archive items. Do **not** enable HEVC
MPEG-TS copy / Live TV Direct Play on Studio until a Mini fork soak proves Plex
Apple TV Direct Play. Twin remaps are report-only / curated
(`scripts/report_archive_hevc_twins.py`).

## Troubleshooting UI

Settings → **Troubleshooting** (Web UI + macOS app) lists public-safe scripts with hover help — see [Scripts-and-Tools](Scripts-and-Tools).
