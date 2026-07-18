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

## Full index

See **[INDEX.md](INDEX.md)** for the complete topic map (guides, wiki, plex, installation).

## Wiki (GitHub Wiki mirror)

In-tree wiki pages live in **[wiki/](wiki/)** — same structure as the public [StreamTV Wiki](https://github.com/roto31/StreamTV/wiki).

- [Wiki home](wiki/Home.md)
- [Documentation index](wiki/Documentation-Index.md)
- [Platform: macOS](wiki/macOS.md) · [Linux](wiki/Linux.md)

## Operator guides

| Guide | Path |
|-------|------|
| Core operator quickstart | [guides/CORE_OPERATOR_QUICKSTART.md](guides/CORE_OPERATOR_QUICKSTART.md) |
| Channel Builder | [channel-builder.md](channel-builder.md) |
| Import vs Builder | [guides/IMPORT_VS_BUILDER.md](guides/IMPORT_VS_BUILDER.md) |
| Metadata enrichment | [guides/METADATA_ENRICHMENT.md](guides/METADATA_ENRICHMENT.md) |
| EPG sync classes | [guides/EPG_SYNC_CLASSES.md](guides/EPG_SYNC_CLASSES.md) |
| PBS + Playwright | [guides/PBS_PLAYWRIGHT.md](guides/PBS_PLAYWRIGHT.md) |
| Archive.org operator | [guides/ARCHIVE_ORG_OPERATOR.md](guides/ARCHIVE_ORG_OPERATOR.md) |
| StreamTV + Tunarr hybrid | [guides/STREAMTV_TUNARR_HYBRID.md](guides/STREAMTV_TUNARR_HYBRID.md) |

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
