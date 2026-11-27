# Plex video hold (identity-preserving)

Apple TV / Plex Live TV cancels a tune when it does not see a **video** keyframe
within ~10 seconds. StreamTV’s MPEG-TS **null** keepalives (`PID 0x1FFF`, 8192
bytes) keep the HTTP socket open but do **not** count as video. This hold layer
emits a real **H.264 + AAC** MPEG-TS loop immediately, then splices to the
upstream StreamTV or external stream when it produces non-null TS packets.

## What stays the same

- StreamTV DeviceID, BaseURL (`:8410`), UDP **65001** discovery
- No new HDHomeRun device in Plex

## Components

| Piece | Role |
|-------|------|
| [`streamtv/tuners/video_hold.py`](../../streamtv/tuners/video_hold.py) | Hold mux: emit hold → splice → optional re-hold; YouTube wait-phase (`rehold=False`) |
| [`streamtv/main.py`](../../streamtv/main.py) `/auto/v*` | **YouTube wait-phase hold** when `STREAMTV_PLEX_VIDEO_HOLD_YOUTUBE=1` and `youtube_full_cache` + YouTube channel (**default off**). Full native re-hold only with `STREAMTV_PLEX_VIDEO_HOLD_NATIVE=1`. Archive CDN-first stays unwrapped unless listed in `STREAMTV_PLEX_VIDEO_HOLD_ARCHIVE_CHANNELS` (wait-phase, no re-hold; production `1984.2`; see [Layer C](ARCHIVE_PROBE_RETRY_KEEPALIVE.md#layer-c--non-faststart-slow-open-lesson-41c)). `/hdhomerun/auto/v*` is never wrapped. |
| `data/plex_hold.ts` | Pre-encoded 2s 720p loop (gitignored; generate below) |
| `scripts/generate_plex_hold_ts.sh` | Builds the hold file |

## TunarrRAM vs SSD

- **StreamTV cache** still uses `/Volumes/TunarrRAM/streamtv-cache` (+ universal healer: **45%** / **1.7 GiB** / **300 Mi** free).
- **external HLS/transcode** must use `~/Library/Caches/streamtv-transcode` (not TunarrRAM).

Set external → Settings → FFmpeg → Transcode directory, or edit
`~/Library/Preferences/external/settings.json` `settings.ffmpeg.transcodeDirectory`,
then restart external.app.

## Operator install

```bash
# 1) Hold asset
bash scripts/generate_plex_hold_ts.sh

# 2) external SSD heal LaunchAgent

# 3) After streamtv/ changes: full kickstart (not soft deploy)
launchctl kickstart -k "gui/$(id -u)/com.streamtv"
```

Disable hold everywhere: `STREAMTV_PLEX_VIDEO_HOLD=0` in the StreamTV LaunchAgent env.

`/auto/v*` behavior:

| Mode | Env | Behavior |
|------|-----|----------|
| **YouTube wait-phase (opt-in)** | `STREAMTV_PLEX_VIDEO_HOLD_YOUTUBE=1` | When `youtube_full_cache` is on and the channel’s on-air/playlist is YouTube, emit hold until first non-null video, then **never re-hold**. Archive CDN-first channels are not wrapped. **Default is off** (`0`) — cold full-cache waits otherwise use null keepalives. |
| Full native re-hold | `STREAMTV_PLEX_VIDEO_HOLD_NATIVE=1` | Hold + re-hold on silence for all `/auto/v*` (risk: Archive copy-mode black freeze). Default **off**. |
| Off (default for YouTube wait) | `STREAMTV_PLEX_VIDEO_HOLD_YOUTUBE=0` (or unset) and native unset | Null keepalives only during waits (Plex may return to guide on long cold caches). |


Silence before re-hold (external / native full mode) defaults to **45s**. Override with
`STREAMTV_PLEX_HOLD_SILENCE_SEC`.

## Verify

```bash
# YouTube music channel: first bytes should be hold h264, not 8192-byte nulls
curl -s -m 8 -o /tmp/hold_probe.ts -w 'HTTP %{http_code} size=%{size_download}\n' \
  'http://127.0.0.1:8410/auto/v1987'
ffprobe -v error -show_entries stream=codec_type,codec_name -of default=nw=1 /tmp/hold_probe.ts

# Archive Magnum should stay CDN-first (no YouTube wait wrap)
curl -s -m 8 -o /tmp/arch_probe.ts -w 'HTTP %{http_code} size=%{size_download}\n' \
  'http://127.0.0.1:8410/auto/v80'

# SSD healer dry-run
```

**Pass (YouTube):** `size_download` ≫ 8192, `h264` + `aac` within ~2s; log
`video_hold: YouTube wait-phase wrap`. Apple TV cold tune stays on channel.
**Pass (Archive):** real program TS after brief keepalive; no wait-phase wrap log.
**Pass (allowlisted Archive, e.g. 1984.2):** TTFB < 1 s with hold h264/aac; log
`video_hold: Archive wait-phase wrap` then `spliced to upstream (… rehold=False)`.

## Related

- [TunarrRAM recovery](TUNARRRAM_PLAYOUT_RECOVERY.md)
- [FFmpeg stall / keepalive](FFMPEG_STALL_KEEPALIVE.md) — mid-stream FFmpeg 0% CPU
- Rule `plex-hdhomerun-tuning.mdc` — null keepalive vs video hold
