# Mini-Dev — Plex Live TV UI / server parity automation

**Date:** 2026-11-25  
**Host:** Mac Mini  
**Working drive:** `/Volumes/SSD Storage 2/Development_working_Drive/streamtv-resilience/`

## What “real” means

Manual Plex Live TV does **not** `curl` StreamTV. It asks **Plex Media Server** to tune the DVR/grabber; PMS then opens StreamTV’s HDHomeRun URL (`/auto/v{N}`), usually from the Mini LAN address.

This harness does the same server path:

1. `POST /livetv/dvrs/{dvrId}/channels/{channel}/tune`
2. Consume returned Live TV session HLS for N seconds (keeps grabber open)
3. Optional `--safari-ui` opens Plex Web for the session; optional `--applescript-guide` types the channel into the Live TV guide (Accessibility)

## Smoke (1987)

- Tune HTTP 200; `/livetv/sessions` size ≥ 1  
- HLS consume ~6.6 MiB in 45 s  
- StreamTV log: HDHomeRun/playout for channel **1987** (Scandal — The Warrior)  
- Agent: `com.streamtv.mini-plex-ui-parity-tune` every 1800 s  

## Scripts

| Path | Role |
|------|------|
| `…/scripts/plex_livetv_ui_parity_tune.py` | PMS `/tune` + HLS + optional Safari |
| `…/scripts/install-plex-ui-parity-tune-launchagent.sh` | Install/replace LaunchAgent |
| `…/scripts/plex_livetv_unattended_tune.py` | Older curl-only soak (superseded for continuous) |

## Not required for parity

- Plex desktop app (Mini has PMS + Safari only)  
- AppleScript alone without PMS `/tune` (deep links without `/tune` did not create sessions)

*Mini-Dev only; Studio unchanged until owner asks.*
