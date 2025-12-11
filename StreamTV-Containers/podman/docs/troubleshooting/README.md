# Troubleshooting Documentation

This directory contains focused troubleshooting guides for specific issue categories.

## Main Guide

- **[TROUBLESHOOTING.md](../TROUBLESHOOTING.md)** - Complete troubleshooting guide (in parent directory)

## Focused Troubleshooting Guides

### Installation & Setup
- **[INSTALLATION_ISSUES.md](INSTALLATION_ISSUES.md)** - Python, FFmpeg, virtual environment, port conflicts, and installation script issues

### Integration
- **[PLEX_INTEGRATION_ISSUES.md](PLEX_INTEGRATION_ISSUES.md)** - Plex tuner discovery, channel mapping, EPG guide, and streaming issues

### Streaming & Playback
- **[STREAMING_ISSUES.md](STREAMING_ISSUES.md)** - Channels won't play, buffering, format errors, and playback problems

### FFmpeg
- **[FFMPEG_ISSUES.md](FFMPEG_ISSUES.md)** - FFmpeg installation, codec errors, format issues, demuxing errors, and performance

### Network & Connectivity
- **[NETWORK_ISSUES.md](NETWORK_ISSUES.md)** - DNS resolution, YouTube/Archive.org connectivity, timeouts, and network performance

### Database
- **[DATABASE_ISSUES.md](DATABASE_ISSUES.md)** - Connection errors, corruption, locking, performance, and maintenance

## Tools & Scripts

- **[TROUBLESHOOTING_SCRIPTS.md](TROUBLESHOOTING_SCRIPTS.md)** - Interactive troubleshooting scripts documentation and usage
- **[scripts/](scripts/)** - Standalone troubleshooting scripts (for use when web UI is unavailable)
  - Diagnostic scripts: `check_python.py`, `check_ffmpeg.py`, `check_database.py`, `check_ports.py`, `test_connectivity.py`
  - Repair scripts: `repair_database.py`
  - Maintenance scripts: `clear_cache.py`
  - Interactive scripts: `troubleshoot_streamtv.sh`, `troubleshoot_plex.sh`, `view-logs.sh`

## Quick Reference

**By Issue Type:**
- **Installation problems** → [INSTALLATION_ISSUES.md](INSTALLATION_ISSUES.md)
- **Plex not working** → [PLEX_INTEGRATION_ISSUES.md](PLEX_INTEGRATION_ISSUES.md)
- **Videos won't play** → [STREAMING_ISSUES.md](STREAMING_ISSUES.md)
- **FFmpeg errors** → [FFMPEG_ISSUES.md](FFMPEG_ISSUES.md)
- **Network problems** → [NETWORK_ISSUES.md](NETWORK_ISSUES.md)
- **Database errors** → [DATABASE_ISSUES.md](DATABASE_ISSUES.md)

**By Symptom:**
- **"Python not found"** → [INSTALLATION_ISSUES.md](INSTALLATION_ISSUES.md#python-not-found)
- **"FFmpeg not found"** → [INSTALLATION_ISSUES.md](INSTALLATION_ISSUES.md#ffmpeg-not-found) or [FFMPEG_ISSUES.md](FFMPEG_ISSUES.md#ffmpeg-not-found)
- **"Error tuning channel"** → [PLEX_INTEGRATION_ISSUES.md](PLEX_INTEGRATION_ISSUES.md#error-tuning-channel-in-plex)
- **"DNS resolution error"** → [NETWORK_ISSUES.md](NETWORK_ISSUES.md#dns-resolution-errors)
- **"Database locked"** → [DATABASE_ISSUES.md](DATABASE_ISSUES.md#database-locked-errors)
- **"Error during demuxing"** → [FFMPEG_ISSUES.md](FFMPEG_ISSUES.md#ffmpeg-demuxing-errors) or [STREAMING_ISSUES.md](STREAMING_ISSUES.md#format-specific-issues)

## Using Troubleshooting Tools

### Web Interface Tools

1. **Streaming Logs:**
   - Access: http://localhost:8410/logs
   - Real-time error detection
   - Click errors for details and self-heal

2. **Diagnostic Scripts:**
   - Run from documentation pages
   - Available in troubleshooting guide
   - Auto-fix options for common issues

3. **AI Troubleshooting:**
   - Install Ollama for AI-powered help
   - Analyzes errors and suggests fixes
   - Access: http://localhost:8410/ollama

### Command Line Tools

**When Web UI is Available:**
- Use diagnostic scripts via web interface (recommended)
- Access: http://localhost:8410/docs/troubleshooting

**When Web UI is NOT Available:**
- Use standalone scripts in [scripts/](scripts/) directory
- See [scripts/README.md](scripts/README.md) for usage
- All scripts can be run from command line

**Available Scripts:**
- Diagnostic: `check_python.py`, `check_ffmpeg.py`, `check_database.py`, `check_ports.py`, `test_connectivity.py`
- Repair: `repair_database.py`
- Maintenance: `clear_cache.py`
- Interactive: `troubleshoot_streamtv.sh`, `troubleshoot_plex.sh`, `view-logs.sh`

**Other Tools:**
- Verification script: `./verify-installation.sh` (from StreamTV root)
- Log viewing: `./scripts/view-logs.sh` (from StreamTV root)

## Getting Help

1. **Start with the main guide:** [TROUBLESHOOTING.md](../TROUBLESHOOTING.md)
2. **Check focused guides:** Use the guides above for specific issues
3. **Run diagnostics:** Use web interface diagnostic scripts
4. **Check logs:** Review streaming logs for error details
5. **Use self-heal:** Click errors in logs for automatic fixes
