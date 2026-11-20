# FFmpeg mid-stream stall → keepalive-only

When Archive.org FFmpeg stalls mid-item (~0% CPU, no stdout), HDHomeRun can keep
serving MPEG-TS **null keepalives** (~8 KiB) forever. Plex / Apple TV then appear
“tuned” but drop to the guide.

## Defense in this release

### In-process (ChannelManager / mpegts path)

After the first chunk, if FFmpeg produces no stdout for
`STREAMTV_FFMPEG_STALL_SEC` (default **90**), StreamTV kills that process so
continuous playout can advance instead of feeding keepalives forever.

**DVD overlay (Lesson 59):** libx264 burn often gaps stdout for more than the
5s read timeout while MPEG-TS is already flowing. Overlay sessions that have
yielded bytes do **not** log “stdout silence” warnings on those gaps. A true
hang (no bytes for the full stall limit) still aborts.

Set on the StreamTV LaunchAgent / environment, for example:

```bash
STREAMTV_FFMPEG_STALL_SEC=90
```

### External healer (in tree)

Complementary belt for wedged Archive.org FFmpeg processes the streamer did not
abort:

| Path | Role |
|------|------|
| `scripts/heal_stalled_ffmpeg.py` | Dry-run by default; `--apply` SIGKILL low-CPU long-running Archive FFmpeg (**skips** `-filter_complex` / overlay / `subtitles=` burn encodes — quiet CPU is normal there) |
| `scripts/install-stalled-ffmpeg-heal-launchagent.sh` | Installs `com.streamtv.stalled-ffmpeg-heal` (every **120** s) |
| `.cursor/skills/heal-stalled-ffmpeg-keepalive` | Operator verify skill |

StreamTVMac Foundation Models recovery whitelists `heal_stalled_ffmpeg.py` and
runs it from the repo when present.

In-tree lag healer (different problem): `scripts/heal_playout_lag.py` +
`scripts/install-playout-lag-heal-launchagent.sh`.

### Archive DVD/PGS overlay (channel `subtitle_mode: default`)

English DVD/PGS burn forces `libx264`. Long encodes can trip the **in-process** 90s
stdout-silence guard. The **external** healer deliberately skips `-filter_complex` /
overlay / `subtitles=` argv so Magnum copy-path is not SIGKILL'd because a Godzilla
overlay encode is quiet. Confirm post-abort retune still yields h264+aac ≫8192.
Do not disable `STREAMTV_FFMPEG_STALL_SEC` for overlay channels.

## Operator checklist

1. Confirm symptom: HDHomeRun returns ~8192 B keepalives; FFmpeg at ~0% CPU on Archive item.
2. Ensure `STREAMTV_FFMPEG_STALL_SEC` is set on the live StreamTV service; restart if needed.
3. Optionally install/run the external healer LaunchAgent above.
4. Retune the Plex client after playout advances ([Plex Live TV recovery](../plex/PLEX_LIVE_TV_RECOVERY.md)).

## Related

- [Auto-healer / Foundation Models](../AUTO_HEALER.md)
- [TunarrRAM recovery](TUNARRRAM_PLAYOUT_RECOVERY.md) for cache disk full / Errno 28
- [Streaming issues](../troubleshooting/STREAMING_ISSUES.md)
- [Lessons Learned](../../LESSONS_LEARNED.md) Issues 41, 44, 59
