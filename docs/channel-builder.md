# Channel Builder

Assemble custom StreamTV channels from Archive.org, YouTube, PBS, and Plex through a guided web wizard or REST API.

## When to use Channel Builder vs Import Channels

| Task | Use |
|------|-----|
| Create a **new** channel from URLs (YouTube, Archive.org, PBS, Plex `plex://`) | **Channel Builder** (`/builder`) |
| **Migrate** channel YAML from another StreamTV server | **Import Channels** (`/import`) |
| **Bulk import** hand-edited channel packs (`channels:` list YAML) | **Import Channels** (`/import`) |
| Re-import after editing `data/channels*.yaml` on disk | **Import Channels** (`/import`) |

Both paths end at `import_channels_from_yaml()`; Builder also writes `data/unified/{n}.channel.yaml` and `schedules/{n}.yml`.

## Quick start

1. Open **Channel Builder** from the sidebar (`/builder`) or visit `http://localhost:8410/builder`.
2. **Source** — Pick Archive.org, YouTube, PBS, or Plex (Vimeo appears as *Coming soon*).
3. **Sign In** — Inline authentication on the Builder page (Playwright for YouTube/PBS, forms for Archive.org/Plex).
4. **URLs** — Paste or drop links; playlists, collections, and PBS show pages expand on resolve.
5. **Order & Fillers** — Choose playback order; attach reusable filler libraries.
6. **Channel Info** — Set channel number, name, and collection name.
7. **Review & Build** — Compiles unified YAML, imports inventory, writes schedule, resets playout.

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
| `/auth/pbs/login` | POST | Playwright PBS sign-in (async job) |
| `/auth/plex` | POST | Plex server URL + token |
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

## Ordering modes

| UI mode | Schedule output |
|---------|-----------------|
| As added | `order: chronological` (YAML stream index order) |
| Chronological | Streams sorted by upload/broadcast date at build time |
| Shuffle | `order: shuffle` on primary content block |

## Filler collections

Filler libraries are stored in `data/filler_collections/*.json` and referenced at build time. The compiler inserts commercial-break sequences between primary items (Olympics-style pattern).

## PBS sources

PBS is supported in Channel Builder with `source: pbs` in generated channel YAML.

| URL type | Example | Supported? |
|----------|---------|------------|
| Episode / video page | `https://www.pbs.org/video/...` | Yes |
| Show landing page | `https://www.pbs.org/show/nature/` | Yes — expands to `/video/` catalog on resolve |
| Live stream page | `https://www.pbs.org/watch-live/...` | Yes |
| Direct HLS | `https://...lls.pbs.org/....m3u8` | Yes |

Show pages harvest episode links from HTML; full season catalogs use Playwright season iteration when PBS cookies are configured. Catalogs cap at 500 videos per show.

Member-only or geo-restricted PBS content requires PBS sign-in on the Builder **Sign In** step (or cookie upload).

## macOS client

`StreamTVMac` → **Manage Channels** uses `BuilderService` to build from a single URL, or links to the full web builder.

## Architecture

- **Source registry:** `streamtv/builder/sources/`
- **Drafts:** `data/builder_drafts/{id}.json`
- **Community manifests:** `data/builder_sources/*.yaml` (gitignored; example in docs)
- **Built channels:** `data/unified/{N}.channel.yaml`, `data/channels_generated_{N}.yaml`, `schedules/{N}.yml`
- **Scheduling engine:** Unchanged (frozen bedrock) — Builder emits Schedule v1 YAML only.

See also: [Two-layer channel model](channel-two-layer-model.md) · [Custom sources guide](builder/custom-sources-guide.md)
