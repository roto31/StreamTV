# Deep dive — YouTube start/stop & prefetch (Plex reliability)

**Date:** 2026-11-25  
**Host focus:** Mac Mini (Mini-Dev)  
**Parent plan:** `docs/plans/streaming-resilience-scope.md`  
**Goal:** Stop Plex Live TV **start/stop / stall** on YouTube-heavy channels by ensuring the **next** (and current) item is already on disk when playout needs it.

---

## 1. Problem statement (owner)

YouTube should play more reliably on Plex. Perceived **start/stop** (brief black / return-to-guide / rebuffer at item boundaries or cold tune) is worse when the next file is **not** ready. A stronger **prefetch** (guide-ahead partial or full download onto SSD) should keep real media flowing so Plex does not abandon the tune.

This is **distinct from** Archive taxonomy **A** (CDN-first warmup 10–29 s on 1128/1225), but mixed Archive↔YouTube channels share the same continuous playout loop — a cold YouTube boundary looks like start/stop too.

---

## 2. Evidence already in hand

### 2.1 Phase 1 HDHR matrix (hold OFF, TunarrRAM still in use)

| Channel | Source class | t_real | Note |
|---------|--------------|-------:|------|
| 1986 | YouTube music | **0.57 s** | Fast when path healthy |
| 1225 | Archive | **29.2 s** | SLOW_FIRST_MEDIA (**A**) |
| 1128 | Archive | **9.8 s** | Still Plex-fragile |

Implication: first-tune latency is not YouTube’s main failure mode when cache/path is warm; **durability + boundary readiness** are.

### 2.2 Phase 2 SSD cache (Mini)

| Item | Result |
|------|--------|
| `cache.cache_directory` | `/Volumes/SSD Storage 2/…/streamtv-cache` |
| `max_size_gb` | 40 + `com.streamtv.ssd-cache-heal` (dir-size / free-floor) |
| Cache growth | ~**8–9 GiB** after YouTube full-cache activity |
| TunarrRAM | Still mounted; **no longer** live media target |

Implication: capacity (**D**) path is open; disk is no longer the 2 GiB RAM cliff.

### 2.3 PMS UI-parity YouTube soak (2026-11-25 ~13:48 UTC)

`results/plex_ui_parity_youtube_now.json` — real `POST /livetv/dvrs/…/tune` + HLS consume:

| Channel | Tune | Sustained HLS | Note |
|---------|------|---------------|------|
| **1985** | OK (~2.0 s) | ~2.6 MiB / session alive | Best |
| **1986** | OK (~1.1 s) | ~276 B then drop | Client disconnect / thin consume |
| **1987** | OK (~2.5 s) | ~278 B then drop | Same |
| **1989** | OK (~3.1 s) | ~272 B then drop | Same |
| **1991** | **FAIL** (~25 s) | — | Tune did not establish |
| **9102** | **FAIL** (~0 s) | — | Immediate fail |

Ops note: LaunchAgent must run the script from **Application Support** (or Server Clone); external SSD script path hit macOS **TCC Operation not permitted**.

Implication: “tuned” ≠ “Plex-stable stream.” Thin/dropped sessions match **start/stop** symptoms (session dies or never builds bitrate). Failures on 1991/9102 need separate classification (guide mapping, download not READY, GVS, empty lineup).

### 2.4 Platform behavior (why prefetch matters)

| Behavior | Effect on Plex |
|----------|----------------|
| `youtube_full_cache: true` | Must play **local** file; **no** googlevideo CDN fallback while waiting |
| Cache miss / download in flight | `CacheNotReadyError` / wait path → keepalive-only window → Plex abort |
| `prefetch_count` + download queue | Can fill **next** items into SSD **if** scheduled early enough |
| `stream_buffer_mb` / partial `.part` | Can start before full download **if** buffer policy allows |
| Item advance (continuous playout) | New FFmpeg input; if next YouTube file not READY → boundary stall |
| Archive CDN-first vs YouTube local | Path flip at boundary amplifies stop/start on mixed channels |

SSD helps only when the bytes are **already there** (or past buffer floor) at the moment of tune/advance.

---

## 3. Hypotheses (ordered)

