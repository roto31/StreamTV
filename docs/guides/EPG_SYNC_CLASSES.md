# EPG sync classes (A / B / C)

StreamTV classifies channels so XMLTV, playout, and Plex stay aligned without
skipping mid-item on tune.

## Classes

| Class | Channels (examples) | Behavior |
|-------|---------------------|----------|
| **A** | 1986, 1987, 1988, 1991, 1994 | Short-form continuous; **playout-authoritative** row 0; boundary `reloadGuide`; prefetch next item (`count=1`) |
| **B** | 80, 1980, 1984, 123, 143, … | Archive marathon; enable `playout.archive_tune_seek` for intra-episode tune seek |
| **C** | 1929, 11, 1954, … | Cycle/idle; wall-clock guide ahead of air=0 is normal when untuned |

Set per channel in unified YAML:

```yaml
channel:
  number: "1986"
  epg_sync_class: A
```

## Config (`config.yaml`)

```yaml
playout:
  epg_sync_classes:
    A:
      playout_authoritative_epg: true
      epg_pad_seconds: 5
      prefetch_at_boundary: 1
      reload_on_item_boundary: true
    B:
      archive_tune_seek: true
    C: {}

plex:
  reload_on_item_boundary: true
  item_boundary_cooldown_s: 90
  global_reload_cooldown_s: 900
```

## Operator scripts

| Script | Purpose |
|--------|---------|
| `scripts/verify_plex_token.sh` | Plex `reloadGuide` token probe (expect 200) |
| `scripts/verify_epg_sync.sh` | Scheduled EPG alignment (`--all` + class-A channels) |
| `scripts/verify_epg_health_loop.sh` | Token + RAM + active-channel alignment + playout-lag heal |
| `scripts/heal_playout_lag.py` | **Self-heal** saved `last_item_index` stuck behind wall-clock guide (tune-only idle freeze) |
| `scripts/verify_tunarr_ram.sh` | `/Volumes/TunarrRAM` headroom |
| `scripts/install-epg-verify-launchagent.sh` | Every 6 hours |
| `scripts/install-epg-health-launchagent.sh` | Every 30 minutes |
| `scripts/install-playout-lag-heal-launchagent.sh` | Every 15 minutes (+ RunAtLoad) |
| `scripts/install-tunarr-ram-verify-launchagent.sh` | Sundays 03:00 |
| `scripts/plex_class_a_channel_soak.sh` | **8h Plex WebGUI** random class-A retune soak (PIN login in browser) |

### Idle / tune-only freeze (lesson 2026-07-20)

With `cache.playback_mode=buffer` and tune-only buffering, continuous channels **do not**
run FFmpeg while untuned. Before the idle catch-up fix, `last_item_index` stayed frozen
after restart (e.g. Magnum **80** at item 9 while wall-clock guide was at 39).

- **Runtime safeguard:** `ChannelManager` idle loop catches up to wall-clock guide when
  `client_count == 0` and guide is ahead.
- **Periodic self-heal:** `heal_playout_lag.py --apply` (skips channels with active tuners).
  Install: `bash scripts/install-playout-lag-heal-launchagent.sh`
  Typical LaunchAgent: `com.streamtv.playout-lag-heal` (every **15 minutes** + RunAtLoad).

```bash
./venv/bin/python scripts/heal_playout_lag.py --dry-run
./venv/bin/python scripts/heal_playout_lag.py --apply
./venv/bin/python scripts/heal_playout_lag.py --apply --channel 80
```

### Class-A EPG mega-slots when playout lags

For class-A channels (e.g. **1987**, **1991**), if live `last_item_index` trails the
wall-clock guide, XMLTV must **not** stretch a single on-air row across many hours.
Lagging rows cap to media duration (+120s) and rebase so the live title still covers
“now”. Retune Plex clients after a large guide rebuild ([Plex Live TV recovery](../plex/PLEX_LIVE_TV_RECOVERY.md)).

## Plex DVR hygiene

- Use **one** StreamTV HDHomeRun device (`http://<host>:8410/discover.json`).
- Remove duplicate or external DVR entries when using direct StreamTV guide.
- Set EPG URL to `http://<host>:8410/iptv/xmltv.xml`
- **`reloadGuide` DVR id:** operator scripts and `com.streamtv.epg-health` default to
  Plex DVR **119** (retired **117** / **113** / **109** return HTTP 404). StreamTV
  `guide_reload` falls back to live `/livetv/dvrs` discovery on failure. Override with
  `PLEX_DVR_ID` / `config.plex.dvr_id` when PMS recreates the DVR.
- After `reloadGuide`, **retune** class-A channels on Plex clients (session lock).
- Automated soak: `bash scripts/plex_class_a_channel_soak.sh` (8h, headed Chrome; auto-clicks Plex user `Roto`, then enter PIN on `http://192.0.2.1:32400/...live-tv...dvr.guide`).
- Override Plex user: `SOAK_PLEX_USER=roto31 bash scripts/plex_class_a_channel_soak.sh`
- Pilot (2–3 min): `SOAK_DURATION_SECONDS=180 SOAK_MIN_DWELL_SECONDS=30 SOAK_MAX_DWELL_SECONDS=45 bash scripts/plex_class_a_channel_soak.sh`

## Verification

```bash
./venv/bin/python scripts/verify_epg_playout_alignment.py --channel 1986
./venv/bin/python scripts/verify_epg_playout_alignment.py --all
bash scripts/verify_plex_token.sh
```

See [Plex Live TV recovery](../plex/PLEX_LIVE_TV_RECOVERY.md).
