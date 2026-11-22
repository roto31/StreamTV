# StreamTV

[![Releases](https://img.shields.io/github/v/release/roto31/StreamTV)](https://github.com/roto31/StreamTV/releases)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**StreamTV** is a cross-platform IPTV streaming platform that creates TV channels from online video sources like YouTube and Archive.org. Stream directly to Plex, Emby, Jellyfin, and HDHomeRun-compatible devices without requiring local media storage.

> **Source:** Canonical development is private [`roto31/StreamTV-source`](https://github.com/roto31/StreamTV-source). This public repo publishes **sanitized documentation**, the **GitHub Wiki**, **signed macOS releases**, and a **culled copy of `streamtv/`** (plus tests/examples) via `scripts/sync_public_code.sh` / `scripts/sync_public_docs.sh`. Channel inventory YAML, schedules, cookies, and secrets are never published — see [Sanitization policy](docs/SANITIZATION_POLICY.md).

## Features

- Direct streaming from YouTube and Archive.org (Channel Builder first-party sources)
- HDHomeRun emulation for Plex, Emby, and Jellyfin
- YAML schedules (`schedules/{n}.yml`) with commercial breaks; M3U + XMLTV EPG (web schedule create/edit removed)
- In-browser `/player` preview (mpegts.js live TS) with VLC handoff
- Soft per-channel stream restart without full server kickstart
- Plex Live TV video hold (H.264+AAC placeholder; YouTube wait-phase opt-in)
- Portable backup / restore (Settings + `/api/backup`)
- Ops healing via scripts (stalled FFmpeg, TunarrRAM, soft deploy); LoudNorm defaults **off**; AI Recovery retired
- Cross-platform: macOS (signed DMG) and Linux (community ports welcome)
- Passkey and OAuth support for YouTube

## Quick start

1. Download the latest [macOS release](https://github.com/roto31/StreamTV/releases) (current tip: **v1.4.3**)
2. Read the [Installation Guide](docs/wiki/Installation-Guide.md)
3. Follow the [Quick Start](docs/installation/QUICK_START.md) in docs

## Documentation

| Resource | Link |
|----------|------|
| Docs index | [docs/README.md](docs/README.md) |
| Complete topic map | [docs/INDEX.md](docs/INDEX.md) |
| Wiki home | [GitHub Wiki](https://github.com/roto31/StreamTV/wiki) |
| Architecture (Mermaid) | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Browser `/player` preview | [docs/guides/PLAYER_PREVIEW.md](docs/guides/PLAYER_PREVIEW.md) |
| Soft deploy | [docs/guides/SOFT_DEPLOY.md](docs/guides/SOFT_DEPLOY.md) |
| Plex video hold | [docs/guides/PLEX_VIDEO_HOLD.md](docs/guides/PLEX_VIDEO_HOLD.md) |
| Backup and restore | [docs/guides/BACKUP_RESTORE.md](docs/guides/BACKUP_RESTORE.md) |
| Metadata enrichment | [docs/guides/METADATA_ENRICHMENT.md](docs/guides/METADATA_ENRICHMENT.md) |
| EPG sync classes | [docs/guides/EPG_SYNC_CLASSES.md](docs/guides/EPG_SYNC_CLASSES.md) |
| Channel Builder | [docs/channel-builder.md](docs/channel-builder.md) |
| Beginner guide | [docs/BEGINNER_GUIDE.md](docs/BEGINNER_GUIDE.md) |
| API reference | [docs/API.md](docs/API.md) |
| Plex integration | [docs/wiki/Plex-Integration.md](docs/wiki/Plex-Integration.md) |
| Troubleshooting | [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) |
| Sanitization policy | [docs/SANITIZATION_POLICY.md](docs/SANITIZATION_POLICY.md) |

### Platform guides (wiki)

- [macOS](https://github.com/roto31/StreamTV/wiki/macOS)
- [Linux](https://github.com/roto31/StreamTV/wiki/Linux)

## Releases

Signed macOS builds are published on the [Releases](https://github.com/roto31/StreamTV/releases) page.

## Support

- [Wiki — Troubleshooting](https://github.com/roto31/StreamTV/wiki/Troubleshooting)
- [Report an issue](https://github.com/roto31/StreamTV/issues)

## License

MIT — see [LICENSE](LICENSE).
