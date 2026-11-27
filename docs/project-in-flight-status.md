# StreamTV — project in-flight status

Rolling snapshot: **2026-11-27** (tip still **`v1.4.7.7`**; Session land on `main` Unreleased).

| Field | Value |
|-------|--------|
| VERSION | 1.4.7.7 |
| HEAD | `main` + Unreleased Session 2026-11-27 (Plex/ATV heal + Issue 75 + inventory) |
| Latest tag | `v1.4.7.7` |
| Public DMG | https://github.com/roto31/StreamTV/releases/tag/v1.4.7.7 |

## Shipped / landing this session (Unreleased → private `main`)

- **Plex/Apple TV Archive path** — probe retry, keepalive heal (≥30 s × 2, skip watching clients), wait-phase hold + geometry (480/720), probe sidecars, first-chunk 60 s, **under-rate copy abort**
- **Issue 75** — cookie-aware warm; reachability classifiers; no false 401 purges; URL uniqueness
- **HEVC** — accept encode on Studio; twin report-only; **Direct Play HOLD** (Mini fork only)
- **Inventory (private)** — Sesame 123 AAPB 1980s rebuild; Mister Rogers 143 S22/S23 anniversary remap + S01 YouTube

## Do not touch without owner `APPROVED:`

Streaming bedrock / scheduling / HDHomeRun / cache behavioral keys / `api/iptv.py` — see `docs/STREAMING_BEDROCK_FROZEN.md`. Phase **3a–3f** remain parked. Studio HEVC MPEG-TS copy stays **off**.

## Doc truth pointers

| Need | Where |
|------|--------|
| What VERSION is tip | Root `VERSION` + this file |
| What’s shipping next | `CHANGELOG.md` `[Unreleased]` / `docs/public-repo/CHANGELOG.md` |
| Resilience ops | `docs/guides/STREAMING_RESILIENCE_OPS.md` · wiki Streaming-Resilience-Ops |
| Archive probe / heal / auth | `docs/guides/ARCHIVE_PROBE_RETRY_KEEPALIVE.md` |
| Troubleshooting scripts | `docs/TROUBLESHOOTING_SCRIPTS.md` · wiki Scripts-and-Tools |
| Architecture diagrams | Root `ARCHITECTURE.md` (Mermaid; canonical) |
| Issue 75 false purge | `LESSONS_LEARNED.md` Issue 75 · rule `archive-org-auth-reachability.mdc` |
