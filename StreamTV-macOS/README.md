# StreamTV - macOS Distribution

StreamTV is an efficient online media streaming platform that emulates HDHomeRun tuners for integration with Plex, Emby, and Jellyfin.

## What's Included

- **StreamTV Core**: Complete streaming platform
- **Installation Scripts**: Automated setup for macOS
- **Documentation**: Complete guides and API documentation
- **Example Configurations**: Ready-to-use channel examples

## Quick Installation

1. **Run the installer:**
   ```bash
   ./install_macos.sh
   ```

2. **Start the server:**
   ```bash
   ./start_server.sh
   ```

3. **Access the web interface:**
   Open http://localhost:8410 in your browser

## Key Features

### HDHomeRun Emulation
- Full HDHomeRun API compatibility
- SSDP auto-discovery
- Multiple virtual tuners
- Direct Plex/Emby/Jellyfin integration

### IPTV Support
- M3U playlist generation
- XMLTV EPG guide
- Channel management
- Schedule-based playout

### Media Sources
- **YouTube**: Direct streaming with authentication
- **Archive.org**: Access to public domain content
- **PBS**: Live and on-demand PBS streams

### Streaming Modes
- **Continuous**: Timeline-based continuous playout (ErsatzTV-style)
- **On-Demand**: Start from beginning or saved position

## Directory Structure

```
StreamTV-macOS/
├── streamtv/              # Core application code
├── scripts/               # Utility scripts
├── schedules/             # Channel schedule files
├── data/                  # Channel icons and data
├── docs/                  # Documentation (if included)
├── install_macos.sh       # Installation script
├── start_server.sh        # Server startup script
├── requirements.txt       # Python dependencies
├── config.example.yaml    # Configuration template
└── README.md             # This file
```

## Configuration

1. Copy the example config:
   ```bash
   cp config.example.yaml config.yaml
   ```

2. Edit `config.yaml` with your settings:
   - Server host/port
   - YouTube/Archive.org credentials
   - HDHomeRun settings
   - Plex integration (optional)

## Integration with Plex

1. Start StreamTV
2. Open Plex → Settings → Live TV & DVR
3. Add Tuner: `http://YOUR_IP:8410/hdhomerun/discover.json`
4. Add Guide: `http://YOUR_IP:8410/iptv/xmltv.xml`
5. Map channels and start watching!

## System Requirements

- **macOS**: 10.15 (Catalina) or later
- **Python**: 3.8 or later
- **FFmpeg**: 6.0 or later
- **RAM**: 2GB minimum (4GB recommended)
- **Disk**: 500MB for installation

## Support & Documentation

- **Installation Guide**: See `INSTALL.md`
- **API Documentation**: http://localhost:8410/docs
- **Troubleshooting**: See documentation in `docs/` directory

## License

See LICENSE file for details.

## Version

This distribution includes StreamTV version 1.0.0
