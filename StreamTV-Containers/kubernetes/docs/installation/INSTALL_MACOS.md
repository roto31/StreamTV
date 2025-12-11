# macOS Installation Guide

Complete installation guide for StreamTV on macOS.

## Quick Start

Run the automated installation script:

```bash
./install_macos.sh
```

This script will:
1. Check and install Python 3.8+ from python.org
2. Install FFmpeg from official sources (Homebrew as fallback)
3. Set up a virtual environment
4. Install all Python dependencies
5. Configure the platform
6. Initialize the database
7. Create launch scripts
8. Optionally start the server

## Manual Installation

If you prefer to install manually:

### 1. Install Python 3.8+

Download and install from [python.org](https://www.python.org/downloads/):
- Choose the macOS installer for your architecture (Intel or Apple Silicon)
- Run the installer and follow the instructions
- Verify installation: `python3 --version`

### 2. Install FFmpeg

#### Option A: Official Source (Recommended for Apple Silicon)

For Apple Silicon Macs, download from [evermeet.cx](https://evermeet.cx/ffmpeg/):
```bash
curl -L -o /tmp/ffmpeg.zip https://evermeet.cx/ffmpeg/ffmpeg-6.1.1.zip
unzip -q -o /tmp/ffmpeg.zip -d /tmp/
sudo mv /tmp/ffmpeg /usr/local/bin/ffmpeg
sudo chmod +x /usr/local/bin/ffmpeg
```

#### Option B: Homebrew (Fallback)

```bash
brew install ffmpeg
```

### 3. Set Up Virtual Environment

```bash
python3 -m venv ~/.retro-tv-simulator/venv
source ~/.retro-tv-simulator/venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### 5. Configure

```bash
cp config.example.yaml config.yaml
# Edit config.yaml as needed
```

### 6. Initialize Database

```bash
python3 -c "from streamtv.database.session import init_db; init_db()"
```

### 7. Create Your First Channel

After installation, you can create channels using:
- The web interface at http://localhost:8410/channels
- The API (see API documentation)
- YAML import files (see SCHEDULES.md)

Example using the script:
```bash
python3 scripts/create_channel.py --number 1 --name "My First Channel"
```

### 8. Start Server

```bash
python3 -m streamtv.main
```

## Installation Locations

- **Virtual Environment**: `~/.streamtv/venv`
- **Launch Script**: `~/.streamtv/start_server.sh`
- **Service Plist**: `~/Library/LaunchAgents/com.streamtv.plist`
- **Logs**: `~/.streamtv/server.log`

## Running as a Service

The installation script creates a macOS LaunchAgent. To use it:

```bash
# Load the service
launchctl load ~/Library/LaunchAgents/com.retro-tv-simulator.plist

# Unload the service
launchctl unload ~/Library/LaunchAgents/com.retro-tv-simulator.plist

# Check status
launchctl list | grep retro-tv-simulator
```

## Uninstallation

Run the uninstall script:

```bash
./uninstall_macos.sh
```

This will:
- Stop the server
- Remove the service
- Remove installation files
- Optionally remove the database

## Troubleshooting

### Python Not Found

If Python is not found after installation:
1. Restart your terminal
2. Check PATH: `echo $PATH`
3. Verify installation: `/usr/local/bin/python3 --version`

### FFmpeg Not Found

If FFmpeg is not found:
1. Check if it's in PATH: `which ffmpeg`
2. For user installation: Add `~/.local/bin` to PATH in `~/.zshrc`:
   ```bash
   export PATH="$HOME/.local/bin:$PATH"
   ```
3. Restart terminal or run: `source ~/.zshrc`

### Port Already in Use

If port 8410 is already in use:
1. Change port in `config.yaml`:
   ```yaml
   server:
     port: 8500
   ```
2. Or stop the existing service:
   ```bash
   launchctl unload ~/Library/LaunchAgents/com.retro-tv-simulator.plist
   ```

### Virtual Environment Issues

If you encounter issues with the virtual environment:
1. Remove and recreate:
   ```bash
   rm -rf ~/.retro-tv-simulator/venv
   python3 -m venv ~/.retro-tv-simulator/venv
   ```
2. Reinstall dependencies:
   ```bash
   source ~/.retro-tv-simulator/venv/bin/activate
   pip install -r requirements.txt
   ```

## System Requirements

- **macOS**: 10.9 (Mavericks) or later
- **Python**: 3.8 or higher
- **RAM**: 2GB minimum, 4GB recommended
- **Disk Space**: 500MB for installation, additional space for media

## Architecture Support

- **Apple Silicon (M1/M2/M3)**: Fully supported
- **Intel Macs**: Fully supported

## Next Steps

After installation:
1. Access the web interface: http://localhost:8410
2. View API documentation: http://localhost:8410/docs
3. Access IPTV playlist: http://localhost:8410/iptv/channels.m3u
4. Add media items via API or web interface
5. Configure schedules for your channels

## Support

For issues or questions:
- Check the [main README](README.md)
- Review [API documentation](docs/API.md)
- Check [installation guide](docs/INSTALLATION.md)

