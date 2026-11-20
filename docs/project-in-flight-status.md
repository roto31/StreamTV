# StreamTV — project in-flight status

Rolling snapshot: **2026-11-19** (signed public DMG cut **`v1.4.1`**).

| Field | Value |
|-------|--------|
| VERSION | 1.4.1 |
| HEAD | `main` tip tagged `v1.4.1` |
| Latest tag | `v1.4.1` |
| Public DMG | https://github.com/roto31/StreamTV/releases/tag/v1.4.1 |

## Shipped in 1.4.1

Material product work previously under `CHANGELOG.md` **`## [Unreleased]`** moved to **`## [1.4.1]`**, including `/player` preview, holiday channel packs + icons, Plex video hold / TunarrRAM / soft-deploy hardenings, and related operator docs. Public sanitized notes: `docs/public-repo/CHANGELOG.md`.

**Next:** Confirm Release workflow green → promote prerelease if needed → clean-Mac `DISTRIBUTION_CHECKLIST.md` smoke when convenient.

## Do not touch without owner `APPROVED:`

Streaming bedrock / scheduling / HDHomeRun / cache behavioral keys / `api/iptv.py` — see `docs/STREAMING_BEDROCK_FROZEN.md`.

## Doc truth pointers

| Need | Where |
|------|--------|
| What VERSION is tip | Root `VERSION` + this file |
| What’s shipping next | `CHANGELOG.md` `[Unreleased]` |
| Historical Jul-2026 status | Superseded banners on `EXECUTIVE_SUMMARY.md` / dated status reports |
