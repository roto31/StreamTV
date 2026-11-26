# StreamTV Streaming Resilience — Full Scope of Work

**Document status:** Planning / engineering charter (no bedrock implementation authorized by this document alone)  
**Date:** 2026-11-25  
**Author:** Cursor agent (research from Studio production evidence + in-tree platform)  
**Owner / authority:** Chris / roto1231  
**Hosts:** Mac Studio = production; Mac Mini (`streamtv-macmini`) = platform development  

---

## 1. Executive summary

Production Live TV on the Mac Studio showed stop/start behavior on holiday kids channels (**1225** Vintage Kids Christmas, **1128** Vintage Kids Thanksgiving; “1228” in conversation maps to **1128**). Investigation concluded:

1. **Recent starter-pack / v1.4.7.5–1.4.7.6 work did not cause these issues.** Production `com.streamtv` has been running since **2026-11-24 20:52** from the Studio repo; streaming bedrock was not deployed for that release work.
2. **`com.streamtv.stalled-ffmpeg-heal` alone will not fully resolve the morning issues.** It only covers Lesson 41 (mid-stream Archive FFmpeg stall → keepalive-only).
3. Full resolution requires a **phased program**: ops baseline → Mini measurement → config experiments → optional frozen-path changes under explicit `APPROVED:` with Mini-first proof and mandatory rollback if streaming degrades.
4. Most building blocks already exist in the platform. Prefer **reuse and measurement** over a new streaming framework rewrite (which would violate the streaming bedrock freeze and raise park risk).
5. **Afternoon 1128 “Can't Reach Server” (post ~11:40 leave) is not the same as morning taxonomy A.** Guide advanced to **`macys_parade_2025`** (item **136**). That Archive asset fails CDN-first FFmpeg open/first-TS under production (see **F** / §2.5). Morning stability was **`macys_parade_2024`** (item **134**). Do not burn Phase 3 CDN-first work on this until the schedule asset is quarantined or proven in an MPEG-TS soak.

**If Phase 3 (frozen-path) changes cannot meet acceptance after two approved attempts: roll back all Phase 3 diffs, leave Phase 0 ops in place, and park the project** pending owner review.

---

## 2. Evidence taxonomy (problems to solve)

| ID | Symptom (Studio evidence) | Mechanism | Primary source |
|----|---------------------------|-----------|----------------|
| **A** | 1128: tune → ~8 KiB keepalive → cancel after **1 chunk** (~25 s) → retry OK | Plex abandons during **CDN-first + FFmpeg warmup** (~11–15 s to real MPEG-TS) | Logs 2026-11-25 10:01–10:02 (**item 134 / 2024**) |
| **B** | 1225: “start/stop” feel with **one** HDHR session; ~**0.94 Mbps** copy+`-re` vs 1128 ~**4 Mbps** transcode | Sparse / low-rate MPEG-TS; Plex buffers without new `/auto/v` reconnects | Soak samples + live FFmpeg |
| **C** | Overnight Magnum ch80: `FFmpeg stalled — no stdout for 90s` | Mid-stream Archive hang → keepalive wedge (Lesson **41**) | Log 01:28 / 02:17 |
| **D** | YouTube: `ENOSPC`, rename fail on TunarrRAM | `youtube_full_cache` on **2 GiB** RAM disk (Issues **40 / 48 / 52**) | Post-kickstart ERROR lines |
| **E** | YouTube GVS/403 / bad formats (fleet risk) | Client / PO-token policy drift | yt-dlp wiki + Issue **73** |
| **F** | 1128 afternoon: same 1-chunk / keepalive surface as **A**, but **no** recovery; Apple TV “Can't Reach Server” | **Fragile schedule asset** `macys_parade_2025` under CDN-first: FFmpeg `Invalid data` / “no data after extended wait” while HTTP 206 + ffprobe succeed | Logs 2026-11-25 ~13:55–14:03; probe 14:12 |

### 2.1 Morning timeline (Archive.org — both channels)

| Time (local) | Channel | What happened |
|--------------|---------|---------------|
| 10:01:37 | **1128** | Tune → keepalive 8 KiB → real MPEG-TS ~15 s later → **cancel after 1 chunk** |
| 10:02:12 | **1128** | Retune → **11 409 chunks** until leave |
| 10:04:46 | **1225** | Tune → video ~11 s → **15 067 chunks** (~6 min) then leave |
| 10:10:34 | **1128** | Rejoin → remained ESTABLISHED / stable |

