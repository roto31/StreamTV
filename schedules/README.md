# Schedule Files

On-disk YAML schedules are the authority for continuous playout and XMLTV.

## Naming

```text
schedules/{channel_number}.yml
```

Examples: `80.yml`, `1980.yml`, `1954.1.yml`.

## How to create or change a schedule

| Method | Notes |
|--------|-------|
| Channel Builder / Import | Writes `schedules/{n}.yml` as part of channel assembly |
| Edit YAML on disk | Then soft-restart the channel (see Soft deploy) |
| `scripts/create_schedule.sh` | Optional interactive helper that **writes a YAML file** |

The **Schedules** web page (`/schedules`) is a **read-only** inventory.  
`POST` / `PUT` `/api/schedules` return **410 Gone**.

## Format

See [docs/SCHEDULES.md](../docs/SCHEDULES.md) for the `content` / `sequence` / `playout` shape and ErsatzTV-style directives.

Minimal shape:

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
