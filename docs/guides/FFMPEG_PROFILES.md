# Transcoding hub (FFmpeg)

Central operator doc for Settings → **Transcoding**.

## Default Live TV path

StreamTV **remuxes at source resolution** (H.264/AAC MPEG-TS). Plex, Emby, Jellyfin,
and TV clients scale for the display. Resolutions UI is **retired**. Watermarks UI is
**retired**.

Leave channel **FFmpeg Profile** empty unless you have a specific encode need.

## Global FFmpeg (`/settings/ffmpeg`)

`config.yaml` binaries, hardware acceleration hints, and thread counts.

## Channel profiles (`/settings/ffmpeg-profiles`)

Optional DB templates (`/api/ffmpeg-profiles`). When a channel sets `ffmpeg_profile_id`,
continuous playout binds that profile at channel start.

- **LoudNorm** defaults **off** (fleet policy). See [LOUDNORM_FLEET_AUDIO.md](LOUDNORM_FLEET_AUDIO.md).
- Profile `resolution_id` remains a DB FK (seeded 1080p) but **scale UI is retired**;
  do not rely on profile scale for production. Prefer remux + client scaling.
- Profile argv can diverge from frozen bedrock goldens — treat profiles as advanced.

## Per-channel overrides

Channel edit → FFmpeg profile dropdown (optional).

## Subtitles

External text subtitle files are **not** in the schedule schema.

**Live TV — opt-in embedded DVD/PGS overlay:** Set channel `subtitle_mode` to
`default` (or any value other than `none`). Overlay runs only when:

- audio language is labeled and **not** English, and
- an English bitmap subtitle stream exists (`dvd_subtitle` / PGS / …).

**Fleet default stays `subtitle_mode: none`.**

## Golden tests

Archive.org, PBS, Plex, and YouTube argv are frozen — see `tests/test_ffmpeg_command_golden.py`.
Never regenerate goldens to pass a profile or loudnorm change.
