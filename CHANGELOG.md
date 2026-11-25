# Changelog

All notable user-facing changes to StreamTV releases.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Documentation

- [Docs index](docs/README.md)
- [Wiki home](https://github.com/roto31/StreamTV/wiki)

## [Unreleased]

## [1.4.7.6] - 2026-11-25

### Fixed
- **macOS DMG** — new signed and notarized build with the refreshed optional starter channels and clearer sample-install errors.

## [1.4.7.5] - 2026-11-25

### Changed
- **Optional starter channels refreshed** — Movies, Music Videos, Saturday Morning Kids, and Greatest Sports use fuller curated playlists (cartoon blocks and championship highlights rather than holiday/Olympic filler).

### Fixed
- **Sample-channel install failures are visible** — invalid stream metadata is sanitized before import, and the setup UI shows errors instead of advancing when a pack fails.

## [1.4.7.4] - 2026-11-24

### Fixed
- **Setup: sample channels were greyed out** when pack files were not beside the running server. StreamTV now finds packs in the app bundle / Application Support / install directory and makes them selectable.

## [1.4.7.3] - 2026-11-24

### Fixed
- **Settings → Updates: "Download DMG" could offer an older version** — it now always fetches the latest release, and the update check refreshes every 5 minutes.

## [1.4.7.2] - 2026-11-24

### Fixed
- **First-run setup: starter channels were greyed out** — the optional Movies / Music Videos / Saturday Morning Kids / Greatest Sports starter channels (9101–9104) are now included and selectable.
- **First-run setup: LaunchAgent install errors** — failures now show a short plain-language message, with technical details tucked under "Show details".
- **In-app update now also refreshes the setup helper scripts**, so "Install LaunchAgents" works after updating.

## [1.4.7.1] - 2026-11-24

### Fixed
- **Update process fixed** — Settings → Updates → "Agree and update" (in the Web UI and the macOS app) failed with a server error and never started. The update now runs: pre-update backup, apply, restart, then a "server is back up" banner. If you are on 1.4.7 and the button fails, install this DMG manually once; later updates work in-app.

## [1.4.7] - 2026-11-24

### Added
- **First-run setup** — SetupDone marker, in-app / WebUI setup (port, YouTube & Archive.org sign-in, optional MCP), factory reset.
- **macOS app Web UI tab** — Administer via embedded WebUI or native Admin hub; Settings → Updates with release notes and DMG download.
- **Channel Creator MCP v2** — Guided 11-tool profile, Streamable HTTP on port 8411 with bearer/OAuth/dual (Cloudflare Access) auth, host and remote setup scripts, and end-to-end rehearsal. Wiki-first: [Channel Creator MCP](https://github.com/roto31/StreamTV/wiki/Channel-Creator-MCP), [host wiring](https://github.com/roto31/StreamTV/wiki/Channel-Creator-MCP-Host-Wiring), [auth](https://github.com/roto31/StreamTV/wiki/Channel-Creator-MCP-Auth) (same content also under `docs/guides/`).
- **Channel Creator MCP one-liner** — `curl -fsSL https://raw.githubusercontent.com/roto31/StreamTV/main/scripts/install_channel_creator_mcp.sh | bash` clones the public repo and runs interactive host wiring.
- **Core dependency freshness check** — operator script verifies yt-dlp minimum version, YouTube player-client policy, and FFmpeg presence so sudden YouTube breakages from stale extractors are caught early.
- **Plex Live TV AAC codec check (first-run)** — when Plex Media Server is installed, setup verifies external AAC decoder packs under Plex’s Application Support Codecs folder and blocks finish until they are present (with retry). Operator scripts can trigger Plex’s on-demand download or copy from a healthy same-build host.
- **First-run production bootstrap** — optional install of the macOS LaunchAgent for the StreamTV server, weekly yt-dlp updater, and install-location choice (standard app support vs advanced existing folder). Optional sample channel packs may be offered in the product build.

### Fixed
- **YouTube playback 403 on some VODs** — player client policy now prefers `visionos` (then `web_safari`, `web_embedded`); yt-dlp minimum version raised to 2026.8.19.
- **YouTube / Archive.org Sign In** blank Internal Server Error in the macOS app when the server runs from Application Support.

### Changed
- **Docs / Wiki** — ChatGPT remote access is no longer “deferred”; indexes and diagrams cover stdio local hosts and tunneled `:8411` for ChatGPT / Claude web.

## [1.4.6] - 2026-11-22

### Added
- **WebUI redesign** — Modern design system (self-hosted fonts, Lucide SVG icons, light/dark tokens), rebuilt application shell, and restyled Channel Builder. WCAG 2.2 AA focus and contrast.
- **WebUI platform polish** — Web app manifest, theme-color metas, View Transitions, safe-area / `dvh` layout, sticky table headers, and page-aware global search with live result announcements.
- **Installer app** — Notarized DMG embeds the Channel Builder SPA so `/builder` works out of the box.

### Fixed
- Shell helpers (`authenticatedFetch`, `registerActions`, `whenDomReady`) load before page scripts.
- Duplicate search field IDs between the header and Media/Playlists/Playouts pages.
- Dark-mode form and button contrast below WCAG AA.

## [1.4.5] - 2026-11-22

### Added
- **Product scope** — Documented macOS-only core: Archive.org + YouTube Builder, YAML schedules, remux at source resolution, optional Channel Creator MCP.
- **Public demo pack** — Example channel 101 (Big Buck Bunny) + schedule template and a 15-minute first-channel guide.
- **Transcoding hub** — Settings groups global FFmpeg and optional channel profiles.

### Changed
- **Schedules API** — Creating or editing schedule *items* via `/api/schedule-items` returns **410**; edit `schedules/{n}.yml` on disk instead.
- **NOTICE** — Acknowledgments for ErsatzTV Legacy and Tunarr (zlib); StreamTV does not vendor their source.
- **Documentation / Wiki** — Implementation page rewritten for current integrations; schedule create/edit docs match read-only UI and API 410.
- **Tunarr proxy** — Status endpoint only; library browse routes removed.
- **Swagger `/docs`** — Works with Content-Security-Policy (exact `/docs` and `/redoc`).
- **Browser preview** — `/player` uses mpegts.js (MPEG-TS), not HLS-primary.

### Fixed
- **Channel Builder guide titles** — Archive.org percent-encoded filename stems are decoded before YAML/XMLTV so Plex guide cells show human-readable titles.
- **Channel Builder Archive runtimes** — Download URLs resolve real durations into schedule/XMLTV so the guide matches what is on air; build refuses Archive items without a runtime.

### Removed
- **Linux packaging** — StreamTV is macOS-only; Linux installer overlay and Linux fork documentation removed.
- **Watermarks and Resolutions settings** — Retired; remux keeps source resolution; clients scale.
- **PBS authentication UI** — Retired (DRM / unsupported for new channels).

## [1.4.4] - 2026-11-22

### Added
- **Application icon** — Official StreamTV macOS / web mark: wood-cabinet CRT with archival film strip + play/stream pane (favicon included).

## [1.4.3] - 2026-11-21

### Added
- **Channel Creator MCP** — Optional stdio MCP (`mcp_streamtv` + optional `mcp_archive_org`) for natural-language channel creation via Builder + soft-deploy tools. Full signal-path diagrams (create → import → HDHomeRun tune), intake UX, and tool catalog — see [Channel Creator MCP](docs/guides/CHANNEL_CREATOR_MCP.md) and wiki [Channel-Creator-MCP](https://github.com/roto31/StreamTV/wiki/Channel-Creator-MCP).
- **MCP host wiring guide** — Step-by-step configs and diagrams for **Cursor**, **VS Code** (Continue/Cline), **Claude Desktop**, **local models** (Qwen3 32B / Llama 3.3 70B / Qwen3 8B), and **ChatGPT** (deferred HTTPS bridge) — see [Host wiring](docs/guides/CHANNEL_CREATOR_MCP_HOST_WIRING.md).
- **Channel Creator MCP setup script** — Optional interactive installer (`scripts/setup_channel_creator_mcp.sh`) prompts for platform and apply/dry-run/emit mode, then wires that host only.
- **Archive.org URL guard for MCP** — `builder_add_links` rejects `*.ia.mp4` derivative URLs; agents must use canonical `…/download/<id>/<file>.mp4`.

### Changed
- **Channel Builder** — First-party sources are **Archive.org** and **YouTube** only.
- **Schedules** — Web create/edit removed; Schedules page is a read-only inventory of on-disk `schedules/{n}.yml` (playout + guide authority). Create/update schedule API returns 410.
- **Collections UI** — Manual/Smart/Multi Collections page and `/api/collections` retired; use Playlists + Builder + Import.
- **AI Recovery** — Foundation Models / Ollama / AutoHealer operator surface retired; ops healing remains scripts only.
- **Web UI** — Restored CSP-safe button actions across operator pages; Playouts table layout fixed.

### Removed
- **Disabled / orphan inventory** — Retired unused channel packs and schedule YAML that had no matching enabled channel so Schedules inventory matches the live lineup.

### Fixed
- **Release gate** — Builder sources API test matches Archive.org + YouTube only.

### Docs
- Public docs and GitHub wiki refreshed for the core trim, Channel Creator MCP guides, and tip **1.4.3**.

## [1.4.2] - 2026-11-19

### Fixed
- **macOS release packaging** — Signed DMG publish continues when Apple’s notary service returns a transient error on the disk image after the app itself is already notarized.

## [1.4.1] - 2026-11-19

### Added
- **In-browser `/player` preview** — Channel preview uses mpegts.js against a remuxed live TS feed, with mid-join keyframe wait and a VLC open handoff. Plex / HDHomeRun tuning paths are unchanged.
- **Vintage holiday channel packs** — New Year's (**1201**), Valentine's (**214**), Easter (**401**), Fourth of July (**704**), Halloween (**1031**), Thanksgiving (**1128**), plus Kids Christmas (**1225**), each with matching mid-century guide icons.
- **Plex Live TV video hold** — Cold start and mid-show gaps send a real H.264+AAC placeholder instead of empty keepalive packets so Apple TV is less likely to bounce to the guide — see [Plex video hold](docs/guides/PLEX_VIDEO_HOLD.md).
- **Channel 1954.1 — Godzilla Movies** — 30 Godzilla films from Archive.org in release-year order (1954–2004), with a channel guide icon. Guide listings use the movie title only. Disney Anthology remains channel 1954.
- **Optional offline English burn for Archive.org** — Inventory checks every audio track for English first; optional idle burn tooling remains for rare titles without embedded English — see [StreamTV + Tunarr hybrid](docs/guides/STREAMTV_TUNARR_HYBRID.md).
- **Optional Tunarr library export** — Export ready Archive.org cache files to a separate folder for Tunarr Local Media (does not change live TV) — see [StreamTV + Tunarr hybrid](docs/guides/STREAMTV_TUNARR_HYBRID.md).

### Fixed
- **Channel 1989 guide titles** — Humanized Archive.org filename stems into readable guide titles (URLs / stream ids unchanged).
- **YouTube wait-phase hold** — Default YouTube hold wrap is off to avoid cold-cache black/spinner; on-tune YouTube wait capped at **60s**; native re-hold remains opt-in. See [Plex video hold](docs/guides/PLEX_VIDEO_HOLD.md).
- **TunarrRAM / Live TV black screen** — Universal TunarrRAM watchdog every 60 s (45% / **1.7 GiB** hard ceiling / 300 Mi free); YouTube full-cache under that ceiling; see [TunarrRAM recovery](docs/guides/TUNARRRAM_PLAYOUT_RECOVERY.md).
- **Video hold / return-to-guide** — YouTube full-cache channels get a wait-phase H.264+AAC hold on tune; Archive stays unwrapped. See [Plex video hold](docs/guides/PLEX_VIDEO_HOLD.md).
- **RAM cache download race** — YouTube full-cache prefetch pauses before the RAM disk is full and only downloads one file at a time — see [TunarrRAM recovery](docs/guides/TUNARRRAM_PLAYOUT_RECOVERY.md).
- **Godzilla English overlay stall warnings** — Live subtitle overlay no longer logs false “FFmpeg stalled” warnings while video is still flowing — see [FFmpeg stall / keepalive](docs/guides/FFMPEG_STALL_KEEPALIVE.md).
- **Softer channel restarts** — Operators can refresh Live TV channel streams without restarting the whole StreamTV server — see [Soft deploy](docs/guides/SOFT_DEPLOY.md).
- **Phase 2 ops** — Cache waits for the RAM disk if it is missing at boot; SSDP “no route” spam is quieted; a small resource log samples CPU/memory; Nature (1982) removed from the Live TV lineup until guide lag is fixed.
- **YouTube music mid-stream 403s** — With TunarrRAM headroom and the free-space healer running, YouTube items download to local cache before playout again — see [TunarrRAM recovery](docs/guides/TUNARRRAM_PLAYOUT_RECOVERY.md).
- **macOS app no longer fights the production server** — Opening StreamTV.app while the LaunchAgent is already on port 8410 attaches to that server instead of spawning a second copy.
- **Safer stalled-FFmpeg healer** — External stall cleanup no longer kills subtitle overlay encodes that are quietly busy (e.g. Godzilla English burn). See [FFmpeg stall / keepalive](docs/guides/FFMPEG_STALL_KEEPALIVE.md).
- **Weekly yt-dlp update** — Production restarts only when yt-dlp actually upgrades, not on every Sunday “already up to date” run.
- **Foundation Models page** — Missing template returns a clear unavailable page instead of a blank server error.
- **Plex Live TV guide reload** — Operator defaults and auto-reload now track the current Plex DVR id after PMS recreates the Live TV source (stale ids returned 404). See [Plex Live TV recovery](docs/plex/PLEX_LIVE_TV_RECOVERY.md).
- **Auto-healer safety** — Automated fixes no longer rewrite streaming core files; repeated applies for the same error pattern are capped — see [Auto-Healer](docs/AUTO_HEALER.md).
- **Stuck cache downloads** — Dead or auth-blocked YouTube/Archive.org downloads no longer retry forever on every tune; use the cache retry API after fixing cookies or removing bad items.
- **Godzilla channel guide titles** — Each listing shows the movie name only, not the channel name as a series.

### Changed
- **Godzilla Live TV English subtitles** — Channel 1954.1 again overlays embedded English DVD subtitles on Japanese-audio prints, with hardenings so Plex is less likely to stall — see [FFmpeg profiles](docs/guides/FFMPEG_PROFILES.md).
- **Optional Tunarr library prefetch** — Download full Archive.org files into the Tunarr library folder from StreamTV channel inventory; re-scan Tunarr after apply — see [StreamTV + Tunarr hybrid](docs/guides/STREAMTV_TUNARR_HYBRID.md).

### Docs
- Operator guides for FFmpeg stall heal, LoudNorm CPU monitor, and TunarrRAM heal scripts match the in-repo tooling — see [FFmpeg stall](docs/guides/FFMPEG_STALL_KEEPALIVE.md), [LoudNorm](docs/guides/LOUDNORM_FLEET_AUDIO.md), [TunarrRAM](docs/guides/TUNARRRAM_PLAYOUT_RECOVERY.md).
- Soft stream refresh without a full server restart — see [Soft deploy](docs/guides/SOFT_DEPLOY.md).
- GitHub Actions on **push to main** no longer fail only because macOS runtime files changed; **pull requests** still block those paths.

## [1.4.0] - 2026-09-19

See [macOS release CI](docs/macos-release-ci.md)

### Added
- **Automatic backup and restore** — Portable zip of settings, channels, schedules, and secrets; Settings → Backup & Restore; optional first-launch restore — see [Backup and restore](docs/guides/BACKUP_RESTORE.md).
- **Optional on-device AI recovery** — On macOS 26+, choose Apple Foundation Models (or Ollama / no AI) for classifying issues and suggesting approved heals — see [Foundation Models recovery](docs/guides/FOUNDATION_MODELS_RECOVERY.md).

### Changed
- **Fleet audio leveling** — Software FFmpeg profile loudness normalization for more consistent channel volume — see [LoudNorm fleet audio](docs/guides/LOUDNORM_FLEET_AUDIO.md).
- **RAM-cache recovery guidance** — Operator docs for keeping YouTube cache disk from filling and recovering playout — see [TunarrRAM playout recovery](docs/guides/TUNARRRAM_PLAYOUT_RECOVERY.md).

### Fixed
- **Plex Live TV guide reload** — Operator health scripts default to the current StreamTV DVR id after PMS upgrades — see [Plex Live TV recovery](docs/plex/PLEX_LIVE_TV_RECOVERY.md).
- **Idle playout / guide alignment** — Continuous channels catch up when untuned; class-A guide slots no longer stretch for hours when playout lags — see [EPG sync classes](docs/guides/EPG_SYNC_CLASSES.md).
- **macOS first-launch / Run Setup** — Bundled `PYTHONPATH` and Homebrew `python3.12` shim detection on Apple Silicon.
- **CI release gate** — Full pytest suite is a hard gate on GitHub-hosted macOS release builds.

## [1.3.6] - 2026-07-18

See [macOS release CI](docs/macos-release-ci.md)

### Fixed
- **First-launch Run Setup** — Setup no longer fails silently on a new Mac when the server log file is missing; Homebrew Python 3.10+ is detected; setup errors stay visible until resolved.

## [1.3.5] - 2026-07-18

See [Channel Builder](docs/channel-builder.md) · [Metadata enrichment](docs/guides/METADATA_ENRICHMENT.md) · [macOS release CI](docs/macos-release-ci.md)

### Added
- **Channel Builder — post-build metadata enrichment** — After import, optional TVDB/TVMaze/TMDB enrichment for guide titles and plots (series name/year fields; soft-skip if credentials missing).
- **Channel Builder — TVMaze or TVDB credentials** — Choose TVMaze (free-account username + dashboard API key), TVDB (API key), or both; keys saved in operator config via Builder auth endpoints.
- **Builder metadata auth tests** — Provider readiness checks and mocked TVMaze/TVDB auth route coverage.

### Fixed
- **TVDB episode pagination** — Long series episode lists follow TVDB v4 `links.next` so enrichment resolves past the first page.

## [1.3.4] - 2026-07-18

### Fixed
- **Archive.org VOD playout loop** — Archive HTTP inputs no longer reconnect at EOF, so continuous channels (e.g. Magnum) advance to the next episode instead of looping one VOD for hours.

### Build/CI
- Signed and notarized macOS DMG releases build on GitHub-hosted macOS runners.

## [1.3.3] - 2026-07-17

See [Metadata enrichment](docs/guides/METADATA_ENRICHMENT.md) · [EPG sync classes](docs/guides/EPG_SYNC_CLASSES.md) · [Architecture](ARCHITECTURE.md) · [Channel Builder](docs/channel-builder.md)

### Added
- **Metadata enrichment tooling** — Playback-safe enrichment (`--meta-only`, never writes duration); TVDB/TVMaze/TMDB merge into nested `meta_data`; Sesame Street / Mister Rogers SxxExx retitle helpers; stratified guide accuracy audit scripts
- **EPG sync classes (A/B/C)** — Channel-level guide vs playout policy; class-A playout-authoritative XML and Plex guide reload helpers
- **Channel Builder PBS improvements** — Full-episode filter, Passport/DRM public-stream filter, higher PBS show expand cap, cookies import for PBS resolve
- **Documentation** — Operator guides indexed; Mermaid diagrams for enrichment and EPG sync in Architecture; wiki/docs indexes updated for 1.3.3

### Changed
- YouTube RAM full-cache default off under buffer mode (prefer CDN-direct to avoid disk-full playback errors)
- Plex guide reload cooldowns and class-A item-boundary reload behavior

### Fixed
- Guide metadata false matches when Archive season/episode labels disagree with TVDB (re-match by air date where titles carry dates)
- Nested Archive + enrichment metadata merge (providers no longer wipe Archive fields)
- Plex guide reload when DVR id changes after PMS upgrades
- PBS VOD preferring FFmpeg-playable clear HLS over DRM manifests; Playwright season harvest for PBS show expand
- EPG live-air anchoring so Plex “now” matches continuous playout

## [1.3.2] - 2026-07-12

### Added
- **Core platform closure** — PBS metadata on media create; configurable boot-defer channel lists; bedrock backup script; media PATCH API; import path admin gate; HDHR/IPTV/builder HTTP tests; operator quickstart and source guides
- **WebGUI** — authenticated API fetch on core pages; media library add/delete/edit; dashboard PBS auth status; Resources nav links (Guides, Builder, Import)
- **Channel Builder** — block build when PBS show URLs need expansion
- **Tunarr integration API** — media sources, search, custom shows proxy
- **Plex hybrid UI** — Tunarr-first library browse with native fallback
- **Channel Builder v2** — source-first wizard with PBS show expander
- **tvOS scaffold** — channel list, EPG, HLS playback executable

### Changed
- HDHomeRun returns 503 when playout engine is still starting (no silent fallback tune)
- Playout API uses generic channel metadata (removed hard-coded channel blurbs)
- Documentation routes for Channel Builder and Import vs Builder guides

### Fixed
- Broken `/docs/channel_builder` link from Import page
- Import API cleanup (unused imports)

## [1.3.1] - 2026-07-11

See [macOS tree protection](docs/MACOS_TREE_PROTECTION.md) · [Linux repo workflow](docs/LINUX_REPO_WORKFLOW.md)

### Added
- Forbidden-path guards and Linux export tooling
- Public sanitization gates for release sync

### Removed
- Legacy non-macOS/non-Linux platform packaging overlays

## [1.3.0] - 2026-07-11

See [Docs index](docs/README.md) · [Plex Live TV recovery](docs/plex/PLEX_LIVE_TV_RECOVERY.md)

### Added
- YouTube RAM full-cache for smoother VOD playback in buffer mode
- Olympics time-capsule channel schedules (1980–1998)
- Playout reset at arbitrary item for troubleshooting

### Changed
- CI and test determinism improvements for macOS releases
- Plex guide reload fixes when playout resumes behind wall-clock

### Fixed
- Plex guide stale after playout resume
- EPG / playout lag on continuous channels
- YouTube RAM-cache audio-only transcode regression
