# StreamTV

[![Releases](https://img.shields.io/github/v/release/roto31/StreamTV)](https://github.com/roto31/StreamTV/releases)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**StreamTV** is a **macOS** IPTV streaming platform that creates TV channels from
**YouTube** and **Archive.org**. Stream directly to Plex, Emby, Jellyfin, and
HDHomeRun-compatible devices. Remux keeps source resolution; clients scale.

> **Source:** Canonical development is private [`roto31/StreamTV-source`](https://github.com/roto31/StreamTV-source).
> This public repo publishes **sanitized documentation**, the **GitHub Wiki**,
> **signed macOS releases**, and a **culled open-source tree** via
> `scripts/sync_public_code.sh` / `scripts/sync_public_docs.sh`. Fleet channel YAML,
> cookies, and secrets are never published — see [Sanitization policy](docs/SANITIZATION_POLICY.md).
> Scope: [Product scope](docs/PRODUCT_SCOPE.md).

## Features

- Direct streaming from YouTube and Archive.org (Channel Builder first-party sources)
- HDHomeRun emulation for Plex, Emby, and Jellyfin
- YAML schedules (`schedules/{n}.yml`); M3U + XMLTV EPG (web schedule create/edit removed)
- In-browser `/player` preview (**mpegts.js** live TS) with VLC handoff
- Soft per-channel stream restart without full server kickstart
- Portable backup / restore (Settings + `/api/backup`)
- Ops healing via scripts; LoudNorm defaults **off**
- Optional [Channel Creator MCP](docs/guides/CHANNEL_CREATOR_MCP.md) for AI hosts
- Platform: **macOS** (signed DMG)

## Quick start

1. Download **v1.4.5** from [Releases](https://github.com/roto31/StreamTV/releases/tag/v1.4.5) (`StreamTV.1.4.5-macos.dmg`, signed + notarized)
2. Read the [Installation Guide](docs/wiki/Installation-Guide.md) and [Product scope](docs/PRODUCT_SCOPE.md)
3. Follow [First channel in 15 minutes](docs/guides/FIRST_CHANNEL_15_MIN.md) (public demo pack)

## Documentation

| Resource | Link |
|----------|------|
| Product scope | [docs/PRODUCT_SCOPE.md](docs/PRODUCT_SCOPE.md) |
| Docs index | [docs/README.md](docs/README.md) |
| Architecture (Mermaid) | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Browser `/player` preview | [docs/guides/PLAYER_PREVIEW.md](docs/guides/PLAYER_PREVIEW.md) |
| Channel Creator MCP | [docs/guides/CHANNEL_CREATOR_MCP.md](docs/guides/CHANNEL_CREATOR_MCP.md) |
| Sanitization policy | [docs/SANITIZATION_POLICY.md](docs/SANITIZATION_POLICY.md) |
| Wiki home | [GitHub Wiki](https://github.com/roto31/StreamTV/wiki) |

## Releases

Signed macOS builds are published on the [Releases](https://github.com/roto31/StreamTV/releases) page.

## License

MIT — see [LICENSE](LICENSE).
