# Archive probe retry + keepalive auto-heal

**Status:** shipped (private tip / production Studio + Mini). Lesson **41b**.

Multi-gigabyte Archive.org CDN MP4s can miss StreamTV’s **5 s** quick ffprobe even when
the file is already **H.264 + AAC**. Issue **23** correctly refuses blind copy, so a
probe miss used to force **libx264** — which often produced only HDHomeRun
**keepalive (~8192 B)** until Plex/Apple TV abandoned the tune (~25 s). The external
stall healer’s old **300 s** etime floor also skipped those wedges.

This guide covers the **two-layer** fix: safer Archive probe escalation, then
automatic unstick if a tune still wedges.

## Layer A — Archive probe escalation (bedrock)

In `mpegts_streamer._detect_input_codec` (Archive HTTP only):

1. First `_quick_ffprobe_codec` (**5 s**).
2. On miss: **one** retry at **15 s** with a larger probesize/analyzeduration.
3. Prefer a large enough ring-buffer `.part` for the retry when present; if that
   miss, still retry the **CDN** URL (incomplete `.part` must not skip CDN).
4. Only then call `_infer_mp4_codec_defaults` (force libx264+AAC).
5. Never invent copy without a successful probe (Issue 23 stays).

Kickstart `com.streamtv` after upgrading — soft-deploy does **not** reload modules.

```mermaid
flowchart TD
  tune[Plex / HDHomeRun Archive item] --> q5[Quick ffprobe 5s]
  q5 -->|h264/aac| copy[FFmpeg copy MPEG-TS]
  q5 -->|miss| ring{Ring .part large enough?}
  ring -->|yes| r15[ffprobe 15s on .part]
  ring -->|no| c15[ffprobe 15s on CDN]
  r15 -->|ok| copy
  r15 -->|miss| c15
  c15 -->|ok| copy
  c15 -->|miss| infer[Issue 23: force libx264+AAC]
  copy --> media[Real TS bytes ≫ 8192]
  infer --> risk[Slow first TS / keepalive risk]
  risk --> plexFail[Plex may drop ~25s]
  risk --> layerB[Layer B heal]
```

## Layer B — automatic unstick (ops)

LaunchAgent `com.streamtv.stalled-ffmpeg-heal` every **~120 s**:

1. `heal_stalled_ffmpeg.py` — archive.org ffmpeg, not overlay/burn, pcpu≤**0.15**,
   etime≥**90 s** (was 300) → SIGTERM.
2. `heal_keepalive_tunes.py` — sample configured `/auto/v*` (~12 s); if
   **KEEPALIVE_ONLY** (~8192), kill matching stalled ffmpeg and
   `POST …/stream-restart` (soft).

```mermaid
flowchart TD
  LA[com.streamtv.stalled-ffmpeg-heal @ 120s] --> H1[heal_stalled_ffmpeg]
  H1 -->|etime≥90 low CPU archive| Kill[SIGTERM ffmpeg]
  LA --> H2[heal_keepalive_tunes]
  H2 --> Sample[GET /auto/vN ~12s]
  Sample -->|bytes ≫ 8192| OK[Leave alone]
  Sample -->|KEEPALIVE_ONLY| Kill
  Kill --> Soft[POST stream-restart]
  Soft --> CM[ChannelManager respawns item]
```

Install / refresh:

```bash
bash scripts/install-stalled-ffmpeg-heal-launchagent.sh
```

Env: `STREAMTV_STALL_HEAL_MIN_ETIME=90`, `STREAMTV_STALL_HEAL_MAX_PCPU=0.15`.

## Operator verify

```bash
# Expect bytes ≫ 8192 and h264/aac — never treat 8192 as success
curl -s -m 60 -o /tmp/soak.ts -w "bytes=%{size_download}\n" "http://127.0.0.1:8410/auto/vCHANNEL"
ffprobe -v error -show_entries stream=codec_name -of csv=p=0 /tmp/soak.ts

./venv/bin/python3 scripts/heal_stalled_ffmpeg.py --dry-run
./venv/bin/python3 scripts/heal_keepalive_tunes.py --dry-run
```

Logs to expect on success: `Archive.org probe retry ok … (cdn|ring)` and
`Smart copy mode` / FFmpeg `-c:v copy -c:a copy`.

**Caveat:** mid-item Archive `-ss` into a cold multi‑GB CDN object can still mean
~30 s of keepalive before first TS; Layer B recovers if the first Plex zap drops.

## Related

- [FFMPEG_STALL_KEEPALIVE.md](FFMPEG_STALL_KEEPALIVE.md) — Lesson 41 mid-stream stall
- [STREAMING_RESILIENCE_OPS.md](STREAMING_RESILIENCE_OPS.md) — keep-warm + heal cadence
- [ARCHITECTURE.md](../../ARCHITECTURE.md) — MPEG-TS remux / probe policy diagram
- Wiki: [Streaming-Resilience-Ops](../wiki/Streaming-Resilience-Ops.md) ·
  [Scripts-and-Tools](../wiki/Scripts-and-Tools.md)
- Skill: `.cursor/skills/heal-stalled-ffmpeg-keepalive`
- Lessons: **41**, **41b** (private `LESSONS_LEARNED.md`)
