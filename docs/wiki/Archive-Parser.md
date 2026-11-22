# Archive.org Channel Parser

Create channels from Archive.org collections using the parser scripts and Channel Builder.

> **Canonical:** [ARCHIVE_ORG_OPERATOR.md](https://github.com/roto31/StreamTV/blob/main/docs/guides/ARCHIVE_ORG_OPERATOR.md) · [ARCHITECTURE.md](https://github.com/roto31/StreamTV/blob/main/ARCHITECTURE.md) · [Channel Builder](https://github.com/roto31/StreamTV/blob/main/docs/channel-builder.md)

## Quick start

### GUI (macOS)

```bash
./scripts/archive_collection_parser_dialog.sh
```

### CLI

```bash
python3 scripts/archive_collection_parser.py "https://archive.org/details/<collection-or-item>"
```

## What the parser produces

| Artifact | Typical path | Purpose |
|----------|--------------|---------|
| Channel / inventory YAML | under `data/` (operator-managed) | Channel + media inventory |
| Schedule YAML | `schedules/{channel_number}.yml` | Continuous playout + XMLTV authority |

Prefer the canonical filename `schedules/{channel_number}.yml`. After writing YAML, soft-restart the channel ([Soft deploy](https://github.com/roto31/StreamTV/blob/main/docs/guides/SOFT_DEPLOY.md)).

The Schedules web UI is **read-only**. Do not expect a browser “create schedule” flow.

## Builder vs parser

| Path | Use when |
|------|----------|
| **Channel Builder** (`/builder`) | First-party Archive.org + YouTube wizard |
| **Parser scripts** | Bulk Archive.org collection import / dialogs |
| **Import** | Migrating packs / YAML already on disk |

PBS / Plex / Vimeo Builder builtins are **parked** — see [Channel-Builder-Custom-Sources](Channel-Builder-Custom-Sources).

## Related

- [Schedules](Schedules) · [Implementation](Implementation) · [Documentation Index](Documentation-Index)
- [Troubleshooting](Troubleshooting)
