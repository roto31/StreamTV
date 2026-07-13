# Channel Builder — Custom Sources

Add operator-local streaming sites to Channel Builder using YAML manifests. This page is sanitized for the public wiki.

## Overview

Channel Builder v2 uses a **source registry**:

- **Built-in sources:** Archive.org, YouTube, PBS, Plex (playout-ready today)
- **Coming soon:** Vimeo (metadata stub only)
- **Community sources:** YAML files in `data/builder_sources/`

Community sources can prepare channel metadata while playout adapters are developed separately.

## Quick start

1. Copy the example manifest from the repository: `docs/examples/builder-source.example.yaml`
2. Save as `data/builder_sources/my_site.yaml` on your StreamTV server
3. Reload sources: `POST /api/builder/sources/reload` or restart the app
4. Open `/builder` and pick your source under **Your sources**

## Manifest schema

See `schemas/builder_source.schema.json` in the repository.

Key fields:

- `id` — stable lowercase identifier
- `label` — display name
- `hosts` — URL hostnames for validation
- `auth.method` — `cookies`, `playwright`, or `none`
- `playout_ready` — must be `true` before **Build Channel** succeeds

## Authentication

Sign in on the Builder **Sign In** step. Passwords are not stored; only session cookies are written to `data/cookies/`.

If automated sign-in fails (2FA/CAPTCHA), export a Netscape `cookies.txt` from your browser and upload it in Builder.

## Playout

Building a channel requires a streaming adapter in the playout engine. Until `playout_ready: true` and the adapter ships, Builder blocks build with an actionable message.

See also:

- [Channel Builder](channel-builder.md) (in-tree docs)
- [Authentication](Authentication.md)
- [API Reference](API-Reference.md)

## PDF guide

Download from the Builder UI footer or `GET /api/builder/docs/custom-sources.pdf` after running `scripts/generate_builder_custom_sources_pdf.sh`.
