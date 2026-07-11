# Changelog

All notable user-facing changes to StreamTV releases.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Documentation

- [Docs index](docs/README.md)
- [Wiki home](https://github.com/roto31/StreamTV/wiki)

## [Unreleased]

### Removed
- Windows and container distribution targets; macOS and Linux only under MIT.

## [1.3.0] - 2026-07-11

See [Docs index](docs/README.md) · [Plex Live TV recovery](docs/plex/PLEX_LIVE_TV_RECOVERY.md)

### Added
- YouTube RAM full-cache for smoother VOD playback in buffer mode
- Olympics time-capsule channel schedules (1980–1998)
- Playout reset at arbitrary item for troubleshooting
- Tunarr-style RAM cache eviction after playout advances

### Changed
- CI and test determinism improvements for macOS releases
- Plex guide reload fixes when playout resumes behind wall-clock

### Fixed
- Plex guide stale after playout resume
- EPG / playout lag on continuous channels
- YouTube RAM-cache audio-only transcode regression
- XMLTV EPG generation stability

## [1.0.0] - 2026-01-01

### Added
- HDHomeRun emulation for Plex, Emby, and Jellyfin
- YAML schedule system
- YouTube and Archive.org streaming adapters
- macOS signed and notarized application releases

---

[Unreleased]: https://github.com/roto31/StreamTV/compare/v1.3.0...HEAD
[1.3.0]: https://github.com/roto31/StreamTV/releases/tag/v1.3.0
[1.0.0]: https://github.com/roto31/StreamTV/releases/tag/v1.0.0