Client: Plex at `192.0.2.1`. Production listener: PID on `:8410`, cwd = Studio repo (`com.streamtv`).

### 2.2 Live process contrast (same morning)

| Channel | FFmpeg path | Approx output | Notes |
|---------|-------------|---------------|-------|
| **1128** | Archive CDN, **libx264** remux/transcode | ~4 Mbps | Healthy for Plex Live TV once past warmup |
| **1225** | Archive CDN, **copy + `-re`** (KARE commercials) | ~0.94 Mbps | Playable in soak (h264/aac) but Plex-fragile |

### 2.3 YouTube vs Archive.org (same channels)

| | Archive (today’s 1128/1225 air) | YouTube (post-kickstart) |
|--|--------------------------------|---------------------------|
| Path | CDN-first → FFmpeg from `archive.org` | Prefetch / full-cache to TunarrRAM + yt-dlp |
| This morning HDHR | All sessions | **None** |
| Failure mode | Slow first real chunk; rare 90 s stall (ch 80 overnight) | `ENOSPC` / rename fail when 2 GiB RAM disk fills |
| DB mix | 1225 ≈ 47 archive / 28 YouTube; 1128 ≈ 50 archive / 38 YouTube | When guide hits YouTube items, TunarrRAM pressure dominates |

### 2.4 Studio env snapshot (investigation day)

| Setting / agent | Status |
|-----------------|--------|
| `STREAMTV_FFMPEG_STALL_SEC` | **90** (set) |
| `STREAMTV_CACHE_YOUTUBE_FULL_CACHE` | **true** |
| `com.streamtv.tunarr-ram-heal` | Plist present (interval job) |
| `com.streamtv.stalled-ffmpeg-heal` | **Not installed** |
| TunarrRAM | 2.0 GiB volume; headroom OK at check time (~99% free after purge pressure) |
| yt-dlp | 2026.11.23 meets floor 2026.08.19; clients `visionos` → `web_safari` → `web_embedded` |
| Video hold | Exists; **default OFF** (`STREAMTV_PLEX_VIDEO_HOLD_NATIVE` / `_YOUTUBE`) — Apple TV black/freeze risk if enabled blindly |

### 2.5 Afternoon 1128 split (2026-11-25) — taxonomy **F**, not pure **A**

| Window | Guide / air | Archive item | Outcome |
|--------|-------------|--------------|---------|
| ~10:02–11:44 | Item **134** | `macys_parade_2024` → `nbcs-macys-thanksgiving-day-parade-2024` / `20241128-082900-KGW-1.mpg.mp4` | Long healthy soaks (e.g. **11 409** then **437 873** chunks) until Apple TV exit ~11:40–11:44 |
| After leave | Wall-clock advances | Break / next parade | Idle / retune lands on later index |
| ~13:55+ | Item **136** | `macys_parade_2025` → `macys-2025` / `Macy's Thanksgiving Parade 2025.mp4` | Repeated **1-chunk** cancels; `Error opening input: Invalid data…`; `FFmpeg timeout - no data received after extended wait` (even when stream headers appear) |

**Asset facts (not a missing file):**

| Check | `macys-2025` result |
|-------|---------------------|
| Archive metadata / HEAD / range GET | Item present; HTTP **200/206**; ~1.98 GiB |
| `ffprobe` (Studio, 2026-11-25 ~14:12) | **OK** — h264 854×480 + aac; duration ~19893 s (~5.5 h); container bitrate ~**795 kbps** |
| Production CDN-first FFmpeg → MPEG-TS | **Unreliable** — open/first-TS failures above → keepalive-only → Plex abandon |

**Content source:** Channel **1128** is Archive.org (and some YouTube) via unified YAML `data/channels_1128_vintage_kids_thanksgiving.yaml` + `schedules/1128.yml` continuous playout — not OTA. Parade years are scheduled Archive download URLs (`data/urls_1128-…tsv`, `SOURCES_1128-…md`).

