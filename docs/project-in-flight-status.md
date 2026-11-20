# StreamTV — project in-flight status

Rolling snapshot: **2026-11-19** (signed public DMG **`v1.4.2`**; docs/wiki currency pass).

| Field | Value |
|-------|--------|
| VERSION | 1.4.2 |
| HEAD | `main` tip tagged `v1.4.2` |
| Latest tag | `v1.4.2` |
| Public DMG | https://github.com/roto31/StreamTV/releases/tag/v1.4.2 |

## Shipped in 1.4.2

Release packaging hardenings (DMG notarize soft-fail after app staple; flaky YouTube expiry test). Prior **1.4.1** cut included `/player` preview, holiday channel packs, Plex video hold / TunarrRAM / soft-deploy operator guides. Public sanitized notes: `docs/public-repo/CHANGELOG.md`.

**Next:** Keep public docs/wiki synced after platform changes (rule `streamtv-public-repo-sync`); clean-Mac `DISTRIBUTION_CHECKLIST.md` smoke when convenient.

## Do not touch without owner `APPROVED:`

Streaming bedrock / scheduling / HDHomeRun / cache behavioral keys / `api/iptv.py` — see `docs/STREAMING_BEDROCK_FROZEN.md`.

## Doc truth pointers

| Need | Where |
|------|--------|
| What VERSION is tip | Root `VERSION` + this file |
| What’s shipping next | `CHANGELOG.md` `[Unreleased]` |
| Architecture diagrams | Root `ARCHITECTURE.md` (Mermaid; canonical) |
| Historical Jul-2026 status | Superseded banners on `EXECUTIVE_SUMMARY.md` / dated status reports |
