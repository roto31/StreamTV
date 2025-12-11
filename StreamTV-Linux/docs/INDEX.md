# 📚 StreamTV Documentation Index

Complete guide to all StreamTV documentation, organized by topic with descriptions.

---

## 🚀 Quick Start

**New to StreamTV?** Start here:

- **[Quick Start Guide](installation/QUICK_START.md)** - Get started in minutes
- **[QUICKSTART.md](QUICKSTART.md)** - Quick start overview
- **[Beginner Guide](BEGINNER_GUIDE.md)** - For novice users
- **[Installation Guide](INSTALLATION.md)** - Detailed setup instructions

---

## 📖 Core Documentation

### Essential Guides

- **[README.md](README.md)** - Project overview, features, and documentation structure
- **[INDEX.md](INDEX.md)** - This file - complete documentation index
- **[API.md](API.md)** - Complete API reference with endpoints, request/response formats, and examples
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues, solutions, and diagnostic procedures
- **[YAML_VALIDATION.md](YAML_VALIDATION.md)** - YAML file validation rules and schema documentation

### User Guides by Level

- **[BEGINNER_GUIDE.md](BEGINNER_GUIDE.md)** - Getting started guide for novice users with basic concepts and step-by-step instructions
- **[INTERMEDIATE_GUIDE.md](INTERMEDIATE_GUIDE.md)** - For technicians: architecture overview, configuration details, YAML structure, and advanced troubleshooting
- **[EXPERT_GUIDE.md](EXPERT_GUIDE.md)** - For engineers: complete system architecture, component interactions, code structure, and deep customization

---

## 🔐 Authentication & Security

**Location**: [authentication/](authentication/)

### Authentication Documentation

- **[AUTHENTICATION.md](authentication/AUTHENTICATION.md)** - Basic authentication setup and usage guide for Archive.org and YouTube
- **[AUTHENTICATION_SYSTEM.md](authentication/AUTHENTICATION_SYSTEM.md)** - Complete authentication system overview, web interface login, automatic re-authentication, and credential storage
- **[PASSKEY_AUTHENTICATION.md](authentication/PASSKEY_AUTHENTICATION.md)** - Apple Passkey (WebAuthn) authentication guide for passwordless, biometric authentication using Face ID/Touch ID

---

## 🎯 Features & Integration

### Channel Management

- **[SCHEDULES.md](SCHEDULES.md)** - Creating and managing channel schedules, YAML format, and scheduling concepts
- **[HDHOMERUN.md](HDHOMERUN.md)** - HDHomeRun emulation setup, Plex/Emby/Jellyfin integration, and tuner configuration
- **[COMPARISON.md](COMPARISON.md)** - Feature comparisons with other IPTV solutions

### Advanced Features

**Location**: [features/](features/)

- **[AUTO_HEALER.md](features/AUTO_HEALER.md)** - AI-powered auto-healing system that automatically monitors logs, detects errors, and applies fixes using Ollama AI
- **[ERSATZTV_INTEGRATION.md](features/ERSATZTV_INTEGRATION.md)** - ErsatzTV integration guide and setup instructions
- **[ERSATZTV_COMPLETE_INTEGRATION.md](features/ERSATZTV_COMPLETE_INTEGRATION.md)** - Complete ErsatzTV integration status, all integrated features, and compatibility confirmation

### External Integrations

- **Plex** → [plex/](plex/) - Complete Plex Media Server integration guides
- **ErsatzTV** → [features/ERSATZTV_COMPLETE_INTEGRATION.md](features/ERSATZTV_COMPLETE_INTEGRATION.md)

---

## 🛠️ Troubleshooting

**Location**: [troubleshooting/](troubleshooting/)

- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Main troubleshooting guide with common issues and solutions (in parent directory)
- **[INSTALLATION_ISSUES.md](troubleshooting/INSTALLATION_ISSUES.md)** - Installation and setup issues (Python, FFmpeg, ports, virtual environment)
- **[PLEX_INTEGRATION_ISSUES.md](troubleshooting/PLEX_INTEGRATION_ISSUES.md)** - Plex tuner discovery, channel mapping, EPG guide, and streaming issues
- **[STREAMING_ISSUES.md](troubleshooting/STREAMING_ISSUES.md)** - Video streaming, playback, buffering, and format-specific issues
- **[FFMPEG_ISSUES.md](troubleshooting/FFMPEG_ISSUES.md)** - FFmpeg installation, codec errors, format issues, and performance
- **[NETWORK_ISSUES.md](troubleshooting/NETWORK_ISSUES.md)** - DNS resolution, YouTube/Archive.org connectivity, timeouts, and network performance
- **[DATABASE_ISSUES.md](troubleshooting/DATABASE_ISSUES.md)** - Database connection errors, corruption, locking, performance, and maintenance
- **[TROUBLESHOOTING_SCRIPTS.md](troubleshooting/TROUBLESHOOTING_SCRIPTS.md)** - Interactive troubleshooting scripts documentation using SwiftDialog for automated diagnostics

---

## 📝 Configuration & System

- **[LOGGING.md](LOGGING.md)** - Logging configuration, log file locations, and log viewing tools

---

## 📂 Directory Structure

```
docs/
├── INDEX.md (this file)
├── README.md
│
├── Core Documentation (root level)
│   ├── API.md
│   ├── BEGINNER_GUIDE.md
│   ├── INTERMEDIATE_GUIDE.md
│   ├── EXPERT_GUIDE.md
│   ├── QUICKSTART.md
│   ├── INSTALLATION.md
│   ├── SCHEDULES.md
│   ├── HDHOMERUN.md
│   ├── LOGGING.md
│   ├── TROUBLESHOOTING.md
│   ├── YAML_VALIDATION.md
│   └── COMPARISON.md
│
├── authentication/              # Authentication systems
│   ├── README.md
│   ├── AUTHENTICATION.md
│   ├── AUTHENTICATION_SYSTEM.md
│   └── PASSKEY_AUTHENTICATION.md
│
├── features/                     # Advanced features
│   ├── README.md
│   ├── AUTO_HEALER.md
│   ├── ERSATZTV_INTEGRATION.md
│   └── ERSATZTV_COMPLETE_INTEGRATION.md
│
├── troubleshooting/              # Troubleshooting tools
│   ├── README.md
│   ├── TROUBLESHOOTING_SCRIPTS.md
│   └── scripts/                    # Standalone troubleshooting scripts
│       ├── README.md
│       ├── check_python.py
│       ├── check_ffmpeg.py
│       ├── check_database.py
│       ├── check_ports.py
│       ├── test_connectivity.py
│       ├── repair_database.py
│       ├── clear_cache.py
│       ├── troubleshoot_streamtv.sh
│       ├── troubleshoot_plex.sh
│       └── view-logs.sh
│
├── installation/                 # Setup & installation
│   ├── QUICK_START.md
│   ├── INSTALL_MACOS.md
│   ├── YOUTUBE_API_SETUP.md
│   └── ...
│
└── plex/                         # Plex integration
    ├── README.md
    ├── PLEX_SETUP_COMPLETE.md
    ├── PLEX_INTEGRATION_COMPLETE.md
    └── ...
```

---

## 🔍 Quick Search

### By Task

