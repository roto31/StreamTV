# StreamTV — project in-flight status

Rolling snapshot: **2026-11-25** (tip **`v1.4.7.7`** — Troubleshooting UI + streaming resilience ops parked).

| Field | Value |
|-------|--------|
| VERSION | 1.4.7.7 |
| HEAD | `main` tip tagged `v1.4.7.7` (when pushed) |
| Latest tag | `v1.4.7.7` |
| Public DMG | https://github.com/roto31/StreamTV/releases/tag/v1.4.7.7 |

## Shipped in 1.4.7.7 (this tip)

- **Settings → Troubleshooting** (Web UI + Swift) — public-safe script catalog with hover help
- **Streaming resilience ops** — SSD keep-warm, pre-warm LaunchAgent/scripts, F-class quarantine; **Phase 3 PARKED**
- Prior 1.4.7.x: first-run/SetupDone, AAC gate, freshness, Channel Creator MCP, Updates, starter packs

## Do not touch without owner `APPROVED:`

Streaming bedrock / scheduling / HDHomeRun / cache behavioral keys / `api/iptv.py` — see `docs/STREAMING_BEDROCK_FROZEN.md`. Phase **3a–3f** remain parked (`docs/plans/streaming-resilience-phase3-gate-20261125.md`).

## Doc truth pointers

| Need | Where |
|------|--------|
| What VERSION is tip | Root `VERSION` + this file |
| What’s shipping next | `CHANGELOG.md` `[Unreleased]` / release notes |
| Resilience ops | `docs/guides/STREAMING_RESILIENCE_OPS.md` |
| Troubleshooting scripts | `docs/TROUBLESHOOTING_SCRIPTS.md` · wiki Scripts-and-Tools |
| Product scope | `docs/PRODUCT_SCOPE.md` |
| Architecture diagrams | Root `ARCHITECTURE.md` (Mermaid; canonical) |
