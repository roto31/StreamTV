# Complete Documentation Index

Complete guide to all StreamTV documentation, organized by topic.

# 📚 StreamTV Documentation Index

Complete guide to all StreamTV documentation, organized by topic.

---

## 🚀 Quick Start

**New to StreamTV?** Start here:
- [Quick Start Guide](installation/QUICK_START.md) - Get started in minutes
- [Beginner Guide](BEGINNER_GUIDE.md) - For novice users
- [Installation Guide](INSTALLATION.md) - Detailed setup

---

## 📖 Core Documentation

### Essential Guides
- [README](README.md) - Project overview and features
- [API Documentation](API.md) - Complete API reference
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues and solutions
- [YAML Validation](YAML_VALIDATION.md) - Validate your configurations

### User Guides by Level
- [Beginner Guide](BEGINNER_GUIDE.md) - Getting started
- [Intermediate Guide](INTERMEDIATE_GUIDE.md) - For technicians
- [Expert Guide](EXPERT_GUIDE.md) - For engineers

---

## 📺 Features & Integration

### HDHomeRun & Tunarr
- [HDHomeRun Integration](HDHOMERUN.md) - Emulation setup
- [Core operator quickstart](../guides/CORE_OPERATOR_QUICKSTART.md) - Dashboard → build → tune
- [Import vs Channel Builder](../guides/IMPORT_VS_BUILDER.md) - Migration vs greenfield
- [Channel Builder](../channel-builder.md) - URL-first wizard
- [Metadata enrichment](../guides/METADATA_ENRICHMENT.md) - TVDB/TVMaze/TMDB, SxxExx retitle, guide audits
- [EPG sync classes](../guides/EPG_SYNC_CLASSES.md) - Class A/B/C Plex guide vs playout
- [PBS + Playwright](../guides/PBS_PLAYWRIGHT.md) - Show expansion
- [Archive.org operator](../guides/ARCHIVE_ORG_OPERATOR.md) - Cookies and download paths
- [FFmpeg profiles](../guides/FFMPEG_PROFILES.md) - Profiles vs overrides
- [YouTube geo-blocks](../guides/YOUTUBE_GEO_BLOCKS.md) - Bulk import skips
- [StreamTV + Tunarr hybrid](../guides/STREAMTV_TUNARR_HYBRID.md) - When to use Builder vs Tunarr
- [Add Tunarr in Plex](../guides/ADD_TUNARR_IN_PLEX.md) - Proxy paste URLs
- [Vimeo bedrock gate](../guides/VIMEO_BEDROCK_GATE.md) - Vimeo source policy
- [Architecture (Mermaid)](../../ARCHITECTURE.md) - System and streaming diagrams
- [Comparison](COMPARISON.md) - Feature comparisons

### External Integrations
- **Plex** → [plex/](plex/)
- **ErsatzTV** → [ERSATZTV_COMPLETE_INTEGRATION.md](ERSATZTV_COMPLETE_INTEGRATION.md)

---

## 🔐 Authentication & Security

### Authentication Systems
- [Authentication System](AUTHENTICATION_SYSTEM.md) - Overview
- [Passkey Authentication](PASSKEY_AUTHENTICATION.md) - Modern passwordless
- [Authentication Guide](AUTHENTICATION.md) - Setup and usage

---

## 📝 Feature-Specific Documentation

### 🎬 Archive.org Channel Parser
Create channels from Archive.org collections (e.g., Magnum P.I.)

**Location**: [archive-parser/](archive-parser/)

**Files**:
- `QUICK_REFERENCE_ARCHIVE_PARSER.md` - Quick start ⭐
- `MAGNUM_PI_CHANNEL_COMPLETE.md` - Complete example
- `ARCHIVE_PARSER_IMPLEMENTATION_SUMMARY.md` - Technical details
- `MAGNUM_PI_RESTART_COMPLETE.md` - Reset instructions
- `ARCHIVE_ORG_REDIRECT_FIX.md` - Troubleshooting

**Usage**:
```bash
# Interactive GUI (recommended)
./scripts/archive_collection_parser_dialog.sh

# Command-line
python3 scripts/archive_collection_parser.py "https://archive.org/details/..."
```

---

### 📊 Logging System
Comprehensive logging to `~/Library/Logs/StreamTV/`

**Location**: [logging/](logging/)

**Files**:
- `LOGGING_QUICKSTART.md` - Quick reference ⭐
- `LOGGING.md` - Complete guide
- `LOGGING_SYSTEM_SUMMARY.md` - Technical overview
- `LOGGING_IMPLEMENTATION_COMPLETE.md` - Implementation details
- `LOGGING_COMPLETE_SUMMARY.md` - Summary

**View Logs**:
```bash
# Live view
./scripts/view-logs.sh

# Search errors
./scripts/view-logs.sh search ERROR

# Open in Finder
open ~/Library/Logs/StreamTV/
```

---

### 📡 Plex Integration
Complete Plex Media Server integration

**Location**: [plex/](plex/)

**Files**:
- `PLEX_SETUP_COMPLETE.md` - Initial setup ⭐
- `PLEX_INTEGRATION_COMPLETE.md` - Full integration
- `PLEX_API_SCHEDULE_INTEGRATION_COMPLETE.md` - API + schedules
- `PLEX_EPG_INTEGRATION.md` - EPG metadata
- `PLEX_SCHEDULE_INTEGRATION.md` - Schedule integration
- `PLEX_CONNECTION_FIX.md` - Troubleshooting

---

### 🖥️ Installation & Setup

**Location**: [](installation/)

