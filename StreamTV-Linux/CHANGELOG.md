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
- GitHub Dependabot configuration for automated dependency monitoring
- Security response documentation (SECURITY_RESPONSE.md)
- Dependency security auditing tools (pip-audit, safety, pipdeptree)
- Automated dependency audit script (scripts/audit-dependencies.sh)
- Python 3.10+ migration guide (MIGRATION_PYTHON_3.10.md)
- Python version test script (scripts/test-python-version.sh)
- Development dependencies file (requirements-dev.txt)

### Fixed
- Enum conversion errors in channels and IPTV endpoints (HLS/TS)
- Browser playback compatibility - now uses HLS by default instead of MPEG-TS
- jsonschema dependency compatibility (updated to 4.25.1 with jsonschema-specifications 2024.10.1)
- Draft-04 schema support in jsonschema validation
- Security vulnerabilities in dependencies (54+ CVEs addressed)

### Changed
- **BREAKING**: Minimum Python version requirement upgraded from 3.8+ to 3.10+
- Player now prioritizes HLS streams for browser compatibility
- Updated jsonschema to 4.25.1 (from 4.23.0)
- Updated jsonschema-specifications to 2024.10.1 (from 2023.12.1)
- All platform distributions synchronized with latest code changes
- **Dependencies upgraded to latest secure versions (Python 3.10+ compatible)**:
  - fastapi: 0.115.14 → 0.128.0 (requires Python 3.9+)
  - uvicorn: 0.32.1 → 0.40.0 (requires Python 3.10+)
  - pydantic: 2.9.2 → 2.12.5 (requires Python 3.9+)
  - pydantic-settings: 2.5.2 → 2.12.0 (requires Python 3.10+)
  - yt-dlp: >=2024.12.13,<2025.1.0 → >=2025.12.8 (requires Python 3.10+)
  - alembic: 1.13.2 → 1.17.2 (requires Python 3.10+)
  - python-multipart: 0.0.9 → 0.0.21 (requires Python 3.10+)
  - aiofiles: 24.1.0 → 25.1.0 (requires Python 3.9+)
  - sqlalchemy: 2.0.36 → 2.0.45 (latest)
  - httpx: 0.27.0 → 0.28.1 (latest)
  - lxml: 5.3.0 → 6.0.2 (latest)
  - jinja2: 3.1.4 → 3.1.6 (latest)
  - pyyaml: 6.0.2 → 6.0.3 (latest)
  - pytz: 2024.1 → 2025.2 (latest)
- Docker images updated to use Python 3.12-slim base image
- All installation scripts updated to require Python 3.10+
- StreamTVApp (macOS menu bar) updated to require Python 3.10+
- All documentation updated to reflect Python 3.10+ requirement

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
