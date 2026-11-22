# Schedule file naming

## Canonical rule

```text
schedules/{channel_number}.yml
```

Examples: `schedules/80.yml`, `schedules/1980.yml`, `schedules/1954.1.yml`.

The Schedules web page lists on-disk YAML only (no create/edit UI). Live TV + XMLTV
use these files — see [SCHEDULES.md](../SCHEDULES.md).

## Parser lookup order

`ScheduleParser.find_schedule_file(channel_number)` checks, in order:

1. `mn-olympics-{n}.yml` / `.yaml` (legacy alias — optional)
2. `{n}.yml` / `.yaml` (**canonical**)
3. `magnum-pi-schedule.yml` only when `n == "80"` (legacy alias — optional)

Prefer a single `{n}.yml` per channel. Do not keep orphan files for deleted channels.

## Historical note

Older docs and wiki pages referred to `mn-olympics-{year}.yml` and
`magnum-pi-schedule.yml` as primary names. Those aliases were removed from the
operator tree; numbered `{n}.yml` files are authoritative.
