# StreamTV — project in-flight status (rolling)

**Updated:** 2026-07-18  
**Tip:** `main` @ `3b73c56` · **Shipped:** `v1.3.4`

## Snapshot

| Item | State |
|------|--------|
| Public release | [v1.3.4](https://github.com/roto31/StreamTV/releases/tag/v1.3.4) — notarized DMG |
| Working tree | Clean |
| Stashes | 3 (PBS/Builder WIP from pre-merge) |
| Release CI | GitHub-hosted `macos-latest` (not M4) |
| Day-to-day CI | Still M4 self-hosted (`ci.yml`) |

## Recent movement

- Merged `cursor/sync-streamtvmac-v1-3-2-bundle` → `main` for 1.3.4
- Archive `-reconnect_at_eof` fix; hosted sign/notary; publish `RELEASE_TAG` guard
- Operator smoke: Magnum 80, Nature 1982, XMLTV on-air

## Recommended next actions

1. Fix clean-CI pytest fixtures (promote full suite to hard-gate)
2. Sync public docs/wiki for 1.3.4
3. Triage `git stash` WIP vs live 1982 Nature
4. Optional: install public DMG and log Plex soak

## Reports

- [Status Report 2026-07-18](StreamTV_Status_Report_2026-07-18.md)
- [Gap Closure Plan 2026-07-18](StreamTV_Gap_Closure_Plan_2026-07-18.md)