| ID | Hypothesis | If true, fix shape |
|----|------------|-------------------|
| **H1** | Start/stop is mostly **next-item not READY** at boundary (prefetch too shallow / too late) | Ops: raise `prefetch_count`, earlier enqueue, longer pre-boundary lead time |
| **H2** | Cold tune waits on yt-dlp while Plex sees keepalive | Ops/config: prioritize on-air + N+1 download; optional longer YouTube hold only if Mini-proven |
| **H3** | Session drops after tune because bitrate/path wedges (stall **C**-like or thin MPEG-TS) | Measure null%/bitrate; stalled-ffmpeg healer; not more disk alone |
| **H4** | 1991/9102 fail at PMS `/tune` (mapping / no grabber media) | Lineup/DVR/channel enablement — not prefetch |
| **H5** | Mixed Archive→YouTube boundary is worse than YouTube→YouTube | Prefetch **both** sources into SSD; Archive play-from-cache is separate (closer to 3a) |

---

## 4. Phase 2c — Prefetch deep dive (Mini first, **no bedrock** until proven)

**Objective:** Make YouTube (and mixed) channels **boundary-safe** for Plex by ensuring N and N+1 are cached (or buffered past floor) before advance/tune.

### 4.1 Measurement (build if missing)

| Probe | What to record |
|-------|----------------|
| Boundary gap | Wall time from end of item N → first ≫8 KiB of item N+1 on `/auto/v*` **and** PMS `/tune` |
| Cache readiness | READY / `.part` size / `estimate_buffered_seconds` for N and N+1 at T−60 s, T−10 s, T0 |
| Plex session | `/livetv/sessions` lifetime; HLS bytes over 60–90 s (avoid “tune OK / 276 B” false green) |
| Source class | YouTube vs Archive for N and N+1 |

Artifact dir: `…/streamtv-resilience/results/prefetch_boundary/`

### 4.2 Config experiments (Mini only; rollback plist/yaml)

1. Baseline: current `prefetch_count`, `youtube_full_cache`, SSD cache.  
2. **Aggressive prefetch:** increase `prefetch_count` (e.g. 2→4) on music channels; confirm DownloadQueue logs enqueue of N+1…N+k.  
3. **Lead time:** verify scheduler/reconcile runs often enough that a 3–5 min music video is fully (or buffer-floor) downloaded before air.  
4. **Partial play:** confirm `stream_buffer_mb` / wait policy actually allows `.part` playout for YouTube without falling into CacheNotReady long enough for Plex to quit.  
5. **Archive optional:** allow Archive into same SSD tree via existing download strategy — **does not** fix CDN-first air unless play path uses cache (document; don’t pretend disk alone fixes **A**).

### 4.3 Success criteria (YouTube reliability)

On Mini YouTube-primary set (1985–1987, 1989, 1991, 9102) over ≥24 h Phase 2b + 2c soaks:

- PMS `/tune` success ≥ **95%**  
- Sustained HLS/session ≥ **60 s** with bytes ≫ keepalive (not &lt;1 KiB drop)  
- Boundary gap median under Plex-safe budget (target provisional: **&lt;5 s** to real media on advance; tighten after data)  
- No ENOSPC; cache dir under 40 GiB healer  

### 4.4 When to unpark bedrock

Only if 4.2 config cannot meet 4.3:

| Package | Intent | Gate |
|---------|--------|------|
| **3f** (new) YouTube prefetch / boundary policy | Stronger pre-boundary wait, prioritize N+1, or safer partial-play rules in cache/playout | Mini numbers + `APPROVED: change &lt;path&gt;` |
| **3a** | Archive CDN-first first-media | Separate; don’t conflate with YouTube prefetch |
| **3d** | GVS-403 / clients | Only if logs show 403 storms |

Phase 3 remains **PARKED** until continuous soaks + this deep dive say otherwise.

---

## 5. Continual delivery hooks

| Agent / artifact | Role |
|------------------|------|
| `com.streamtv.ssd-cache-heal` | Keep SSD cache from filling the volume |
| `com.streamtv.mini-plex-ui-parity-tune` | Every 30 min PMS `/tune` YouTube-primary; require **byte floor** in pass criteria (update script if needed) |
| Prefetch boundary report (2c) | Run around known music-channel boundaries; JSON + one-page summary |

