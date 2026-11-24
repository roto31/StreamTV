# StreamTV Platform Documentation

Welcome to the StreamTV platform documentation wiki.

**Current tip:** **v1.4.7** — see [Releases](https://github.com/roto31/StreamTV/releases) and [Product scope](https://github.com/roto31/StreamTV/blob/main/docs/PRODUCT_SCOPE.md).

Canonical deep docs live under [`docs/`](https://github.com/roto31/StreamTV/tree/main/docs) in the public repo. This wiki is the curated entry layer.

## Platform

- **[macOS](macOS)** — Native app, signed DMG, and LaunchAgent production path
- **Linux** — Not offered (no Linux product)

## Quick start

1. Download the latest [macOS release](https://github.com/roto31/StreamTV/releases) (`StreamTV.1.4.7-macos.dmg`)
2. Follow the [Installation Guide](Installation-Guide) · [First-Run-Setup](First-Run-Setup) · [Production-Bootstrap](Production-Bootstrap)
3. [First channel in 15 minutes](https://github.com/roto31/StreamTV/blob/main/docs/guides/FIRST_CHANNEL_15_MIN.md) (public demo pack)

## Architecture diagrams (canonical)

System, HDHomeRun tune, import, Archive URL resolution, MPEG-TS policy, metadata enrichment, and EPG sync diagrams are **Mermaid** in:

- [ARCHITECTURE.md](https://github.com/roto31/StreamTV/blob/main/ARCHITECTURE.md)

Wiki ASCII diagrams (Expert / Intermediate) are summaries only — if they disagree, trust ARCHITECTURE.md.

## Operator guides

- [First-Run-Setup](First-Run-Setup) · [Production-Bootstrap](Production-Bootstrap) · [SetupDone-and-Factory-Reset](SetupDone-and-Factory-Reset) · [In-App-Updates](In-App-Updates)
- [Core-Dependency-Freshness](Core-Dependency-Freshness) (yt-dlp floor / player clients)
- [Plex-Playback-Error-Host](Plex-Playback-Error-Host) (Issue 71–72 AAC / maintenance)
- [Channel-Pack-GitOps](Channel-Pack-GitOps) (private promote → validate → apply)
- [Browser `/player` preview](https://github.com/roto31/StreamTV/blob/main/docs/guides/PLAYER_PREVIEW.md)
- [Soft deploy](https://github.com/roto31/StreamTV/blob/main/docs/guides/SOFT_DEPLOY.md)
- [Plex video hold](https://github.com/roto31/StreamTV/blob/main/docs/guides/PLEX_VIDEO_HOLD.md)
- [TunarrRAM playout recovery](https://github.com/roto31/StreamTV/blob/main/docs/guides/TUNARRRAM_PLAYOUT_RECOVERY.md)
- [Backup and restore](https://github.com/roto31/StreamTV/blob/main/docs/guides/BACKUP_RESTORE.md)
- Ops healing: [FFmpeg stall](https://github.com/roto31/StreamTV/blob/main/docs/guides/FFMPEG_STALL_KEEPALIVE.md) · [TunarrRAM](https://github.com/roto31/StreamTV/blob/main/docs/guides/TUNARRRAM_PLAYOUT_RECOVERY.md) · [Soft deploy](https://github.com/roto31/StreamTV/blob/main/docs/guides/SOFT_DEPLOY.md) (AI Recovery retired)
- [LoudNorm fleet audio](https://github.com/roto31/StreamTV/blob/main/docs/guides/LOUDNORM_FLEET_AUDIO.md) (default **off**)
- [Fleet probe protocol](https://github.com/roto31/StreamTV/blob/main/docs/guides/FLEET_PROBE_PROTOCOL.md)
- [Metadata enrichment](https://github.com/roto31/StreamTV/blob/main/docs/guides/METADATA_ENRICHMENT.md)
- [EPG sync classes](https://github.com/roto31/StreamTV/blob/main/docs/guides/EPG_SYNC_CLASSES.md)
- [Channel Builder](https://github.com/roto31/StreamTV/blob/main/docs/channel-builder.md) (Archive.org + YouTube)
- [Channel Creator MCP](Channel-Creator-MCP) — NL create via guided MCP (signal paths, tools, Archive rules)
- [Channel Creator MCP host wiring](Channel-Creator-MCP-Host-Wiring) — Cursor, VS Code, Claude, local models, ChatGPT/Claude web via `:8411`
- [Channel Creator MCP auth](Channel-Creator-MCP-Auth) — `bearer` / `oauth` / `dual`
- [Schedules (YAML authority)](https://github.com/roto31/StreamTV/blob/main/docs/SCHEDULES.md) — web UI is read-only
- [Core operator quickstart](https://github.com/roto31/StreamTV/blob/main/docs/guides/CORE_OPERATOR_QUICKSTART.md)

## Platform surface (current)

- **Builder first-party sources:** Archive.org, YouTube  
- **Schedules:** `schedules/{n}.yml` on disk; Schedules page inventory only (no create/edit UI)  
- **Remux:** source resolution (clients scale); Transcoding hub for optional profiles  
- **Retired:** Collections UI / `/api/collections`, AI Recovery / Foundation Models / Ollama, Watermarks UI, Resolutions UI, PBS auth UI, schedule-items editor, Tunarr library browse proxies  


## Wiki pages

- [Documentation Index](Documentation-Index)
- [First-Run-Setup](First-Run-Setup) · [Production-Bootstrap](Production-Bootstrap) · [Core-Dependency-Freshness](Core-Dependency-Freshness)
- [Plex-Playback-Error-Host](Plex-Playback-Error-Host) · [Channel-Pack-GitOps](Channel-Pack-GitOps) · [In-App-Updates](In-App-Updates)
- [Implementation & Integrations](Implementation)
- [Channel Creator MCP](Channel-Creator-MCP) · [Host wiring](Channel-Creator-MCP-Host-Wiring) · [HTTP auth](Channel-Creator-MCP-Auth)
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