**Files**:
- `QUICK_START.md` - Get started fast ⭐
- `INSTALL_MACOS.md` - macOS automated setup
- `GUI_INSTALLER_README.md` - GUI installer
- `SWIFTUI_INSTALLER_README.md` - SwiftUI installer
- `QUICK_START_SWIFTUI.md` - SwiftUI quick start

---

### 🍎 SwiftUI Applications

**Location**: [swiftui/](swiftui/)

**Files**:
- `BUILD_SWIFTUI.md` - Building SwiftUI apps
- `README_SWIFTUI.md` - SwiftUI overview

---

### 🔧 Implementation & Status

**Location**: [implementation/](implementation/)

**Files**:
- `PROJECT_STRUCTURE.md` - Project organization
- `PATH_INDEPENDENCE.md` - Path handling
- `ERSATZTV_INTEGRATION_STATUS.md` - ErsatzTV status
- `ERSATZTV_INTEGRATION_SUMMARY.md` - ErsatzTV summary
- `SECURITY_AUDIT_REPORT.md` - Security audit
- `SECURITY_FIXES_IMPLEMENTED.md` - Security fixes
- `GITHUB_PAGE_SUMMARY.md` - GitHub pages

---

## 🛠️ Scripts & Tools

### Channel Management
```bash
# Import channels
python3 scripts/import_channels.py data/channels.yaml

# Archive.org parser
./scripts/archive_collection_parser_dialog.sh
python3 scripts/archive_collection_parser.py <URL>
```

### Logging
```bash
# View logs
./scripts/view-logs.sh
./scripts/view-logs.sh search <term>
./scripts/view-logs.sh open

# Test logging
./scripts/test_logging.py
```

### Troubleshooting
```bash
# Available in scripts/
check_python.sh
check_ffmpeg.sh
check_database.sh
check_ports.sh
test_connectivity.sh
repair_database.sh
```

---

## 📂 Directory Structure

```

├── INDEX.md (this file)
│
├── archive-parser/           # Archive.org channel creation
│   ├── QUICK_REFERENCE_ARCHIVE_PARSER.md
│   ├── MAGNUM_PI_CHANNEL_COMPLETE.md
│   ├── ARCHIVE_PARSER_IMPLEMENTATION_SUMMARY.md
│   └── ...
│
├── logging/                  # Logging system
│   ├── LOGGING_QUICKSTART.md
│   ├── LOGGING.md
│   └── ...
│
├── plex/                     # Plex integration
│   ├── PLEX_SETUP_COMPLETE.md
│   ├── PLEX_INTEGRATION_COMPLETE.md
│   └── ...
│
├── installation/             # Setup & installation
│   ├── QUICK_START.md
│   ├── INSTALL_MACOS.md
│   └── ...
│
├── swiftui/                  # SwiftUI applications
│   ├── BUILD_SWIFTUI.md
│   └── README_SWIFTUI.md
│
├── implementation/           # Technical implementation
│   ├── PROJECT_STRUCTURE.md
│   ├── SECURITY_AUDIT_REPORT.md
│   └── ...
│
└── Core docs (in this directory)
    ├── API.md
    ├── SCHEDULES.md
    ├── AUTHENTICATION_SYSTEM.md
    ├── BEGINNER_GUIDE.md
    ├── TROUBLESHOOTING.md
    └── ...
```

---

## 🔍 Quick Search

### By Task

**I want to...**
- **Create a channel from Archive.org** → [archive-parser/QUICK_REFERENCE_ARCHIVE_PARSER.md](archive-parser/QUICK_REFERENCE_ARCHIVE_PARSER.md)
- **Set up Plex integration** → [plex/PLEX_SETUP_COMPLETE.md](plex/PLEX_SETUP_COMPLETE.md)
- **View application logs** → [logging/LOGGING_QUICKSTART.md](logging/LOGGING_QUICKSTART.md)
- **Install on macOS** → [installation/INSTALL_MACOS.md](installation/INSTALL_MACOS.md)
- **Troubleshoot issues** → [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Create schedules** → [SCHEDULES.md](SCHEDULES.md)
- **Use the API** → [API.md](API.md)

### By Experience Level
- **Beginner** → [BEGINNER_GUIDE.md](BEGINNER_GUIDE.md)
- **Intermediate** → [INTERMEDIATE_GUIDE.md](INTERMEDIATE_GUIDE.md)
- **Expert** → [EXPERT_GUIDE.md](EXPERT_GUIDE.md)

---

## 🆘 Getting Help

1. **Check the docs** - Start with this index
2. **View logs** - `./scripts/view-logs.sh`
3. **Run diagnostics** - `./scripts/check_*.sh`
4. **Troubleshooting guide** - [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

## 📋 Common Workflows

### Creating a New Channel
1. [SCHEDULES.md](SCHEDULES.md) - Learn schedule format
2. Create YAML files in `data/` and `schedules/`
3. Import: `python3 scripts/import_channels.py data/your-channel.yaml`

### Archive.org Channel (Automated)
1. [archive-parser/QUICK_REFERENCE_ARCHIVE_PARSER.md](archive-parser/QUICK_REFERENCE_ARCHIVE_PARSER.md)
2. Run: `./scripts/archive_collection_parser_dialog.sh`
3. Enter Archive.org URL
4. Files auto-generated and imported

### Plex Integration
1. [plex/PLEX_SETUP_COMPLETE.md](plex/PLEX_SETUP_COMPLETE.md) - Initial setup
2. [plex/PLEX_API_SCHEDULE_INTEGRATION_COMPLETE.md](plex/PLEX_API_SCHEDULE_INTEGRATION_COMPLETE.md) - Full integration

---

## 📝 Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for contribution guidelines.

---

**Last Updated**: December 3, 2025
**Version**: 1.0.0
**Status**: ✅ Complete and organized
