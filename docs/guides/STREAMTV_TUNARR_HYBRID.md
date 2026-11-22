# StreamTV + Tunarr hybrid operator guide

StreamTV and [Tunarr](https://github.com/chrisbenincasa/tunarr) complement each other. Use this guide to choose the right tool for each workflow.

**Attribution:** Tunarr is [zlib](https://github.com/chrisbenincasa/tunarr?tab=Zlib-1-ov-file)-licensed.
StreamTV does **not** vendor Tunarr source — see root [NOTICE](../../NOTICE). It uses an HTTP client
(`streamtv/integrations/tunarr_client.py`), optional `/api/integrations/tunarr/*`
proxy routes, and `tuner_manager` HDHomeRun-style proxying. **TunarrRAM** is a
local RAM-disk volume name for StreamTV cache — not Tunarr software.

## When to use StreamTV Builder

- YouTube and Archive.org (first-party Builder builtins; PBS/Plex/Vimeo are parked)
- YAML-first channel inventory (`data/unified/*.channel.yaml`)
- Continuous playout from `schedules/{number}.yml` (web schedule create/edit removed)
- Channel Builder at `/builder`

## When to use Tunarr

- Plex / Jellyfin / Emby library browsing and slot scheduling
- Custom Shows synced from Plex playlists
- Smart Collections and filler lists (in Tunarr’s own UI)
- Tunarr web UI at `http://<tunarr-host>:8000/web`

## When to use both (recommended for Plex households)

1. Configure `tuner_manager` in `config.yaml` (see [ADD_TUNARR_IN_PLEX.md](ADD_TUNARR_IN_PLEX.md)).
2. Add Tunarr in Plex using the StreamTV proxy URL from `/tuners`.
3. Point Plex DVR guide at merged EPG: `http://<streamtv>:8410/tuners/guide.xml`.
4. Call `/api/integrations/tunarr/*` when Tunarr is reachable; native `/api/plex/*` remains available. StreamTV **Collections UI is retired** (`/collections` → `/media`).

## Archive.org library export (optional)

StreamTV already plays Archive.org as live MPEG-TS. To also feed **Tunarr Local Media** without coupling the live path:

1. Ensure items are `READY` in the StreamTV cache (live playout / download queue).
2. Set `tunarr_library.export_directory` to a folder **outside** `cache.cache_directory` (never TunarrRAM / never the live cache tree).
3. Dry-run then apply:

```bash
python3 scripts/export_tunarr_library.py --dry-run
python3 scripts/export_tunarr_library.py --apply
```

4. In Tunarr, add a Local Media source pointing at that export directory. StreamTV does **not** auto-create Tunarr channels.

**Do not** point Tunarr at `cache.cache_directory` — LRU eviction and stream-while-caching `.part` files are for live tune only.

## Prefetch Archive.org into Tunarr library (no FUSE)

When the live cache is buffer/stream-first (few or zero READY Archive.org files), use the **prefetch agent** to download full MP4s straight into `tunarr_library.export_directory`:

1. Config knobs under `tunarr_library`: `prefetch_hours`, `prefetch_max_items`, `prefetch_max_gb`, `channel_numbers` (empty = all enabled continuous Archive.org channels).
2. Dry-run then apply:

```bash
python3 scripts/prefetch_tunarr_library.py --dry-run
python3 scripts/prefetch_tunarr_library.py --apply --max-items 5
```

3. Re-scan **Tunarr Local Media** pointing at the export directory (manual in Tunarr UI for v1). StreamTV does not auto-create Tunarr channels.
4. Never set `export_directory` under `/Volumes/TunarrRAM`. Live HDHomeRun tune is unchanged.

Prefetch skips items already in the export folder and sticky terminal cache failures (`auth_required` / `unavailable` / `no_playable_file`). If a READY cache file already exists, it is exported (hardlink/copy) instead of re-downloaded.

## English tracks (foreign-language Archive.org)

**Primary Live TV path:** channel `subtitle_mode: default` overlays embedded English
DVD/PGS when audio is non-English (hardened ffprobe + no-bytes fallback). Fleet
channels keep `subtitle_mode: none` unless opted in.

**Optional offline burn/bind** (rare titles with no embedded eng bitmap):

```bash
# Inventory — probes ALL audio streams; English audio wins
./venv/bin/python scripts/probe_archive_movie_tracks.py --channel 1954.1 \
  --json data/english_tracks_inventory_1954.1.json

# Idle-only burn (abort if any English audio track)
./venv/bin/python scripts/preburn_english_subs.py \
  --inventory data/english_tracks_inventory_1954.1.json --dry-run
./venv/bin/python scripts/preburn_english_subs.py \
  --inventory data/english_tracks_inventory_1954.1.json --apply --max-items 1

# After a full burned h264+aac exists under data/tunarr_library/burned/
./venv/bin/python scripts/bind_preburned_english.py --channel 1954.1 --dry-run
./venv/bin/python scripts/bind_preburned_english.py --channel 1954.1 --apply
# then import generated YAML into com.streamtv
```

Burned files are also suitable for a **Plex Movies** library (Direct Play). Never write under TunarrRAM.

## API surfaces

| Need | StreamTV endpoint |
|------|-------------------|
| Tunarr health | `GET /api/integrations/tunarr/status` |
| Media sources | `GET /api/integrations/tunarr/media-sources` |
| Search | `GET /api/integrations/tunarr/search?q=...` |
| Custom shows | `GET /api/integrations/tunarr/custom-shows` |
| Smart collections | `GET /api/integrations/tunarr/smart-collections` |
| Native Plex libraries | `GET /api/plex/libraries` |
| Merged EPG | `GET /tuners/guide.xml` |

## EPG note

`config.plex.use_for_epg` is honored at the **merge layer** (`X-Merged-Sources` response header). StreamTV bedrock `iptv.py` is unchanged. Prefer `/tuners/guide.xml` in Plex DVR for a single guide covering StreamTV YAML channels and Tunarr channels.

## References

- [Tunarr channels](https://tunarr.com/configure/channels/)
- [Tunarr scheduling](https://tunarr.com/configure/scheduling/)
- [Tunarr custom shows](https://tunarr.com/configure/library/custom-shows/)
