# StreamTV

[![Releases](https://img.shields.io/github/v/release/roto31/StreamTV)](https://github.com/roto31/StreamTV/releases)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## StreamTV: Your own TV channels, without the storage bill

Drive prices are brutal right now, and you've already got a shelf of them
spinning. Meanwhile, the stuff you actually want to watch is sitting free on
**Archive.org** and **YouTube**: old network specials, vintage commercials,
classic sports, local stations from decades ago. Finding it is the problem.
You'd have to dig through two sites, with endless searches and dead ends, and
then you'd still have to download it all and find room for it.

**StreamTV** skips that. Describe the channel you want in plain language, like
"1980s Saturday morning cartoons with the original ads" or "Minnesota Twins
games, starting on the hour." The optional
[Channel Creator MCP](docs/guides/CHANNEL_CREATOR_MCP.md) installs in your AI
agent, IDE, or local LLM, so you can build channels just by talking. Prefer to
skip the MCP? The built-in channel builder lets you drop in links to individual
videos or whole collections, and it builds the channel for you.

Either way, StreamTV puts the content in order and runs it as a live channel
with a real guide. Plex, Emby, Jellyfin, and other HDHomeRun-compatible apps
see it as a normal tuner, so you tune in like any other channel.

There's no library to build and no drives to buy. Your hoarder instincts still
get used: you curate, you organize, and you decide what's worth watching. You
just don't have to keep every file.

### Why it's different

- **Skip the search.** Describe what you want, or paste links you've already found.
- **Two ways to build.** Use the Channel Creator MCP in your AI tool, or paste links into the built-in channel builder.
- **Real channel feel.** Scheduled programming, a guide, period commercial breaks.
- **Works with what you run.** Plex, Emby, Jellyfin, anything that speaks HDHomeRun.

**StreamTV** is a **macOS** IPTV platform (signed + notarized DMG). Remux keeps
source resolution; clients scale for display.

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

1. Download **v1.4.7** from [Releases](https://github.com/roto31/StreamTV/releases/tag/v1.4.7) (`StreamTV.1.4.7-macos.dmg`, signed + notarized)
2. Read the [Installation Guide](docs/wiki/Installation-Guide.md), [First-run setup](https://github.com/roto31/StreamTV/wiki/First-Run-Setup), and [Product scope](docs/PRODUCT_SCOPE.md)
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
