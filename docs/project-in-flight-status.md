# StreamTV — project in-flight status

Rolling snapshot: **2026-11-21** (signed public DMG **`v1.4.3`** cut in progress / tip).

| Field | Value |
|-------|--------|
| VERSION | 1.4.3 |
| HEAD | `main` tip tagged `v1.4.3` |
| Latest tag | `v1.4.3` |
| Public DMG | https://github.com/roto31/StreamTV/releases/tag/v1.4.3 |

## Shipped in 1.4.3

Channel Creator MCP (`mcp_streamtv` / optional `mcp_archive_org`), host wiring + all-in-one setup script, `.ia.mp4` ban, core trim (schedules inventory, Collections/AI surfaces retired, Builder Archive+YouTube only). Public sanitized notes: `docs/public-repo/CHANGELOG.md`.

**Next:** Promote public prerelease after CI notarize; clean-Mac `DISTRIBUTION_CHECKLIST.md` smoke when convenient.

## Do not touch without owner `APPROVED:`

Streaming bedrock / scheduling / HDHomeRun / cache behavioral keys / `api/iptv.py` — see `docs/STREAMING_BEDROCK_FROZEN.md`.

## Doc truth pointers

| Need | Where |
|------|--------|
| What VERSION is tip | Root `VERSION` + this file |
| What’s shipping next | `CHANGELOG.md` `[Unreleased]` |
| Architecture diagrams | Root `ARCHITECTURE.md` (Mermaid; canonical) |
| Historical Jul-2026 status | Superseded banners on `EXECUTIVE_SUMMARY.md` / dated status reports |
