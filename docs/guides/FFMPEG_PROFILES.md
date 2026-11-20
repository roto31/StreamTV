# FFmpeg profiles vs overrides

## Profiles

Global templates in **Settings → FFmpeg Profiles** (`/api/ffmpeg-profiles`).

## Per-channel overrides

Channel edit → FFmpeg profile dropdown. Overrides apply to that channel's MPEG-TS output only.

## Continuous playout binding

When a channel has `ffmpeg_profile_id` set, continuous playout binds that profile at
**channel start** (not only the on-demand stream path).

## LoudNorm fleet audio

One-pass `loudnorm` + limiter for fleet levels and true-peak control, plus optional
CPU-based auto-demotion — see [LOUDNORM_FLEET_AUDIO.md](LOUDNORM_FLEET_AUDIO.md).

## Subtitles

External text subtitle files are **not** in the schedule schema. `mpegts_streamer` still
leaves `subtitle_path` unset.

**Live TV — opt-in embedded DVD/PGS overlay:** Set channel `subtitle_mode` to
`default` (or any value other than `none`). Overlay runs only when:

- audio language is labeled and **not** English, and
- an English bitmap subtitle stream exists (`dvd_subtitle` / PGS / …).

English-audio and unlabeled-audio items stay on the copy/encode path (frozen
Archive.org goldens unchanged).

**Stall harden (2026-09-20):** ffprobe ignores `attached_pic` / cover-art
`mjpeg`/`png`; burn-enabled channels no longer always use a 6M probesize;
overlay sessions that produce no MPEG-TS bytes rebuild once without burn.

**Fleet default stays `subtitle_mode: none`.** Enable per-channel only (e.g.
**1954.1** Godzilla).

**Optional offline tooling** (rare titles with no embedded eng bitmap):

1. `scripts/probe_archive_movie_tracks.py` — inventory all audio/sub tracks.
2. `scripts/preburn_english_subs.py` / `bind_preburned_english.py` — idle burn +
   local bind (not the primary Live TV path).
3. Future: OpenSubtitles API offline `.srt` fetch for `no_english` items only
   (not live scrape-as-you-play).
4. Future: idle Whisper / MLX (`scripts/whisper_english_srt.py` when added) for
   `no_english` inventory rows only — **never** on the MPEG-TS tune path.

Plex Live TV cannot select extra audio/subtitle tracks on HDHomeRun MPEG-TS.
Plex Movies can Direct Play burned files under `data/tunarr_library/burned/` if used.

## Golden tests

Archive.org, PBS, Plex, and YouTube argv are frozen — see `tests/test_ffmpeg_command_golden.py`.
Never regenerate goldens to pass a profile or loudnorm change.