---

## 6. Out of scope / do not

- Streaming framework rewrite  
- Enabling `STREAMTV_PLEX_VIDEO_HOLD_NATIVE` without new Mini proof (Phase 1 hold-on was worse)  
- Studio cache move before Mini 24 h green  
- Regenerating FFmpeg goldens / editing frozen paths without `APPROVED:`  

---

## 7. Next actions

1. ~~Harden UI-parity **pass** rule~~ — done Mini-Dev 2026-11-25: `--min-bytes` default **1 000 000**; thin ~278 B sessions no longer `ok`; LaunchAgent updated; history dir `results/plex_ui_parity_history/`.  
2. ~~Add Mini **boundary + cache-ready** probe~~ — done: `streamtv-resilience/scripts/prefetch_boundary_probe.py`; baselines in `results/prefetch_boundary/`. Cold t_real **5–20 s**, warm **&lt;1 s**.  
3. ~~Run prefetch_count A/B on Mini~~ — now **`prefetch_count: 4`** (from 0→3→4); post-4 HDHR **5/6 ≤5 s**. Compare 24 h UI-parity sustained vs pre-change.  
4. ~~**H4 / 9102**~~ — mapped via Plex guide dropdown; restored to YouTube-primary.  
5. ~~**Archive A/1225**~~ — `marathon_80s_1` quarantined from schedule (Studio+Mini); not a 2c/3f issue.  
6. ~~**Studio SSD + prefetch**~~ — applied 2026-11-25 (owner permission): Studio `StreamTV-media-cache` + `prefetch_count: 4` + ssd-cache-heal.  
7. ~~**Keep-warm ops (Studio)**~~ — applied 2026-11-25 ~18:25 (owner: complete remaining cold-YouTube ops):
   - `prefetch_count: **6**` (4→6)
   - `default_ttl_hours: **72**` (4→72)
   - `evict_after_play: **false**`, `evict_off_schedule: **false**`
   - Pre-warm: `scripts/prewarm_youtube_cache.py` (sequential `/auto/v*`, ≥55 s, 1 MiB floor)
   - Backup: `config.yaml.bak.keepwarm.*`; kickstart `com.streamtv` done ~18:26
   - First pre-warm: **8/8** defaults passed (1984–1989, 1991, 1994); `9102` not on Studio lineup
8. ~~**Keep-warm re-soak**~~ — Studio Plex ~18:44–18:56: Archive/mixed OK; 1986/1987 cold→READY; 1991 Plex-abort→keepalive wedge (soft-restart), next item played.  
9. ~~**F-class quarantine + Mini keep-warm + prewarm habit**~~ — done ~19:00 (gate §Remaining).  
10. ~~**Phase 3 / 3f**~~ — **PARKED** (owner 2026-11-25 ~19:23). Draft **3f** only if hang repeats on already-READY files after park lift.

### 7.1 Status note (2026-11-25 ~23:58Z)

- Mini: UI-parity CD disabled; healers + `prefetch_count: 4` remain (mirror keep-warm when Mini-Dev next touched).  
- Studio: SSD cache path live; YouTube/Archive cache dirs created under `/Volumes/SSD Storage/StreamTV-media-cache`.  
- Phase **3** frozen packages still **parked** pending named soak justification.

### 7.2 Keep-warm tracking (2026-11-25 ~18:25 local)

| Lever | Before | After | Notes |
|-------|--------|-------|-------|
| `prefetch_count` | 4 | **6** | Deeper N+k under yt concurrency=1 |
| `default_ttl_hours` | 4 | **72** | Music VOD stick on 40 GiB SSD |
| `evict_after_play` | true | **false** | Retain last-played READY |
| `evict_off_schedule` | true | **false** | Retain off-window READY |
| Pre-warm | none | `scripts/prewarm_youtube_cache.py` | Run post-kickstart / pre-Plex |
| `stream_buffer_mb` | 32 | 32 (unchanged) | Optional later A/B |
| volume_guard concurrency | 1 | 1 | Raising = **3f** / frozen `cache/` |

---

*Mini-Dev evidence doc. Complements Phase 0/1 reports and `streaming-resilience-plex-ui-parity.md`.*
