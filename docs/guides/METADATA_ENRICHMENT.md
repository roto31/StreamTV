# Metadata Enrichment System

Guide to enriching StreamTV media with TVDB, TVMaze, TMDB, and cited historical sidecars for **richer Plex Live TV guide rows** (XMLTV).

---

## Important limits

| What enrichment does | What it does **not** do |
|----------------------|-------------------------|
| Better `title` / `sub-title` / `desc` / `icon` / `category` / `episode-num` in `/iptv/xmltv.xml` | Run Plex TVDB/TMDB **Match agents** on Live TV |
| Store provider plots/posters/cast on `MediaItem.meta_data` | Emit cast in XMLTV `<credits>` (needs APPROVED `iptv.py` change) |
| Survive Archive.org scrape under `meta_data.archive` | Link Live TV airings to library watched/resume |
| Playback-safe `meta_data` writes | Change `duration`, playout indices, schedules, or URLs |

Plex Live TV is HDHomeRun + XMLTV only. For library-matched UX, use Tunarr library channels — see [STREAMTV_TUNARR_HYBRID.md](STREAMTV_TUNARR_HYBRID.md).

**Gracenote/TMS:** not integrated. Use for manual conflict confirmation only.

---

## Playback-safe defaults

Mass runs must:

- Use `--meta-only` (default **true**) — never writes `MediaItem.duration`
- Never run `reset_channel_playout.py` or `launchctl kickstart` as part of enrichment
- Verify with `scripts/verify_enrichment_playback.py --duration-index backups/enrichment/.../duration_index.json`
- Refresh Plex with `bash scripts/reload_plex_streamtv_guide.sh` only

Optional `--update-columns` copies description/thumbnail onto columns (still never duration). `--no-meta-only` also rewrites titles (avoid for mass runs).

---

## Data contract (`MediaItem.meta_data`)

```json
{
  "archive": { "identifier": "...", "url": "...", "...": "Archive.org scrape" },
  "enrichment": {
    "source": "tvmaze|tvdb|tmdb|historical|archive",
    "sources_consulted": ["tvdb", "tvmaze"],
    "title": "Episode or movie title",
    "description": "Plot summary",
    "description_completeness": 240,
    "season": 5,
    "episode": 19,
    "thumbnail": "https://...",
    "genres": ["Drama", "Action"],
    "rating": 8.8,
    "series_name": "Magnum P.I.",
    "air_date": "1985-09-26",
    "cast": [{"name": "...", "role": "actor|director"}],
    "unverified": false,
    "conflicts": [],
    "citations": [{"type": "url|archive|book", "ref": "...", "accessed": "YYYY-MM-DD"}]
  }
}
```

Helpers: `streamtv/utils/media_meta.py` (`parse_meta_data`, `get_enrichment`, `merge_enrichment`, `prefer_longest_description`, `append_conflict_log`).

**Conflict rule:** when two sources disagree on plot/title, keep the **longest description**, set `unverified: true`, append to `conflicts[]`, and log `data/enrichment/conflicts/YYYY-MM-DD.jsonl`.

XMLTV (`streamtv/api/iptv.py`) prefers `enrichment.*` for description, icon, genres, episode numbers, and optional `star-rating`. Cast is stored in meta_data only until bedrock unlock — see [`data/enrichment/reports/CAST_DEFER.md`](../../data/enrichment/reports/CAST_DEFER.md).

---

## Providers

1. **TVDB** — primary for TV series (API key / read token)
2. **TVMaze** — consulted with TVDB; longest description wins
3. **TMDB** — movies (`--type movie`); credits → `cast`
4. **Historical sidecars** — Olympics / non-API (`scripts/enrich_historical.py`)
5. **Archive fallback** — music / unresolved (`scripts/enrich_archive_fallback.py`, always `unverified`)

---

## Configuration

```yaml
metadata:
  enabled: true
  auto_enrich: false   # keep false until import hooks call merge_enrichment
  tvdb_api_key: null   # or STREAMTV_METADATA_TVDB_API_KEY
  tvdb_read_token: null
  tmdb_api_key: null   # or STREAMTV_METADATA_TMDB_API_KEY
  enable_tvdb: true
  enable_tvmaze: true
  enable_tmdb: true
  cache_duration: 86400
```

---

## Usage

