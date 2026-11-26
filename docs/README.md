# StreamTV Complete Documentation

Welcome to the complete StreamTV documentation. This documentation is organized into three levels to accommodate users of all skill levels.

## Documentation Levels

### [Beginner Guide](./BEGINNER_GUIDE.md)
**For Novice Users**
- What is StreamTV?
- Basic concepts and terminology
- Simple setup and usage
- Common tasks step-by-step
- Basic troubleshooting

### [Intermediate Guide](./INTERMEDIATE_GUIDE.md)
**For Technicians**
- Architecture overview
- Configuration details
- YAML file structure
- Channel and schedule management
- Advanced troubleshooting
- Script usage

### [Expert Guide](./EXPERT_GUIDE.md)
**For Engineers**
- Complete system architecture
- Component interactions
- Code structure and patterns
- Advanced configuration
- Customization and extension
- Deep troubleshooting

## Start here

- **[Product scope](PRODUCT_SCOPE.md)** — what is in / out of the core product
- **[First channel in 15 minutes](guides/FIRST_CHANNEL_15_MIN.md)** — public demo pack

## Full index

See **[INDEX.md](INDEX.md)** for the complete topic map (guides, wiki, plex, installation).

## Wiki (GitHub Wiki mirror)

In-tree wiki pages live in **[wiki/](wiki/)** — same structure as the public [StreamTV Wiki](https://github.com/roto31/StreamTV/wiki).

- [Wiki home](wiki/Home.md)
- [Documentation index](wiki/Documentation-Index.md)
- [Platform: macOS](wiki/macOS.md) (Linux not offered)

## Operator guides

| Guide | Path |
|-------|------|
| Core operator quickstart | [guides/CORE_OPERATOR_QUICKSTART.md](guides/CORE_OPERATOR_QUICKSTART.md) |
| Backup and restore | [guides/BACKUP_RESTORE.md](guides/BACKUP_RESTORE.md) |
| First-run setup | [guides/FIRST_RUN_SETUP.md](guides/FIRST_RUN_SETUP.md) |
| Production bootstrap (universal) | [guides/PRODUCTION_BOOTSTRAP_UNIVERSAL.md](guides/PRODUCTION_BOOTSTRAP_UNIVERSAL.md) |
| SetupDone / factory reset | [guides/SETUP_DONE_AND_FACTORY_RESET.md](guides/SETUP_DONE_AND_FACTORY_RESET.md) |
| Source auth (YouTube / Archive.org) | [guides/SOURCE_AUTH_YOUTUBE_ARCHIVE.md](guides/SOURCE_AUTH_YOUTUBE_ARCHIVE.md) |
| Core dependency freshness (yt-dlp) | [guides/CORE_DEPENDENCY_FRESHNESS.md](guides/CORE_DEPENDENCY_FRESHNESS.md) |
| Plex Playback Error host triage | [guides/PLEX_PLAYBACK_ERROR_HOST.md](guides/PLEX_PLAYBACK_ERROR_HOST.md) |
| macOS Web UI sidebar | [guides/MACOS_APP_WEBUI_SIDEBAR.md](guides/MACOS_APP_WEBUI_SIDEBAR.md) |
| Native admin parity | [guides/NATIVE_ADMIN_PARITY.md](guides/NATIVE_ADMIN_PARITY.md) |
| In-app Updates | [guides/IN_APP_UPDATES.md](guides/IN_APP_UPDATES.md) |
| Ops healing (scripts only) | [FFMPEG_STALL_KEEPALIVE](guides/FFMPEG_STALL_KEEPALIVE.md) · [TUNARRRAM](guides/TUNARRRAM_PLAYOUT_RECOVERY.md) · [SOFT_DEPLOY](guides/SOFT_DEPLOY.md) |
| LoudNorm fleet audio | [guides/LOUDNORM_FLEET_AUDIO.md](guides/LOUDNORM_FLEET_AUDIO.md) |
| FFmpeg stall / keepalive | [guides/FFMPEG_STALL_KEEPALIVE.md](guides/FFMPEG_STALL_KEEPALIVE.md) |
| Plex video hold | [guides/PLEX_VIDEO_HOLD.md](guides/PLEX_VIDEO_HOLD.md) |
| TunarrRAM playout recovery | [guides/TUNARRRAM_PLAYOUT_RECOVERY.md](guides/TUNARRRAM_PLAYOUT_RECOVERY.md) |
| Soft deploy (no full kickstart) | [guides/SOFT_DEPLOY.md](guides/SOFT_DEPLOY.md) |
| Browser `/player` preview | [guides/PLAYER_PREVIEW.md](guides/PLAYER_PREVIEW.md) |
| Fleet probe protocol | [guides/FLEET_PROBE_PROTOCOL.md](guides/FLEET_PROBE_PROTOCOL.md) |
| FFmpeg profiles | [guides/FFMPEG_PROFILES.md](guides/FFMPEG_PROFILES.md) |
| YouTube geo-blocks | [guides/YOUTUBE_GEO_BLOCKS.md](guides/YOUTUBE_GEO_BLOCKS.md) |
| Vimeo bedrock gate | [guides/VIMEO_BEDROCK_GATE.md](guides/VIMEO_BEDROCK_GATE.md) |
| Lessons Learned (Issues 1–61) | [../LESSONS_LEARNED.md](../LESSONS_LEARNED.md) |
| Channel Builder (Archive.org + YouTube) | [channel-builder.md](channel-builder.md) |
| Schedules (YAML authority; UI read-only) | [SCHEDULES.md](SCHEDULES.md) |
| Channel Creator MCP v2 (guided tools + signal paths) | [guides/CHANNEL_CREATOR_MCP.md](guides/CHANNEL_CREATOR_MCP.md) |
| Channel Creator MCP host wiring (Cursor / VS Code / Claude / local / ChatGPT+Claude web) | [guides/CHANNEL_CREATOR_MCP_HOST_WIRING.md](guides/CHANNEL_CREATOR_MCP_HOST_WIRING.md) |
| Channel Creator MCP HTTP auth (`bearer` / `oauth` / `dual`) | [guides/CHANNEL_CREATOR_MCP_AUTH.md](guides/CHANNEL_CREATOR_MCP_AUTH.md) |
| Channel Creator MCP host generator + remote/e2e scripts | [`scripts/channel_creator_mcp_hosts.zsh`](../scripts/channel_creator_mcp_hosts.zsh) · [`channel_creator_mcp_remote.zsh`](../scripts/channel_creator_mcp_remote.zsh) · [`channel_creator_e2e_rehearsal.zsh`](../scripts/channel_creator_e2e_rehearsal.zsh) |
| Channel Creator MCP legacy installer | [`scripts/setup_channel_creator_mcp.sh`](../scripts/setup_channel_creator_mcp.sh) · [helpers README](../scripts/channel-creator-mcp/README.md) |
| Application icon (macOS + favicon) | [`branding/app-icon/`](../branding/app-icon/README.md) · `scripts/install_app_icon.sh` |
| Import vs Builder | [guides/IMPORT_VS_BUILDER.md](guides/IMPORT_VS_BUILDER.md) |
| Channel pack GitOps (private promote → validate → apply) | [guides/CHANNEL_PACK_GITOPS.md](guides/CHANNEL_PACK_GITOPS.md) · `scripts/validate_channel_pack.py` · `scripts/apply_channel_pack.sh` |
| Metadata enrichment | [guides/METADATA_ENRICHMENT.md](guides/METADATA_ENRICHMENT.md) |
| EPG sync classes | [guides/EPG_SYNC_CLASSES.md](guides/EPG_SYNC_CLASSES.md) |
| PBS (retired from Builder) | [guides/PBS_PLAYWRIGHT.md](guides/PBS_PLAYWRIGHT.md) |
| Archive.org operator | [guides/ARCHIVE_ORG_OPERATOR.md](guides/ARCHIVE_ORG_OPERATOR.md) |
| Sanitization policy (public sync) | [SANITIZATION_POLICY.md](SANITIZATION_POLICY.md) |

## Architecture diagrams

Mermaid diagrams (system, HDHomeRun tune, import, Archive URL resolution, MPEG-TS policy, metadata enrichment, EPG sync) live in **[ARCHITECTURE.md](../ARCHITECTURE.md)** at the repository root. Keep them updated when streaming, import, enrichment, or EPG paths change.

## Quick Links

- [Installation Guide](./INSTALLATION.md)
- [Quick Start Guide](./installation/QUICK_START.md)
- [API Documentation](./API.md)
- [HDHomeRun Integration](./HDHOMERUN.md)
- [Schedule System](./SCHEDULES.md)
- [Troubleshooting](./TROUBLESHOOTING.md)
- [Troubleshooting Scripts](./TROUBLESHOOTING_SCRIPTS.md)

## Getting Help

1. **Start with the Beginner Guide** if you're new to StreamTV
2. **Check the Intermediate Guide** for configuration and setup details
3. **Refer to the Expert Guide** for deep technical information
4. **Use Troubleshooting Scripts** for automated problem diagnosis

## Documentation Structure

```
docs/
├── README.md / INDEX.md
├── guides/              # Operator guides
├── wiki/                # Public wiki mirror
├── channel-builder.md
├── plex/ logging/ installation/ archive-parser/
├── swiftui/ implementation/
├── public-repo/         # Sanitized public README + CHANGELOG templates
└── BEGINNER|INTERMEDIATE|EXPERT + API, SCHEDULES, HDHOMERUN, …
```
