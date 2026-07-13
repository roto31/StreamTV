# Channel Builder — Custom streaming sources

This guide explains how to add **community** (operator-local) streaming sources to Channel Builder without modifying playout bedrock until you are ready.

## Architecture

| Layer | Responsibility |
|-------|----------------|
| **Builder registry** | `streamtv/builder/sources/` — source picker, URL validation, auth methods |
| **Builder resolver** | `streamtv/builder/resolver.py` — metadata and expansion (PBS show pages, playlists) |
| **Builder auth** | `/api/builder/auth/*` — inline sign-in; cookies saved under `data/cookies/` |
| **Playout bedrock** | `streamtv/streaming/**` — FFmpeg adapters, golden tests (owner approval required) |

Community sources can appear in Builder with `playout_ready: false` so you prepare channel YAML while implementing the streaming adapter separately.

## Quick start

1. Copy [`docs/examples/builder-source.example.yaml`](../examples/builder-source.example.yaml) to `data/builder_sources/my_site.yaml`.
2. Edit `id`, `label`, and `hosts`.
3. Restart StreamTV or call `POST /api/builder/sources/reload`.
4. Open `/builder` — your source appears under **Your sources**.

## Manifest fields

Validated by [`schemas/builder_source.schema.json`](../../schemas/builder_source.schema.json).

| Field | Required | Description |
|-------|----------|-------------|
| `id` | yes | Lowercase key (`my_streaming_site`) |
| `label` | yes | Display name in Source Picker |
| `hosts` | yes | Hostnames for URL validation |
| `auth.method` | no | `cookies`, `playwright`, `password`, `token`, or `none` |
| `auth.login_url` | for Playwright | Sign-in page URL |
| `auth.cookies_domain` | recommended | Cookie domain filter after Playwright login |
| `url_patterns` | no | Hint paths shown in the URL paste step |
| `supports_expand` | no | Show/collection expansion (custom module) |
| `playout_ready` | no | Default `false` — must be `true` to build a channel |
| `channel_source` | when playout enabled | `source` value in unified YAML |
| `module` | advanced | Python import path for custom resolver hooks |

## Authentication

Passwords are **never** persisted. Playwright sign-in writes Netscape `cookies.txt` files only.

| Method | Builder UI |
|--------|------------|
| `cookies` | Upload `cookies.txt` |
| `playwright` | Email + password (automated browser) |
| `password` / `token` | Source-specific forms (Plex uses token today) |

2FA and CAPTCHA may block Playwright — use cookie upload as fallback.

## Resolver hooks

For metadata beyond URL slug titles, implement an optional Python module and set `module` in the manifest. PBS show expansion (`streamtv/builder/pbs_show.py`) is the reference pattern for harvest + dedupe.

## Enable playout (bedrock)

When the streaming adapter exists and bedrock changes are **owner-approved**:

1. Add `channel_source` to [`schemas/channel.schema.json`](../../schemas/channel.schema.json) `source` enum.
2. Implement `StreamSource` adapter under `streamtv/streaming/`.
3. Wire importer mapping in channel import path.
4. Set `playout_ready: true` in the community manifest.
5. Add tests; run golden FFmpeg tests if the adapter uses FFmpeg.
6. Update `CHANGELOG.md` and sync distributions.

## Vimeo roadmap

Vimeo is registered as `coming_soon` in the built-in registry. When a bedrock adapter is approved, flip `streamtv/builder/sources/builtins/vimeo.py` to `active` and complete the playout checklist above.

## Publishing

- Wiki: [Channel Builder Custom Sources](https://github.com/roto31/StreamTV/wiki/Channel-Builder-Custom-Sources)
- Regenerate PDF: `bash scripts/generate_builder_custom_sources_pdf.sh`
- Public sync: `bash scripts/sync_public_docs.sh --apply --wiki`
