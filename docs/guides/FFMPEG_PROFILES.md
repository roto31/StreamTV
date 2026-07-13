# FFmpeg profiles vs overrides

## Profiles

Global templates in **Settings → FFmpeg Profiles** (`/api/ffmpeg-profiles`).

## Per-channel overrides

Channel edit → FFmpeg profile dropdown. Overrides apply to that channel's MPEG-TS output only.

## Subtitles (v1.3.2)

External subtitle files are **not** in the schedule schema yet. `mpegts_streamer` leaves `subtitle_path` unset by design until schema support lands.

## Golden tests

Archive.org, PBS, Plex, and YouTube argv are frozen — see `tests/test_ffmpeg_command_golden.py`.
