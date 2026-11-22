# StreamTV — project in-flight status

Rolling snapshot: **2026-11-22** (signed public DMG **`v1.4.5`**).

| Field | Value |
|-------|--------|
| VERSION | 1.4.5 |
| HEAD | `main` tip tagged `v1.4.5` |
| Latest tag | `v1.4.5` |
| Public DMG | https://github.com/roto31/StreamTV/releases/tag/v1.4.5 |

## Shipped in 1.4.5

Core product trim (watermarks / resolutions / PBS auth / schedule-items UI / Tunarr browse), Transcoding hub, Swagger CSP fix, mpegts.js docs, PRODUCT_SCOPE + public demo pack, open-source cull, **signed + notarized** `StreamTV.1.4.5-macos.dmg` (Developer ID stapled; `spctl` accepted).

## Do not touch without owner `APPROVED:`

Streaming bedrock / scheduling / HDHomeRun / cache behavioral keys / `api/iptv.py` — see `docs/STREAMING_BEDROCK_FROZEN.md`.

## Doc truth pointers

| Need | Where |
|------|--------|
| What VERSION is tip | Root `VERSION` + this file |
| What’s shipping next | `CHANGELOG.md` `[Unreleased]` |
| Product scope | `docs/PRODUCT_SCOPE.md` |
| Architecture diagrams | Root `ARCHITECTURE.md` (Mermaid; canonical) |
| Historical Jul-2026 status | Superseded banners on `EXECUTIVE_SUMMARY.md` / dated status reports |