**Ops implication (YAML/data — not bedrock):** Quarantine or replace **`macys_parade_2025`** until an `/auto/v1128` soak yields ≫8192 sustained bytes on that URL (or swap to a known-good alternate). One-shot “air 2024” is temporary: while tuned, playout holds; when the item ends or the channel is idle, wall-clock / lag-heal advances again — **do not** loop force-air (that *would* feel like skip back/forth). Mis-attributing **F** as Phase **3a** CDN-first latency burns freeze budget.

---

## 3. What will *not* fully fix this alone

| Action | Covers | Does not cover |
|--------|--------|----------------|
| Install `com.streamtv.stalled-ffmpeg-heal` | **C** (Lesson 41 Archive 0% CPU wedge) | **A**, **B**, **D**, **E**, **F** |
| Kickstart / soft-deploy loops | Temporary wedge clear | Root causes above |
| Starter-pack / DMG release work | First-run samples | Continuous fleet playout |
| Blind `STREAMTV_PLEX_VIDEO_HOLD_NATIVE=1` | Maybe **A** | May regress Apple TV (Issue 62); does not fix **F** |
| Repeated force-air to 2024 | Temporary watchable picture | Wall-clock / idle catch-up returns to **2025**; thrash if looped |

---

## 4. Platform inventory (reuse first)

### 4.1 In-tree modules and ops

| Area | Existing pieces |
|------|-----------------|
| Stall | In-process abort (`STREAMTV_FFMPEG_STALL_SEC`); `scripts/heal_stalled_ffmpeg.py`; `scripts/install-stalled-ffmpeg-heal-launchagent.sh`; skill `heal-stalled-ffmpeg-keepalive`; docs `guides/FFMPEG_STALL_KEEPALIVE.md` |
| TunarrRAM | `scripts/heal_tunarr_ram.sh` / purge; `verify_tunarr_ram.sh`; install LaunchAgent scripts; docs `guides/TUNARRRAM_PLAYOUT_RECOVERY.md`; Issues 40 / 48 / 52 |
| Plex tune gap | `streamtv/tuners/video_hold.py`; wrap on `/auto/v` in `streamtv/main.py` (opt-in) |
| Keepalive / CDN-first | `mpegts_keepalive.py`; CDN-first skip in `cache/playback_buffer.py` |
| YouTube | TTL cache; `StreamURLExpiredError` re-resolve; clients in `ffmpeg/constants.py`; `check_core_dependency_freshness.py`; Issue 73 rules |
| Verify | Skills `verify-hdhomerun-streaming`, `diagnose-empty-channel`; `scripts/probe_hdhr_hang.py`; golden FFmpeg tests |
| Freeze | `docs/STREAMING_BEDROCK_FROZEN.md` — `streamtv/streaming/**`, `ffmpeg/**`, `cache/**`, `hdhomerun/**`, `scheduling/**`, `api/iptv.py` |

### 4.2 External documentation constraints

**yt-dlp**

- [PO Token Guide](https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide) — GVS/Player/Subs PO tokens; prefer a **PO Token provider plugin** over hand-extracted tokens (video-bound, short-lived).
- Prefer **updating yt-dlp** and using clients that still return working formats (project policy: `visionos` → `web_safari` → `web_embedded`; **never** put `android_vr` first).
- Client availability changes between releases; treat named clients as temporary, not permanent architecture.

**FFmpeg / Live TV practice**

- Copy-mode MPEG-TS for IPTV/Plex commonly needs **muxrate / CBR floor above content bitrate**; undersized mux → buffering / dropouts.
- `-reconnect` family helps transient CDN/HTTP drops (project already uses reconnect on many Archive inputs; do **not** add `-reconnect_at_eof` on YouTube/Archive VOD in ways that break continuous advance — see `streamtv-safety` rules).
- Plex Live TV is intolerant of long silence after tune (keepalive-only or slow first media).

---

## 5. Freeze, Mini-first, and rollback policy

### 5.1 Freeze

Any change that alters tune behavior, bytes on the wire, FFmpeg argv, playout index, guide alignment, or cache hit/miss is **bedrock**. Edits require an owner message in-session:

- `APPROVED: change <path> — <reason>`  
- or `APPROVED: unfreeze streaming bedrock for <task>`

Never regenerate golden snapshots to force a pass. Canonical tree only (`streamtv/`); run `python3 scripts/build_distributions.py` after approved canonical changes.

