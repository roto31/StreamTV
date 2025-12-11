# StreamTV macOS Distribution - Installation Guide

## Quick Start

### Option 1: Automated Installation (Recommended)

Double-click `Install-StreamTV.command` or run:
```bash
./install_macos.sh
```

### Option 2: Manual Installation

1. **Install Python 3.8+**
   - Download from [python.org](https://www.python.org/downloads/)
   - Or use Homebrew: `brew install python3`

2. **Install FFmpeg**
   - Download from [evermeet.cx](https://evermeet.cx/ffmpeg/) (Apple Silicon)
   - Or use Homebrew: `brew install ffmpeg`

3. **Set up virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

4. **Install dependencies**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

5. **Configure**
   ```bash
   cp config.example.yaml config.yaml
   # Edit config.yaml as needed
   ```

6. **Start server**
   ```bash
   ./start_server.sh
   # Or: python3 -m streamtv.main
   ```

## System Requirements

- macOS 10.15 (Catalina) or later
- Python 3.8 or later
- FFmpeg 6.0 or later
- 2GB RAM minimum
- 500MB disk space

## Features

- **HDHomeRun Emulation**: Compatible with Plex, Emby, Jellyfin
- **IPTV Support**: M3U playlists and XMLTV EPG
- **Multiple Sources**: YouTube, Archive.org, PBS
- **Continuous Streaming**: ErsatzTV-style timeline-based playout
- **On-Demand Streaming**: Start from beginning or saved position

## Configuration

Edit `config.yaml` to configure:
- Server host and port
- YouTube/Archive.org authentication
- HDHomeRun settings
- Plex integration
- Logging levels

## Troubleshooting

See `docs/TROUBLESHOOTING.md` for common issues and solutions.

## Support

- Documentation: See `docs/` directory
- API Documentation: http://localhost:8410/docs (after starting server)
