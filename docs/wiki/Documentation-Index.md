# StreamTV Documentation Index

Complete guide to StreamTV documentation, organized by topic.

**Version:** 1.4.4 · **Updated:** 2026-11-22  
Sync this wiki with `bash scripts/sync_public_docs.sh --apply --wiki` from StreamTV-source.

**Platform notes:** Builder = Archive.org + YouTube; Schedules UI read-only (`schedules/{n}.yml`); Collections UI and AI Recovery retired.

> Deep docs live in the public repo tree. Prefer **absolute links** below (GitHub Wiki cannot resolve `../guides/`).

---

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
| Browser `/player` preview | [PLAYER_PREVIEW.md](https://github.com/roto31/StreamTV/blob/main/docs/guides/PLAYER_PREVIEW.md) |
| Soft deploy | [SOFT_DEPLOY.md](https://github.com/roto31/StreamTV/blob/main/docs/guides/SOFT_DEPLOY.md) |
| Plex video hold | [PLEX_VIDEO_HOLD.md](https://github.com/roto31/StreamTV/blob/main/docs/guides/PLEX_VIDEO_HOLD.md) |
| TunarrRAM recovery | [TUNARRRAM_PLAYOUT_RECOVERY.md](https://github.com/roto31/StreamTV/blob/main/docs/guides/TUNARRRAM_PLAYOUT_RECOVERY.md) |
| Fleet probe protocol | [FLEET_PROBE_PROTOCOL.md](https://github.com/roto31/StreamTV/blob/main/docs/guides/FLEET_PROBE_PROTOCOL.md) |
| Backup and restore | [BACKUP_RESTORE.md](https://github.com/roto31/StreamTV/blob/main/docs/guides/BACKUP_RESTORE.md) |
| Ops healing (scripts only) | [FFMPEG_STALL](https://github.com/roto31/StreamTV/blob/main/docs/guides/FFMPEG_STALL_KEEPALIVE.md) · [TunarrRAM](https://github.com/roto31/StreamTV/blob/main/docs/guides/TUNARRRAM_PLAYOUT_RECOVERY.md) |
| LoudNorm (default **off**) | [LOUDNORM_FLEET_AUDIO.md](https://github.com/roto31/StreamTV/blob/main/docs/guides/LOUDNORM_FLEET_AUDIO.md) |
| FFmpeg stall / keepalive | [FFMPEG_STALL_KEEPALIVE.md](https://github.com/roto31/StreamTV/blob/main/docs/guides/FFMPEG_STALL_KEEPALIVE.md) |
| Channel Builder | [channel-builder.md](https://github.com/roto31/StreamTV/blob/main/docs/channel-builder.md) |
| Channel Creator MCP (NL + signal-path diagrams) | [guides/CHANNEL_CREATOR_MCP.md](https://github.com/roto31/StreamTV/blob/main/docs/guides/CHANNEL_CREATOR_MCP.md) · wiki [Channel-Creator-MCP](Channel-Creator-MCP) |
| Channel Creator MCP host wiring | [guides/CHANNEL_CREATOR_MCP_HOST_WIRING.md](https://github.com/roto31/StreamTV/blob/main/docs/guides/CHANNEL_CREATOR_MCP_HOST_WIRING.md) (Cursor, VS Code, Claude, local, ChatGPT; all-in-one setup script) |
| Channel Creator MCP setup script | [`scripts/setup_channel_creator_mcp.sh`](https://github.com/roto31/StreamTV/blob/main/scripts/setup_channel_creator_mcp.sh) · [Scripts-and-Tools](Scripts-and-Tools) |
| Import vs Builder | [IMPORT_VS_BUILDER.md](https://github.com/roto31/StreamTV/blob/main/docs/guides/IMPORT_VS_BUILDER.md) |
| Metadata enrichment | [METADATA_ENRICHMENT.md](https://github.com/roto31/StreamTV/blob/main/docs/guides/METADATA_ENRICHMENT.md) |
| EPG sync classes | [EPG_SYNC_CLASSES.md](https://github.com/roto31/StreamTV/blob/main/docs/guides/EPG_SYNC_CLASSES.md) |
| Archive.org operator | [ARCHIVE_ORG_OPERATOR.md](https://github.com/roto31/StreamTV/blob/main/docs/guides/ARCHIVE_ORG_OPERATOR.md) |
| StreamTV + Tunarr hybrid | [STREAMTV_TUNARR_HYBRID.md](https://github.com/roto31/StreamTV/blob/main/docs/guides/STREAMTV_TUNARR_HYBRID.md) |
| Add Tunarr in Plex | [ADD_TUNARR_IN_PLEX.md](https://github.com/roto31/StreamTV/blob/main/docs/guides/ADD_TUNARR_IN_PLEX.md) |
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
- [Beginner-Guide](Beginner-Guide) · [Intermediate-Guide](Intermediate-Guide) · [Expert-Guide](Expert-Guide)
- [Installation-Guide](Installation-Guide) · [Schedules](Schedules) · [Logging](Logging)
- [Authentication](Authentication) · [Authentication-System](Authentication-System)
- [Archive-Parser](Archive-Parser) · [Channel-Builder-Custom-Sources](Channel-Builder-Custom-Sources) · [Channel-Creator-MCP](Channel-Creator-MCP)
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

**Status:** Wiki mirror current with tip **1.4.5** (core trim + signed DMG + public demo pack); publish via `scripts/sync_public_docs.sh --apply --wiki`.
