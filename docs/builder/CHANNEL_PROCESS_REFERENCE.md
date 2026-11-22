---
title: "StreamTV Vintage Channels — How the Channels Were Built: Executive Summary and Reproduction Reference"
subtitle: "New channels 1225, 101, 214, 401, 704, 1031, 1128 and 1224, with channel 2011 as the edge case for editing an existing channel"
date: "November 22, 2026"
---

# How to read this document {.unnumbered}

**Purpose.** This document records how the vintage channels in this conversation were built. It covers every query, search method, parsing method, rule, decision, failure and limitation that can still be seen. Use it to repeat the process, or as the design input for the Channel Creator MCP (Section 14).

**What it covers.** Eight **new** channels:

- 1225 Vintage Kids Christmas;
- six holiday channels: 101 New Year's, 214 Valentine's Day, 401 Easter, 704 Fourth of July, 1031 Halloween and 1128 Thanksgiving;
- 1224 Vintage Prime Time Christmas.

They share one method, and Sections 4–8 describe it. The ninth build, channel 2011, **added to an existing channel** rather than creating one. It is the edge case in Section 9, which shows that editing an existing channel is possible and what extra work it takes.

**Citation key.** Every factual claim carries a source tag:

| Tag | Meaning | Example |
|---|---|---|
| **[F pkg/file Lnn]** | A delivered package file. Package names: `1225` (vintage-kids-xmas-1225.zip), `hol` (vintage-holiday-channels.zip), `1224` (the standalone prime-time build in `primetime/out`), `2011` (prime-time-xmas-2011.zip) | [F hol/README.md L16–17] |
| **[T#]** | A conversation turn, read back from this chat's history (Appendix A.1) | [T7] |
| **[E##]** | An entry in the detailed channel-2011 log (Appendix A.2) | [E25] |
| **[K path Lnn]** | A script or data file in the reproduction kit (Section 13) | [K primetime/build_prime.py L58–75] |
| **[R path Lnn]** | StreamTV source (public `roto31/StreamTV` at `d691270` = private `roto31/StreamTV-source` at `353d02e` for every cited file) | [R streamtv/importers/stream_id_registry.py L19–21] |
| **[A]** | My own assessment or inference, **not** a recorded fact | [A] |

**What is and is not observable.**

- **Read back, with exact text:** the conversation history for all 36 turns. It records each tool call (the exact query code) and every message, but **not the raw results** of those calls.
- **Truncated turns:** turns 1 (1225 research) and 7 (holiday research) are cut off in the history, so any calls after the cut-off are **not observable in this conversation**.
- **Results survive only as files:** `yt1.txt` holds the 1225 YouTube search results; `xmas/archive_files.json`, `xmas/yt_len.json`, `holidays/archive.json` and `holidays/yt.json` hold the verified files, runtimes and uploaders; `prime_data.py` and `holidays_data.py` hold the final picks with their evidence notes.
- **No hidden steps:** where a fact rests only on a summary, it says so.

**Corrections to the request brief.** The brief asked for this document. The files contradict it in these places:

| Brief says | Files show | Evidence |
|---|---|---|
| Channel 2011's original configuration has 17 Archive.org streams | **18** streams, all archive.org, with **16** unique ids; one id appears three times | [F 2011/base/channels_generated_2011.original.yaml L17, L24, L31] |
| 2011's `urls.tsv` has 70 records (35 events, 35 commercials) | **71** records: **40** events, **31** commercials; **18** archive.org and **53** YouTube URLs | [F 2011/urls.tsv] |
| No repository was referenced | The public `https://github.com/roto31/StreamTV` and the private `https://github.com/roto31/StreamTV-source` were given and cloned. Both were consulted | [T2]–[T4] |
| The work is about channel 2011 | 2011 was the last of nine builds. The other eight created new channels, and they are the main subject here at the user's request | [T0], [T6], [T8], [T13], [T15] |

One more correction concerns the 1225 delivery message, which said "49 programs … 48 come from archive.org and 6 from YouTube" [T5]. The channel file shows 49 programs, **43** from archive.org and **6** from YouTube. The "48 archive.org files" in that message count the 43 programs plus 5 archive.org break reels [K fixtures/candidates_1225.json]; [A].

# Executive summary

- **What was built.** Eight new StreamTV channels of off-air vintage TV recordings from archive.org and YouTube. Each plays in air-date order, with a real commercial-break reel between programs. The reels are WCCO 4 / KSTP 5 / KARE 11 Minnesota reels where they exist, otherwise network reels.

  | Channel | Name | Programs | Tier 1 | Break items | Long reels at end | One loop | Archive / YouTube streams |
  |---|---|---|---|---|---|---|---|
  | 1225 | Vintage Kids Christmas | 49 (3 marathon tapes) | 29 | 27 reels | 4 | 53.7 h | 48 / 28 |
  | 101 | Vintage New Year's | 9 | 2 | 16 reels | 2 | 18.8 h | 12 / 13 |
  | 214 | Vintage Kids Valentine's Day | 3 | 1 | 10 reels | 1 | 3.7 h | 3 / 10 |
  | 401 | Vintage Kids Easter | 13 | 2 | 6 reels | 0 | 14.6 h | 12 / 7 |
  | 704 | Vintage Fourth of July | 5 | 2 | 12 reels | 2 | 13.6 h | 6 / 11 |
  | 1031 | Vintage Kids Halloween | 13 | 9 | 15 reels | 1 | 12.3 h | 16 / 12 |
  | 1128 | Vintage Kids Thanksgiving | 70 (57 Macy's) | 18 | 18 reels | 6 | 158.6 h | 52 / 36 |
  | 1224 | Vintage Prime Time Christmas | 31 | 13 | 24 reels + 7 station IDs | 3 | 36.7 h | 10 / 52 |

  Counts are from the channel files, via [K fixtures/candidates_*.json]. Loop hours are the sum of item runtimes [K ref_plan.py]; [F hol/README.md L7–14].
- **One method.** Every build ran the same pipeline (Section 4):
  1. Search archive.org with `advancedsearch.php` and YouTube with its search page, from JavaScript in the browser.
  2. Check each candidate's file, runtime and uploader.
  3. Label the evidence that commercials are included.
  4. Sort into Tier 1 and Tier 2.
  5. Write one channel YAML and one schedule.
  6. Validate with StreamTV's own validators.
  7. Rehearse the import on a throwaway StreamTV server.
  8. Ship a gated, colored zsh installer.
- **One play order.** In every channel:
  - programs play oldest to newest;
  - each gap between programs gets one or more short break reels;
  - reels over 20 minutes and multi-program "marathon" tapes play as a block at the end;
  - the loop repeats.

  Channel 1225 used a slightly different reel rotation from the later builds, and 1224 adds a station ID after each break (Section 8.4). **One reference planner rebuilds all eight channels and schedules byte-for-byte** from the recorded inputs (Section 13.1).
- **What changed along the way.** The first 1225 schedule used 2-minute `duration:` breaks. After a test import, it was reworked to play one whole reel per gap with `all:` [T5]. The same code path is defect M1 in Section 14.
- **Templates for the improved MCP.** These eight channels are the templates the new Channel Creator MCP follows when it builds **new** channels:
  - `kids_specials` (like 1225);
  - `holiday_family` (like the six holiday channels);
  - `prime_time_station_ids` (like 1224).

  The MCP never recreates them. Their recorded inputs only prove that the template code matches them.
- **Edge case.** Channel 2011 was an edit of an existing channel. It needed a merge from the user's file (not an export), an inventory of what each existing tape contains, a no-repeat check, two install modes and an installer that refuses unknown items (Section 9). It shows editing is possible. It is not the default path for new channels.
- **Main limitations.**
  - Placeholder air days: 6 in 1224, 2 in 1225, 1 in 704, 1 in 1031.
  - Commercials edited out of many uploads: 28 Macy's parades and 11 prime-time programs.
  - Commercial presence sometimes shown only by a "WOC" label or inferred from runtime.
  - YouTube removals.
  - No KCCO material for any channel.
  - URL reachability couldn't be tested from the workspace.

  See Section 12.

# Scope and evidence base

**In scope.** Every channel build in this conversation, from November 18 to November 22, 2026, in order: 1225 [T0–T5]; the six holiday channels [T6–T7]; the Macy's parade expansion and its full-broadcast check [T8–T12]; 1224 and its conversion into the 2011 add-on [T13–T19]; and this audit.

**Evidence used.**

1. **Delivered packages:** `vintage-kids-xmas-1225.zip` (6 files), `vintage-holiday-channels.zip` (26 files), `prime-time-xmas-2011.zip` (10 files), and the 1224 build output. All were byte-compared with fresh rebuilds (Section 13).
2. **Build scripts and recorded data**, still in the workspace:
   - `xmas/build.py`, `archive_files.json`, `yt_len.json`, `report.py`;
   - `holidays/build_all.py`, `holidays_data.py`, `holidays_extras.py`, `archive.json`, `af1.json`, `af2.json`, `yt.json`;
   - `primetime/prime_data.py`, `build_prime.py`, `build_2011.py`;
   - `yt1.txt`.
3. **The conversation history** (Appendix A), read with the chat history tool. The query code is extracted to `evidence/turn01_turn07_queries.md`, `turn05_queries.md` and `turn09_queries.md`.
4. **The StreamTV repositories** (Section 3.3).

**Not in scope.** Playing the actual video. The workspace can't reach archive.org or YouTube, so no video was streamed [T9]; [F hol/README.md].

# Knowledge, rules, repositories and assumptions that informed the work

## User requirements (origin: user messages)

| Build | Requirement (user's words, shortened) | Origin |
|---|---|---|
| 1225 | "a vintage Kids Christmas Channel … build a list of URLs from the search which can be fed into StreamTV". An attachment was referenced; **its contents are not observable in this conversation** | [T0] |
| all | Public wiki repo, then private source repo | [T2], [T4] |
| Holidays | "Do the same thing as above for every other major holiday which have had holiday specials created — Thanksgiving, Halloween, Easter, etc. One channel for each" | [T6] |
| 1128 | Add full Macy's Thanksgiving Day Parade recordings, "as many … as you can"; partials only if that is all that exists for a year | [T8] |
| 1128 | Are the listed parade years all full broadcasts? (answered: no; 16 full with commercials, 30 with commercials cut, 6 uncertain, 7 partial) | [T11]–[T12] |
| 1224 | Christmas movies or specials that aired in the **evenings**, 1980s/1990s, **CBS or ABC** only, holiday commercials, complete airings preferred, **WCCO 4 or KSTP 5** commercials between programs | [T13] |
| 2011 | Add to the **existing channel 2011**; then the uploaded 2011 file; "no duplicate programs"; scope "within 2011 only"; keep the 1992 tape | [T15]; [E15]–[E24] |

The style requirements carried from one build to the next. "Do the same thing as above" made 1225 the template for the holidays [T6]. "The same style of programming as the previous two" made 1225 and the holiday channels the template for 1224 [T13].

## Standing preferences (origin: the user's saved memory)

- **Script-First:** complete paste-ready scripts instead of manual steps.
- **Verification gates:** stop on failure, print FAILED, show artifacts and diagnostics, give repairs, and end with a PASS/FAIL table.
- **Oh My Zsh colors:** the zsh `colors` module.

All three installers follow them. They have 8 numbered steps with the same `record`/`fail`/`summary` helpers [F 1225/install_vintage_kids_xmas.zsh L42–88]; [F hol/install_vintage_holiday_channels.zsh L87–254].

## Repositories (authoritative)

| Repository | Used for |
|---|---|
| `roto31/StreamTV` (public; wiki also cloned) | Wiki pages on custom sources and schedules; `docs/YAML_VALIDATION.md` [T3] |
| `roto31/StreamTV-source` (private) | Channel and schedule JSON schemas (`schemas/`), `YAMLValidator`, `ScheduleParser`, the importer, a throwaway test server copied to `stv-test/` [T5]; [T16] |

Repository facts that shaped decisions:

- **The import format** is `channels: [{number, name, group, description, enabled, streams: [...]}]`, with stream fields `id, collection, type (event|commercial), year, broadcast_date, slot, network, runtime, source, url, notes` [R schemas/channel.schema.json]; [T3].
- **Schedules live in `schedules/<n>.yml`** and are looked up in the order `mn-olympics-<n>.yml`, `mn-olympics-<n>.yaml`, `<n>.yml`, `<n>.yaml` [R streamtv/scheduling/parser.py L171–182].
- **`duration:` filler items** expect a string. A whole-collection item plays the entire collection [R streamtv/scheduling/engine.py L248–296]. These lines were read during the 1225 build ("Read the duration filler logic"), and the schedule was then reworked to one reel per gap [T5]; [A: the reason is inferred from the order of those steps; the test output itself is not preserved].
- **Upload import** (`POST /api/import/channels/yaml?validate=true`, field `yaml_file`):
  - it writes the upload to a temporary file and imports it, so no copy is kept in `data/` [R streamtv/api/import_api.py L126–200];
  - it scans the temp folder for duplicate ids [R streamtv/importers/channel_importer.py L535–536].
- **An existing media row is reused by URL** [R streamtv/importers/channel_importer.py L127]. That is why two channels can share a break reel.
- **Wiki mismatch:** the wiki lists a separate validate route that the code doesn't have, so the installers validate during import [T5].

## Domain knowledge used, and its origin

| Fact | Origin |
|---|---|
| WCCO = CBS 4, KSTP = ABC 5, KARE = NBC 11, KCCO = CBS 7 (Alexandria) in Minnesota | Uploader descriptions and general knowledge [A]; the definitions are written into every SOURCES file [F 1225/SOURCES.md §Plain-language terms L5–15] |
| "WOC" in a title means "with original commercials" | Uploader convention; defined in SOURCES [F hol/sources/*-SOURCES.md, Plain-language terms] |
| Macy's parade on NBC; CBS ran its own "All-American Thanksgiving Day Parade" coverage | Item titles and descriptions [K holidays/holidays_data.py L56–110] |
| A full Macy's broadcast runs about 3 hours; 2 h 6 min–2 h 26 min means the commercials were cut | Runtime comparison during the full-broadcast check [T12]; [A: an assessment from runtimes] |
| Network shares of each station over the decades | Not researched; taken from item descriptions where stated, otherwise left as the uploader gave it |

## Datasets

There were no external datasets. All candidates came from live archive.org and YouTube responses at build time. They were frozen into the data files listed in Section 2, which makes rebuilding deterministic (Section 13).

# The process, end to end

## The common pipeline (all eight new channels)

| # | Step | Why | Evidence |
|---|---|---|---|
| 1 | Read the request and the StreamTV format; check which channel numbers are free | The import format and schedule rules come from the repo, not memory | [T3], [T7] |
| 2 | Open archive.org in the built-in browser pane and run search code there | The workspace shell is blocked from archive.org and YouTube; browser-side `fetch()` works | [T1]; [T7] |
| 3 | archive.org rounds: broad combined query → one query per keyword → station/collection queries | Broad first for recall, then targeted queries for the named specials, Minnesota stations and known VHS collections | Appendix C |
| 4 | archive.org metadata and uploader pass | Get the real `.mp4` file name, runtime, description and uploader | Section 5 |
| 5 | Open YouTube; run the search jobs, then the watch-page pass | Same intent; confirm length, playability and channel | Section 6 |
| 6 | Pick items into a data file (tuples with tier, commercials label and a note) | The note records the evidence and any placeholder | [K xmas/build.py L20–108]; [K holidays/holidays_data.py]; [K primetime/prime_data.py] |
| 7 | Generate the channel YAML, schedule, `urls.tsv` and `SOURCES.md` | Section 8 | [K …/build*.py] |
| 8 | Validate: JSON schemas, `YAMLValidator`, `ScheduleParser` | StreamTV's own checks | [T5]; [T9]; Section 10 |
| 9 | Rehearse on a throwaway StreamTV (`stv-test`, SSDP off): import, M3U, guide | Catch format and schedule problems before the user's server | [T5]; [T9] |
| 10 | Write the gated installer; test the failure path; package; deliver with a plain summary | Owner preferences (Section 3.2) | [T5]; [T9] |

## Build timeline

| Build | Turns | Decisions worth knowing |
|---|---|---|
| 1225 | [T0]–[T5] | Kids' specials from CBS/ABC/NBC 1981–2005, with Minnesota reels alternating with network reels. The first schedule used 2-minute `duration:` breaks; after the test import it was changed to one reel per gap, with long reels and marathon tapes at the end. Programs were re-sorted by air date. The original 1981 WLS *Santa Claus Is Comin' to Town* had gone from YouTube, so the archive.org mirror was used |
| Holidays | [T6]–[T7], [T9] | Planned: Halloween, Thanksgiving, Easter, Valentine's, New Year's, St. Patrick's, July 4th [T7]. St. Patrick's Day and Mother's Day were dropped for lack of material. New Year's and July 4th were widened to family broadcasts (Rose Parade, Rockin' Eve, the 1986 Statue of Liberty coverage). The reel rotation changed so that every reel plays each loop (Section 8.4) [T9] |
| Macy's | [T8]–[T12] | One recording per year, choosing the fullest copy, with commercials where possible; partials only where nothing fuller exists. 57 Macy's recordings covering 55 years, plus 8 CBS parades. A later check found only 16 years are full broadcasts with commercials [T12] |
| 1224 | [T13]–[T14] | Prime-time CBS/ABC Christmas 1980–1999. WCCO and KSTP reels alternate, plus a station ID after every break. Nothing from 1225 is repeated except shared WCCO/KSTP reels [F 1224/SOURCES.md L5]. It was built and validated as a standalone channel, then turned into the 2011 add-on when the user asked [E11]; [E15] |
| 2011 | [T15]–[T19] | Edit of an existing channel (Section 9) |

# How Archive.org was searched and parsed

**Where it ran.** JavaScript in the built-in browser pane of the Claude desktop app, on a tab open at `https://archive.org/` (same-origin `fetch`). The first attempts with workspace `curl` and `WebFetch` were blocked or unusable [T1].

**Endpoints.**

| Endpoint | Use | Parameters / parsing |
|---|---|---|
| `https://archive.org/advancedsearch.php` | Search | `q` (Lucene syntax), `fl[]=identifier,title,date,collection,uploader` (varied by query), `rows=200`–`5000`, `page=1,2` for large sweeps, `sort[]=item_count desc` for collection discovery, `output=json` |
| `https://archive.org/metadata/<identifier>` | Files and metadata | `files[].name`, `length` (seconds), `size`; `metadata.title`, `date`, `creator`, `collection`, `description` (HTML stripped, truncated), `subject`; review count |
| `https://archive.org/details/<identifier>` (HTML) | Uploader handle | Regex `href="/details/@([^"\/?#]+)"` |
| `https://archive.org/download/<id>/<file>` | The URL written to YAML | File name from the metadata list, percent-encoded with `urllib.parse.quote` [K holidays/build_all.py L17–28] |

**Search syntax used.**

- **Field queries:** `title:`, `description:`, `subject:`, `collection:`, `identifier:capture-a*`, `mediatype:movies`, `mediatype:collection`.
- **Combining terms:** boolean `AND`/`OR`, quoted phrases, and in one round a date range.
- **Collections queried directly:**
  - `vintagevhsvault`;
  - `smokesvhsdvrcollection` (Smoke's VHS/DVR collection);
  - `vhscommercials`;
  - `capture-a*`, a numbered capture series.

All query text is in Appendix C.

**Client-side filters.**

- **Christmas (1225):** a Christmas-word regex on the title, plus a broadcast-word regex on the title and identifier: `cbs|abc|nbc|wcco|kstp|…|woc|commercial(s)|ads|broadcast|airing|off-air|bumper|promo|break(s)|vhs|recorded|original` [T1].
- **Holidays:** the same idea, with a call-sign pattern `[KW][A-Z]{2,3}(-TV)?`. Junk titles were dropped:
  - `opening to`, `closing to`, `split screen`;
  - `fanmade`, `dvd menu`;
  - `review`, `reaction`, `trailer`, `credits`.

  Weak collections were dropped: `community_media`, `fringe`, `tvarchive` and `deemphasize` [T7].

**File selection rules** [T7]:

- Keep `.mp4` files, except `VIDEO_TS.mp4`.
- Drop an `.ia.mp4` derivative whenever its original `.mp4` exists.
- If there's no `.mp4`, fall back to other video types.
- Take the file name verbatim from the metadata list.

The recorded results are `holidays/archive.json` (104 items: `{u: uploader, f: [[file, seconds, bytes]]}`) and `xmas/archive_files.json` (44 items: `[[file, seconds]]`).

**Long jobs.** Browser console calls time out, so metadata passes ran as background jobs stored on `window` (`metaJob`, `fileJob`) and were polled [T7]; [T9].

# How YouTube was searched and parsed

**Tooling.** No API and no key. JavaScript `fetch()` ran in a tab open at `https://www.youtube.com/` [T5]; [T7].

**Search.**

1. Fetch `GET /results?search_query=<q>&sp=EgIQAQ%253D%253D` (the `sp` value is the "Videos" filter).
2. Extract the JSON with `var ytInitialData = (\{.*?\});<\/script>`.
3. Walk the object for every `videoRenderer`, keeping `videoId`, title, channel name, handle (`canonicalBaseUrl`) and `lengthText`. The first 14 results per query were kept.
4. Batches ran as a background job (`ytJob`) and were polled [T7].

The 1225 searches also listed channel playlists (`gridPlaylistRenderer`) for collector channels [T5].

**Watch-page check.**

1. Fetch `GET /watch?v=<id>`.
2. Extract with `var ytInitialPlayerResponse = (\{.*?\});(?:var|<\/script>)`.
3. Read `videoDetails.lengthSeconds`, `playabilityStatus.status`, `microformat.playerMicroformatRenderer.ownerProfileUrl` and the description (`vidJob`) [T7].

The results are stored as `{videoId: [seconds, status, handle]}` in `holidays/yt.json` (100 videos) and as `{videoId: [seconds, status]}` in `xmas/yt_len.json` (32 videos).

**Query design.** Each query names a program, network and year with words like "commercials", "original broadcast", "full broadcast" or "full tape". There are station queries ("WCCO <holiday> commercials", "KSTP …") and collector-channel queries ("tcmedianow <holiday>"). The query counts are:

- 1225: 20 + 15;
- holidays: 15 + 22 + 23 + 10;
- Macy's: one per missing year;
- 1224: 65.

They are in Appendix C.

# How content was selected and classified

**Inclusion rules by channel:**

| Channel | Rule | Evidence |
|---|---|---|
| 1225 | Kids' Christmas specials as broadcast on CBS, ABC or NBC, 1981–2005, off-air captures | [F 1225/channel-1225-vintage-kids-christmas.yaml L5] |
| 101–1128 | The holiday's kids' specials on CBS/ABC/NBC, 1980s to early 2000s. New Year's and July 4th were widened to family broadcasts; Thanksgiving adds parades | [F hol/sources/*-SOURCES.md, Plain-language terms, "Tier 1 / Tier 2"]; [T9] |
| 1224 | CBS/ABC prime-time Christmas movies and specials, 1980–1999; breaks only from WCCO/KSTP; nothing already on 1225 | [F 1224/SOURCES.md L5]; [T13] |

**Commercial-presence labels** (in each program's `notes`):

| Label | Meaning |
|---|---|
| `yes` | Stated in the description or title |
| `mostly` / `some` | Stated as partial |
| `label-only` | Only "WOC" in the title |
| `inferred` | Runtime fits a commercial slot |
| `unverified` | The description is silent |
| `no` | Removed or never present |

These labels are rendered into plain words in SOURCES [K holidays/build_all.py L30–33].

| Label | 1225 | 101 | 214 | 401 | 704 | 1031 | 1128 | 1224 |
|---|---|---|---|---|---|---|---|---|
| yes | 20 | 4 | 2 | 4 | 2 | 10 | 11 | 13 |
| mostly / some | 5 / 2 | – | – | – | – | – | – / 1 | – |
| label-only | 12 | – | – | – | – | 1 | 3 | 1 |
| inferred | 1 | 2 | – | 1 | – | 1 | 14 | 1 |
| unverified | 9 | 3 | 1 | 8 | 3 | 1 | 13 | 5 |
| no | – | – | – | – | – | – | 28 | 11 |

Counts are from [K fixtures/candidates_*.json].

**Tiers.** Tier 1 is a strong match: the right holiday, a CBS, ABC or NBC broadcast (CBS/ABC for 1224), the target years, and commercials confirmed. Tier 2 means one of those is missing or unconfirmed [F hol/sources/*-SOURCES.md, "Tier 1 / Tier 2"]; [F 1224/SOURCES.md]. Tier 1 items are listed first in SOURCES. Both tiers are loaded into the channel.

**Duplicates and exclusions.**

- **One copy per airing.** Other copies are listed under "Also found, not loaded" as backups [F 1225/SOURCES.md L136–145].
- **Macy's.** Duplicate copies for the same year were skipped; only the most complete was kept [K holidays/holidays_extras.py L65].
- **Different years are not repeats.** The same special in a different year stays, labeled "(repeat)" [K holidays/holidays_data.py L27].
- **Excluded:** home-video and DVD rips; fan edits and "opening to" videos; reviews and reactions; items outside the network or years; St. Patrick's Day and Mother's Day as whole channels [T9].

**Placeholder dates.** When only a month or year was known, a day was assigned so the item could be ordered, and the note says so. Notes containing "placeholder": 1224 (6), 1225 (2), 704 (1), 1031 (1). Another 5 entries in 1225 have no date at all: the 3 marathon tapes and the two parts of NBC's *A Christmas Dream* (1984). They sort as December 31 of their year [K fixtures]; [K ref_plan.py].

# How content was assembled

## File formats

- **Channel file:** `channel-<n>-<slug>.yaml`, one channel with group `Holiday` and `enabled: true`.
  - Programs are `type: event` with `year`, `broadcast_date`, `slot` ("Title (Network, date)"), `network`, `runtime` (ISO 8601), `source` (archive|youtube), `url` and `notes` ("Tier N; commercials: X. <evidence>. Page: <link>").
  - Break reels are `type: commercial` [F 1225/channel-1225-vintage-kids-christmas.yaml L1–20].
- **Schedule:** `schedules/<n>.yml`, containing:
  - `name`, `description`, and `media: {preferred_extension: mp4, mp4_only: true}`;
  - one `content` entry per program and per reel (`order: chronological`);
  - one `sequence` of `all:` items with `custom_title`, with breaks marked `filler_kind: Commercial`;
  - `playout: [{sequence}, {repeat: true}]`

  [F 1225/schedules/1225.yml].

## One collection per program and per reel

Every program and every reel has its own collection, played with `all:`:

- programs: `<prefix> - <title> (<net> <year>) [<id>]`;
- breaks: `<prefix> - Break - <title> [<id>]`.

This gives each item its own guide title and lets reels rotate independently. It replaced the first 1225 design, which used `duration:` breaks [T5].

## Ordering

Programs sort by `broadcast_date`, or `<year>-12-31` when there is no date. The sort is stable, so ties keep the data-file order [K xmas/build.py L146–147]; [K holidays/build_all.py L78]; [K primetime/build_prime.py L58].

## Break rotation (three versions, one family)

| Version | Used by | Rule | Evidence |
|---|---|---|---|
| **Parity alternate** | 1225 | Gap *i* gets the next Minnesota reel if *i* is even, otherwise the next network reel. Each list has its own counter and wraps; one reel per gap | [K xmas/build.py L143–152] |
| **Interleave and wrap** | 101–1128 | Interleave the groups (Minnesota, network): M1, N1, M2, N2 … When one list runs out, continue with the other. Hand out max(programs, reels) reels round-robin over the gaps, so every reel plays each loop and extra reels double up | [K holidays/build_all.py L80–94] |
| **Interleave and wrap + station ID** | 1224 (and 2011) | As above, with groups WCCO and KSTP. After each gap, add station ID `ids[i mod 7]` | [K primetime/build_prime.py L58–75] |

In all three, reels longer than 20 minutes are taken out of the rotation and play at the end as "Commercial Break Marathon" items. Multi-program marathon tapes, with ids starting `marathon_`, play after them [K xmas/build.py L134, L153–156]; [K holidays/build_all.py L68, L95–98].

The parity rule is not a special case of interleave-and-wrap. Running 1225 through interleave-and-wrap gives a different schedule [K ref_plan.py; tested], so the reference planner keeps both (Section 13.1).

## No-repeat rules for new channels

- **Within a channel:** one copy per airing; other copies are listed as backups (Section 7).
- **Across channels:** 1224 excludes every 1225 program. It shares 12 WCCO/KSTP break reels with 1225 by URL [F 1224/SOURCES.md L5]; [K fixtures; compared].
- **Id finding.** 10 of the 12 shared reels have **different ids** in the two channels (for example `wcco_rudolph_1986` vs `wcco_rudolph_1986_breaks`). Two share both id and URL. StreamTV reuses a media row by URL on import [R streamtv/importers/channel_importer.py L127], so this worked. But each channel's YAML id no longer identifies the shared media row [A]. Section 14 (M10) turns this into a rule.

# Edge case: editing an existing channel (channel 2011)

The user asked for the prime-time channel to be added to their existing channel 2011 [T15]. This section shows that editing an existing channel is possible, and what it takes beyond the new-channel method.

**What was different.**

1. **Base file.** The user uploaded their current 2011 file [E17]. The server export drops fields, so the merge was built from that file [R streamtv/api/export_api.py L22]; [E14].
2. **The import replaces the playlist.** Importing syncs the channel's main playlist to exactly the file's streams [R streamtv/importers/channel_importer.py L333–368]. The merged file therefore lists every item to keep [E12].
3. **The existing items needed dates.** The 11 kept original items had none, so they got schedule-only sort keys from their archive.org metadata [K primetime/build_2011.py EXISTING_DATES]; [E23].
4. **No-repeat across old and new.** Each kept item declares what it contains (`CONTAINS`), including the programs inside multi-program tapes. The build asserts that no program appears twice [E25]. The user set the scope ("within 2011 only") and chose between two conflicting tapes ("keep the 1992 tape") [E24].
5. **Planned removals.** 7 original items were removed in the default mode and 9 in `prefer-complete`, each with a reason [F 2011/merge_manifest.yaml L10–24, L82–100].
6. **Two install modes.**
   - `default` keeps 2011's own copies of two movies.
   - `--prefer-complete` swaps in complete ABC airings with commercials [F 2011/README.md L13–18].
7. **Safer installer.** Before changing anything it stops if:
   - a program is scheduled twice;
   - a removal differs from the manifest;
   - 2011, on the server or in `data/`, holds an item the package doesn't know.

   It backs up the schedule and moves any higher-priority `mn-olympics-2011.*` schedule aside [F 2011/install_prime_time_xmas_into_2011.zsh L128–265].

**Result.** 71 items (40 programs, 31 WCCO/KSTP reels and IDs) and 123 sequence items. It plays 45 distinct programs once per loop. The rehearsals passed in both modes [E25]–[E28].

**Problems specific to editing.**

- **Temp-folder scan.** A stray `/tmp/keep2011.yaml` failed the import, because the upload import scans the temp folder [E27].
- **Shared database rows.** A repo-wide id fix renamed database rows shared with 1225, so it was narrowed and then removed [E20].
- **Lost installer.** The rebuild deleted the installer, so it is now kept outside the output folder [E26].
- **Shared ids in the original file.** The original 2011 file had one id shared by three Winnie the Pooh files, the same id the Builder's 48-character truncation produces [E17]; [E35].

**Takeaway.** Editing is possible and repeatable, but it needs four inputs a new channel doesn't:

- the channel's source file;
- an inventory of what existing items contain;
- user decisions on conflicts;
- an installer that refuses unknown items.

The default for new work is a new channel on a free number [A].

# Validation and testing

| Check | Tool | 1225 | Holidays | 1224 | 2011 |
|---|---|---|---|---|---|
| JSON Schema | `jsonschema` against `schemas/channel.schema.json` and `schedule.schema.json` | Pass [T5] | Pass [T9] | Pass [E11] | Pass [E30] |
| StreamTV validator | `YAMLValidator` | Pass | Pass | Pass | Pass |
| Schedule parser | `ScheduleParser.parse_file` | Pass | Pass | Pass | Pass |
| Test-server import, M3U, guide | Throwaway StreamTV on `localhost:8410` | Pass; guide order checked [T5] | Each channel in channel list and guide [T9] | Not observable in this conversation | 71/71; both modes [E28] |
| Installer failure path | Deliberate bad input | Tested [T5] | Tested, plus `-c` subset [T9] | — | Unknown item → step 5 FAILED [E21] |
| URL reachability | Installer step 3 (oEmbed for YouTube; HEAD for archive.org) | Checked live during research; the installer re-checks on the user's Mac [T5] | Same [T9] | Same | Not run in the workspace [E28] |
| Rebuild in this audit | `ref_plan.py` from the recorded inputs | Byte-equal | Byte-equal (all 6) | Byte-equal | Byte-equal (original scripts) [E30] |
| Re-validation in this audit | `validate_against_streamtv.py` on the rebuilt files | ok 76 streams | ok 25 / 13 / 19 / 17 / 28 / 88 | ok 62 | ok 71 |

# Tools, libraries, scripts and file formats

- **Browser.** The built-in browser pane of the Claude desktop app, driven by JavaScript (same-origin `fetch`). Claude in Chrome is the preferred browser setting but was not connected [T1].
- **Python 3:** PyYAML (`safe_dump(sort_keys=False, allow_unicode=True, width=200)`), jsonschema, `urllib.parse.quote`, `json`, `re`. StreamTV modules: `streamtv.validation`, `streamtv.scheduling.parser`.
- **zsh:** the `colors` module, curl, cmp; the installers.
- **Build scripts:**
  - `xmas/build.py`, `report.py`, `report_template.md` (1225);
  - `holidays/build_all.py`, `holidays_data.py`, `holidays_extras.py` (six channels);
  - `primetime/prime_data.py`, `build_prime.py` (1224);
  - `build_2011.py`, `gen_sources_2011.py` (2011).
- **Formats:** channel YAML, schedule YAML, a TSV URL list (`id type network date runtime url`), Markdown SOURCES and README files, zip.
- **Server endpoints used:**
  - `POST /api/import/channels/yaml?validate=true`
  - `GET /api/channels`, `GET /api/channels/number/{n}`
  - `GET /iptv/channels.m3u`, `GET /iptv/xmltv.xml`
  - `GET https://www.youtube.com/oembed?format=json&url=…` (installer URL check)

  [F 1225/install_vintage_kids_xmas.zsh L147–231]
- **Reproduction kit:** Section 13.

# Problems, failures, workarounds and limitations

| Problem | Workaround / status | Builds | Evidence |
|---|---|---|---|
| The workspace can't reach archive.org or YouTube | Browser-side `fetch` in the built-in browser | all | [T1] |
| Console calls time out | Background jobs on `window`, then polling | all | [T7]; [T9] |
| `duration:` breaks didn't behave as time-boxed breaks | One whole reel per gap with `all:` | 1225 → all | [T5]; Section 14 M1 |
| A YouTube original was taken down (1981 WLS *Santa Claus*) | Used the archive.org mirror | 1225 | [T5] |
| No KCCO material at all; no complete special recorded off WCCO or KSTP (except 2011's) | Minnesota content comes from break reels | all | [T5]; [T9] |
| Too little material for St. Patrick's Day and Mother's Day | No channel made | holidays | [T9] |
| Few kids' specials for New Year's and July 4th | Widened to family broadcasts; Rockin' Eve items can be removed by id prefix `rockin_eve_` | 101, 704 | [T9] |
| Valentine's Day has only 3 programs | Repeats often; add reels if more are found | 214 | [K holidays/holidays_extras.py L103] |
| **Commercials edited out** of most 1986–2020 Macy's uploads, and of 11 prime-time programs | Labeled `no`; Tier 2 | 1128, 1224 | [T12]; Section 7 |
| **Inferred / label-only** commercial presence | Labeled in notes | all | Section 7 |
| **Placeholder air days** | Flagged in notes | 1224, 1225, 704, 1031 | Section 7 |
| **YouTube availability risk** (10–52 YouTube streams per channel) | The installer's URL check; rerun each season | all | Section 2 |
| Wiki lists a validate route the code lacks | Validate during import | all | [T5] |
| One archive.org file name contained a hidden no-break space | Took names verbatim from the metadata file list and rebuilt | 1225 → all | [T5] |
| The same reel has different ids in 1224 and 1225 | Works because media rows are reused by URL; should be one id (M10) | 1224 | Section 8.5 |
| Live search results drift | Reproduction rebuilds the same *files* from recorded inputs, not the same *search results* | all | [A] |

# How to reproduce the process exactly

## Rebuild all eight new channels from recorded inputs (deterministic)

```zsh
cd reproduction-kit/newkit
python3 ref_plan.py /tmp/out fixtures/candidates_*.json     # 8 channel files + 8 schedules
for f in fixtures/expected/*; do cmp $f /tmp/out/${f:t} && print "same ${f:t}"; done
cd ~/StreamTV-source && for n in 101 214 401 704 1031 1128 1224 1225; do
  python3 /path/to/validate_against_streamtv.py /tmp/out/channel-$n-*.yaml /tmp/out/$n.yml; done
```

Expected: all 16 files are byte-identical to the delivered ones, and the validator prints `ok N streams N schedule keys` for each channel (Section 10).

- **Inputs.** `fixtures/candidates_<n>.json` was extracted from the original build data by `extract_candidates.py`, which runs the original build scripts in a scratch copy.
- **Each input file holds:**
  - the channel settings: number, name, slug, collection prefix, descriptions, `rotation`, `break_groups`, `station_id_after_each_gap`, `long_reel_seconds: 1200`, `style`;
  - every candidate in stream order, with `role` (program, marathon, break, station_id), `group`, title, network, date, year, tier, commercials, note, page, url, source and seconds.

## Rebuild with the original scripts

`python3 xmas/build.py`, `python3 holidays/build_all.py` and `python3 primetime/build_prime.py` reproduce the delivered files byte-for-byte; this was checked in this audit. The first two use absolute paths under `/home/claude`.

For 2011, see Section 9 and the channel-2011 kit: `build_2011.py`, `build_prime.py`, `gen_sources_2011.py` [E30].

## Repeat the research (live; results will drift)

1. Open `https://archive.org/` in a browser tab and run the archive.org code from Appendix C in its console. Open `https://www.youtube.com/` in another tab for the YouTube code. Each script must run on the site it fetches from.
2. Apply Section 7. Record each pick as a tuple, with tier, commercials label and an evidence note.
3. Build with the matching script, validate, then run the installer on the StreamTV host **without** `--skip-url-check`.

## Install

| Package | Command |
|---|---|
| 1225 | `./install_vintage_kids_xmas.zsh -d ~/StreamTV-source -u http://192.0.2.1:8410 [-k KEY]` [T5] |
| Holidays | `./install_vintage_holiday_channels.zsh [-c 1031,1128]` [F hol/README.md L18–27] |
| 2011 | `./install_prime_time_xmas_into_2011.zsh [--prefer-complete]` [F 2011/README.md L11–23] |

# Findings for the Channel Creator MCP

These are verified from the current code (public `d691270` = private `353d02e`).

| # | Finding | Evidence |
|---|---|---|
| M1 | **Breaks between items don't work.** For each link the compiler emits `{"all": <whole collection>}` plus `{"duration": 120}`. The engine's duration parser expects a string, logs "Could not parse duration: 120", and skips the break. The collection plays once per link, with no breaks. Every channel here avoided this by using one collection per item and `all:` | [R streamtv/builder/compiler.py L209–270]; [R streamtv/scheduling/parser.py L32–69]; reproduced [E35] |
| M2 | **Stream ids collide.** Archive ids are cut to 48 characters, so files of one item collide (2011's original file shows this) | [R streamtv/builder/resolver.py L73–75]; [E35] |
| M3 | **One collection per channel**, so no per-program breaks or per-item guide titles | [R streamtv/builder/compiler.py L142–207] |
| M4 | **"Chronological" means upload date**, not air date | [R streamtv/builder/compiler.py L122–130, L184–185] |
| M5 | **No YouTube discovery** | [R mcp_streamtv/main.py TOOL_SPECS] |
| M6 | **Unsafe Archive stream URLs** (`.ia.mp4`, pinned storage server, unencoded file names) | [R mcp_archive_org/tools.py L217–282] |
| M7 | **No commercials evidence, tiers, sources report, or long-reel/marathon handling**; no output in the format of the channels above | [R streamtv/builder/models.py]; [R streamtv/builder/compiler.py L315–378] |
| M8 | **Upload import scans the temp folder** for duplicate ids | [R streamtv/importers/channel_importer.py L535–536]; [E27] |
| M9 | **The duplicate-id check skips the Builder's own files.** `assert_unique_stream_ids` ignores every `channels_generated_*.yaml`, so ids in Builder-made channels are never checked against each other | [R streamtv/importers/stream_id_registry.py L19–21, L50–54] |
| M10 | **The same URL can enter under different ids** in different channels (1224 vs 1225, Section 8.5). The importer silently reuses the media row by URL. A new channel should reuse the existing id for a known URL | [R streamtv/importers/channel_importer.py L127]; [K fixtures] |
| M11 | **Runtimes aren't guaranteed exact.** The schema allows whole seconds only; a test value `PT27M25.37S` was rejected. Without a YAML runtime, the importer truncates the archive.org length, and the frozen timeline defaults missing durations to 1,800 s | [R schemas/channel.schema.json]; [R streamtv/builder/resolver.py L112–119]; [R streamtv/scheduling/playout_timeline.py L17–31]; test server, Nov 22 |
| M12 | **Source metadata never reaches the guide.** The channels carry no `description` or `thumbnail`, so Plex's guide repeats the title as the description. On a test server, a stream with `description` starting `Original air date: February 10, 1989.` and a local thumbnail produced the right sub-title, description and icon through the frozen XMLTV writer, with no code change. YouTube `ytimg` and `.webp` icons are dropped by that writer, and YAML categories need a small non-frozen importer change | [R streamtv/api/iptv.py L845–856, L923–964, L1007–1009]; [R streamtv/importers/stream_metadata.py L104–132]; test server |
| M13 | **The guide shows whole minutes.** XMLTV start and stop times are floored to the minute (frozen code); playback uses exact seconds. A 35-second bumper showed as a zero-length guide entry | [R streamtv/api/iptv.py L49–57]; test server |

# Appendix A. Evidence logs {.unnumbered}

## A.1 Conversation turns (read back from this chat's history) {.unnumbered}

| Turn | Who | Content |
|---|---|---|
| T0 | User | 1225 request: vintage kids' Christmas channel; "use the attached" (attachment not observable) |
| T1 | Claude | 1225 research. Reachability test; WebFetch attempts; built-in browser opened; archive.org queries, collection discovery, metadata and uploader passes (Appendix C.1). **Truncated in history** |
| T2 | User | Public wiki `github.com/roto31/StreamTV` |
| T3 | Claude | Cloned the repo and wiki; read the custom-sources and schedules pages, `YAML_VALIDATION.md`, schemas and importer |
| T4 | User | Private repo `github.com/roto31/StreamTV-source` |
| T5 | Claude | 1225 YouTube research (20 + 15 queries) and watch-page pass; `build.py`; validation; test server; duration-filler investigation and rework; air-date sort; installer; SOURCES; delivery (`vintage-kids-xmas-1225.zip`) |
| T6 | User | Holiday channels request |
| T7 | Claude | Holiday research: archive.org rounds, Smoke's collection, metadata and file passes, YouTube (70 queries), watch-page pass; `yt.json`. **Truncated in history** |
| T8 | User | Add Macy's parades, full where possible, partials if nothing else |
| T9 | Claude | Macy's archive.org and YouTube searches; one per year; the six channels built, validated, test-imported; failure and subset tests; delivery (`vintage-holiday-channels.zip`) |
| T11 | User | Are the listed parade years all full broadcasts? |
| T12 | Claude | Runtime/commercials check of each Macy's file: 16 full with commercials, 30 commercials cut, 6 uncertain, 7 partial |
| T13 | User | Prime-time CBS/ABC Christmas channel, WCCO/KSTP breaks (00:46, Nov 22) |
| T14 | Claude | Prime-time research and the 1224 build (detail in A.2, E02–E11) |
| T15 | User | "Ensure this can be added to an existing channel, channel 2011" |
| T16– | both | 2011 work (A.2, E12–E29), then this audit |

Turn 10 is an empty assistant entry in the history.

## A.2 Channel 2011 detailed log (Nov 22, CT) {.unnumbered}

| ID | Time | Event |
|---|---|---|
| E01 | 00:46 | Prime-time request |
| E02–E10 | 00:47–00:52 | archive.org rounds 1–3 (13 queries), metadata passes, YouTube rounds 1–3 (65 queries), watch-page check of 62 videos (all `OK`) |
| E11 | 00:53 | `prime_data.py`, `build_prime.py`; channel 1224 built; schema, validator and parser pass |
| E12–E14 | 00:55–00:56 | Read the importer playlist sync, schedule lookup, export, and delete rules |
| E15 | 00:54 | User: add to channel 2011 |
| E17 | 00:59 | User uploaded the 2011 file (18 streams; one id ×3) |
| E18–E21 | 01:00–01:04 | Merge design, `build_2011.py`, installer, rehearsals, id-sync problems, gate test |
| E22–E24 | 01:05–01:07 | "No duplicate programs"; tape contents fetched; user chose "within 2011 only" and "keep the 1992 tape" |
| E25–E28 | 01:08–01:11 | `CONTAINS` inventory; 7/9 removals; installer recreated; temp-folder 400 fixed; final rehearsals PASS |
| E29 | 01:12 | `prime-time-xmas-2011.zip` delivered |
| E30 | 10:40 | Audit: zip byte-identical to the build; counts recomputed; kit rebuild identical |
| E35 | 10:46 | M1 and M2 reproduced by running Builder code |

# Appendix B. Package inventory {.unnumbered}

| Package | Files |
|---|---|
| 1225 | `channel-1225-vintage-kids-christmas.yaml` (76 streams), `schedules/1225.yml` (76 content keys, 99 sequence items), `install_vintage_kids_xmas.zsh` (242 lines, 8 gated steps), `urls.tsv`, `README.md`, `SOURCES.md` |
| Holidays | `channels/channel-<n>-<slug>.yaml` ×6, `schedules/<n>.yml` ×6 (sequence items: 101 → 25, 214 → 13, 401 → 26, 704 → 17, 1031 → 28, 1128 → 145), `sources/<n>-<slug>-SOURCES.md` ×6, `urls/<n>-<slug>.tsv` ×6, `install_vintage_holiday_channels.zsh` (268 lines, 8 steps, `-c` subset), `README.md` |
| 1224 | `channel-1224-vintage-prime-time-christmas.yaml` (62 streams), `schedules/1224.yml` (62 keys, 96 sequence items), `urls.tsv`, `SOURCES.md`. Not delivered as its own package; the user redirected the work to channel 2011 before delivery [T15] |
| 2011 | `channels_generated_2011.yaml` (71), `schedules/2011.yml` (123 items), `prefer-complete/…`, `merge_manifest.yaml`, `base/…original.yaml` (18), `urls.tsv` (71), `install_prime_time_xmas_into_2011.zsh` (307 lines), `README.md`, `SOURCES.md` |

# Appendix C. All queries, verbatim {.unnumbered}

The runnable code for every call is in the evidence folder: `turn01_turn07_queries.md`, `turn05_queries.md` and `turn09_queries.md`, extracted from the history, plus the channel-2011 research scripts `research/01`–`06`. The query text follows.

## C.1 Channel 1225 — archive.org [T1] {.unnumbered}

- `title:(christmas OR holiday OR rudolph OR frosty OR grinch OR santa OR snowman OR "charlie brown") AND (commercials OR commercial OR ads OR breaks OR "woc" OR airing OR broadcast OR "off-air" OR vhs) AND mediatype:movies`
- `(wcco OR kstp OR kcco OR kmsp OR minneapolis OR "twin cities") AND (christmas OR holiday OR december) AND mediatype:movies`
- `collection:(vintagevhsvault OR vintage_vhs_vault) AND (christmas OR holiday)`
- `mediatype:collection AND (title:(vhs) OR title:(commercials) OR title:("tv recordings") OR title:(broadcast))`, sorted by item count
- A title sweep of 68 special names (`title:(rudolph) OR title:(frosty) OR title:("santa claus is comin") OR …`) `AND mediatype:movies`, rows 5000, pages 1–2
- `title:(wcco OR kstp OR kcco OR "kstp-tv" OR "wcco-tv" OR kare OR kmsp OR "channel 4 minneapolis" OR "twin cities") AND mediatype:movies`
- `description:(wcco OR kstp OR kcco) AND (christmas OR holiday OR december OR santa) AND mediatype:movies`
- `title:("christmas specials" OR "christmas special recordings" OR "holiday specials" OR "christmas tape" OR "holiday tape" OR "christmas commercials") AND mediatype:movies`
- `collection:smokesvhsdvrcollection AND (title:(dec OR december OR christmas OR holiday) OR description:(christmas OR santa OR rudolph OR frosty OR grinch OR "charlie brown" OR holiday))`
- `title:(wcco OR kstp OR kcco) AND (title:(december OR christmas OR holiday) OR description:(christmas OR rudolph OR frosty OR grinch OR santa)) AND mediatype:movies`
- `identifier:capture-a* AND (title:(wcco OR kstp OR kcco OR kare OR kmsp)) AND title:(12)`
- `collection:vhscommercials AND title:(wcco OR kstp OR kcco OR "kstp-tv" OR "wcco-tv")`
- A metadata pass and an uploader pass over the shortlisted identifiers. The identifier lists are visible in [T1] and not repeated here. Earlier WebFetch/curl attempts used `(christmas) AND (commercials)` and CBS/ABC/NBC and Minnesota variants (see the evidence file).

## C.2 Channel 1225 — YouTube [T5] {.unnumbered}

*Round 1 (20):*

- WCCO christmas commercials
- KSTP christmas commercials
- KCCO christmas
- WCCO Charlie Brown Christmas 1986
- KSTP Rudolph
- TCMediaNow christmas
- CBS Christmas special with commercials 1980s
- ABC Christmas special original broadcast commercials 1980s
- NBC Christmas special with commercials 1987
- Muppet Family Christmas original broadcast commercials
- Garfield Christmas CBS commercials
- Rudolph CBS 1990s with commercials
- Frosty the Snowman CBS commercials 1980s
- Winnie the Pooh and Christmas Too ABC 1991 commercials
- Claymation Christmas Celebration CBS commercials
- He-Man She-Ra Christmas special 1985 commercials
- Christmas specials VHS commercials 1990s full tape
- Year Without a Santa Claus ABC commercials
- A Charlie Brown Christmas CBS 1980s commercials
- Pee-wee Playhouse Christmas CBS 1988 commercials

*Round 2 (15):*

- Christmas special full broadcast original commercials 1980s
- Christmas special full broadcast commercials 1990s CBS
- Rudolph the Red-Nosed Reindeer CBS full broadcast commercials
- Frosty the Snowman CBS full broadcast with commercials
- A Charlie Brown Christmas CBS full broadcast commercials
- A Garfield Christmas full broadcast commercials
- Claymation Christmas Celebration full broadcast commercials
- Winnie the Pooh and Christmas Too ABC full broadcast
- Santa Claus is Comin to Town ABC full broadcast commercials
- Mickey's Christmas Carol NBC full broadcast commercials
- Christmas Toy 1986 ABC full broadcast commercials
- A Wish for Wings That Work CBS 1991 commercials
- Its Christmastime Again Charlie Brown 1992 CBS commercials
- Disney Christmas special CBS full broadcast commercials
- How the Grinch Stole Christmas CBS 1980s full broadcast commercials

The results of round 1 are preserved in `yt1.txt`.

## C.3 Holiday channels — archive.org [T7] {.unnumbered}

- **Round 1:** one combined `title:(…)` query per holiday.
  - Halloween: `halloween`, `"great pumpkin"`, `"grinch night"`, `howl-oween`, `"pumpkin who couldn"`, `"witch's night out"`, `"mad monster"`, `"boo to you"`, `"garfield's halloween"`, `"garfield in disguise"`, `"disney halloween"`, `"casper's halloween"`, `"halloween treat"`, `"scary tales"`, `trick or treat`, `"monster bash"`, `spooky`.
  - Thanksgiving: `thanksgiving`, `"mayflower"`, `"macy's"`, `"turkey"`, `pilgrim`, `"parade"`.
- **Round 2:** one `title:(<k>) AND mediatype:movies` query per keyword.
  - **Halloween (19):** `"great pumpkin"`, `"garfield's halloween"`, `"garfield in disguise"`, `"grinch night"`, `howl-oween`, `"halloween treat"`, `"disney halloween"`, `"disney's halloween"`, `"scary tales"`, `"witch's night out"`, `"casper's halloween"`, `"pumpkin who couldn"`, `"boo to you too"`, `"halloween that almost"`, `"dracula saved"`, `"halloween tree"`, `boogedy`, `"halloween hall"`, `"halloween special"`.
  - **Thanksgiving (10):** `"charlie brown thanksgiving"`, `"garfield's thanksgiving"`, `"mouse on the mayflower"`, `"thanksgiving that almost"`, `"mayflower voyagers"`, `"thanksgiving day parade"`, `"thanksgiving parade"`, `"thanksgiving diet"`, `"thanksgiving special"`, `"turkey caper"`.
  - **Easter (13):** `"easter beagle"`, `"peter cottontail"`, `"easter bunny is comin"`, `"first easter rabbit"`, `"bugs bunny's easter"`, `"daffy duck's easter"`, `"easter bear"`, `"easter fever"`, `"easter surprise"`, `"easter special"`, `"easter egg"`, `"easter parade"`, `easter`.
  - **Valentine's (7):** `"be my valentine"`, `"bugs bunny's valentine"`, `"cupid"`, `"valentine for you"`, `"valentine special"`, `"valentine's day"`, `valentine`.
  - **New Year's (10):** `"happy new year, charlie brown"`, `"happy new year charlie brown"`, `"shiny new year"`, `"rose parade"`, `"tournament of roses"`, `"rockin' eve"`, `"new year's eve"`, `"new years eve"`, `"new year's day"`, `"new year's special"`.
  - **St. Patrick's (6):** `"st. patrick"`, `"st patrick"`, `"saint patrick"`, `leprechaun`, `"luck of the irish"`, `shamrock`.
  - **July 4th (11):** `"fourth of july"`, `"4th of july"`, `"yankee doodle cricket"`, `"christmas in july"`, `"this is america, charlie brown"`, `"independence day"`, `"capitol fourth"`, `"liberty weekend"`, `"boston pops"`, `fireworks`, `"birth of the constitution"`.
- **Smoke's collection by month:** `collection:smokesvhsdvrcollection AND title:(oct OR october OR nov OR november OR feb OR april OR apr OR jul OR july OR "dec. 31" OR "jan. 1")`.
- **Metadata and file passes** over the shortlisted identifiers. The lists are visible in [T7]; the verified results are in `holidays/archive.json`.

## C.4 Holiday channels — YouTube [T7] {.unnumbered}

- **Halloween (15):**
  - tcmedianow Halloween; WCCO Halloween commercials; KSTP Halloween commercials
  - Great Pumpkin Charlie Brown CBS original broadcast commercials
  - Garfield Halloween Adventure CBS 1985 commercials
  - Halloween Is Grinch Night ABC original broadcast
  - Bugs Bunny Howl-oween special CBS commercials
  - Raggedy Ann Pumpkin Who Couldn't Smile CBS
  - Witch's Night Out NBC 1978 broadcast
  - Disney Halloween CBS 1980s with commercials
  - Halloween special 1980s original broadcast commercials
  - Boo to You Too Winnie the Pooh CBS 1996 commercials
  - Garfield in Disguise CBS 1985 Halloween broadcast
  - Casper Halloween special NBC 1979 commercials
  - Halloween 1980s cartoons VHS commercials full tape
- **Thanksgiving and Easter (22):**
  - tcmedianow Thanksgiving; WCCO Thanksgiving commercials; KSTP Thanksgiving commercials; KARE Thanksgiving parade commercials
  - Charlie Brown Thanksgiving CBS original broadcast commercials
  - Garfield's Thanksgiving CBS 1989 commercials
  - Mouse on the Mayflower NBC broadcast
  - Mayflower Voyagers This Is America Charlie Brown CBS 1988
  - Macy's Thanksgiving Day Parade NBC with commercials 1980s
  - CBS All American Thanksgiving Day Parade full broadcast commercials
  - Thanksgiving That Almost Wasn't broadcast
  - Daffy Duck Thanks-for-Giving special CBS
  - tcmedianow Easter; WCCO Easter commercials
  - It's the Easter Beagle Charlie Brown CBS broadcast commercials
  - Here Comes Peter Cottontail ABC original broadcast commercials
  - Easter Bunny Is Comin to Town ABC broadcast commercials
  - First Easter Rabbit NBC broadcast
  - Bugs Bunny Easter special CBS commercials
  - Yogi the Easter Bear 1994 broadcast commercials
  - Walt Disney World Easter Parade ABC commercials
  - Easter special 1980s original broadcast commercials
- **Valentine's, New Year's, July 4th, St. Patrick's (23):**
  - Be My Valentine Charlie Brown CBS original broadcast commercials
  - Valentine special CBS 1980s commercials
  - Winnie the Pooh A Valentine for You ABC 1999 commercials
  - Bugs Bunny Valentine special CBS broadcast
  - Mickey's Happy Valentine Special NBC 1989
  - Cathy's Valentine CBS 1989
  - Berenstain Bears Valentine Special NBC 1982
  - Valentine's Day 1980s commercials CBS ABC NBC
  - WCCO Valentine commercials
  - Happy New Year Charlie Brown CBS 1986 broadcast commercials
  - Rudolph's Shiny New Year ABC original broadcast commercials
  - Tournament of Roses Parade 1980s broadcast commercials NBC
  - Rose Parade CBS 1990s full broadcast commercials
  - New Year's Day 1980s commercials WCCO
  - New Year's Rockin Eve 1980s full broadcast commercials
  - Yankee Doodle Cricket ABC broadcast
  - Macy's Fourth of July Fireworks NBC 1980s broadcast commercials
  - Fourth of July 1980s TV commercials broadcast
  - This Is America Charlie Brown Birth of the Constitution CBS broadcast commercials
  - Rudolph and Frosty's Christmas in July ABC broadcast commercials
  - St. Patrick's Day special cartoon broadcast commercials 1980s
  - St Patrick's Day parade broadcast 1980s commercials
  - Leprechaun special TV broadcast 1980s
- **Follow-ups (10):**
  - 1986 Liberty Weekend ABC full broadcast commercials
  - Macy's Fourth of July fireworks spectacular 1990s NBC full broadcast
  - Boston Pops July 4th 1980s broadcast commercials
  - July 4th 1980s full broadcast with commercials
  - Statue of Liberty centennial 1986 ABC opening ceremonies broadcast
  - Fourth of July special 1990s CBS NBC ABC commercials
  - Independence Day 1987 We the People 200 CBS broadcast
  - Mother's Day special Bugs Bunny CBS broadcast commercials
  - Easter Parade 1980s ABC Disney full broadcast commercials RetroWDW
  - Disney Halloween 1990s ABC broadcast commercials
- **Watch-page pass:** over the shortlisted video ids; results in `holidays/yt.json`.

## C.5 Macy's parade expansion [T9] {.unnumbered}

- archive.org: `(title:("macy's" OR macys OR "macy s") AND title:(parade)) AND mediatype:movies` (rows=1000), then metadata and uploader passes.
- YouTube: `<year> Macy's Thanksgiving Day Parade full` for 1960–1971, 1973–1975, 1977–1979, 2017, 2019 and 2021, plus these:
  - Macy's Thanksgiving Day Parade with commercials full broadcast
  - Macy's parade 1970s NBC broadcast
  - CBS All-American Thanksgiving Parade full broadcast 1980s
  - and others listed in `turn09_queries.md`
- Then a watch-page pass.

## C.6 Channel 1224 / 2011 {.unnumbered}

The 13 archive.org queries and 65 YouTube queries are unchanged from the channel-2011 audit. They are listed verbatim in the research scripts `research/01`–`06`:

- archive.org round 1: CBS/ABC + commercials/WOC, WCCO/KSTP, and title-only CBS/ABC;
- round 2: "complete broadcast", named prime-time titles, variety hosts, WOC labels, subject tags;
- round 3: movie-slot names, description phrases, KSTP/WCCO in December;
- YouTube rounds 1–3: program + network + "commercials" / "complete broadcast"; station reels; uploader-style phrasing.
