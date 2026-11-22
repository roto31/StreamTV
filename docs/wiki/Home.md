# StreamTV Platform Documentation

Welcome to the StreamTV platform documentation wiki.

**Current tip:** **v1.4.3** — signed macOS DMG on [Releases](https://github.com/roto31/StreamTV/releases/tag/v1.4.3).

Canonical deep docs live under [`docs/`](https://github.com/roto31/StreamTV/tree/main/docs) in the public repo. This wiki is the curated entry layer.

## Platform distributions

### Desktop

- **[macOS](macOS)** — Native app, installer, and menu bar app
- **[Linux](Linux)** — Install scripts and systemd integration

## Quick start

1. Download the latest [macOS release](https://github.com/roto31/StreamTV/releases) (or choose **macOS** / **Linux** above)
2. Follow the [Installation Guide](Installation-Guide)
3. Configure StreamTV and create your first channel

## Architecture diagrams (canonical)

System, HDHomeRun tune, import, Archive URL resolution, MPEG-TS policy, metadata enrichment, and EPG sync diagrams are **Mermaid** in:

- [ARCHITECTURE.md](https://github.com/roto31/StreamTV/blob/main/ARCHITECTURE.md)

Wiki ASCII diagrams (Expert / Intermediate) are summaries only — if they disagree, trust ARCHITECTURE.md.

## Operator guides

- [Browser `/player` preview](https://github.com/roto31/StreamTV/blob/main/docs/guides/PLAYER_PREVIEW.md)
- [Soft deploy](https://github.com/roto31/StreamTV/blob/main/docs/guides/SOFT_DEPLOY.md)
- [Plex video hold](https://github.com/roto31/StreamTV/blob/main/docs/guides/PLEX_VIDEO_HOLD.md)
- [TunarrRAM playout recovery](https://github.com/roto31/StreamTV/blob/main/docs/guides/TUNARRRAM_PLAYOUT_RECOVERY.md)
- [Backup and restore](https://github.com/roto31/StreamTV/blob/main/docs/guides/BACKUP_RESTORE.md)
- Ops healing: [FFmpeg stall](https://github.com/roto31/StreamTV/blob/main/docs/guides/FFMPEG_STALL_KEEPALIVE.md) · [TunarrRAM](https://github.com/roto31/StreamTV/blob/main/docs/guides/TUNARRRAM_PLAYOUT_RECOVERY.md) · [Soft deploy](https://github.com/roto31/StreamTV/blob/main/docs/guides/SOFT_DEPLOY.md) (AI Recovery retired)
- [LoudNorm fleet audio](https://github.com/roto31/StreamTV/blob/main/docs/guides/LOUDNORM_FLEET_AUDIO.md) (default **off**)
- [FFmpeg stall / keepalive](https://github.com/roto31/StreamTV/blob/main/docs/guides/FFMPEG_STALL_KEEPALIVE.md)
- [Fleet probe protocol](https://github.com/roto31/StreamTV/blob/main/docs/guides/FLEET_PROBE_PROTOCOL.md)
- [Metadata enrichment](https://github.com/roto31/StreamTV/blob/main/docs/guides/METADATA_ENRICHMENT.md)
- [EPG sync classes](https://github.com/roto31/StreamTV/blob/main/docs/guides/EPG_SYNC_CLASSES.md)
- [Channel Builder](https://github.com/roto31/StreamTV/blob/main/docs/channel-builder.md) (Archive.org + YouTube)
- [Channel Creator MCP](https://github.com/roto31/StreamTV/blob/main/docs/guides/CHANNEL_CREATOR_MCP.md) — NL create via MCP (signal-path diagrams)
- [Channel Creator MCP host wiring](https://github.com/roto31/StreamTV/blob/main/docs/guides/CHANNEL_CREATOR_MCP_HOST_WIRING.md) — Cursor, VS Code, Claude, local models, ChatGPT deferred; optional `scripts/setup_channel_creator_mcp.sh`
- [Schedules (YAML authority)](https://github.com/roto31/StreamTV/blob/main/docs/SCHEDULES.md) — web UI is read-only
- [Core operator quickstart](https://github.com/roto31/StreamTV/blob/main/docs/guides/CORE_OPERATOR_QUICKSTART.md)

## Platform surface (current)

- **Builder first-party sources:** Archive.org, YouTube  
- **Schedules:** `schedules/{n}.yml` on disk; Schedules page inventory only (no create/edit UI)  
- **Retired:** Collections UI / `/api/collections`, AI Recovery / Foundation Models / Ollama operator UI  

## Wiki pages

- [Documentation Index](Documentation-Index)
- [Channel Creator MCP](Channel-Creator-MCP)
- [API Reference](API-Reference)
- [Plex Integration](Plex-Integration)
- [Troubleshooting](Troubleshooting)
- [Schedules](Schedules)
- [Beginner](Beginner-Guide) · [Intermediate](Intermediate-Guide) · [Expert](Expert-Guide)

## Additional resources

- [GitHub repository](https://github.com/roto31/StreamTV) — sanitized source, docs, releases
- [Issues](https://github.com/roto31/StreamTV/issues)
- [Sanitization policy](https://github.com/roto31/StreamTV/blob/main/docs/SANITIZATION_POLICY.md)

## Contributing

See [CONTRIBUTING.md](https://github.com/roto31/StreamTV/blob/main/CONTRIBUTING.md).
