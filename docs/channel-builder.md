# Channel Builder

Assemble custom StreamTV channels from **Archive.org** and **YouTube** through a guided web wizard or REST API.

First-party Builder sources are **Archive.org** and **YouTube** only. PBS, Plex, and Vimeo Builder builtins are parked under `parked/builder-sources/` (playback adapters for existing inventory may still resolve those URLs).

## When to use Channel Builder vs Import Channels

| Task | Use |
|------|-----|
| Create a **new** channel from URLs (YouTube, Archive.org) | **Channel Builder** (`/builder`) |
| **Migrate** channel YAML from another StreamTV server | **Import Channels** (`/import`) |
| **Bulk import** hand-edited channel packs (`channels:` list YAML) | **Import Channels** (`/import`) |
| Re-import after editing `data/channels*.yaml` on disk | **Import Channels** (`/import`) |

Both paths end at `import_channels_from_yaml()`; Builder also writes `data/unified/{n}.channel.yaml` and `schedules/{n}.yml`.

## Quick start

1. Open **Channel Builder** from the sidebar (`/builder`) or visit `http://localhost:8410/builder`.
2. **Source** — Pick Archive.org or YouTube (optional community YAML sources under `data/builder_sources/`).
3. **Sign In** — Inline authentication (Playwright for YouTube; form for Archive.org).
4. **URLs** — Paste or drop links; playlists and Archive collections expand on resolve.
5. **Order & Fillers** — Choose playback order; attach reusable filler libraries.
6. **Channel Info** — Set channel number, name, collection name, and optional **metadata enrichment** fields (series name / year; defaults on).
7. **Review & Build** — Compiles unified YAML, imports inventory, writes `schedules/{n}.yml`, resets playout, then **enriches** media via TVDB/TVMaze/TMDB when enabled.

Schedules are **YAML authority** for playout + XMLTV. There is no web “create schedule” UI — Builder/Import write the file; afterwards edit `schedules/{n}.yml` on disk if needed. See [SCHEDULES.md](SCHEDULES.md).

### Metadata enrichment (post-build)

After a successful build, Channel Builder runs playback-safe enrichment (`meta_data.enrichment` + description/thumbnail columns) when **Enrich metadata after build** is checked (default).

| Channel Info field | Purpose |
|--------------------|---------|
| Enrich metadata after build | On/off (default on) |
| Enrichment type | `series` or `movie` (TMDB) |
| Series metadata provider | **TVMaze** (free account username + dashboard API key), **TVDB** (API key), or **Both** |
| TVMaze credentials | Saved via Builder to `metadata.tvmaze_username` / `metadata.tvmaze_api_key` (HTTP Basic; not in the draft) |
| TVDB API key | Saved via Builder to `metadata.tvdb_api_key` in operator `config.yaml` (not stored in the draft) |
| Series / show name | Explicit override; if empty, auto from channel name (noise stripped) or episode titles |
| Year | Optional year hint for provider search |

**Provider choice (series):**

| Option | Required | Behavior |
|--------|----------|----------|
| TVMaze | Free [tvmaze.com](https://www.tvmaze.com) account → dashboard API key + username | Titles/plots via [TVMaze API](https://www.tvmaze.com/api); public calls also work without a key (IP rate limits) |
| TVDB | Free API key from [thetvdb.com](https://thetvdb.com/api-information) | Often better for long-running / deep catalogs |
| Both | Both keys recommended | Queries both; soft-falls back when a key is missing |

Failures become **warnings** on the build job — the channel still imports. See [Metadata Enrichment](guides/METADATA_ENRICHMENT.md).

### Extensibility

- **Custom sources:** YAML manifests in `data/builder_sources/` — see [Custom sources guide](builder/custom-sources-guide.md).
- **PDF:** `bash scripts/generate_builder_custom_sources_pdf.sh` → `/builder/custom-sources-guide.pdf`
- **Wiki:** [Channel Builder Custom Sources](https://github.com/roto31/StreamTV/wiki/Channel-Builder-Custom-Sources)

### Build frontend (first time or after UI changes)

```bash
cd frontend/builder
npm install --cache /tmp/npm-cache-streamtv
npm run build
```

## REST API (`/api/builder`)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/sources` | GET | List built-in + community sources |
| `/sources/reload` | POST | Rescan `data/builder_sources/` |
| `/auth/status` | GET | Per-source auth configured state |
| `/auth/archive` | POST | Archive.org username/password |
| `/auth/youtube/login` | POST | Playwright YouTube sign-in (async job) |
| `/auth/{scope}/cookies` | POST | Upload Netscape cookies.txt |
| `/docs/custom-sources.pdf` | GET | Download custom-sources guide |
| `/drafts` | POST | Create draft |
| `/drafts/{id}` | GET, PATCH, DELETE | Load / update / delete draft |
| `/drafts/{id}/links` | POST | Add URLs (batch, max 500) |
| `/drafts/{id}/resolve` | POST | Start async metadata resolution |
| `/drafts/{id}/build` | POST | Compile, import, reset playout |
| `/jobs/{id}` | GET | Poll job progress |
| `/filler-collections` | GET, POST | List / create filler libraries |
| `/auth-check` | POST | Pre-flight auth requirements |

OpenAPI docs: `/docs#/Channel%20Builder`

Retired Builder auth (PBS / Plex) lives under `parked/builder-sources/` and is **not** part of the live catalog. See [PBS Playwright](guides/PBS_PLAYWRIGHT.md) and [Vimeo gate](guides/VIMEO_BEDROCK_GATE.md).

## Ordering modes

| UI mode | Schedule output |
|---------|-----------------|
| As added | `order: chronological` (YAML stream index order) |
| Chronological | Streams sorted by upload/broadcast date at build time |
| Shuffle | `order: shuffle` on primary content block |

## Filler collections

Filler libraries are stored in `data/filler_collections/*.json` and referenced at build time. The compiler inserts commercial-break sequences between primary items (Olympics-style pattern).

## macOS client

`StreamTVMac` → **Manage Channels** uses `BuilderService` to build from a single URL, or links to the full web builder.

## Architecture

- **Source registry:** `streamtv/builder/sources/` (builtins: `archive_org`, `youtube`)
- **Drafts:** `data/builder_drafts/{id}.json`
- **Community manifests:** `data/builder_sources/*.yaml` (gitignored; example in docs)
- **Built channels:** `data/unified/{N}.channel.yaml`, `data/channels_generated_{N}.yaml`, `schedules/{N}.yml`
- **Scheduling engine:** Unchanged (frozen bedrock) — Builder emits Schedule v1 YAML only.

See also: [Two-layer channel model](channel-two-layer-model.md) · [Custom sources guide](builder/custom-sources-guide.md) · [Schedules](SCHEDULES.md)
