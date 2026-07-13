# Changelog

All notable user-facing changes to StreamTV releases.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Documentation

- [Docs index](docs/README.md)
- [Wiki home](https://github.com/roto31/StreamTV/wiki)

## [Unreleased]

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
