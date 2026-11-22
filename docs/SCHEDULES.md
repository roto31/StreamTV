# Schedules (YAML authority)

Continuous playout and XMLTV for each channel come from an on-disk schedule file:

```text
schedules/{channel_number}.yml
```

Examples: channel `80` → `schedules/80.yml`; channel `1980` → `schedules/1980.yml`;
channel `1954.1` → `schedules/1954.1.yml`.

The scheduling engine (`ScheduleParser` / `ScheduleEngine`) is **frozen bedrock**.
Operators change order and fillers by editing YAML (or regenerating it via Channel
Builder / import), not by creating schedules in the web UI.

## Web UI

| Page | Behavior |
|------|----------|
| **Schedules** (`/schedules`) | **Read-only** inventory of `schedules/*.yml` that map to channels |
| **Playouts** (`/playouts`) | Live “what’s on now” / timeline state |

There is **no** Add / Edit / Save Schedule flow. Orphan YAML files with no matching
channel still appear in inventory until removed from disk.

## HTTP API

| Method | Path | Behavior |
|--------|------|----------|
| `GET` | `/api/schedules/yaml-inventory` | Read-only list of on-disk YAML (+ channel name/enabled when present) |
| `GET` | `/api/schedules` | Legacy DB schedule rows (playout does **not** use these) |
| `GET` | `/api/schedules/{id}` | Legacy DB row |
| `POST` | `/api/schedules` | **410 Gone** — creation disabled |
| `PUT` | `/api/schedules/{id}` | **410 Gone** — update disabled |
| `DELETE` | `/api/schedules/{id}` | Deletes a legacy DB row only; **refused (409)** while a YAML file exists for that channel |

Prefer editing `schedules/{n}.yml` on disk. After YAML changes that should take
effect without a full process restart, use soft deploy / stream-restart for the
channel (see [Soft deploy](guides/SOFT_DEPLOY.md)). Module-level Python changes
still need a full `com.streamtv` kickstart.

## YAML format

Schedule files define content blocks, sequences, and playout instructions.

### Content

Maps keys to DB **collection** names (inventory groups — not the retired Collections UI):

```yaml
content:
  - key: 1980_opening
    collection: Retro Olympics - 1980 Opening Ceremony (ABC)
    order: chronological
  - key: mn80_pre_roll
    collection: MN 1980 Pre-Roll IDs (TC Media Now)
    order: shuffle
```

- `key` — unique id referenced by sequences  
- `collection` — exact collection name in SQLite  
- `order` — `chronological` or `shuffle`

### Sequences

```yaml
sequence:
  - key: mn80-pre-roll
    items:
      - duration: "00:01:00"
        content: mn80_pre_roll
        filler_kind: Commercial
        trim: true
        discard_attempts: 2
  - key: mn80-channel
    items:
      - pre_roll: true
        sequence: mn80-pre-roll
      - all: 1980_opening
        custom_title: "Lake Placid Opening Ceremony (ABC)"
      - pre_roll: false
```

Sequence items may be:

- **Duration fillers** — `duration` + `content` key  
- **Full content blocks** — `all: <content_key>`  
- **Nested sequences** — `sequence: <sequence_key>`  
- **Pre / mid / post-roll flags** — control commercial insertion around blocks  

### Playout

```yaml
playout:
  - sequence: mn80-channel
  - repeat: true
```

`repeat: true` loops the sequence for continuous Live TV.

Optional top-level fields used by operators / Builder:

```yaml
name: Channel display name
description: Operator note
media:
  preferred_extension: mp4
  mp4_only: true   # Archive.org H.264 MP4 preference
```

## How lookup works

`ScheduleParser.find_schedule_file(channel_number)` looks under `schedules/` for:

1. Legacy aliases `mn-olympics-{n}.yml` / `.yaml` (if present)  
2. Canonical `{n}.yml` / `{n}.yaml`  
3. Legacy Magnum alias `magnum-pi-schedule.yml` only for channel `80` (if present)

**Canonical practice:** keep one file per channel as `schedules/{n}.yml`. Do not leave
orphan YAMLs for deleted channels — they clutter the Schedules inventory and are not
in Plex until a matching enabled channel exists.

## Features (YAML)

### Pre-roll / mid-roll / post-roll

```yaml
- pre_roll: true
  sequence: mn80-pre-roll
- all: 1980_opening
  custom_title: "Lake Placid Opening Ceremony (ABC)"
- pre_roll: false
```

### Custom titles

Override guide / playlist titles without renaming media rows:

```yaml
- all: 1980_opening
  custom_title: "Lake Placid Opening Ceremony (ABC)"
```

### Duration-based fillers

```yaml
- duration: "00:08:00"
  content: ads_1980_wjcl
  filler_kind: Commercial
  trim: true
  discard_attempts: 6
```

## Runtime behavior

1. **HDHomeRun / continuous TS** — ChannelManager uses the YAML timeline (with
   `playout_start_time`) so clients join in progress.  
2. **XMLTV** — Guide slots derive from the same YAML durations / custom titles.  
3. **Collections** — YAML `collection:` names resolve to SQLite collections populated
   by import / Builder. The **Collections web UI and `/api/collections` are retired**;
   manage inventory via Import, Builder, Playlists, and Media.

## Creating or changing a channel schedule

| Goal | Path |
|------|------|
| New channel from Archive.org / YouTube URLs | [Channel Builder](channel-builder.md) (`/builder`) — writes `schedules/{n}.yml` |
| Migrate / bulk YAML packs | [Import](guides/IMPORT_VS_BUILDER.md) (`/import`) |
| Reorder / edit fillers | Edit `schedules/{n}.yml` on disk, then soft-restart that channel |

Do **not** invent playout order only in the DB schedule tables — Live TV ignores them
when YAML exists.

## Troubleshooting

| Symptom | Check |
|---------|--------|
| Channel missing from Plex guide | Channel enabled in DB + present in `/lineup.json`; YAML alone is not enough |
| Schedules page shows a file with no channel name | Orphan YAML — delete or add the channel |
| Empty / wrong playout | Collection names in YAML match DB; content keys match sequence refs |
| Parse errors | Server logs; validate structure against `schemas/schedule.schema.json` when available |

## Related

- [Channel Builder](channel-builder.md)  
- [Import vs Builder](guides/IMPORT_VS_BUILDER.md)  
- [EPG sync classes](guides/EPG_SYNC_CLASSES.md)  
- [Soft deploy](guides/SOFT_DEPLOY.md)  
- Wiki: [Schedules](https://github.com/roto31/StreamTV/wiki/Schedules)
