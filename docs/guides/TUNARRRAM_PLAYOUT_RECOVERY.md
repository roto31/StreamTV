# TunarrRAM / playout recovery

StreamTV can cache YouTube (and related) media on a RAM disk such as
`/Volumes/TunarrRAM/streamtv-cache`. When that volume fills, playout fails with
`Errno 28` (no space) and clients see black screens.


## Symptoms

- Logs: `Errno 28` / disk full under TunarrRAM cache paths
- Channels black or stuck after prefetch/download bursts
- Remote Archive `-ss` seeks timing out on first chunk (related env below)

## Mitigations

### Free-space verify (in-tree)

```bash
bash scripts/verify_tunarr_ram.sh
bash scripts/install-tunarr-ram-verify-launchagent.sh
```

`verify_tunarr_ram.sh` reports free space / `.part` pressure on
`/Volumes/TunarrRAM` (defaults via env). Optional dry-run prune of old `.part`
files when `PRUNE_PART_HOURS` is set — it is a **verify / light prune**, not a
full “keep ≥300 Mi free” healer.

### Auto heal (in tree)

| Path | Role |
|------|------|
| `scripts/verify_tunarr_ram.sh` | Free-space / `.part` pressure report |
| `scripts/install-tunarr-ram-verify-launchagent.sh` | Verify LaunchAgent |
| `scripts/heal_tunarr_ram.sh` | Universal volume watchdog (every **60 s** via LaunchAgent) |
| `scripts/heal_tunarr_ram_purge.py` | Purge logic: used% / 1.7 GiB ceiling / free-floor → delete non-open files |
| `scripts/install-tunarr-ram-heal-launchagent.sh` | Installs `com.streamtv.tunarr-ram-heal` |
| `com.streamtv.tunarr-ram-heal` | LaunchAgent for the heal script |

**Pressure policy (default):** universal (not per tuned channel). Purge when
**any** of:

| Trigger | Default | Env |
|---------|---------|-----|
| Early used% | ≥ **45%** | `STREAMTV_TUNARRAM_MAX_USED_PCT` |
| Hard used ceiling | ≥ **1.7 GiB** | `STREAMTV_TUNARRAM_MAX_USED_GB` |
| Free floor | &lt; **300 Mi** | `STREAMTV_TUNARRAM_MIN_FREE_MB` |

Deletes every file under `streamtv-cache` **except** paths currently open by
ffmpeg/StreamTV (active streaming / download), including matching `.part`
siblings. Also removes orphan external HLS dirs `/Volumes/TunarrRAM/stream_*`
when not open (legacy HLS-on-RAM; settings should use SSD
`~/Library/Caches/streamtv-transcode`). Prefetch copies that are not open are
removed so a 2 Gi RAM disk cannot reach the 1.7 GiB used ceiling.

```bash
bash scripts/install-tunarr-ram-heal-launchagent.sh   # 60s / 45% / 1.7 GiB / 300 Mi
DRY_RUN=1 bash scripts/heal_tunarr_ram.sh
bash scripts/heal_tunarr_ram.sh   # apply when over threshold
```

### `youtube_full_cache`

Full YouTube cache to RAM improves mid-song 403 resilience but fills small RAM disks quickly.

**Current production (2026-09-20):** `youtube_full_cache` is **on** again with the
**60 s** volume watchdog (45% early / **1.7 GiB** hard ceiling / 300 Mi free).
Prefetch stays concurrency‑1 and volume‑gated; on-air `download_now` is ungated.
If used climbs past thresholds, heal purges non-open cache files.

**Re-enable checklist** (if turned off again):

1. `df -h /Volumes/TunarrRAM` — prefer used &lt; 45% and used &lt; 1.7 GiB.
2. `com.streamtv.tunarr-ram-heal` installed (`StartInterval` **60**) with
   `STREAMTV_TUNARRAM_MAX_USED_PCT=45`, `STREAMTV_TUNARRAM_MAX_USED_GB=1.7`,
   and `STREAMTV_TUNARRAM_MIN_FREE_MB=300`.
3. Set `cache.youtube_full_cache: true` in repo `config.yaml` **and**
   LaunchAgent `STREAMTV_CACHE_YOUTUBE_FULL_CACHE=true` (yaml wins at load;
   keep env in sync).
4. `launchctl kickstart -k gui/$(id -u)/com.streamtv` — log should show
   `DownloadQueue: youtube_full_cache enabled`.
5. If TunarrRAM hits Errno 28 / approaches 1.7 GiB used: run
   `scripts/heal_tunarr_ram.sh` (or wait for the 60 s agent).

**Boot without TunarrRAM:** lifespan logs `CACHE START FAILED` and retries every
`STREAMTV_CACHE_RETRY_SEC` (default 30) until `/Volumes/TunarrRAM` is mounted and
writable — no silent `warning` only.

### Prefetch vs 2 Gi race (Lesson 48)

Healer interval is **60 s** with a **1.7 GiB** hard used ceiling; concurrent
yt-dlp can still spike between ticks — keep concurrency 1 and volume gates on.

In-process gates (`streamtv/cache/volume_guard.py`):

- Pause **prefetch** (`ensure_download_started` + download poll) when used ≥ **50%**
  or free &lt; **400 Mi** (complements the volume watchdog’s 45% / 1.7 GiB / 300 Mi).
- `youtube_full_cache`: at most **one** concurrent download; poll and prefetch
  share `_in_flight`.
- On-air `download_now` is **not** paused (current item still downloads).

Log: `DownloadQueue: defer prefetch … (volume or concurrency)`.

### Resource sample (Phase 2)

```bash
bash scripts/install-resource-sample-launchagent.sh
tail -f ~/Library/Logs/StreamTV/resource-sample.log
```

Logs Python `:8410` RSS/`%cpu`, TunarrRAM used%, and top ffmpeg lines every 60s.

### Archive tune seek

If remote Archive `-ss` exceeds FFmpeg first-chunk timeout on tune:

```bash
STREAMTV_PLAYOUT_ARCHIVE_TUNE_SEEK=false
```

Set on the StreamTV LaunchAgent environment, then restart the service.

## Checklist

1. `df -h /Volumes/TunarrRAM` (or your cache mount).
2. Run `bash scripts/verify_tunarr_ram.sh`; free space with `scripts/heal_tunarr_ram.sh` if needed.
3. Review `cache.youtube_full_cache` and download concurrency.
4. Confirm `STREAMTV_PLAYOUT_ARCHIVE_TUNE_SEEK` if Archive tunes hang on first chunk.
5. Retune Plex after recovery ([Plex Live TV recovery](../plex/PLEX_LIVE_TV_RECOVERY.md)).