### 5.2 Mini-Dev first

| Role | Host | Rule |
|------|------|------|
| Production | Mac Studio | Hands-off for streaming experiments unless owner reports production issue or explicitly approves Studio change |
| Development | Mac Mini | All Phase 1–3 implementation and soak tests first |

Do not copy Mini experiments into Studio or push Mini trees to StreamTV-source.

### 5.3 Rollback (mandatory)

```
Mini implement → Mini soak (Archive + YouTube) → written report →
owner APPROVED: change <path> → Studio change window →
soak Studio one channel →
if any degradation: IMMEDIATE rollback + full incident report →
no re-land until owner accepts the report.
If two consecutive approved attempts fail acceptance → PARK project,
rollback all Phase 3 diffs, leave Phase 0 ops in place.
```

**Degradation includes:** rise in keepalive-only tunes, worse null%, ENOSPC storms, Apple TV black/freeze, golden test failures, GVS-403 storms.

---

## 6. Phased engineering plan

### Phase 0 — Ops baseline (Studio allowed; **no bedrock**)

**Goal:** Close known gaps with in-tree tooling before any code change.

1. Install `com.streamtv.stalled-ffmpeg-heal` (addresses **C**).
2. Confirm `com.streamtv.tunarr-ram-heal` fires; run `verify_tunarr_ram.sh`; document 2 GiB vs full-cache (addresses **D** pressure).
3. Operator runbook: soak `http://127.0.0.1:8410/auto/v{N}` ≥50 s; distinguish keepalive-only vs low-bitrate playable.
4. Capture pre-change baseline metrics (tune gap times, bitrate, ERROR classes for 24 h).
5. **Content ops (taxonomy F):** ~~quarantine~~ → **replaced 2026-11-25** `macys_parade_2025` with Archive `ch-11-11-27-2025-08-28-pm` (KNTV San Jose complete off-air; 15 s copy soak ~10 MiB). Prior `macys-2025` kept in notes only.

**Exit criteria:** Magnum-class stalls self-heal; TunarrRAM does not sit at ENOSPC overnight; no Studio `streamtv/` edits; **F** either soaked green or removed from air.

### Phase 1 — Measurement harness on Mini-Dev (**no Studio streaming edits**)

**Goal:** Prove which lever fixes **A/B** before touching freeze.

| Deliverable | Purpose |
|-------------|---------|
| `scripts/plex_tune_gap_report.py` (or equivalent) | Time: HDHR request → first 8 KiB → first ≫8 KiB → stable bitrate |
| Channel matrix | 1225/1128 Archive copy vs Archive transcode vs YouTube cached vs YouTube cold |
| Bitrate / null% probe | Flag copy paths ≲2 Mbps as “Plex-fragile” |
| Hold A/B (env only) | Mini only: `STREAMTV_PLEX_VIDEO_HOLD_NATIVE=1` on one Archive channel; Apple TV + Plex pass/fail |

**Exit criteria:** Written Mini report with numbers; no Studio kickstart for experiments.

### Phase 2 — Config / LaunchAgent experiments (Mini first)

**Goal:** Fix **A/B/D** without argv/bedrock if possible.

Priority order:

1. **SSD/HDD cache directory** for full-cache (ops) — best ROI for YouTube **D**. **Done on Mini-Dev (2026-11-25):** `cache.cache_directory` → `/Volumes/SSD Storage 2/Development_working_Drive/streamtv-cache`, `max_size_gb: 40`, healer `com.streamtv.ssd-cache-heal` (dir-size cap + free-floor; **not** TunarrRAM used%). TunarrRAM left mounted but unused for media cache.
2. Verify prefetch/heal thresholds for **large disks** — volume `%` healers are insufficient on SSD/HDD; require directory-size heal (above). In-process `volume_guard` still keys off volume `%` (bedrock; defer unless APPROVED).
3. **Video hold** only if Phase 1 shows Plex survive rate ↑ and **no** Apple TV black. Phase 1 Mini A/B: hold ON worse (KEEPALIVE_ONLY) — **do not** enable on Studio.
4. Content/ops: avoid sole reliance on long VHS commercial **copy** as air for kids channels when possible (YAML/data — not bedrock). Same bucket as taxonomy **F**: drop/replace Archive URLs that fail CDN-first MPEG-TS soak even when `ffprobe` is green (1128 `macys_parade_2025`).

