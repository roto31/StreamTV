# Changelog

All notable changes to StreamTV will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive GitHub Wiki documentation
- Issue templates for bugs and feature requests
- Pull request template
- Contributing guidelines
- Security policy
- HLS-first player implementation for browser compatibility
- Enum conversion fixes for database compatibility across all platforms
- Cross-platform synchronization script for StreamTVApp

### Fixed
- Enum conversion errors in channels and IPTV endpoints (HLS/TS)
- Browser playback compatibility - now uses HLS by default instead of MPEG-TS
- jsonschema dependency compatibility (updated to 4.25.1 with jsonschema-specifications 2024.10.1)
- Draft-04 schema support in jsonschema validation

### Changed
- Player now prioritizes HLS streams for browser compatibility
- Updated jsonschema to 4.25.1 (from 4.23.0)
- Updated jsonschema-specifications to 2024.10.1 (from 2023.12.1)
- All platform distributions synchronized with latest code changes

## [1.0.0] - 2025-01-XX

### Added
- Initial release with all platform distributions
- macOS distribution with installer and launchers
- Windows distribution with PowerShell scripts
- Linux distribution with systemd integration
- Docker container distribution
- Docker Compose multi-service setup
- Kubernetes manifests
- Podman rootless container support
- Complete documentation for all platforms
- GitHub Wiki with comprehensive guides
- Install scripts for all platforms
- Verification scripts
- Archive.org collection parser
- YouTube OAuth authentication
- Passkey authentication support
- HDHomeRun emulation
- IPTV M3U and XMLTV EPG support
- Plex Media Server integration
- Advanced scheduling with YAML
- Web-based management interface
- RESTful API
- Logging system
- Troubleshooting tools

### Features
- Direct streaming from YouTube and Archive.org
- No local media storage required
- Cross-platform support (macOS, Windows, Linux)
- Container orchestration support
- Multiple authentication methods
- Comprehensive error handling
- Auto-healing system
- Metadata extraction
- Channel management
- Playlist creation
- Schedule-based playout

## [0.1.0] - Pre-release

### Added
- Initial development version
- Core streaming functionality
- Basic channel management
- YouTube adapter
- Archive.org adapter

---

[Unreleased]: https://github.com/roto31/StreamTV/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/roto31/StreamTV/releases/tag/v1.0.0
[0.1.0]: https://github.com/roto31/StreamTV/releases/tag/v0.1.0
