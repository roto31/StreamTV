# Backup and restore

Portable zip backups of StreamTV **settings, channels, schedules, and secrets** for moving to a new Mac or recovering from disk failure.

Automatic backups are **on by default**. The app writes `streamtv-backup-latest.zip` after settings, channel, schedule, or import changes (30s debounce). Streaming bedrock code is not modified — backup only copies files and SQLite.

## What is included

| Member | Contents |
|--------|----------|
| `manifest.json` | `format_version` (1), app version, UTC time, hostname, member hashes |
| `config.yaml` | Preferences and integration settings |
| `streamtv.db` | Channels, media, collections, playlists, schedules, FFmpeg profiles, watermarks |
| `data/*.yaml` | YAML-source channel inventories |
| `data/channel_icons/` | Channel logos |
| `data/builder_drafts/` | In-progress Channel Builder drafts |
| `data/tuner_device_ids/` | Stable HDHomeRun device IDs |
| `schedules/*.yml` | On-disk playout schedules |
| `cookies/` | YouTube / Archive.org / PBS cookie files when configured |
| `secrets.env` | Optional (`backup.include_secrets`, default true) |

**Not included:** `venv/`, bundled Python/FFmpeg, YouTube/disk cache media, logs.

## Location

- **macOS app:** `~/Library/Application Support/StreamTV/backups/`
- **Dev / LaunchAgent:** `<config parent>/backups/` (or `STREAMTV_BACKUP_DIR`)

Files:

- `streamtv-backup-latest.zip` — always the newest snapshot (atomic replace)
- `streamtv-backup-YYYYMMDD-HHMMSS.zip` — retained copies (`backup.retain_count`, default 7)

Mode `0600`. Treat zips as **credentials** (tokens and cookies).

## Config

```yaml
backup:
  enabled: true
  debounce_seconds: 30
  retain_count: 7
  include_secrets: true
```

Environment overrides use the `STREAMTV_BACKUP_` prefix (e.g. `STREAMTV_BACKUP_ENABLED=false`).

## Web UI

**Settings → Backup & Restore** (`/settings/backup`):

- Status and backup directory
- **Backup now**
- **Download latest**
- **Restore from zip** (validate-only dry run available)

## API

| Method | Path | Notes |
|--------|------|-------|
| `GET` | `/api/backup/status` | Directory + scheduler state |
| `POST` | `/api/backup/now` | Immediate snapshot |
| `GET` | `/api/backup/latest` | Download zip; **auth required** when `security.api_key_required` |
| `POST` | `/api/backup/restore` | Upload zip; stages pending restore (`?dry_run=true` validates only) |

Restore via API **stages** the zip and requires a **server restart**. Lifespan applies the pending restore before opening the DB.

## macOS app

- **Settings → Backup & Restore:** Backup Now, Reveal Backups Folder, Restore…
- **Welcome (first launch):** optional **Restore from Backup…** before Continue

Swift only copies the zip and writes `.streamtv-restore-pending` + `streamtv-restore-pending.zip`. Python performs the restore on the next server start.

## New-machine checklist

1. Install StreamTV on the new Mac and complete Python setup (or stage restore on Welcome).
2. Copy `streamtv-backup-latest.zip` from the old Mac’s `backups/` folder.
3. Restore (app Settings/Welcome or web UI), then ensure the server restarts once.
4. Re-check FFmpeg (`brew install ffmpeg`) — host-local `ffmpeg_path` / `ffprobe_path` / `cache.cache_directory` are **not** applied from the backup.
5. Re-point Plex Live TV at this Mac’s HDHomeRun URL if the LAN address changed.

## Safety

- Before replace, restore writes a `.streamtv-pre-restore-<timestamp>/` copy of prior config/DB/data subsets.
- Restore **replaces** (does not merge) config, database, selected `data/` trees, and schedules.
- Playback positions are not specially exported; they regenerate on air.

## Related

- [Import vs Channel Builder](IMPORT_VS_BUILDER.md)
- [Core operator quickstart](CORE_OPERATOR_QUICKSTART.md)
- [Product scope](../PRODUCT_SCOPE.md) (AI heal is out of scope; backups remain the recovery path)
- Per-channel YAML export remains at `GET /api/export/channels/{id}/yaml` (not a full install backup)
