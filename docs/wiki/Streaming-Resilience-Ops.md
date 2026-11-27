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
  Prefetch --> AutoWarm["idle auto-warm / evening LA"]
  AutoWarm --> Ready["Cache READY"]
  Ready --> Plex["Plex Live TV"]
  Dead["F-class quarantine"] --> Ready
  Probe["Archive probe 5s + 15s retry"] --> Copy["H.264/AAC copy when verified"]
  Copy --> Plex
  Stall["heal_stalled_ffmpeg etime≥90 + keepalive bridge"] --> Soft["soft stream-restart"]
  Soft --> Plex
  P3["Phase 3a–3f bedrock"] -.->|"PARKED"| SSD
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

## Troubleshooting UI

Settings → **Troubleshooting** (Web UI + macOS app) lists public-safe scripts with hover help — see [Scripts-and-Tools](Scripts-and-Tools).
