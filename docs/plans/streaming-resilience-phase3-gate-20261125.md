# Phase 3 gate decision — 2026-11-25 ~18:02 local

**Owner:** conditional APPROVED to start Phase 3 *if evidence proves*.  
**Status: PARKED (owner 2026-11-25 ~19:23).** Do not open any named package (**3a–3f**).  
**Verdict:** Ops/config + quarantine sufficient. Post–keep-warm Studio manual (Archive→YT→mixed, ~18:44–18:56) explained by ops/content — not bedrock. Re-open only on **already READY** hang or new GVS-403 / Archive CDN matrix.

## Evidence sources
1. **Mini manual tunes** (preferred over UI-parity CD) — YouTube cold→retune OK; prefetch 0→4; SSD cache.  
2. **Mini boundary probe** — post-prefetch4 HDHR **5/6 ≤5 s**.  
3. **1225 item-94** — quarantined `marathon_80s_1` (content/F-class), not 3a.  
4. **Studio post-SSD kickstart** (this window) — see below.  
5. **Studio mixed-channel manual HDHR** — **done ~18:03–18:13** from Plex `192.0.2.1` (see §Studio manual soaks).  
6. **Studio post–keep-warm manual** — **done ~18:44–18:56** Archive→YouTube→mixed (see §Keep-warm re-soak).

## Studio post-SSD + manual mixed soaks (~17:57–18:13)
| Signal | Result |
|--------|--------|
| Cache path | `/Volumes/SSD Storage/StreamTV-media-cache` (prefetch=4) |
| Cache size | ~**4.8 GiB** (mostly `youtube/`) |
| `Cache READY` | Ongoing large YouTube fills on SSD |
| ENOSPC | **0** |
| WARN timeout/stall | **0** in session |
| Manual soaks | **7/9 sustained** (≥1500 chunks); **2 short** then retune sustained (**1984**, **1988** YouTube tune-buffer) |

## Package-by-package

| Pkg | Open? | Why |
|-----|-------|-----|
| **3a** CDN-first | **No** | Failures explained by fragile assets (F + 1225 `marathon_80s_1`); quarantine first. No proof buffer/streamer change required. |
| **3b** copy CBR | **No** | No new sustained copy-bitrate matrix failure post-ops. |
| **3c** stall heal | **No** (ops done) | LaunchAgent already on Studio/Mini. |
| **3d** yt-dlp/clients | **No** | No GVS-403 storm in this evidence set. |
| **3e** video hold | **No** | Mini Phase 1: hold ON worse. |
| **3f** prefetch bedrock | **Parked** | Keep-warm re-soak sufficient; no READY-file hang proof. Owner parked Phase 3 entirely ~19:23. |

## Keep-warm re-soak (Studio Plex WebUI, ~18:44–18:56)

Order: Archive → YouTube → mixed. Plex `192.0.2.1`.

| Ch | Phase | Result vs prev (~18:03) |
|----|-------|-------------------------|
| 80, 123 | Archive | Instant first-media (CDN-first); healthy (new vs prev set) |
| 1128 | Mixed | Instant; `[CACHE HIT]` local — better than historical slow Archive CDN |
| 1225 | Archive | Instant; WCCO Frosty breaks (quarantine holding) — matches prev sustained |
| 1986, 1987 | YouTube | Cold `download_now` ~20–23 s → READY/Streaming — same class as prev 1984/1988, recovered in-session |
| 1991 | YouTube | Cold wait → Plex Playback Error (~25 s) → file READY late → retune hung **keepalive/~90% null** → soft-restart → item 131 *Hard Workin' Man* **played clean** |

**Verdict of re-soak:** Keep-warm direction validated for Archive + typical YT. Residual risk = (1) Plex abort before READY under concurrency-1, (2) post-abort FFmpeg/keepalive wedge — F-class dead ids quarantined (below).

## Remaining (non-Phase-3)
1. ~~Owner Studio manual mixed tunes~~ — done ~18:03–18:13; 7/9 sustained; 1984/1988 cold→retune.  
2. Optional: retarget cache to `/Volumes/SSD Storage/TunarrRAM/streamtv-cache` (requested; not applied).  
3. ~~Keep-warm ops (cold YouTube wait)~~ — **applied Studio 2026-11-25 ~18:25** (see §Keep-warm).  
4. ~~Keep-warm re-soak~~ — **done ~18:44–18:56** (above).  
5. ~~**F-class quarantine**~~ — **done ~19:00:** `IJyX07YuzDk` removed from 1991 inventories; `kUGC5oRpbkg` from 1987 (+ starter 9102 URL); vault `data/quarantine/dead_youtube_fclass_20261125.yaml`; DB collection/playlist links cleared Studio+Mini; soft-restarted 1991/1987 Studio.  
6. ~~**Mini-Dev keep-warm mirror**~~ — **done:** prefetch 6 / TTL 72 / evict false; prewarm scripts + `com.streamtv.prewarm-youtube`; kickstart health 200.  
7. ~~**Pre-warm habit**~~ — **ops tooling (optional):** `scripts/kickstart_streamtv_with_prewarm.sh`, `scripts/install-prewarm-youtube-launchagent.sh` (daily 17:00); installed Studio+Mini. Not core playout — run installer or kickstart wrapper to enable.  
8. ~~**Phase 3**~~ — **PARKED** (owner 2026-11-25 ~19:23). No **3a–3f**. Re-open gate only if hang repeats on an **already READY** file, or new GVS-403 / Archive CDN matrix.

## Keep-warm ops (Studio, 2026-11-25) — tracked

| Item | Value / artifact | Status |
|------|------------------|--------|
| `prefetch_count` | **6** (was 4) | Applied `config.yaml` |
| `default_ttl_hours` | **72** (was 4) | Applied |
| `evict_after_play` | **false** | Applied |
| `evict_off_schedule` | **false** | Applied |
| Pre-warm script | `scripts/prewarm_youtube_cache.py` | Added; first run **8/8** Studio defaults (≥1 MiB); `9102` omitted (not in lineup) |
| Config backup | `config.yaml.bak.keepwarm.*` | On disk |
| Kickstart | `com.streamtv` after config | Done (~18:26); pid refreshed; `youtube_full_cache enabled` |
| Mini mirror | Same knobs on Mini-Dev | **Done** (~19:00); Mini-Dev tag applies to Mini tree only |
| Pre-warm habit | kickstart wrapper + daily 17:00 LA | **Installed** Studio+Mini (optional ops; not auto in `streamtv/`) |
| **3f** / Phase 3 | all frozen packages | **PARKED** (owner) — READY-file hang or new taxonomy storm to re-open |

**Operator:** prefer `bash scripts/kickstart_streamtv_with_prewarm.sh` after full kickstart; evening LA at 17:00 if installed. Do not soft-restart mid-`download_now`.

## Rule
Do not edit `streamtv/streaming/**`, `cache/**`, `ffmpeg/**`, etc. until a **named** `APPROVED: change <path>` after soak shows config/ops insufficient.
