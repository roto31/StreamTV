# StreamTV — project in-flight status

Rolling snapshot: **2026-11-22** (core → 100% trim; tip **`v1.4.5`**).

| Field | Value |
|-------|--------|
| VERSION | 1.4.5 |
| HEAD | `main` (tag after release CI) |
| Latest tag | cut `v1.4.5` after public sync + smoke |
| Public DMG | tag `v1.4.5` on https://github.com/roto31/StreamTV/releases |

## Shipped in 1.4.5 (this cut)

Product surface trim (watermarks / resolutions / PBS auth / schedule-items UI / Tunarr browse), Transcoding hub, Swagger CSP fix, mpegts.js docs, PRODUCT_SCOPE + public demo pack, Linux retire + Builder title/runtime fixes, open-source culled sync.

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
