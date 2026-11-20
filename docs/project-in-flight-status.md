# StreamTV — project in-flight status

Rolling snapshot: **2026-09-19** (Phase 1 packaging: **`VERSION` → 1.4.0**; tag/DMG pending operator).

| Field | Value |
|-------|--------|
| VERSION | 1.4.0 (packaging PR; not yet tagged) |
| HEAD | `main` tip past `v1.3.6` + release bump branch |
| Latest tag | `v1.3.6` (2026-07-18) until `v1.4.0` is pushed |
| Public DMG | https://github.com/roto31/StreamTV/releases/tag/v1.3.6 (1.4.0 after release CI) |

## Shipped in 1.4.0 packaging cut

Material product commits previously under `CHANGELOG.md` **`## [Unreleased]`** moved to **`## [1.4.0]`**, including:

- Automatic backup and restore (+ Settings UI, macOS first-launch, `/api/backup/*`)
- Apple Foundation Models + AutoHealer dual-backend
- LoudNorm / TunarrRAM / FFmpeg stall / playout-lag operator docs and in-repo heals where present
- Magnum ch80 classic artwork notes; YouTube 403 / Clean-CI / release pytest gate
- Docs index sync (`docs/INDEX.md`)

**Next:** Merge packaging PR → Chris confirms bedrock tip acceptance → `git tag v1.4.0 && git push origin v1.4.0` → signed DMG + clean-Mac `DISTRIBUTION_CHECKLIST.md` smoke.

## Do not touch without owner `APPROVED:`

Streaming bedrock / scheduling / HDHomeRun / cache behavioral keys / `api/iptv.py` — see `docs/STREAMING_BEDROCK_FROZEN.md`. Tip past `v1.3.6` already contains `c4943f2` bedrock paths on `main`; packaging release does not add new bedrock edits.

## Doc truth pointers

| Need | Where |
|------|--------|
| What VERSION is tip | Root `VERSION` + this file |
| What’s shipping next | `CHANGELOG.md` `[Unreleased]` (empty after 1.4.0 cut) |
| Historical Jul-2026 status | Superseded banners on `EXECUTIVE_SUMMARY.md` / dated status reports |