**Phase 2b — Continual delivery (Mini, no re-work loop):**

| Agent | Interval | Role |
|-------|----------|------|
| `com.streamtv.ssd-cache-heal` | 120 s | Cap cache dir (40 GiB) / protect volume free (40 GiB) |
| `com.streamtv.mini-plex-ui-parity-tune` | 1800 s | Unattended **real** PMS Live TV tune: `POST /livetv/dvrs/{id}/channels/{N}/tune` + HLS consume (YouTube-primary); JSON under working-drive `results/` |
| (legacy) `mini-plex-unattended-tune` | — | Curl `/auto/v*` only — superseded; unload when UI-parity agent installed |

Optional flags on the UI-parity script: `--safari-ui` (open Plex Web), `--applescript-guide` (type channel in Safari Live TV; needs Accessibility).

**Studio gate:** Do **not** move Studio production cache off TunarrRAM until Mini Phase 2b shows **24 h green** (no ENOSPC; UI-parity YouTube soaks mostly OK; SSD cache under cap). Owner must explicitly ask for the Studio apply.

**Platform backlog (shipping installs):**

- First-run / setup **cache path picker**: default `~/Library/Application Support/StreamTV/cache`; user may choose any writable SSD/HDD path; advanced RAM-disk opt-in only.
- Persist to `cache.cache_directory` + install **dir-size healer** (never ship TunarrRAM-only without a directory-size cap).

**Rollback:** Revert plist/env + `cache_directory`; kickstart Mini; re-soak.

### Phase 2c — YouTube start/stop & prefetch deep dive (Mini first)

**Goal:** Resolve Plex **start/stop / stall** on YouTube by ensuring current + **next guide item** are on SSD (or past buffer floor) before tune/advance — so Plex sees continuous real media, not keepalive gaps.

**Canonical write-up:** `docs/plans/streaming-resilience-youtube-prefetch-deep-dive.md`

**Evidence folded in (2026-11-25):**

| Source | Finding |
|--------|---------|
| Phase 1 | YouTube **1986** t_real ~0.57 s when healthy; Archive **A** is the slow first-tune class |
| SSD cache | ~8–9 GiB growth; dir-size healer online — **D** capacity path open |
| PMS UI-parity soak | 4/6 tuned; only **1985** sustained HLS (~2.6 MiB); **1986/87/89** thin drop (~276 B); **1991/9102** tune fail |
| Platform | `youtube_full_cache` refuses CDN fallback → miss/late prefetch ⇒ Plex abort window |
| Ops | LaunchAgent script must live under Application Support (SSD path TCC-denied) |

**Work:** boundary + cache-ready probes; `prefetch_count` / lead-time A/B on Mini; harden UI-parity pass on **byte floor** (not tune-OK alone). Archive-into-SSD optional for mixed channels — **does not** fix CDN-first **A** unless play path uses cache.

**Exit → Studio:** same 24 h gate as 2b, plus YouTube session survival / boundary gap targets in the deep-dive doc.

### Phase 3 — Frozen-path engineering (**PARKED** — owner 2026-11-25 ~19:23)

**Parked.** Studio keep-warm + quarantine + manual soaks met ops acceptance; no named **3a–3f**. Re-open only with owner `APPROVED:` for a **named** package after **already READY** hang or new GVS-403 / Archive CDN matrix. See `streaming-resilience-phase3-gate-20261125.md`.

Touch only after Phase 2b/2c fail to meet acceptance **and** the park lift above is satisfied. **Each package is a separate approval.**

