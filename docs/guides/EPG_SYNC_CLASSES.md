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
| `scripts/verify_epg_health_loop.sh` | Token + RAM + active-channel alignment |
| `scripts/verify_tunarr_ram.sh` | `/Volumes/TunarrRAM` headroom |
| `scripts/install-epg-verify-launchagent.sh` | Every 6 hours |
| `scripts/install-epg-health-launchagent.sh` | Every 30 minutes |
| `scripts/install-tunarr-ram-verify-launchagent.sh` | Sundays 03:00 |
| `scripts/plex_class_a_channel_soak.sh` | **8h Plex WebGUI** random class-A retune soak (PIN login in browser) |

## Plex DVR hygiene

- Use **one** StreamTV HDHomeRun device (`http://<host>:8410/discover.json`).
- Remove duplicate or Tunarr DVR entries when using direct StreamTV guide.
- Set `tuner_manager.merged_guide: false` and EPG URL:
  `http://<host>:8410/iptv/xmltv.xml`
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