```bash
# Series — prefer schedule media (same set playout uses)
./venv/bin/python scripts/enrich_metadata.py 80 "Magnum P.I." --year 1980 --from-schedule --meta-only --dry-run
./venv/bin/python scripts/enrich_metadata.py 80 "Magnum P.I." --year 1980 --from-schedule --meta-only --update-columns

# Movies
./venv/bin/python scripts/enrich_metadata.py 1980.1 "1980s Movies" --type movie --from-schedule --meta-only --update-columns

# Olympics / historical (cited sidecars)
./venv/bin/python scripts/enrich_historical.py export --channel 1980
# Edit data/enrichment/olympics/1980/entries.json citations, then:
./venv/bin/python scripts/enrich_historical.py apply --file data/enrichment/olympics/1980/entries.json --update-description

# Music / unresolved archive fallback (do NOT --force over good API data)
./venv/bin/python scripts/enrich_archive_fallback.py 1986 1987 --genres Music

# Force re-fetch
./venv/bin/python scripts/enrich_metadata.py 80 "Magnum P.I." --year 1980 --from-schedule --force --meta-only

# Sampled guide accuracy audit (20% stratified by channel)
./venv/bin/python scripts/audit_guide_metadata_sample.py --fraction 0.20 --seed 20260717
# → data/enrichment/reports/GUIDE_ACCURACY_AUDIT_LATEST.md

# Sesame Street / Mister Rogers → SxxExx titles (DB; needs TVDB key in env)
export STREAMTV_METADATA_TVDB_API_KEY='…'   # do not commit
./venv/bin/python scripts/streamtv_sxxexx_retitle_db.py --channel 123 --apply
./venv/bin/python scripts/streamtv_sxxexx_retitle_db.py --channel 143 --apply
./venv/bin/python scripts/enrich_metadata.py 123 "Sesame Street" --year 1969 --from-schedule --meta-only --update-columns
./venv/bin/python scripts/enrich_metadata.py 143 "Mister Rogers' Neighborhood" --year 1968 --from-schedule --meta-only --update-columns
```

After enrichment:

```bash
./venv/bin/python scripts/verify_enrichment_playback.py \
  --baseline /tmp/enrich-playback-baseline.json \
  --duration-index backups/enrichment/<pre>/duration_index.json
bash scripts/reload_plex_streamtv_guide.sh
```

Retune the channel in Plex (Custom Streaming) so the client picks up new guide cards.

---

## Channel waves (operator order)

| Wave | Channels | Method |
|------|----------|--------|
| B Movies | 1970, 1980.1, 1990, 2000, 2010, 1929 | TMDB `--type movie` |
| A Series | 80, 1984.1, 143, 1954, 11, 1982, 123 | TVDB/TVMaze `--from-schedule` |
| C Olympics | 1980, 1984, 1988, 1992, 1994, 1998 | Historical sidecars |
| D Music / gaps | 1985–1987, 1991, leftovers | Archive fallback (`unverified`) |

See `data/enrichment/olympics/CATALOG_HOLES.md` for missing day collections and Summer Olympics (no channels).

---

## Fallback chain (series)

```
Try TVDB + TVMaze (longest description; conflict → unverified)
    ↓
Archive description fallback (unverified + citations)
    ↓
Conflict JSONL for manual / Gracenote review
```

---

## Operator notes

- Enrichment is **opt-in** (`auto_enrich: false`). Re-imports that overwrite `meta_data` wholesale will wipe `enrichment` unless they use `merge_enrichment`.
- **Never** run `enrich_archive_fallback.py --force` on channels that already have TVDB/TMDB enrichment — it overwrites API plots.
- Archive.org URLs must be percent-decoded before parsing `1x01` season markers.
- ytimg / `.webp` programme icons are still omitted in XMLTV; TVMaze/TMDB JPEG/PNG posters are emitted.
- Movie matching uses title/year scoring; prefer archive `episode_title` + year from filename.
- TVDB genres often filled from TVMaze series record.
- Phase 0 backups live under `backups/enrichment/pre-*`.

---

## Verification

```bash
curl -s "http://127.0.0.1:8410/iptv/xmltv.xml" -o /tmp/epg.xml
# Channel ids are bare numbers (e.g. 80, 1970) — not streamtv.80
python3 - <<'PY'
import xml.etree.ElementTree as ET
root = ET.parse("/tmp/epg.xml").getroot()
for ch in ("80", "1970", "1980"):
    for prog in root.findall("programme"):
        if prog.get("channel") != ch:
            continue
        print(ch, prog.findtext("title"), prog.findtext("sub-title"))
        print("  desc", (prog.findtext("desc") or "")[:80])
        print("  icon", prog.find("icon") is not None)
        print("  cats", [c.text for c in prog.findall("category")])
        break
PY
bash scripts/verify_plex_token.sh
```
