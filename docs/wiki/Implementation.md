# Implementation & Integrations

Technical notes for developers and operators. Tip version: **v1.4.5** ([`VERSION`](https://github.com/roto31/StreamTV/blob/main/VERSION)). Product scope: [PRODUCT_SCOPE.md](https://github.com/roto31/StreamTV/blob/main/docs/PRODUCT_SCOPE.md).

Canonical deep docs live under [`docs/`](https://github.com/roto31/StreamTV/tree/main/docs). This page is the curated integrations surface — not a dump of historical incident notes.

## Platform surface (current)

| Area | Current behavior | Evidence |
|------|------------------|----------|
| Product | **macOS only** (no Linux product) | [Linux](Linux), `AGENTS.md` |
| Builder first-party sources | Archive.org + YouTube | `streamtv/builder/sources/builtins/__init__.py` |
| Schedules | On-disk `schedules/{n}.yml`; web UI **read-only** | [Schedules](Schedules), `streamtv/api/schedules.py` |
| Schedule create/update API | `POST` / `PUT` `/api/schedules` → **410 Gone** | `streamtv/api/schedules.py` |
| Collections UI / `/api/collections` | **Retired** (`/collections` → `/media`) | `streamtv/main.py`, `parked/collections-ui/` |
| AI Recovery / Foundation Models / Ollama UI | **Retired** (parked) | `parked/ai-recovery/` |
| Soft deploy vs kickstart | Soft recycles channel streams; kickstart reloads Python | [SOFT_DEPLOY.md](https://github.com/roto31/StreamTV/blob/main/docs/guides/SOFT_DEPLOY.md) |

## Third-party inspiration (Tunarr credit)

StreamTV does **not** vendor [Tunarr](https://github.com/chrisbenincasa/tunarr) source and no longer runs an external Tunarr proxy, merged guide, or library-export integration. Remaining credit is for **design inspiration** (continuous playout / RAM-cache ideas). Full attribution: root [NOTICE](https://github.com/roto31/StreamTV/blob/main/NOTICE).

### TunarrRAM naming

`/Volumes/TunarrRAM` is a **local RAM-disk volume name** used for StreamTV cache pressure management. It is not Tunarr software. See [TunarrRAM recovery](https://github.com/roto31/StreamTV/blob/main/docs/guides/TUNARRRAM_PLAYOUT_RECOVERY.md).

## Scheduling (still present)

Continuous playout and XMLTV come from YAML, not from the web “create schedule” UI.

```text
Builder / Import / disk edit  →  schedules/{n}.yml  →  ScheduleParser  →  ScheduleEngine  →  MPEG-TS + XMLTV
```

| Still present | Not present |
|---------------|-------------|
| `streamtv/scheduling/parser.py`, `engine.py` (frozen bedrock) | Web Add / Edit / Save Schedule |
| YAML `content` / `sequence` / `playout` | Successful `POST`/`PUT` `/api/schedules` (returns **410**) |
| Optional CLI helper `scripts/create_schedule.sh` (writes YAML on disk) | Collections UI for schedule authoring |

### ErsatzTV-style directives (engine)

Python handlers in `streamtv/scheduling/engine.py` (inspired by ErsatzTV YAML patterns; not a C# fork):

| Directive | Handler |
|-----------|---------|
| `padToNext` | `_handle_pad_to_next` |
| `padUntil` | `_handle_pad_until` |
| `waitUntil` | `_handle_wait_until` |
| `skipItems` | `_handle_skip_items` |
| `shuffleSequence` | `_handle_shuffle_sequence` |

Also: YAML `import:`, pre/mid/post-roll sequence refs, duration fillers, `repeat`. Deep how-to: [ERSATZTV_INTEGRATION.md](https://github.com/roto31/StreamTV/blob/main/docs/features/ERSATZTV_INTEGRATION.md) · [SCHEDULES.md](https://github.com/roto31/StreamTV/blob/main/docs/SCHEDULES.md).

### IPTV endpoints (still present)

From `streamtv/api/iptv.py` (among others):

- `GET /iptv/channels.m3u`, `GET /iptv/channels.m3u8`
- `GET /iptv/xmltv.xml`
- `GET /iptv/channel/{n}.m3u8` (HLS)
- `GET /iptv/channel/{n}.ts` (MPEG-TS)

Primary Live TV path for Plex is HDHomeRun `/auto/v*` + MPEG-TS, not “create schedule in the browser.”

## Third-party inspiration (attribution)

| Project | What StreamTV has | What StreamTV is not |
|---------|-------------------|----------------------|
| [ErsatzTV Legacy](https://github.com/ErsatzTV/legacy) (zlib; archived/deprecated line) | Inspired schedule YAML patterns and the five directives above, reimplemented in Python under `streamtv/scheduling/` | Not a fork; not vendored ErsatzTV source |
| [Tunarr](https://github.com/chrisbenincasa/tunarr) (zlib) | Design inspiration for continuous playout and RAM-cache ideas (Tunarr-style comments in code) | Not vendored Tunarr source; no live Tunarr HTTP client, `/tuners` proxy, or library export |

Canonical acknowledgments: root [NOTICE](https://github.com/roto31/StreamTV/blob/main/NOTICE). StreamTV itself is MIT — [LICENSE](https://github.com/roto31/StreamTV/blob/main/LICENSE).

## Related wiki pages

- [Schedules](Schedules) · [API Reference](API-Reference) · [Documentation Index](Documentation-Index)
- [Channel Builder Custom Sources](Channel-Builder-Custom-Sources) · [Plex Integration](Plex-Integration)
- [Home](Home)

## Historical private notes (not this page)

Older Magnum naming / FFmpeg hwaccel / amalgamed status reports live under private `docs/implementation/` and dated `docs/reports/`. They are **not** current product truth. Do not re-paste them into the public wiki.
