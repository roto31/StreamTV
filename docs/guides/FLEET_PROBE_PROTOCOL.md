# Fleet probe protocol (StreamTV + Tunarr)

Use this before declaring channels “dead.” Aggressive concurrent curls refill
TunarrRAM and create false keepalive-only results.

## Rules

1. **Heal first:** `df -h /Volumes/TunarrRAM` — prefer used &lt; 45%. Run
   `bash scripts/heal_tunarr_ram.sh` if higher.
2. **One worker:** never probe more than one channel at a time.
3. **Timeout:** 8–15 s for a smoke check; **30–45 s** soak for “is video real?”
4. **Classify late packets**, not only the first chunk (first chunk is often the
   8192-byte null keepalive).
5. **Do not** soft-restart all channels then immediately fleet-probe.
6. Tunarr h264+aac alone is not success — identical short captures / `testsrc` /
   `generic-offline-screen` mean the **error slate**, not the program.

## Smoke (single channel)

```bash
bash scripts/heal_tunarr_ram.sh
curl -s -m 40 -o /tmp/ch.ts -w 'size=%{size_download}\n' \
  'http://127.0.0.1:8410/auto/v80'
ffprobe -v error -show_entries stream=codec_type,codec_name -of csv=p=0 /tmp/ch.ts
```

## Soft restart (watched channels only)

```bash
bash scripts/deploy_soft.sh --channel 80 1980.1
# wait ~10s for FFmpeg warm, then soak
```

## Related

- [TunarrRAM recovery](TUNARRRAM_PLAYOUT_RECOVERY.md)
- [Plex video hold](PLEX_VIDEO_HOLD.md)
- Skill `verify-hdhomerun-streaming`
