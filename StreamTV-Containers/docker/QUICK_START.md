# StreamTV Quick Start Guide

## Installation (5 minutes)

### Step 1: Install
Double-click `Install-StreamTV.command` or run:
```bash
./install_macos.sh
```

### Step 2: Start Server
Double-click `Start-StreamTV.command` or run:
```bash
./start_server.sh
```

### Step 3: Access Web Interface
Open http://localhost:8410 in your browser

## First-Time Setup

1. **Configure Authentication** (if needed):
   - Archive.org: Add username/password in web interface
   - YouTube: Add cookies file or OAuth credentials

2. **Create Channels**:
   - Use the web interface at http://localhost:8410
   - Or import from YAML files in `schedules/` directory

3. **Integrate with Plex**:
   - Plex → Settings → Live TV & DVR
   - Add Tuner: `http://YOUR_IP:8410/hdhomerun/discover.json`
   - Add Guide: `http://YOUR_IP:8410/iptv/xmltv.xml`

## Common Tasks

### View Logs
- Web interface: http://localhost:8410/logs
- Plex logs: http://localhost:8410/plex-logs

### Manage Channels
- Web interface: http://localhost:8410/channels
- API: http://localhost:8410/api/channels

### Import Channels
- Web interface: http://localhost:8410/import
- Or use API: POST /api/import/channels/yaml

## Troubleshooting

**Server won't start?**
- Check Python: `python3 --version` (needs 3.8+)
- Check FFmpeg: `ffmpeg -version`
- Run: `./verify-installation.sh`

**Channels not showing in Plex?**
- Verify server is running
- Check firewall allows port 8410
- Verify HDHomeRun is enabled in config.yaml

**Streaming errors?**
- Check logs at http://localhost:8410/logs
- Verify media source URLs are accessible
- Check FFmpeg installation

## Next Steps

- Read `README.md` for full documentation
- See `INSTALL.md` for detailed installation
- Check `docs/TROUBLESHOOTING.md` for more help
