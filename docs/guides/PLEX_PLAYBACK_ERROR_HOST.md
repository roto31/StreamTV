# Plex Live TV “Playback Error” — host triage (Issue 71)

Use this when **Plex** shows Playback Error (or endless loading) on StreamTV
channels, but StreamTV WebUI preview and/or cache look fine.

StreamTV cannot force Plex to remux successfully if the **Plex Media Server**
host is out of disk, stuck in startup maintenance, or rewriting grabber segments
to a full volume. Do **not** change streaming bedrock first.

Related: [PLEX_LIVE_TV_RECOVERY.md](../plex/PLEX_LIVE_TV_RECOVERY.md) (DVR /
reloadGuide), [PLEX_VIDEO_HOLD.md](PLEX_VIDEO_HOLD.md),
[TUNARRRAM_PLAYOUT_RECOVERY.md](TUNARRRAM_PLAYOUT_RECOVERY.md),
[SOFT_DEPLOY.md](SOFT_DEPLOY.md), LESSONS Issue 71.

---

## 1. Split StreamTV vs Plex

| Check | Healthy signal |
|-------|----------------|
| Listener | `lsof -nP -iTCP:8410 -sTCP:LISTEN` — cwd is the **production repo**, not `~/Library/Application Support/StreamTV` |
| Health | `curl -sS http://127.0.0.1:8410/health` → `status: healthy` |
| Lineup | `curl -sS http://127.0.0.1:8410/lineup.json` — count ≫ 1; target GuideNumbers exist |
| Soak | Capture `/auto/v{N}` long enough for the source (YouTube ≥50s). Require real codecs and low late-null % — not HTTP 200 alone |

If StreamTV soak fails: use StreamTV skills (`verify-hdhomerun-streaming`,
YouTube tune diagnosis Issues 62–64). Stop blaming Plex.

If StreamTV soak **passes** and Plex still errors: continue below.

---

## 2. Boot disk and Plex Transcoder temp

**Symptom in PMS / Transcoder logs:**

```text
Error opening output file media-%05d.ts
```

**Cause:** Boot Data volume ~full. Live TV remux writes `ssegment` chunks under
the Transcoder temp directory (default under
`~/Library/Caches/PlexMediaServer/Transcode`).

**Steps:**

1. `df -h /` — free space should stay comfortably above a few GiB during tunes.
2. Create a temp dir on a volume with headroom, e.g.:
   `/Volumes/Server Clone/PlexTranscode`
3. Point PMS at it **without destroying Preferences**:

```bash
NEWTEMP="/Volumes/Server Clone/PlexTranscode"
mkdir -p "$NEWTEMP"
defaults write com.plexapp.plexmediaserver TranscoderTempDirectory "$NEWTEMP"
# Optional: symlink cache Transcode → NEWTEMP if you use that path
```

Or inject **only** `TranscoderTempDirectory="…"` into an existing
`~/Library/Application Support/Plex Media Server/Preferences.xml` after backup.

4. Quit/reopen Plex Media Server (or kickstart your PMS LaunchAgent **once**).
5. Confirm `defaults read com.plexapp.plexmediaserver TranscoderTempDirectory`
   and that new segment files appear under `$NEWTEMP` during a tune.

**Never:** Replace `Preferences.xml` with a brand-new minimal file that only
contains FriendlyName + token + TranscoderTempDirectory. That can break local
sign-in / mapping (see §4).

---

## 3. YouTube channels and TunarrRAM

**Symptoms:** Channel works in StreamTV preview after cache READY; Plex fails or
spins; StreamTV logs googlevideo **403** without full-cache.

**Steps:**

1. Ensure APFS RAM disk `/Volumes/TunarrRAM` (≈2 Gi) + heal LaunchAgent
   (`com.streamtv.tunarr-ram-heal`).
2. Production `config.yaml`: `cache.cache_directory` under TunarrRAM;
   `youtube_full_cache: true` when required for the channel.
3. LaunchAgent env: cache paths aligned; keep
   `STREAMTV_PLEX_VIDEO_HOLD_YOUTUBE=0` (Issue 62).
4. On-air: wait for `download_now` / `CACHE HIT` — do not soft-restart loops
   (Issue 64).

See [TUNARRRAM_PLAYOUT_RECOVERY.md](TUNARRRAM_PLAYOUT_RECOVERY.md).

---

## 4. Plex `/identity` 503 — startup maintenance

**Symptoms:**

```text
HTTP 503
Plex Media Server is currently running startup maintenance tasks.
```

Logs (`~/Library/Logs/Plex Media Server/Plex Media Server.log`):

- `MyPlex: mapping state set to 'Unknown'`
- `attempted to online our built-in agents but we're not yet signed in`
- `Grabber: Plex Tuner Service not running` / timeout
- Plugins ERROR opening `http://127.0.0.1:32400/...` (503 chicken-egg)

**Facts:**

- A running `Plex Media Server` PID is **not** enough.
- `plex.tv` may still accept the online token while **local** mapping /
  `presence` stays broken.
- `POST/GET …/myplex/claim` also returns **503** during maintenance — API
  reclaim will not clear the lock.

**Steps:**

1. On the Mac **GUI** session: Quit Plex Media Server completely; wait ~10s;
   open from Applications.
2. Complete any sign-in, claim, or privacy/TCC prompts.
3. Wait until `curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:32400/identity`
   prints **200** (often after BPQ settles; if still 503 after several minutes,
   continue).
4. Avoid rapid `kill -9` / kickstart loops (launchd throttle / worse state).
5. If still stuck: repair or reinstall Plex Media Server; prefer keeping
   `~/Library/Application Support/Plex Media Server` so Live TV device rows
   (StreamTV HDHR id) survive — restore Preferences from backup if you have one.

After identity **200**, retune **one** Live TV channel (native, then YouTube).

---

## 5. Remux / AAC notes (secondary)

If StreamTV soak is good, disk has space, and `/identity` is 200, but Plex still
fails:

- Check Transcoder logs for `AAC` / `sample rate not set` / `0 channels` —
  often early null keepalive or hold-splice before real media.
- Do **not** enable YouTube Plex video hold to hide spinners (Issue 62).
- Do **not** patch frozen `streamtv/` without owner `APPROVED:`.

---

## Quick command card

```bash
# StreamTV production?
lsof -nP -iTCP:8410 -sTCP:LISTEN
lsof -a -p "$(lsof -nP -iTCP:8410 -sTCP:LISTEN -t | head -1)" -d cwd

curl -sS http://127.0.0.1:8410/health
curl -sS http://127.0.0.1:8410/lineup.json | python3 -c 'import sys,json; d=json.load(sys.stdin); print(len(d))'

# Plex up?
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:32400/identity

# Disk
df -h / 
df -h /Volumes/TunarrRAM 2>/dev/null

# Transcoder preference
defaults read com.plexapp.plexmediaserver TranscoderTempDirectory 2>/dev/null || true
```

---

## See also

- LESSONS_LEARNED Issue 71
- Rule `.cursor/rules/plex-livetv-host-ops.mdc`
- Issues 42–43 (app vs production), 51 (soft deploy), 53 (log slice), 62–64 (YouTube)
