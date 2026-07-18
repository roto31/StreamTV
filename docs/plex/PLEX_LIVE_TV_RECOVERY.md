# Plex Live TV recovery after StreamTV restart or hang

StreamTV cannot force a Plex client to retune automatically. Plex Live TV
holds tuner sessions and does not expose a supported API to restart playback on
a specific channel after StreamTV restarts or after the Plex Tuner Service hangs.

## What StreamTV does automatically

- Continuous playout resumes from saved `last_item_index` after restart.
- MPEG-TS bytes are available again on `/hdhomerun/auto/v{channel}`.
- YouTube RAM-cache waits are capped at `cache.tune_buffer_max_wait_seconds`
  (default **5s**) when a tuner is connected, then FFmpeg falls back to CDN.
- Off-schedule cache eviction is scoped per channel schedule so channel 1986
  prefetch cannot delete channel 1991 cache files.

## What Plex does not do

- Plex clients do **not** auto-retune when StreamTV restarts.
- Plex does **not** release a tuner immediately after disconnect; holds are often
  ~15 minutes by design.
- There is no reliable, documented Plex API to tell a Live TV session to retry
  the current channel after a backend outage.

## Known working operator recovery (Plex)

Use these when Plex shows **Playback Error**, **Could not tune channel**, or an
infinite spinner after StreamTV was restarted:

### 1. Retune in Plex (fastest)

1. Stop playback on the stuck channel.
2. Select the same channel again in the Live TV guide.

StreamTV will join the current on-air item (`tune join deferred` in logs).

### 2. Restart Plex Tuner Service (when tuning fails on every channel)

On the Plex Media Server host:

```bash
# macOS / Linux — kill hung tuner service; PMS usually respawns it
pkill -f "Plex Tuner Service"
```

If channels still fail, restart Plex Media Server:

```bash
# macOS — quit from menu bar, or:
launchctl kickstart -k gui/$(id -u)/com.plexmediaserver

# Linux systemd
sudo systemctl restart plexmediaserver
```

### 3. Refresh guide (EPG drift only)

Plex **Settings → Live TV & DVR → Refresh Guide** often does **not** re-fetch
XMLTV from StreamTV when playout has resumed behind the wall-clock schedule.
Use the server API instead:

```bash
bash scripts/reload_plex_streamtv_guide.sh
bash scripts/verify_plex_token.sh   # expect HTTP 200; 403 = fix STREAMTV_PLEX_TOKEN
```

After StreamTV restart, when playout resumes behind wall-clock (`last_item_index`
< guide index), StreamTV can auto-call the same API if `plex.auto_reload_guide`
is true (default) and a Plex token is available.

Then wait 1–2 minutes and reopen the Live TV guide on clients.

**After a full `reloadGuide` rebuild**, Plex may still show the wrong “now
playing” title until you **stop and retune** the channel — the grid can update
while the active tuner session keeps old programme metadata (e.g. guide shows
Emmylou Harris while Ronnie Milsap is on-air). Retune fixes the session overlay.

**Stacked / double titles in every guide cell** (especially after multiple
`reloadGuide` runs): Plex’s EPG database can retain duplicate airings when XMLTV
start times shift by seconds between fetches. StreamTV now stabilizes emitted
start times per on-air item. To clear airings already stacked in Plex:

1. Plex → Settings → Live TV & DVR → remove the XMLTV guide source (or the
   whole StreamTV device).
2. Re-add the tuner; set EPG to `http://<streamtv-host>:8410/tuners/guide.xml`
   when `merged_guide` is enabled.
3. Run `bash scripts/reload_plex_streamtv_guide.sh` once, wait 2–3 minutes,
   then retune channels on clients.

### 4. Re-add tuner (last resort)

**Before re-adding:** remove duplicate DVRs (physical HDHomeRun, Tunarr, or old
StreamTV entries). Plex should use **one** StreamTV device at
`http://<streamtv-host>:8410/hdhomerun/discover.json` with EPG
`http://<streamtv-host>:8410/iptv/xmltv.xml` when `tuner_manager.merged_guide`
is **false** (recommended for playout-aligned guide).

1. Plex → Settings → Live TV & DVR → remove extra StreamTV/Tunarr/duplicate devices.
2. Re-add using `http://<streamtv-host>:8410/hdhomerun/discover.json`.
3. Rescan channels and set XMLTV to `http://<streamtv-host>:8410/iptv/xmltv.xml`.
   When `tuner_manager.merged_guide` is enabled (StreamTV + Tunarr on one Plex
   server), use the merged guide:
   `http://<streamtv-host>:8410/tuners/guide.xml`

## StreamTV-side checks

```bash
curl -s http://127.0.0.1:8410/health
curl -s -m 20 -o /dev/null -w "%{http_code} %{size_download}\n" \
  http://127.0.0.1:8410/hdhomerun/auto/v1991
df -h /Volumes/TunarrRAM
```

Healthy tune: HTTP **200** and non-zero bytes within ~20s.

## Related docs

- [Plex integration troubleshooting](../troubleshooting/PLEX_INTEGRATION_ISSUES.md)
- [Add Tunarr/StreamTV in Plex](../guides/ADD_TUNARR_IN_PLEX.md)
