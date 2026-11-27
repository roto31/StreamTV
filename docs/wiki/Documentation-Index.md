# StreamTV Documentation Index

Complete guide to StreamTV documentation, organized by topic.

**Version:** 1.4.7 · **Updated:** 2026-11-24  
Sync this wiki with `bash scripts/sync_public_docs.sh --apply --wiki` from StreamTV-source.

**Platform notes:** Builder = Archive.org + YouTube; Schedules UI read-only (`schedules/{n}.yml`); Collections UI and AI Recovery retired; first-run includes install location, optional samples, Plex AAC gate, yt-dlp freshness.

> Deep docs live in the public repo tree. Prefer **absolute links** below (GitHub Wiki cannot resolve `../guides/`).

---

## First-run / macOS app

- Wiki: [First-Run-Setup](First-Run-Setup) · [Production-Bootstrap](Production-Bootstrap) · [SetupDone-and-Factory-Reset](SetupDone-and-Factory-Reset) · [Source-Auth-YouTube-Archive](Source-Auth-YouTube-Archive)
- Wiki: [Core-Dependency-Freshness](Core-Dependency-Freshness) · [Plex-Playback-Error-Host](Plex-Playback-Error-Host) · [Channel-Pack-GitOps](Channel-Pack-GitOps)
- Wiki: [macOS-App-WebUI-Sidebar](macOS-App-WebUI-Sidebar) · [Native-Admin-Parity](Native-Admin-Parity) · [In-App-Updates](In-App-Updates)

## Quick start

