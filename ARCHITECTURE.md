# StreamTV — Architecture

StreamTV is a cross-platform IPTV platform (FastAPI + Python) that turns online
video sources (Archive.org, YouTube, PBS, Plex) into live TV channels and exposes
them as a spoofed HDHomeRun tuner plus IPTV M3U/XMLTV for Plex, Emby, Jellyfin,
Kodi, and VLC.

> Diagrams are Mermaid. GitHub renders them automatically. Keep them in sync when
> the streaming, import, or source-resolution paths change (see
> `.cursor/rules/streaming-pipeline-verification.mdc`).

## 1. System architecture

```mermaid
flowchart TD
    subgraph Clients
        PLEX["Plex / Emby / Jellyfin"]
        KODI["Kodi / VLC"]
        BROWSER["Web browser"]
    end

    subgraph App["StreamTV FastAPI app (streamtv/)"]
        MW["Middleware: CORS, security headers, CSRF, API key, rate limit"]
        subgraph Routers
            HDHR["HDHomeRun router: discover / lineup / auto stream"]
            IPTV["IPTV router: M3U, XMLTV, HLS"]
            API["REST API: channels, media, playlists, import, settings"]
            WEB["Web UI: dashboard, channels, player"]
        end
        SSDP["SSDP server (UDP 1900 discovery)"]
        CM["ChannelManager -> ChannelStream (continuous playout)"]
        SCHED["Scheduling: ScheduleParser + ScheduleEngine"]
        STREAMER["MPEGTSStreamer (FFmpeg transcode to MPEG-TS)"]
        SM["StreamManager (source detection + URL resolution)"]
        subgraph Adapters
            YT["YouTubeAdapter (yt-dlp)"]
            AO["ArchiveOrgAdapter"]
            PBS["PBSAdapter"]
            PX["PlexAdapter"]
        end
        IMP["ChannelImporter (YAML -> channels/media/playlists)"]
        DB[("SQLite via SQLAlchemy")]
    end

    EXT["Source origins: archive.org, youtube.com, pbs.org, Plex server"]
    FFMPEG["FFmpeg / FFprobe"]

    PLEX -->|discover/lineup/tune| HDHR
    KODI -->|M3U / XMLTV| IPTV
    BROWSER --> WEB
    BROWSER --> IPTV

    HDHR --> CM
    IPTV --> CM
    CM --> SCHED
    CM --> STREAMER
    SCHED --> DB
    STREAMER --> SM
    SM --> YT & AO & PBS & PX
    YT & AO & PBS & PX --> EXT
    STREAMER --> FFMPEG
    API --> DB
    API --> IMP
    IMP --> DB
    App --> SSDP
```

## 2. HDHomeRun streaming (how Plex tunes a channel)

This is the platform's prime objective path. An empty stream returns HTTP 200 by
design (errors are swallowed so Plex does not hard-fail), so success is verified by
real byte count + codecs — see the `verify-hdhomerun-streaming` skill.

**Continuous playout:** `playout_start_time` + schedule durations pick **which**
item is current (EPG-aligned). Playback always starts at **0:00 of that file** —
no FFmpeg `-ss` mid-program seek. Applies to Archive.org and YouTube alike.

```mermaid
sequenceDiagram
    participant Plex
    participant HDHR as HDHomeRun router
    participant CM as ChannelManager
    participant PB as PlaybackBuffer
    participant STR as MPEGTSStreamer
    participant SM as StreamManager
    participant AO as ArchiveOrgAdapter
    participant AORG as archive.org
    participant FF as FFmpeg

    Plex->>HDHR: GET /discover.json, /lineup.json
    HDHR-->>Plex: device info + channel lineup
    Plex->>HDHR: GET /hdhomerun/auto/v{number}
    HDHR->>CM: get_channel_stream(number) — client count +1
    Note over CM: tune_only_buffer: no FFmpeg until tuner connects
    CM->>CM: pick current item from schedule timeline (no -ss)
    CM->>PB: wait_for_playback_buffer (if buffer mode)
    alt CDN-first tune (direct_stream_first + client connected)
        PB-->>CM: skip buffer wait — start FFmpeg immediately
    else buffer prefetch incomplete
        CM->>Plex: MPEG-TS null keepalive chunks + sleep(0.5)
    end
    CM->>STR: stream current schedule item from file start
    STR->>SM: get_stream_url(media.url)
    SM->>AO: extract_identifier + extract_filename (full sub-path)
    AO->>AORG: HEAD /download/{id}/{file} (5s timeout, follow redirects)
    AORG-->>AO: 200/302 direct CDN URL
    AO-->>SM: direct stream URL
    SM-->>STR: stream URL
    alt ffprobe OK within budget
        STR->>FF: VBR mpegts remux or libx264+AAC transcode
    else Archive.org probe skip (Issue 23)
        STR->>FF: H.264 video copy + AAC encode, VBR mpegts (no -muxrate 4M)
    end
    FF-->>STR: TS packets (must exceed 8192 bytes)
    STR-->>HDHR: TS chunks
    HDHR-->>Plex: video/mp2t stream
```

## 3. YAML channel import

The importer reuses the request-scoped DB session so returned ORM objects stay
attached during response serialization — see
`.cursor/rules/fastapi-orm-session-lifecycle.mdc`.