| Package | Likely paths | Intent | Required tests |
|---------|--------------|--------|----------------|
| **3a** Faster/safer first media for Archive CDN-first | `playback_buffer.py`, possibly `mpegts_streamer.py` | Shrink Plex abort window (**A**) without breaking keepalive contract | HDHR soak; keepalive size ≫8 KiB after first media |
| **3b** Copy-path MPEG-TS floor (CBR/null fill or gated remux) | `ffmpeg/constants.py` + streamer | Raise copy bitrate floor for Plex (**B**); never unconditional YouTube `-muxrate` (safety rule) | Golden tests must stay green or add **gated** golden; YouTube path unchanged |
| **3c** Stall healer edge cases | healer script (± streamer) | Keep overlay skip (Issue 44); don’t kill quiet DVD burns | heal dry-run suite |
| **3d** YouTube durability | `constants.py` clients/floor; optional PO-token **plugin** | Track yt-dlp; no hand-rolled format strings | `test_youtube_ydl_opts.py`, freshness script |
| **3e** Native hold policy | `video_hold` / `main.py` | Only if Mini proves safe | Apple TV + Plex matrix |
| **3f** YouTube prefetch / boundary policy | cache queue / playback_buffer (APPROVED paths only) | Stronger N+1 readiness so Plex doesn’t stall at item advance | Mini boundary gap + PMS session byte floor; goldens untouched unless required |

After any approved canonical `streamtv/` change: `python3 scripts/build_distributions.py`; update `CHANGELOG.md` `[Unreleased]`; run `post-playout-change-checklist` skill.

### Phase 4 — Park criteria

Park and roll back **all Phase 3** diffs if any of:

- Cannot get Plex first-tune success ≥95% on Mini Archive matrix without breaking Apple TV  
- Copy-path CBR/remux breaks goldens / YouTube copy rules or exceeds acceptable fleet CPU  
- YouTube remains ENOSPC-bound despite **SSD/HDD cache + dir-size healer** (ops park: capacity/policy, not more bedrock)  
- Studio soak worse than pre-change baseline on null% / keepalive-only rate  
- Two consecutive owner-approved attempts fail acceptance  

Phase 0 ops may remain.

---

## 7. Module map (build vs reuse)

| Need | Build new? | Notes |
|------|------------|-------|
| Stall watchdog | **Reuse** | Install LaunchAgent |
| TunarrRAM watchdog | **Reuse on RAM-only hosts** | Prefer SSD cache + `ssd-cache-heal` on Mini/platform |
| SSD media-cache healer | **Build** (Mini scripts) | Dir-size + free-floor; Phase 2 |
| Plex tune-gap telemetry | **Build** (scripts) | Phase 1 |
| Plex Live TV UI-parity tune | **Build** (Mini scripts) | PMS `/tune` + HLS; Phase 2b (add byte-floor pass) |
| Prefetch / boundary probes | **Build** (Mini scripts) | Phase 2c YouTube start/stop deep dive |
| Video hold | **Reuse** (env) | Experiment only; default stays off |
| YouTube prefetch policy | **Maybe** (frozen → **3f**) | Only if 2c config A/B fails |
| Archive copy bitrate floor | **Maybe** (frozen) | Phase 3b after evidence |
| CDN-first latency cut | **Maybe** (frozen) | Phase 3a |
| PO Token provider | **Maybe integrate** (plugin) | Only if visionos/HLS path dies |
| New streaming framework rewrite | **Do not build** | Contradicts freeze; high park risk |

---

## 8. Acceptance definition (“fully resolved”)

On Studio, for representative Archive + YouTube channels (including 1128 / 1225):

1. **A** — First Plex tune reaches real media (≫8 KiB) within budget without mandatory manual retune (measure on **known-good** Archive items, e.g. 1128 **2024**, not **F**).  
2. **B / C** — Sustained soak ≥5 min: h264/aac; no keepalive-only wedge.  
3. **D** — YouTube cold/warm: no ENOSPC in 24 h under normal prefetch.  
4. **E** — Dependency freshness gate green; no GVS-403 storm on floor clients.  
5. **F** — Fragile schedule keys quarantined or replaced; no production guide slot stuck on a CDN-first open/timeout loop.  
6. Rollback drill documented once on Mini.

---

## 9. Recommended immediate next steps

