# Schedules

Continuous playout and the Plex/XMLTV guide for each channel come from an on-disk YAML file:

```text
schedules/{channel_number}.yml
```

Examples: `80` → `schedules/80.yml`, `1980` → `schedules/1980.yml`, `1954.1` → `schedules/1954.1.yml`.

Canonical deep doc: [docs/SCHEDULES.md](https://github.com/roto31/StreamTV/blob/main/docs/SCHEDULES.md).

## Web UI

| Page | Behavior |
|------|----------|
| **Schedules** (`/schedules`) | **Read-only** inventory of on-disk YAML files |
| **Playouts** (`/playouts`) | Live “what’s on now” |

There is **no** web Add / Edit / Save Schedule flow. Creating or reordering schedules in the browser is disabled.

## API (high level)

| Method | Path | Behavior |
|--------|------|----------|
| `GET` | `/api/schedules/yaml-inventory` | Read-only on-disk inventory |
| `GET` | `/api/schedules` | Legacy DB rows (not used for Live TV when YAML exists) |
| `POST` / `PUT` | `/api/schedules`… | **410 Gone** |
| `DELETE` | `/api/schedules/{id}` | Legacy DB only; **409** if YAML still exists for the channel |

## YAML shape

Three sections: **content** (keys → collection names), **sequence** (order, fillers, pre/mid/post-roll), **playout** (`sequence` + usually `repeat: true`).

```yaml
name: Example Channel
content:
  - key: main
    collection: Example Collection
    order: chronological
sequence:
  - key: loop
    items:
      - all: main
playout:
  - sequence: loop
  - repeat: true
```

Collection names refer to SQLite inventory groups filled by **Import** or **Channel Builder**. The Collections web UI and `/api/collections` are **retired**.

## Canonical file names

Prefer `schedules/{channel_number}.yml` only. Orphan YAML (no matching enabled channel) shows on the Schedules page but **does not** appear in Plex until a channel exists and is enabled.

## How to change order

| Goal | Path |
|------|------|
| New Archive.org / YouTube channel | [Channel Builder](https://github.com/roto31/StreamTV/blob/main/docs/channel-builder.md) |
| Bulk / migrate packs | [Import vs Builder](https://github.com/roto31/StreamTV/blob/main/docs/guides/IMPORT_VS_BUILDER.md) |
| Edit fillers / order | Edit `schedules/{n}.yml` on disk, then soft-restart the channel |

See also: [Soft deploy](https://github.com/roto31/StreamTV/blob/main/docs/guides/SOFT_DEPLOY.md) · [EPG sync classes](https://github.com/roto31/StreamTV/blob/main/docs/guides/EPG_SYNC_CLASSES.md)

## Related

- [Documentation Index](Documentation-Index)
- [Home](Home)
- [API Reference](API-Reference)