```mermaid
flowchart LR
    Y["Channel YAML (channels: -> streams:)"] --> EP["POST /api/import/channels/yaml[/path]"]
    EP --> V{"validate?"}
    V -->|yes| SchemaCheck["YAMLValidator (JSON schema)"]
    V -->|no| IMP
    SchemaCheck --> IMP["ChannelImporter.import_from_yaml (request session)"]
    IMP --> CH["Channel rows"]
    IMP --> MI["MediaItem rows"]
    IMP --> COL["Collections"]
    IMP --> PL["Playlist + PlaylistItems"]
    CH & MI & COL & PL --> DB[("SQLite")]
    IMP --> RESP["HTTP 200: serialized channels"]
```

## 4. Source URL resolution (Archive.org)

The fix that unblocked Archive.org streaming: `extract_filename()` returns the full
path after the identifier (files often live in sub-directories) — see
`.cursor/rules/source-url-parsing.mdc`.

```mermaid
flowchart TD
    URL["media_item.url e.g. download/ID/Sub Dir/file.mp4"] --> DET["StreamManager.detect_source"]
    DET --> ID["extract_identifier -> ID"]
    DET --> FN["extract_filename -> 'Sub Dir/file.mp4' (full path)"]
    ID --> META["GET /metadata/ID"]
    FN --> MATCH["match against metadata file names"]
    META --> MATCH
    MATCH --> BUILD["build /download/ID/<encoded file>"]
    BUILD --> HEAD["HEAD validate + follow redirects"]
    HEAD --> OUT["direct CDN stream URL -> FFmpeg"]
```

## 5. MPEG-TS remux policy (Plex path)

FFmpeg command selection in `mpegts_streamer.py`. See `.cursor/rules/ffmpeg-mpegts-plex.mdc`
and `LESSONS_LEARNED.md` Issues 23, 28–32.

```mermaid
flowchart TD
    IN["HTTP input URL"] --> PROBE{"ffprobe within budget?"}
    PROBE -->|yes| COPY{"can_copy_video + can_copy_audio?"}
    PROBE -->|timeout on archive.org .mp4| SKIP["Issue 23: H.264 copy + AAC encode"]
    SKIP --> VBR1["VBR mpegts remux<br/>no -muxrate, no extra_flags on copy"]
    COPY -->|full copy| VBR2["VBR mpegts remux (full copy)"]
    COPY -->|needs transcode| XCODE["libx264 + AAC<br/>no h264_videotoolbox encode"]
    COPY -->|.ia.mp4 URL| XCODE
    VBR1 --> OUT["mpegts stdout -> ChannelManager -> Plex"]
    VBR2 --> OUT
    XCODE --> CBR["CBR -muxrate 4M + encoder flags allowed"]
    CBR --> OUT
```

## Consumer endpoints

| Consumer | Endpoint | Format |
|---|---|---|
| Plex / Emby / Jellyfin (tuner) | `/discover.json`, `/lineup.json`, `/hdhomerun/auto/v{n}` | MPEG-TS (`video/mp2t`) |
| Kodi / VLC / IPTV clients | `/iptv/channels.m3u`, `/iptv/xmltv.xml` | M3U + XMLTV EPG |
| Direct channel stream | `/iptv/channel/{n}.ts` | MPEG-TS |
| Browser preview player | `/player`, `/iptv/channel/{n}.m3u8` | HLS (needs AAC audio; see Known Issues) |

## 6. Metadata enrichment (guide quality)

Operator scripts enrich `media_items.meta_data` without changing playout
`duration`. XMLTV prefers nested `enrichment` plots/posters/`episode-num`. See
[docs/guides/METADATA_ENRICHMENT.md](docs/guides/METADATA_ENRICHMENT.md).

```mermaid
flowchart LR
    SCH["Schedule / channel media"] --> ENR["enrich_metadata.py --meta-only"]
    ENR --> TVDB["TVDB"]
    ENR --> TMZ["TVMaze"]
    ENR --> TMDB["TMDB"]
    TVDB & TMZ & TMDB --> MERGE["media_meta merge<br/>archive + enrichment nests"]
    MERGE --> DB[("SQLite media_items.meta_data")]
    DB --> XMLTV["IPTV XMLTV generation"]
    XMLTV --> PLEX["Plex Live TV guide"]
    RET["streamtv_sxxexx_retitle_db.py"] --> DB
    AUD["audit_guide_metadata_sample.py"] --> SCH
```

## 7. EPG sync classes (Plex guide vs playout)

Channels carry `epg_sync_class` **A** / **B** / **C**. Class A is
playout-authoritative (XML row 0 + boundary `reloadGuide`). See
[docs/guides/EPG_SYNC_CLASSES.md](docs/guides/EPG_SYNC_CLASSES.md).

```mermaid
flowchart TD
    TUNE["Tuner / wall clock"] --> CM["ChannelManager continuous playout"]
    CM --> IDX["on-air item index"]
    IDX --> XML["iptv.xmltv / XMLTV programmes"]
    CLS{"epg_sync_class"}
    CLS -->|A| AUTH["Play-out authoritative<br/>reloadGuide on item boundary"]
    CLS -->|B_or_C| WALL["Guide may follow wall clock<br/>capped on-air stretch"]
    AUTH --> PLEX["Plex DVR guide"]
    WALL --> PLEX
    XML --> PLEX
```

## Distributions

The canonical application is the root `streamtv/` package. Platform mirrors
are kept in sync with `python3 scripts/build_distributions.py` when that script
is part of the release workflow.
