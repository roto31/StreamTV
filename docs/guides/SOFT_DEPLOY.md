# Soft deploy & per-channel isolation (Phase 3)

Avoid full `launchctl kickstart -k …/com.streamtv` when you only need channel
streams to reload schedule/playout state.

## Soft deploy (uvicorn stays up)

```bash
# All enabled channels
bash scripts/deploy_soft.sh

# One or more channels
bash scripts/deploy_soft.sh --channel 80 1954.1

# Preview
bash scripts/deploy_soft.sh --dry-run
```

API equivalents:

| Endpoint | Effect |
|----------|--------|
| `POST /api/channels/by-number/{n}/stream-restart` | One channel |
| `POST /api/channels/stream-restart-all` | Every enabled channel |

## What Phase 3 isolation includes

| Mechanism | Role |
|-----------|------|
| Per-channel `restart_channel` / soft deploy | Recycle one or all streams without killing uvicorn |
| Supervised continuous stream | Unexpected channel crash → restart **that** channel after `STREAMTV_CHANNEL_SUPERVISE_SEC` (default 15s); siblings keep playing |
| FFmpeg `start_new_session=True` | Each encode gets its own process group (killing one FFmpeg does not signal siblings) |

## When full kickstart is still required

- Importing changed Python modules into a running process (uvicorn does not hot-reload `streamtv/` by default; `STREAMTV_RELOAD=0` on production)
- LaunchAgent environment changes (`STREAMTV_CACHE_*`, stall env, etc.)
- Port / SSDP / process completely wedged

## Policy holds until stronger isolation

- **AutoHealer** stays `enabled: false` / `apply_fixes: false`
- **LoudNorm** stays **off** (`data/loudnorm_policy.json` tier `off`) until encode load is further isolated

Related: [TunarrRAM recovery](TUNARRRAM_PLAYOUT_RECOVERY.md), per-channel restart report (historical) `docs/reports/Executive_Summary_Per_Channel_Restart_2026-07-08.md`.
