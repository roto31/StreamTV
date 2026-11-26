# Streaming Resilience — Phase 1 Mini-Dev Report

**Date:** 2026-11-25  
**Host:** Mac Mini (`streamtv-macmini` / 192.0.2.1)  
**Working directory:** `/Volumes/SSD Storage 2/Development_working_Drive/streamtv-resilience/`  
**Tree:** `/Volumes/Server Clone/Users/chris/StreamTV` (Mini-Dev; not pushed to StreamTV-source)  
**Charter:** Studio `docs/plans/streaming-resilience-scope.md`  
**Phase 0:** Studio `docs/plans/streaming-resilience-phase0-results.md`

---

## 1. Working drive

Owner provided space on Mini at:

`/Volumes/SSD Storage 2/Development_working_Drive` (~238 GiB free)

Layout used:

| Path | Role |
|------|------|
| `…/streamtv-resilience/scripts/plex_tune_gap_report.py` | Measurement harness |
| `…/streamtv-resilience/results/` | JSON matrices + plist backup |
| `…/streamtv-resilience/reports/` | This report |
| Mini also has a copy at `…/StreamTV/scripts/plex_tune_gap_report.py` | Convenience only |

---

## 2. Measurement harness

`plex_tune_gap_report.py` polls `/auto/v{N}` via **curl** while sampling on-disk byte growth:

- time to first byte  
- time to ≥8 KiB (keepalive)  
- time to ≥50 KiB (real media floor)  
- sustained bitrate after real media  
- keepalive-only flag  

---

## 3. Matrix results (hold OFF, default Mini env)

Source: `results/tune_gap_matrix.json` (after soft-restart attempt; soak 35 s).

| Channel | Role | ok | Bytes | t_first | t_real | Note | Air hint (Mini log) |
|---------|------|----|------:|--------:|-------:|------|---------------------|
| **1225** | Archive kids (Christmas) | yes | 237 568 | 0.18 s | **29.2 s** | **SLOW_FIRST_MEDIA** | `80s Christmas Specials…` Archive |
| **1128** | Archive kids (Thanksgiving) | yes | 876 544 | 0.18 s | **9.8 s** | LOW_BITRATE | Macy’s parade Archive |
| **80** | Archive series (Magnum) | yes | 4 485 036 | 0.41 s | 0.41 s | LOW_BITRATE* | Magnum S07E04 Archive |
| **1986** | YouTube music | yes | 2 688 508 | 0.06 s | 0.57 s | LOW_BITRATE* | Whitesnake — YouTube |

\*Bitrate estimator is conservative on short post-warmup windows; Studio soak earlier showed ~4 Mbps for healthy Archive remux (1128). Primary signal for Phase 1 is **t_real**, not absolute Mbps.

### Earlier failed urllib runs

Before curl-based rewrite, 1225/1128 often returned `TimeoutError` / `NO_BYTES` while Magnum/YouTube succeeded — consistent with long silent warmup (taxonomy **A**).

---

## 4. Hold A/B (Archive 1225 only)

| Condition | `STREAMTV_PLEX_VIDEO_HOLD_NATIVE` | 1225 result |
|-----------|-----------------------------------|-------------|
| **A (off)** | `0` (default) | ok; **29.2 s** to real media; 237 KB in 35 s |
| **B (on)** | `1` then kickstart | **KEEPALIVE_ONLY** (8192 B) for 40 s soak |

**Revert:** Hold set back to `0`; `com.streamtv` kickstarted; health 200; confirmed `HOLD_NATIVE=0`.

**Apple TV / Plex GUI:** Not exercised on Mini this run (no operator client session). HDHR instrumented soak only.

**Conclusion:** Enabling native video hold on Mini **did not** improve 1225 first-media time in this trial; soak stayed keepalive-only (cold start after kickstart may also have contributed). Do **not** enable hold on Studio based on this A/B.

---

## 5. Mapping to taxonomy

| ID | Mini evidence | Implication |
|----|---------------|-------------|
| **A** | 1225 t_real ≈ **29 s**; 1128 ≈ **10 s** | Plex abort window explained; Phase 2/3a candidates |
| **B** | Low post-warmup bytes on kids channels vs Magnum | Still relevant; needs longer soaks / ffprobe in Phase 2 |
| **C** | Studio Phase 0 healer installed; Mini not the stall host today | Keep healer on Studio |
| **D** | YouTube **1986** tuned quickly (0.57 s real) while TunarrRAM not full | ENOSPC is capacity/ops; not reproduced this run |
| **E** | No GVS-403 in this matrix | Continue freshness checks; no bedrock client change now |

---

## 6. Recommendation (Phase 2 vs Phase 3)

**Do Phase 2 ops next (no bedrock):**

1. Studio/Mini: treat **2 GiB TunarrRAM** as insufficient for sustained `youtube_full_cache` — enlarge RAM disk or move cache to SSD (best ROI for **D**).  
2. Keep `stalled-ffmpeg-heal` + `tunarr-ram-heal` on Studio.  
3. Do **not** ship `STREAMTV_PLEX_VIDEO_HOLD_NATIVE=1` without a better Mini trial (longer settle after kickstart + real Plex/Apple TV).  
4. Content ops: avoid relying on multi-hour Archive specials as sole kids air when CDN+transcode warmup exceeds ~10–15 s.

**Defer Phase 3 bedrock** until owner explicitly approves a named package after reviewing this report:

- **3a** only if Phase 2 cannot shrink first-media time on Archive CDN-first (1225-class).  
- **3b** copy-path bitrate floor only with golden-gated Mini proof.  
- No streaming framework rewrite.

---

## 7. Artifacts on Mini working drive

```
/Volumes/SSD Storage 2/Development_working_Drive/streamtv-resilience/
  scripts/plex_tune_gap_report.py
  results/tune_gap_matrix.json
  results/tune_gap_hold_off.json
  results/tune_gap_hold_on_1225.json
  results/com.streamtv.plist.bak
  reports/streaming-resilience-phase1-mini-report.md
```

---

*End Phase 1 Mini-Dev report. No frozen paths modified. No push to StreamTV-source.*
