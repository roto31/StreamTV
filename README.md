# StreamTV Platform Distributions

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey.svg)]()

**StreamTV** is a cross-platform IPTV streaming platform that creates TV channels from online video sources like YouTube and Archive.org. Stream directly to Plex, Emby, Jellyfin, and HDHomeRun-compatible devices without requiring local media storage.

## 🎯 Features

### Core Capabilities
- **🌐 Direct Streaming**: Stream from YouTube and Archive.org without downloads
- **📺 HDHomeRun Emulation**: Native integration with Plex, Emby, and Jellyfin
- **📅 Advanced Scheduling**: YAML-based schedules with commercial breaks
- **🐳 Container Support**: Docker, Kubernetes, and Podman deployments
- **🖥️ Cross-Platform**: Native support for macOS, Windows, and Linux
- **🔌 IPTV Support**: M3U playlists and XMLTV EPG generation
- **⚡ FastAPI**: Modern async Python web framework
- **🔐 Authentication**: Passkey and OAuth support for YouTube

### Streaming Sources
- ✅ **YouTube**: Direct streaming with quality selection and OAuth authentication
- ✅ **Archive.org**: Support for video collections and individual items
- 🔄 **Extensible**: Easy to add new streaming sources via adapter pattern

### Integration
- **Plex Media Server**: Direct HDHomeRun tuner or M3U/EPG
- **Emby/Jellyfin**: HDHomeRun or IPTV support
- **Kodi**: IPTV Simple Client
- **VLC**: Direct M3U playlist support
- **HDHomeRun Devices**: Full API compatibility

## 📦 Available Distributions

### Desktop Platforms

- **[macOS](StreamTV-macOS/)** - Native macOS distribution with installer
  - Automated installation script
  - `.command` launchers for easy startup
  - Full documentation included

- **[Windows](StreamTV-Windows/)** - Windows distribution
  - PowerShell installation script
  - Batch and PowerShell startup scripts
  - Windows service support documentation

- **[Linux](StreamTV-Linux/)** - Linux distribution
  - Distribution detection (apt, dnf, pacman)
  - systemd service integration
  - Firewall configuration guides

### Container Platforms

- **[Docker](StreamTV-Containers/docker/)** - Single-container deployment
- **[Docker Compose](StreamTV-Containers/docker-compose/)** - Multi-service setup
- **[Kubernetes](StreamTV-Containers/kubernetes/)** - K8s manifests with ingress
- **[Podman](StreamTV-Containers/podman/)** - Rootless container support

## 🚀 Quick Start

### macOS
```bash
cd StreamTV-macOS
./install_macos.sh
./start_server.sh
# Or double-click: Install-StreamTV.command
```

### Windows
```powershell
cd StreamTV-Windows
.\install_windows.ps1
.\start_server.ps1
```

### Linux
```bash
cd StreamTV-Linux
./install_linux.sh
./start_server.sh
```

### Docker
```bash
cd StreamTV-Containers/docker
docker build -t streamtv .
docker run -p 8410:8410 streamtv
```

**Access the web interface**: Open `http://localhost:8410` in your browser

## 📋 Requirements

- **Python**: 3.8 or higher
- **FFmpeg**: For video transcoding (automatically installed by install scripts)
- **Network**: Internet connection for streaming
- **Platform-specific**: See individual distribution READMEs

## 📚 Documentation

### Complete Guides
- **[GitHub Wiki](https://github.com/roto31/StreamTV/wiki)** - Comprehensive documentation
- **[Documentation Index](https://github.com/roto31/StreamTV/wiki/Documentation-Index)** - All guides organized
- **[Scripts & Tools](https://github.com/roto31/StreamTV/wiki/Scripts-and-Tools)** - Utility scripts

### Quick Links
- [Installation Guide](https://github.com/roto31/StreamTV/wiki/Installation-Guide)
- [Beginner Guide](https://github.com/roto31/StreamTV/wiki/Beginner-Guide) - For new users
- [Plex Integration](https://github.com/roto31/StreamTV/wiki/Plex-Integration) - Setup guide
- [API Reference](https://github.com/roto31/StreamTV/wiki/API-Reference) - Complete API docs
- [Troubleshooting](https://github.com/roto31/StreamTV/wiki/Troubleshooting) - Common issues

### Platform-Specific
Each distribution includes complete documentation in `docs/`:
- Installation instructions
- Quick start guides
- Platform-specific configuration
- Troubleshooting guides
- API documentation

## 🔗 Integration Examples

### Plex Media Server
1. Install StreamTV on your server
2. Add StreamTV as HDHomeRun tuner in Plex
3. Scan for channels
4. Watch your custom channels in Plex!

See [Plex Integration Guide](https://github.com/roto31/StreamTV/wiki/Plex-Integration) for detailed instructions.

### IPTV Clients
- **Kodi**: Use IPTV Simple Client with M3U playlist
- **VLC**: Open M3U playlist directly
- **Emby/Jellyfin**: Add as IPTV source or HDHomeRun tuner

## 🛠️ Scripts & Tools

StreamTV includes utility scripts for:
- Channel creation from Archive.org collections
- Schedule generation
- Log viewing and troubleshooting
- Database management

See [Scripts Documentation](https://github.com/roto31/StreamTV/wiki/Scripts-and-Tools) for complete list.

## 📖 Wiki Pages

Comprehensive documentation available in the [GitHub Wiki](https://github.com/roto31/StreamTV/wiki):
- [macOS](https://github.com/roto31/StreamTV/wiki/macOS) - Complete macOS guide
- [Windows](https://github.com/roto31/StreamTV/wiki/Windows) - Complete Windows guide
- [Linux](https://github.com/roto31/StreamTV/wiki/Linux) - Complete Linux guide
- [Containers](https://github.com/roto31/StreamTV/wiki/Containers) - Container platforms
- [Archive Parser](https://github.com/roto31/StreamTV/wiki/Archive-Parser) - Create channels from Archive.org
- [Logging](https://github.com/roto31/StreamTV/wiki/Logging) - Logging system

## 📝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

- Report bugs via [Issues](https://github.com/roto31/StreamTV/issues)
- Suggest features via [Feature Requests](https://github.com/roto31/StreamTV/issues/new?template=feature_request.md)
- Submit pull requests following our [PR template](.github/pull_request_template.md)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🌟 Project Status

✅ **Stable** - Production ready
- Cross-platform distributions available
- Comprehensive documentation
- Active development

## 🔍 Resources

- [GitHub Wiki](https://github.com/roto31/StreamTV/wiki) - Complete documentation
- [Issues](https://github.com/roto31/StreamTV/issues) - Bug reports and feature requests
- [Pull Requests](https://github.com/roto31/StreamTV/pulls) - Contributions
- [Releases](https://github.com/roto31/StreamTV/releases) - Version history

---

**Made with ❤️ for the IPTV community**
