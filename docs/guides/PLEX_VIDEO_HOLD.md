# Plex video hold (identity-preserving)

Apple TV / Plex Live TV cancels a tune when it does not see a **video** keyframe
within ~10 seconds. StreamTV’s MPEG-TS **null** keepalives (`PID 0x1FFF`, 8192
bytes) keep the HTTP socket open but do **not** count as video. This hold layer
emits a real **H.264 + AAC** MPEG-TS loop immediately, then splices to the
upstream StreamTV or Tunarr stream when it produces non-null TS packets.

## What stays the same

- StreamTV DeviceID, BaseURL (`:8410`), UDP **65001** discovery
- Tunarr-in-Plex paste URL: `http://<lan>:8410/tuners/proxy/tunarr`
- No new HDHomeRun device in Plex

## Components

| Piece | Role |
|-------|------|
| [`streamtv/tuners/video_hold.py`](../../streamtv/tuners/video_hold.py) | Hold mux: emit hold → splice → optional re-hold; YouTube wait-phase (`rehold=False`) |
| [`streamtv/main.py`](../../streamtv/main.py) `/auto/v*` | **YouTube wait-phase hold** when `youtube_full_cache` + YouTube channel (default). Full native re-hold only with `STREAMTV_PLEX_VIDEO_HOLD_NATIVE=1`. Archive CDN-first stays unwrapped. |
| [`streamtv/api/tuner_manager.py`](../../streamtv/api/tuner_manager.py) | Proxies Tunarr video under same BaseURL + hold |
| `data/plex_hold.ts` | Pre-encoded 2s 720p loop (gitignored; generate below) |
| `scripts/generate_plex_hold_ts.sh` | Builds the hold file |
| `scripts/heal_tunarr_ssd_transcode.py` | Caps Tunarr SSD transcode dir |
| `com.streamtv.tunarr-ssd-transcode-heal` | LaunchAgent every 120s |

## TunarrRAM vs SSD

- **StreamTV cache** still uses `/Volumes/TunarrRAM/streamtv-cache` (+ existing 55% healer).
- **Tunarr HLS/transcode** must use `~/Library/Caches/tunarr-transcode` (not TunarrRAM).
- SSD caps: **`STREAMTV_TUNARR_SSD_MAX_GB=4`**, **`STREAMTV_TUNARR_SSD_MIN_FREE_GB=20`**.

Set Tunarr → Settings → FFmpeg → Transcode directory, or edit
`~/Library/Preferences/tunarr/settings.json` `settings.ffmpeg.transcodeDirectory`,
then restart Tunarr.app.

## Operator install

```bash
# 1) Hold asset
bash scripts/generate_plex_hold_ts.sh

# 2) Tunarr SSD heal LaunchAgent
bash scripts/install-tunarr-ssd-transcode-heal-launchagent.sh

# 3) After streamtv/ changes: full kickstart (not soft deploy)
launchctl kickstart -k "gui/$(id -u)/com.streamtv"
```

Disable hold everywhere: `STREAMTV_PLEX_VIDEO_HOLD=0` in the StreamTV LaunchAgent env.

`/auto/v*` behavior:

| Mode | Env | Behavior |
|------|-----|----------|
| **YouTube wait-phase (default)** | `STREAMTV_PLEX_VIDEO_HOLD_YOUTUBE=1` (default) | When `youtube_full_cache` is on and the channel’s on-air/playlist is YouTube, emit hold until first non-null video, then **never re-hold**. Archive CDN-first channels are not wrapped. |
| Full native re-hold | `STREAMTV_PLEX_VIDEO_HOLD_NATIVE=1` | Hold + re-hold on silence for all `/auto/v*` (risk: Archive copy-mode black freeze). |
| Off | `STREAMTV_PLEX_VIDEO_HOLD_YOUTUBE=0` and native unset | Null keepalives only during waits (Plex may return to guide). |

Tunarr proxy hold stays on (re-encode recovers quickly).

Silence before re-hold (Tunarr / native full mode) defaults to **45s**. Override with
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
./venv/bin/python3 scripts/heal_tunarr_ssd_transcode.py --dry-run
```

**Pass (YouTube):** `size_download` ≫ 8192, `h264` + `aac` within ~2s; log
`video_hold: YouTube wait-phase wrap`. Apple TV cold tune stays on channel.
**Pass (Archive):** real program TS after brief keepalive; no wait-phase wrap log.

## Related

- [Add Tunarr in Plex](ADD_TUNARR_IN_PLEX.md)
- [TunarrRAM recovery](TUNARRRAM_PLAYOUT_RECOVERY.md)
- [FFmpeg stall / keepalive](FFMPEG_STALL_KEEPALIVE.md) — mid-stream FFmpeg 0% CPU
- Rule `plex-hdhomerun-tuning.mdc` — null keepalive vs video hold