1. ~~Phase 0 Studio~~ / ~~Phase 1 Mini~~ / ~~Phase 2 item 1 SSD cache on Mini~~ — done; ~~**Phase 0 item 5 (F)**~~ — 1128 KNTV replace (owner Approved).  
2. ~~**Phase 2b UI-parity CD**~~ — **stopped/disabled 2026-11-25** (owner: manual tune better evidence than CD pid). Healers remain: `ssd-cache-heal` + `stalled-ffmpeg-heal`. **9101/9102 mapped.**  
3. ~~**Phase 2c YouTube measurement**~~ — **`prefetch_count: 4`** on Mini; boundary probe post-4: **5/6 HDHR ≤5 s**; manual soaks show cold→retune OK. Enough to treat YouTube SSD/prefetch direction as validated for Mini.  
4. ~~**Phase 0 / C**~~ — Mini `stalled-ffmpeg-heal` (AS/TCC-safe) + Studio agent verified.  
5. ~~**Archive A/1225 quarantine**~~ — **done 2026-11-25:** removed `marathon_80s_1` (6 hr pack) from `schedules/1225.yml` (+ notes in channel YAML/TSV); imported + soft-deployed Mini & Studio. Keep II/III.  
6. ~~**Studio SSD cache apply**~~ — **done 2026-11-25 (owner permission):** `cache_directory` → `/Volumes/SSD Storage/StreamTV-media-cache`, `max_size_gb: 40`, `prefetch_count: 4`, `com.streamtv.ssd-cache-heal` installed; kickstarted `com.streamtv`. Backup `config.yaml.bak.tunarrram.*`.  
7. ~~**Studio keep-warm (cold YouTube wait)**~~ — **done 2026-11-25 ~18:25:** `prefetch_count: 6`, `default_ttl_hours: 72`, `evict_after_play/off_schedule: false`, `scripts/prewarm_youtube_cache.py`; kickstart + pre-warm. Tracked in `streaming-resilience-phase3-gate-20261125.md` §Keep-warm and youtube deep-dive §7.2.  
8. ~~**Keep-warm re-soak (Studio)**~~ — **done ~18:44–18:56:** Archive/mixed instant; YT cold→READY OK; 1991 abort→keepalive wedge healed by soft-restart, next item clean. Gate updated.  
9. ~~**F-class quarantine + Mini keep-warm + prewarm habit**~~ — **done ~19:00:** dead YT ids vaulted; Mini-Dev knobs mirrored; optional `com.streamtv.prewarm-youtube` + kickstart wrapper (ops tooling, not core playout).  
10. ~~**Phase 3**~~ — **PARKED** (owner 2026-11-25 ~19:23). No **3a–3f**. Gate: `streaming-resilience-phase3-gate-20261125.md`.

---

## 10. Related references (in repo)

| Doc / artifact | Role |
|----------------|------|
| `docs/STREAMING_BEDROCK_FROZEN.md` | Freeze manifest |
| `docs/guides/FFMPEG_STALL_KEEPALIVE.md` | Lesson 41 |
| `docs/guides/TUNARRRAM_PLAYOUT_RECOVERY.md` | Issue 40/48 ops |
| `docs/plans/streaming-resilience-youtube-prefetch-deep-dive.md` | Phase 2c YouTube start/stop + prefetch |
| `docs/plans/streaming-resilience-plex-ui-parity.md` | PMS `/tune` automation |
| `data/channels_1128_vintage_kids_thanksgiving.yaml` | 1128 Archive/YouTube URLs (`macys_parade_2024` / `_2025`) |
| `data/SOURCES_1128-vintage-kids-thanksgiving.md` | Source research for Thanksgiving pack |
| `docs/guides/PLEX_LIVE_TV_RECOVERY.md` | Plex recovery (if present) |
| `LESSONS_LEARNED.md` | Issues 13, 30, 40, 41, 44, 48, 52, 62, 71–73 |
| `.cursor/rules/streaming-bedrock-frozen.mdc` | Agent freeze enforcement |
| `.cursor/rules/streamtv-safety.mdc` | FFmpeg / yt-dlp invariants |
| `.cursor/rules/mini-dev-isolation.mdc` | Studio vs Mini |
| `.cursor/skills/heal-stalled-ffmpeg-keepalive` | Stall heal skill |
| `.cursor/skills/verify-hdhomerun-streaming` | Tune verification |

---

## 11. Document control

| Field | Value |
|-------|-------|
| Title | StreamTV Streaming Resilience — Full Scope of Work |
| Formats | Markdown source; DOCX / PDF exports generated alongside |
| Source path | `docs/plans/streaming-resilience-scope.md` |
| Classification | Internal engineering plan |
| Implementation | Not authorized by document alone — requires owner `APPROVED:` for frozen paths |

---

*End of document.*