**I want to...**
- **Get started quickly** → [QUICKSTART.md](QUICKSTART.md) or [installation/QUICK_START.md](installation/QUICK_START.md)
- **Set up authentication** → [authentication/AUTHENTICATION.md](authentication/AUTHENTICATION.md)
- **Use Passkey authentication** → [authentication/PASSKEY_AUTHENTICATION.md](authentication/PASSKEY_AUTHENTICATION.md)
- **Set up Plex integration** → [plex/PLEX_SETUP_COMPLETE.md](plex/PLEX_SETUP_COMPLETE.md)
- **Enable auto-healing** → [features/AUTO_HEALER.md](features/AUTO_HEALER.md)
- **View application logs** → [LOGGING.md](LOGGING.md)
- **Install on Linux** → [installation/INSTALL_LINUX.md](installation/INSTALL_LINUX.md)
- **Troubleshoot issues** → [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Installation problems** → [troubleshooting/INSTALLATION_ISSUES.md](troubleshooting/INSTALLATION_ISSUES.md)
- **Plex integration issues** → [troubleshooting/PLEX_INTEGRATION_ISSUES.md](troubleshooting/PLEX_INTEGRATION_ISSUES.md)
- **Streaming problems** → [troubleshooting/STREAMING_ISSUES.md](troubleshooting/STREAMING_ISSUES.md)
- **FFmpeg errors** → [troubleshooting/FFMPEG_ISSUES.md](troubleshooting/FFMPEG_ISSUES.md)
- **Network issues** → [troubleshooting/NETWORK_ISSUES.md](troubleshooting/NETWORK_ISSUES.md)
- **Database problems** → [troubleshooting/DATABASE_ISSUES.md](troubleshooting/DATABASE_ISSUES.md)
- **Use troubleshooting scripts** → [troubleshooting/TROUBLESHOOTING_SCRIPTS.md](troubleshooting/TROUBLESHOOTING_SCRIPTS.md)
- **Run scripts when web UI unavailable** → [troubleshooting/scripts/](troubleshooting/scripts/)
- **Create schedules** → [SCHEDULES.md](SCHEDULES.md)
- **Use the API** → [API.md](API.md)
- **Integrate with ErsatzTV** → [features/ERSATZTV_INTEGRATION.md](features/ERSATZTV_INTEGRATION.md)

### By Experience Level

- **Beginner** → [BEGINNER_GUIDE.md](BEGINNER_GUIDE.md)
- **Intermediate** → [INTERMEDIATE_GUIDE.md](INTERMEDIATE_GUIDE.md)
- **Expert** → [EXPERT_GUIDE.md](EXPERT_GUIDE.md)

---

## 📋 Documentation Files Reference

### Core Documentation

| File | Description |
|------|-------------|
| [README.md](README.md) | Project overview, features, and documentation structure |
| [INDEX.md](INDEX.md) | Complete documentation index (this file) |
| [QUICKSTART.md](QUICKSTART.md) | Quick start overview and getting started guide |
| [INSTALLATION.md](INSTALLATION.md) | Detailed installation instructions for all platforms |
| [API.md](API.md) | Complete API reference with endpoints and examples |
| [SCHEDULES.md](SCHEDULES.md) | Creating and managing channel schedules |
| [HDHOMERUN.md](HDHOMERUN.md) | HDHomeRun emulation and Plex/Emby/Jellyfin integration |
| [LOGGING.md](LOGGING.md) | Logging configuration and log viewing |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Common issues and solutions |
| [YAML_VALIDATION.md](YAML_VALIDATION.md) | YAML file validation rules and schemas |
| [COMPARISON.md](COMPARISON.md) | Feature comparisons with other solutions |

### User Guides

| File | Description |
|------|-------------|
| [BEGINNER_GUIDE.md](BEGINNER_GUIDE.md) | Guide for novice users with basic concepts |
| [INTERMEDIATE_GUIDE.md](INTERMEDIATE_GUIDE.md) | Guide for technicians with architecture and configuration |
| [EXPERT_GUIDE.md](EXPERT_GUIDE.md) | Guide for engineers with deep technical details |

### Authentication

| File | Description |
|------|-------------|
| [authentication/AUTHENTICATION.md](authentication/AUTHENTICATION.md) | Basic authentication setup and usage |
| [authentication/AUTHENTICATION_SYSTEM.md](authentication/AUTHENTICATION_SYSTEM.md) | Complete authentication system architecture |
| [authentication/PASSKEY_AUTHENTICATION.md](authentication/PASSKEY_AUTHENTICATION.md) | Apple Passkey (WebAuthn) authentication guide |

### Features

| File | Description |
|------|-------------|
| [features/AUTO_HEALER.md](features/AUTO_HEALER.md) | AI-powered auto-healing system for error detection and fixes |
| [features/ERSATZTV_INTEGRATION.md](features/ERSATZTV_INTEGRATION.md) | ErsatzTV integration guide and setup |
| [features/ERSATZTV_COMPLETE_INTEGRATION.md](features/ERSATZTV_COMPLETE_INTEGRATION.md) | Complete ErsatzTV integration status and features |

### Troubleshooting

| File | Description |
|------|-------------|
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Main troubleshooting guide (in root) |
| [troubleshooting/INSTALLATION_ISSUES.md](troubleshooting/INSTALLATION_ISSUES.md) | Installation and setup issues (Python, FFmpeg, ports, virtual environment) |
| [troubleshooting/PLEX_INTEGRATION_ISSUES.md](troubleshooting/PLEX_INTEGRATION_ISSUES.md) | Plex tuner discovery, channel mapping, EPG guide, and streaming issues |
| [troubleshooting/STREAMING_ISSUES.md](troubleshooting/STREAMING_ISSUES.md) | Video streaming, playback, buffering, and format-specific issues |
| [troubleshooting/FFMPEG_ISSUES.md](troubleshooting/FFMPEG_ISSUES.md) | FFmpeg installation, codec errors, format issues, and performance |
| [troubleshooting/NETWORK_ISSUES.md](troubleshooting/NETWORK_ISSUES.md) | DNS resolution, YouTube/Archive.org connectivity, timeouts, and network performance |
| [troubleshooting/DATABASE_ISSUES.md](troubleshooting/DATABASE_ISSUES.md) | Database connection errors, corruption, locking, performance, and maintenance |
| [troubleshooting/TROUBLESHOOTING_SCRIPTS.md](troubleshooting/TROUBLESHOOTING_SCRIPTS.md) | Interactive troubleshooting scripts documentation |
| [troubleshooting/scripts/](troubleshooting/scripts/) | Standalone troubleshooting scripts (for use when web UI unavailable) |
| [troubleshooting/scripts/](troubleshooting/scripts/) | Standalone troubleshooting scripts (for use when web UI unavailable) |

### Installation

| File | Description |
|------|-------------|
| [installation/QUICK_START.md](installation/QUICK_START.md) | Quick installation guide |
| [installation/INSTALL_MACOS.md](installation/INSTALL_MACOS.md) | macOS automated installation |
| [installation/YOUTUBE_API_SETUP.md](installation/YOUTUBE_API_SETUP.md) | YouTube API setup instructions |

### Plex Integration

| File | Description |
|------|-------------|
| [plex/README.md](plex/README.md) | Plex integration overview |
| [plex/PLEX_SETUP_COMPLETE.md](plex/PLEX_SETUP_COMPLETE.md) | Complete Plex setup guide |
| [plex/PLEX_INTEGRATION_COMPLETE.md](plex/PLEX_INTEGRATION_COMPLETE.md) | Full Plex integration documentation |

---

## 🆘 Getting Help

1. **Check the docs** - Start with this index
2. **View logs** - See [LOGGING.md](LOGGING.md)
3. **Run diagnostics** - Use [troubleshooting/TROUBLESHOOTING_SCRIPTS.md](troubleshooting/TROUBLESHOOTING_SCRIPTS.md)
4. **Troubleshooting guide** - [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

## 📝 Contributing

See the main project repository for contribution guidelines.

---

**Last Updated**: December 11, 2025  
**Version**: 1.0.0  
**Status**: ✅ Complete and organized