- [Quick Start Guide](https://github.com/roto31/StreamTV/blob/main/docs/installation/QUICK_START.md)
- [Beginner Guide](https://github.com/roto31/StreamTV/blob/main/docs/BEGINNER_GUIDE.md)
- [Installation Guide](https://github.com/roto31/StreamTV/blob/main/docs/INSTALLATION.md) · Wiki: [Installation-Guide](Installation-Guide)
- [macOS releases (DMG)](https://github.com/roto31/StreamTV/releases) — preferred install path

---

## Architecture diagrams (canonical)

Mermaid (system, HDHomeRun tune, import, Archive URL, MPEG-TS, enrichment, EPG):

- **[ARCHITECTURE.md](https://github.com/roto31/StreamTV/blob/main/ARCHITECTURE.md)**

Wiki Expert/Intermediate ASCII diagrams are summaries only.

---

## Core documentation

- [Docs hub](https://github.com/roto31/StreamTV/blob/main/docs/README.md)
- [Full INDEX](https://github.com/roto31/StreamTV/blob/main/docs/INDEX.md)
- [API](https://github.com/roto31/StreamTV/blob/main/docs/API.md) · Wiki: [API-Reference](API-Reference)
- [Troubleshooting](https://github.com/roto31/StreamTV/blob/main/docs/TROUBLESHOOTING.md) · Wiki: [Troubleshooting](Troubleshooting)
- [YAML Validation](https://github.com/roto31/StreamTV/blob/main/docs/YAML_VALIDATION.md)
- [Beginner](https://github.com/roto31/StreamTV/blob/main/docs/BEGINNER_GUIDE.md) · [Intermediate](https://github.com/roto31/StreamTV/blob/main/docs/INTERMEDIATE_GUIDE.md) · [Expert](https://github.com/roto31/StreamTV/blob/main/docs/EXPERT_GUIDE.md)

---

## Operator guides (1.4.x)

| Guide | Link |
|-------|------|
| Core operator quickstart | [CORE_OPERATOR_QUICKSTART.md](https://github.com/roto31/StreamTV/blob/main/docs/guides/CORE_OPERATOR_QUICKSTART.md) |
| First-run / SetupDone | wiki [First-Run-Setup](First-Run-Setup) · [PRODUCTION_BOOTSTRAP](https://github.com/roto31/StreamTV/blob/main/docs/guides/PRODUCTION_BOOTSTRAP_UNIVERSAL.md) |
| Core dependency freshness | wiki [Core-Dependency-Freshness](Core-Dependency-Freshness) · [guide](https://github.com/roto31/StreamTV/blob/main/docs/guides/CORE_DEPENDENCY_FRESHNESS.md) |
| Plex Playback Error host | wiki [Plex-Playback-Error-Host](Plex-Playback-Error-Host) · [guide](https://github.com/roto31/StreamTV/blob/main/docs/guides/PLEX_PLAYBACK_ERROR_HOST.md) |
| Channel pack GitOps | wiki [Channel-Pack-GitOps](Channel-Pack-GitOps) · [guide](https://github.com/roto31/StreamTV/blob/main/docs/guides/CHANNEL_PACK_GITOPS.md) |
| Browser `/player` preview | [PLAYER_PREVIEW.md](https://github.com/roto31/StreamTV/blob/main/docs/guides/PLAYER_PREVIEW.md) |
| Soft deploy | [SOFT_DEPLOY.md](https://github.com/roto31/StreamTV/blob/main/docs/guides/SOFT_DEPLOY.md) |
| Plex video hold | [PLEX_VIDEO_HOLD.md](https://github.com/roto31/StreamTV/blob/main/docs/guides/PLEX_VIDEO_HOLD.md) |
| TunarrRAM recovery | [TUNARRRAM_PLAYOUT_RECOVERY.md](https://github.com/roto31/StreamTV/blob/main/docs/guides/TUNARRRAM_PLAYOUT_RECOVERY.md) |
| Fleet probe protocol | [FLEET_PROBE_PROTOCOL.md](https://github.com/roto31/StreamTV/blob/main/docs/guides/FLEET_PROBE_PROTOCOL.md) |
| Backup and restore | [BACKUP_RESTORE.md](https://github.com/roto31/StreamTV/blob/main/docs/guides/BACKUP_RESTORE.md) |
| Ops healing (scripts only) | [FFMPEG_STALL](https://github.com/roto31/StreamTV/blob/main/docs/guides/FFMPEG_STALL_KEEPALIVE.md) · [TunarrRAM](https://github.com/roto31/StreamTV/blob/main/docs/guides/TUNARRRAM_PLAYOUT_RECOVERY.md) |
| LoudNorm (default **off**) | [LOUDNORM_FLEET_AUDIO.md](https://github.com/roto31/StreamTV/blob/main/docs/guides/LOUDNORM_FLEET_AUDIO.md) |
| FFmpeg stall / keepalive | [FFMPEG_STALL_KEEPALIVE.md](https://github.com/roto31/StreamTV/blob/main/docs/guides/FFMPEG_STALL_KEEPALIVE.md) |
| Archive probe retry + keepalive heal (41b) | [ARCHIVE_PROBE_RETRY_KEEPALIVE.md](https://github.com/roto31/StreamTV/blob/main/docs/guides/ARCHIVE_PROBE_RETRY_KEEPALIVE.md) · wiki [Streaming-Resilience-Ops](Streaming-Resilience-Ops) |
| Channel Builder | [channel-builder.md](https://github.com/roto31/StreamTV/blob/main/docs/channel-builder.md) |
| Channel Creator MCP v2 (guided + signal-path diagrams) | wiki [Channel-Creator-MCP](Channel-Creator-MCP) · [guides/CHANNEL_CREATOR_MCP.md](https://github.com/roto31/StreamTV/blob/main/docs/guides/CHANNEL_CREATOR_MCP.md) |
| Channel Creator MCP host wiring | wiki [Channel-Creator-MCP-Host-Wiring](Channel-Creator-MCP-Host-Wiring) · [guides/…](https://github.com/roto31/StreamTV/blob/main/docs/guides/CHANNEL_CREATOR_MCP_HOST_WIRING.md) |
| Channel Creator MCP HTTP auth | wiki [Channel-Creator-MCP-Auth](Channel-Creator-MCP-Auth) · [guides/…](https://github.com/roto31/StreamTV/blob/main/docs/guides/CHANNEL_CREATOR_MCP_AUTH.md) (`bearer` / `oauth` / `dual`) |
| Channel Creator MCP GitHub one-liner | [`install_channel_creator_mcp.sh`](https://github.com/roto31/StreamTV/blob/main/scripts/install_channel_creator_mcp.sh) — `curl -fsSL … \| bash` |
| Channel Creator MCP host / remote / e2e scripts | [`setup_channel_creator_mcp.sh`](https://github.com/roto31/StreamTV/blob/main/scripts/setup_channel_creator_mcp.sh) · [`channel_creator_mcp_hosts.zsh`](https://github.com/roto31/StreamTV/blob/main/scripts/channel_creator_mcp_hosts.zsh) · [`channel_creator_mcp_remote.zsh`](https://github.com/roto31/StreamTV/blob/main/scripts/channel_creator_mcp_remote.zsh) · [`channel_creator_e2e_rehearsal.zsh`](https://github.com/roto31/StreamTV/blob/main/scripts/channel_creator_e2e_rehearsal.zsh) |
| Import vs Builder | [IMPORT_VS_BUILDER.md](https://github.com/roto31/StreamTV/blob/main/docs/guides/IMPORT_VS_BUILDER.md) |
| Metadata enrichment | [METADATA_ENRICHMENT.md](https://github.com/roto31/StreamTV/blob/main/docs/guides/METADATA_ENRICHMENT.md) |
| EPG sync classes | [EPG_SYNC_CLASSES.md](https://github.com/roto31/StreamTV/blob/main/docs/guides/EPG_SYNC_CLASSES.md) |
| Archive.org operator | [ARCHIVE_ORG_OPERATOR.md](https://github.com/roto31/StreamTV/blob/main/docs/guides/ARCHIVE_ORG_OPERATOR.md) |
| FFmpeg profiles | [FFMPEG_PROFILES.md](https://github.com/roto31/StreamTV/blob/main/docs/guides/FFMPEG_PROFILES.md) |
| PBS (retired from Builder) | [PBS_PLAYWRIGHT.md](https://github.com/roto31/StreamTV/blob/main/docs/guides/PBS_PLAYWRIGHT.md) |
| YouTube geo-blocks | [YOUTUBE_GEO_BLOCKS.md](https://github.com/roto31/StreamTV/blob/main/docs/guides/YOUTUBE_GEO_BLOCKS.md) |
| Vimeo (retired from Builder) | [VIMEO_BEDROCK_GATE.md](https://github.com/roto31/StreamTV/blob/main/docs/guides/VIMEO_BEDROCK_GATE.md) |
| HDHomeRun | [HDHOMERUN.md](https://github.com/roto31/StreamTV/blob/main/docs/HDHOMERUN.md) |
| Schedules | [SCHEDULES.md](https://github.com/roto31/StreamTV/blob/main/docs/SCHEDULES.md) |
| Sanitization policy | [SANITIZATION_POLICY.md](https://github.com/roto31/StreamTV/blob/main/docs/SANITIZATION_POLICY.md) |

---

## Wiki pages (this wiki)

- [Home](Home) · [macOS](macOS)
- [First-Run-Setup](First-Run-Setup) · [Production-Bootstrap](Production-Bootstrap) · [SetupDone-and-Factory-Reset](SetupDone-and-Factory-Reset)
- [Core-Dependency-Freshness](Core-Dependency-Freshness) · [Plex-Playback-Error-Host](Plex-Playback-Error-Host) · [Channel-Pack-GitOps](Channel-Pack-GitOps) · [In-App-Updates](In-App-Updates)
- [Beginner-Guide](Beginner-Guide) · [Intermediate-Guide](Intermediate-Guide) · [Expert-Guide](Expert-Guide)
- [Installation-Guide](Installation-Guide) · [Schedules](Schedules) · [Logging](Logging)
- [Authentication](Authentication) · [Authentication-System](Authentication-System)
- [Archive-Parser](Archive-Parser) · [Channel-Builder-Custom-Sources](Channel-Builder-Custom-Sources) · [Channel-Creator-MCP](Channel-Creator-MCP) · [Host-Wiring](Channel-Creator-MCP-Host-Wiring) · [Auth](Channel-Creator-MCP-Auth)
- [Plex-Integration](Plex-Integration) · [Scripts-and-Tools](Scripts-and-Tools)
- [SwiftUI](SwiftUI) · [Implementation](Implementation) · [Troubleshooting](Troubleshooting)
- [API-Reference](API-Reference)

---

## Auth & security (repo docs)

- [Authentication](https://github.com/roto31/StreamTV/blob/main/docs/AUTHENTICATION.md)
- [Authentication System](https://github.com/roto31/StreamTV/blob/main/docs/AUTHENTICATION_SYSTEM.md)
- [Passkey Authentication](https://github.com/roto31/StreamTV/blob/main/docs/PASSKEY_AUTHENTICATION.md)

---

## Contributing

[CONTRIBUTING.md](https://github.com/roto31/StreamTV/blob/main/CONTRIBUTING.md)

---

**Status:** Wiki mirror current with tip **1.4.7** (first-run bootstrap, Plex AAC gate, yt-dlp freshness, signed DMG); publish via `scripts/sync_public_docs.sh --apply --wiki`.
