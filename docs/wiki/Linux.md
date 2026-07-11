# Linux

Complete documentation for StreamTV on Linux.

## Quick Links

### Overview


StreamTV is an efficient online media streaming platform that emulates HDHomeRun tuners for integration with Plex, Emby, and Jellyfin.

## What's Included

- **StreamTV Core**: Complete streaming platform
- **Installation Scripts**: Automated setup for Linux
- **Documentation**: Complete guides and API documentation
- **Example Configurations**: Ready-to-use channel examples
- **Systemd Service**: Optional systemd service for running as a daemon

## Quick Installation

### Automated Installation (Recommended)

1. **Run the installer:**
   ```bash
   chmod +x install_linux.sh
   ./install_linux.sh
   ```

2. **Start the server:**
   ```bash
   ./start_server.sh
   ```

3. **Access the web interface:**
   Open http://localhost:8410 in your browser

### Manual Installation

1. **Install system dependencies:**
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install python3 python3-pip python3-venv ffmpeg git
   
   # Fedora/RHEL/CentOS
   sudo dnf install python3 python3-pip ffmpeg git
   
   # Arch Linux
   sudo pacman -S python python-pip ffmpeg git
   ```

2. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```


---

## Installation

# Linux Installation Guide

Complete installation guide for StreamTV on Linux.

## Quick Start

Run the automated installation script:

```bash
chmod +x install_linux.sh
./install_linux.sh
```

This script will:
1. Detect your Linux distribution
2. Install Python 3.8+ and FFmpeg via package manager
3. Set up a virtual environment
4. Install all Python dependencies
5. Configure the platform
6. Initialize the database
7. Create launch scripts
8. Optionally create a systemd service
9. Optionally start the server

## Manual Installation

If you prefer to install manually:

### 1. Install System Dependencies

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv ffmpeg git
```

#### Fedora/RHEL/CentOS
```bash
sudo dnf install python3 python3-pip ffmpeg git
```

#### Arch Linux
```bash
sudo pacman -S python python-pip ffmpeg git
```

### 2. Set Up Virtual Environment

```bash
python3 -m venv ~/.streamtv/venv
source ~/.streamtv/venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### 4. Configure

```bash
cp config.example.yaml config.yaml
# Edit config.yaml as needed
nano config.yaml  # or use your preferred editor
```

### 5. Initialize Database

```bash
python3 -c "from streamtv.database.session import init_db; init_db()"
```

### 6. Create Your First Channel

After installation, you can create channels using:
- The web interface at http://localhost:8410/channels
- The API (see API documentation)
- YAML import files (see SCHEDULES.md)

### 7. Start Server

**Option 1: Using Launch Script**
```bash
./start_server.sh
```

**Option 2: Direct Command**
```bash
source ~/.streamtv/venv/bin/activate
python3 -m streamtv.main
```

## Running as a Systemd Service

### Automatic Setup (via installer)

The installer can create a systemd service automatically. Answer "y" when prompted.

### Manual Setup

1. **Create service file:**
   ```bash
   sudo nano /etc/systemd/system/streamtv.service
   ```

2. **Add service configuration:**
   ```ini
   [Unit]
   Description=StreamTV Media Streaming Server
   After=network.target

   [Service]
   Type=simple
   User=your_username
   WorkingDirectory=/path/to/StreamTV-Linux
   Environment="PATH=/path/to/venv/bin"
   ExecStart=/path/to/venv/bin/python3 -m streamtv.main
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

3. **Enable and start:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable streamtv
   sudo systemctl start streamtv
   ```

4. **Check status:**
   ```bash
   sudo systemctl status streamtv
   ```

5. **View logs:**
   ```bash
   sudo journalctl -u streamtv -f
   ```

## Installation Locations

- **Virtual Environment**: `~/.streamtv/venv`
- **Launch Script**: `~/.streamtv/start_server.sh`
- **Configuration**: `config.yaml` (in application directory)
- **Database**: `streamtv.db` (in application directory)
- **Logs**: `streamtv.log` (in application directory)

## Linux-Specific Configuration

### Firewall Configuration

#### UFW (Ubuntu/Debian)
```bash
sudo ufw allow 8410/tcp
sudo ufw reload
```

#### Firewalld (Fedora/RHEL/CentOS)
```bash
sudo firewall-cmd --add-port=8410/tcp --permanent
sudo firewall-cmd --reload
```

#### iptables
```bash
sudo iptables -A INPUT -p tcp --dport 8410 -j ACCEPT
sudo iptables-save
```

### SELinux Configuration

If SELinux is enabled and causing issues:

**Check status:**
```bash
getenforce
```

**Temporary permissive mode (for testing):**
```bash
sudo setenforce 0
```

**Permanent configuration:**
```bash
sudo setsebool -P httpd_can_network_connect 1
```

### User Permissions

Ensure the user running StreamTV has proper permissions:
- Read/write access to application directory
- Network access for streaming
- Ability to create log files

## Distribution-Specific Notes

### Ubuntu/Debian

- Uses `apt` package manager
- Python 3 is typically pre-installed
- May need to install `python3-venv` separately

### Fedora/RHEL/CentOS

- Uses `dnf` package manager (or `yum` on older versions)
- SELinux may require additional configuration
- EPEL repository may be needed for some packages

### Arch Linux

- Uses `pacman` package manager
- AUR packages available for additional tools
- Rolling release - always up to date

## Troubleshooting

### Python Not Found

- Install Python 3.8+ via package manager
- Verify with: `python3 --version`
- Some distributions use `python` instead of `python3`

### FFmpeg Not Found

- Install via package manager (see above)
- Verify with: `ffmpeg -version`
- Check PATH: `which ffmpeg`

### Permission Denied

- Check file permissions: `ls -la`
- Make scripts executable: `chmod +x script.sh`
- Check directory ownership: `ls -ld`

### Port Already in Use

If port 8410 is already in use:
1. Find the process:
   ```bash
   sudo lsof -i :8410
   # or
   sudo netstat -tulpn | grep 8410
   ```
2. Change port in `config.yaml`:
   ```yaml
   server:
     port: 8411  # Use different port
   ```

### Virtual Environment Issues

If activation fails:
```bash
# Remove and recreate
rm -rf venv
python3 -m venv venv
source venv/bin/activate
```

### Systemd Service Issues

**Check service status:**
```bash
sudo systemctl status streamtv
```

**View service logs:**
```bash
sudo journalctl -u streamtv -n 50
```

**Restart service:**
```bash
sudo systemctl restart streamtv
```

## Next Steps

- [Quick Start Guide](QUICKSTART.md)
- [Configuration Guide](CONFIGURATION.md)
- [API Documentation](API.md)
- [Troubleshooting](TROUBLESHOOTING.md)

---

## Complete Documentation

### Core Documentation

#### README

# StreamTV Complete Documentation

Welcome to the complete StreamTV documentation. This documentation is organized into three levels to accommodate users of all skill levels.

## Documentation Levels

### 📚 [Beginner Guide](BEGINNER_GUIDE.md)
**For Novice Users**
- What is StreamTV?
- Basic concepts and terminology
- Simple setup and usage
- Common tasks step-by-step
- Basic troubleshooting

### 🔧 [Intermediate Guide](INTERMEDIATE_GUIDE.md)
**For Technicians**
- Architecture overview
- Configuration details
- YAML file structure
- Channel and schedule management
- Advanced troubleshooting
- Script usage

### 🏗️ [Expert Guide](EXPERT_GUIDE.md)
**For Engineers**
- Complete system architecture
- Component interactions
- Code structure and patterns
- Advanced configuration
- Customization and extension
- Deep troubleshooting

## Quick Links

- [Installation Guide](INSTALLATION.md)
- [Quick Start Guide](QUICKSTART.md)
- [API Documentation](API.md)
- [HDHomeRun Integration](HDHOMERUN.md)
- [Schedule System](SCHEDULES.md)
- [YAML Validation](YAML_VALIDATION.md)
- [Troubleshooting Scripts](TROUBLESHOOTING_SCRIPTS.md)

## Getting Help

1. **Start with the Beginner Guide** if you're new to StreamTV
2. **Check the Intermediate Guide** for configuration and setup details
3. **Refer to the Expert Guide** for deep technical information
4. **Use Troubleshooting Scripts** for automated problem diagnosis

## Documentation Structure

```
#
├── README.md (this file)
├── BEGINNER_GUIDE.md
├── INTERMEDIATE_GUIDE.md
├── EXPERT_GUIDE.md
├── TROUBLESHOOTING_SCRIPTS.md
├── INSTALLATION.md
├── QUICKSTART.md
├── API.md
├── HDHOMERUN.md
├── SCHEDULES.md
└── YAML_VALIDATION.md
```


---

#### INDEX

# 📚 StreamTV Documentation Index

Complete guide to all StreamTV documentation, organized by topic with descriptions.

---

## 🚀 Quick Start

**New to StreamTV?** Start here:

- **[Quick Start Guide](#QUICK_START.md)** - Get started in minutes
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

**Location**: [#](#)

- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Main troubleshooting guide with common issues and solutions (in parent directory)
- **[INSTALLATION_ISSUES.md](#INSTALLATION_ISSUES.md)** - Installation and setup issues (Python, FFmpeg, ports, virtual environment)
- **[PLEX_INTEGRATION_ISSUES.md](#PLEX_INTEGRATION_ISSUES.md)** - Plex tuner discovery, channel mapping, EPG guide, and streaming issues
- **[STREAMING_ISSUES.md](#STREAMING_ISSUES.md)** - Video streaming, playback, buffering, and format-specific issues
- **[FFMPEG_ISSUES.md](#FFMPEG_ISSUES.md)** - FFmpeg installation, codec errors, format issues, and performance
- **[NETWORK_ISSUES.md](#NETWORK_ISSUES.md)** - DNS resolution, YouTube/Archive.org connectivity, timeouts, and network performance
- **[DATABASE_ISSUES.md](#DATABASE_ISSUES.md)** - Database connection errors, corruption, locking, performance, and maintenance
- **[TROUBLESHOOTING_SCRIPTS.md](#TROUBLESHOOTING_SCRIPTS.md)** - Interactive troubleshooting scripts documentation using SwiftDialog for automated diagnostics

---

## 📝 Configuration & System

- **[LOGGING.md](LOGGING.md)** - Logging configuration, log file locations, and log viewing tools

---

## 📂 Directory Structure

```
#
├── INDEX.md (this file)
├── README.md
│
├── Core Documentation (root level)
│   ├── API.md

---

#### QUICKSTART

# StreamTV Quick Start Guide

## Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure:**
   ```bash
   cp config.example.yaml config.yaml
   # Edit config.yaml if needed
   ```

3. **Run:**
   ```bash
   python -m streamtv.main
   ```

## Basic Usage

### 1. Create a Channel

```bash
curl -X POST http://localhost:8410/api/channels \
  -H "Content-Type: application/json" \
  -d '{
    "number": "1",
    "name": "My YouTube Channel",
    "group": "Entertainment"
  }'
```

### 2. Add a YouTube Video

```bash
curl -X POST http://localhost:8410/api/media \
  -H "Content-Type: application/json" \
  -d '{
    "source": "youtube",
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
  }'
```

### 3. Create a Playlist

```bash
curl -X POST http://localhost:8410/api/playlists \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Playlist",
    "channel_id": 1
  }'
```

### 4. Add Video to Playlist

```bash
curl -X POST http://localhost:8410/api/playlists/1/items/1
```

### 5. Access IPTV Streams

- **M3U Playlist:** http://localhost:8410/iptv/channels.m3u
- **EPG:** http://localhost:8410/iptv/xmltv.xml
- **Channel Stream:** http://localhost:8410/iptv/channel/1.m3u8

## Using with IPTV Clients

### VLC Media Player

1. Open VLC
2. Go to Media → Open Network Stream
3. Enter: `http://localhost:8410/iptv/channels.m3u`
4. Click Play

### Kodi

1. Install IPTV Simple Client addon
2. Configure:
   - M3U Playlist URL: `http://localhost:8410/iptv/channels.m3u`
   - EPG URL: `http://localhost:8410/iptv/xmltv.xml`

### Plex

1. Install xTeVe or similar IPTV proxy
2. Configure with StreamTV endpoints

## Adding Archive.org Content

```bash
curl -X POST http://localhost:8410/api/media \
  -H "Content-Type: application/json" \
  -d '{
    "source": "archive_org",
    "url": "https://archive.org/details/identifier"
  }'
```


---

#### INSTALLATION

# StreamTV Installation Guide

## Requirements

- Python 3.8 or higher
- pip (Python package manager)
- FFmpeg (optional, for advanced streaming features)

## Installation Steps

### 1. Clone or Download

If you have the source code:
```bash
cd streamtv
```

### 2. Create Virtual Environment (Recommended)

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure

Copy the example configuration:
```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml` with your settings:
```yaml
server:
  host: "0.0.0.0"
  port: 8410
  base_url: "http://localhost:8410"

database:
  url: "sqlite:///./streamtv.db"

youtube:
  enabled: true
  quality: "best"

archive_org:
  enabled: true
  preferred_format: "h264"
```

### 5. Initialize Database

The database will be automatically initialized on first run.

### 6. Run the Server

```bash
python -m streamtv.main
```

Or using uvicorn directly:
```bash
uvicorn streamtv.main:app --host 0.0.0.0 --port 8410
```

### 7. Access the Application

- Web Interface: http://localhost:8410
- API Documentation: http://localhost:8410/docs
- IPTV Playlist: http://localhost:8410/iptv/channels.m3u
- EPG: http://localhost:8410/iptv/xmltv.xml

## Docker Installation (Optional)

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-m", "streamtv.main"]
```

Build and run:
```bash
docker build -t streamtv .
docker run -p 8410:8410 -v $(pwd)/config.yaml:/app/config.yaml streamtv
```

---

#### API

# StreamTV API Documentation

This document describes the RESTful API for StreamTV, modeled after ErsatzTV's API structure.

## Base URL

All API endpoints are prefixed with `/api` unless otherwise noted.

## Authentication

If `api_key_required` is enabled in configuration, include the access token as a query parameter:
```
?access_token=YOUR_TOKEN
```

## Endpoints

### Channels

#### Get All Channels
```
GET /api/channels
```

Returns a list of all channels.

**Response:**
```json
[
  {
    "id": 1,
    "number": "1",
    "name": "My Channel",
    "group": "Entertainment",
    "enabled": true,
    "logo_path": null,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
]
```

#### Get Channel by ID
```
GET /api/channels/{channel_id}
```

#### Get Channel by Number
```
GET /api/channels/number/{channel_number}
```

#### Create Channel
```
POST /api/channels
Content-Type: application/json

{
  "number": "1",
  "name": "My Channel",
  "group": "Entertainment",
  "enabled": true,
  "logo_path": null
}
```

#### Update Channel
```
PUT /api/channels/{channel_id}
Content-Type: application/json

{
  "name": "Updated Channel Name"
}
```

#### Delete Channel
```
DELETE /api/channels/{channel_id}
```

### Media Items

#### Get All Media Items
```
GET /api/media?source=youtube&skip=0&limit=100
```

Query parameters:
- `source`: Filter by source (youtube, archive_org)
- `skip`: Number of items to skip (pagination)
- `limit`: Maximum number of items to return

#### Get Media Item by ID
```
GET /api/media/{media_id}
```

#### Add Media Item
```

---

#### TROUBLESHOOTING

# StreamTV Troubleshooting Guide

Complete troubleshooting guide for StreamTV on macOS, Windows, and Linux.

## Quick Diagnostics

Run these diagnostic scripts directly from this page to check your installation:

- [Run Script: check_python](script:check_python) - Check Python installation and version
- [Run Script: check_ffmpeg](script:check_ffmpeg) - Check FFmpeg installation and version
- [Run Script: check_database](script:check_database) - Check database connectivity and integrity
- [Run Script: check_ports](script:check_ports) - Check if required ports are available
- [Run Script: test_connectivity](script:test_connectivity) - Test network connectivity to media sources (with auto-fix for DNS issues)
- [Run Script: repair_database](script:repair_database) - Attempt to repair corrupted database
- [Run Script: clear_cache](script:clear_cache) - Clear application cache

**How to use:** Click on any script link above. You'll be prompted to confirm before the script runs. The results will appear below.

## Using the Web Interface for Troubleshooting

StreamTV includes powerful web-based troubleshooting tools accessible from the web interface:

### Streaming Logs & Self-Healing

1. **Access Streaming Logs**: Click "Streaming Logs" in the sidebar under Resources
2. **Real-Time Monitoring**: View logs as they happen with automatic updates
3. **Error Detection**: Errors and warnings are automatically highlighted and clickable
4. **Click for Details**: Click any error/warning to see:
   - Full error context (20 lines before/after)
   - Matched troubleshooting scripts
   - **"Self-Heal" button** to automatically run fixes
5. **Auto-Fix Prompts**: When scripts detect fixable issues (e.g., missing yt-dlp, DNS issues), you'll be prompted to apply fixes automatically

### Interactive Documentation

All documentation is available directly in the web interface:

- Click **"Documentation"** in the sidebar dropdown
- Browse guides: Quick Start, Beginner, Installation, Path Independence, GUI Installer, SwiftUI Installer
- Click script buttons in documentation to run diagnostics
- Access troubleshooting guides from the **"Troubleshooting"** dropdown

### AI Troubleshooting Assistant

Install Ollama for AI-powered troubleshooting:

1. Click **"AI Troubleshooting"** in the sidebar under Resources
2. Install Ollama (~5 GB base installation)
3. Select and install AI models based on your hardware
4. The AI can analyze errors and suggest fixes based on your system's configuration

**Features**:
- Analyzes log errors and provides explanations
- Suggests fixes based on your system configuration
- Learns from patterns in your logs
- Completely private - no data leaves your machine

## Common Installation Issues

### Python Not Found

**Symptoms**: `python3: command not found` or Python version too old

**Solutions**:

1. **macOS**: 
   - Download from [python.org](https://www.python.org/downloads/)
   - Or use Homebrew: `brew install python3`
   - Run diagnostic: [Run Script: check_python](script:check_python)

2. **Windows**: 
   - Download from [python.org](https://www.python.org/downloads/)
   - Check "Add Python to PATH" during installation
   - Restart terminal/PowerShell after installation

3. **Linux**: 
   - Ubuntu/Debian: `sudo apt-get install python3 python3-pip`
   - Fedora: `sudo dnf install python3 python3-pip`
   - Arch: `sudo pacman -S python python-pip`

### FFmpeg Not Found

**Symptoms**: `ffmpeg: command not found` or FFmpeg errors in logs

**Solutions**:

1. **macOS**: 
   - Apple Silicon: Download from [evermeet.cx](https://evermeet.cx/ffmpeg/)
   - Or use Homebrew: `brew install ffmpeg`
   - Run diagnostic: [Run Script: check_ffmpeg](script:check_ffmpeg)

2. **Windows**: 
   - Download from [ffmpeg.org](https://ffmpeg.org/download.html)
   - Extract and add to PATH
   - Or use Chocolatey: `choco install ffmpeg`

3. **Linux**: 
   - Ubuntu/Debian: `sudo apt-get install ffmpeg`
   - Fedora: `sudo dnf install ffmpeg`
   - Arch: `sudo pacman -S ffmpeg`

---

### Installation Documentation

#### GUI INSTALLER README

# StreamTV GUI Installer for macOS

## Overview

The GUI installer provides a user-friendly graphical interface for installing and updating StreamTV on macOS.

## Features

### Visual Status Indicators

Each module shows its status with color-coded indicators:

- **Green Checkmark (✓)**: Module installed/updated successfully
- **Yellow Warning (⚠)**: Module has issues but installation continued
- **Red Error (✗)**: Module installation failed

### Module Detection

The installer automatically detects:
- **Existing installations**: Checks if modules are already installed
- **Updates needed**: Identifies modules that need updating
- **Corrupted installations**: Detects and offers to fix corrupted modules

### Auto-Fix Capabilities

When issues are detected, the installer can:
- Recreate corrupted virtual environments
- Reinstall missing dependencies
- Fix configuration file issues
- Repair database corruption

## Requirements

- macOS 10.9 (Mavericks) or later
- Python 3.8 or higher (will be installed if missing)
- tkinter (included with Python)

## Installation

### Easy Installation (Double-Click Method)

**Option 1: SwiftUI Installer (Native macOS - Recommended)**
1. Build the SwiftUI installer first (see BUILD_SWIFTUI.md)
2. **Double-click** `Install-StreamTV-SwiftUI.command`
3. The native SwiftUI installer window will open
4. Click **"Start Installation"**
5. Wait for installation to complete
6. Click **"Fix Issues"** if any problems are detected (optional)
7. Click **"Close"** when done

**Option 2: Python GUI Installer (No Build Required)**
1. **Double-click** `Install-StreamTV.command`
2. The Python GUI installer window will open
3. Click **"Start Installation"**
4. Wait for installation to complete
5. Click **"Fix Issues"** if any problems are detected (optional)
6. Click **"Close"** when done

### Alternative Methods

- **SwiftUI**: `Install-StreamTV-SwiftUI.command` - Native macOS experience
- **Python GUI**: `Install-StreamTV.command` - Python-based GUI
- **Shell Script**: `./install-gui.sh` - Run from Terminal
- **Python Direct**: `python3 install_gui.py` - Direct Python execution

## What Gets Installed

The installer automatically:
- ✓ Checks for Python (opens installer if needed)
- ✓ Checks for FFmpeg (installs via Homebrew or direct download)
- ✓ Creates virtual environment
- ✓ Installs all Python packages
- ✓ Sets up configuration
- ✓ Initializes database
- ✓ Sets up workspace directories for your channels
- ✓ Creates launch scripts and launchd service

## Troubleshooting

### "tkinter not found"

---

#### INSTALL LINUX

# Linux Installation Guide

Complete installation guide for StreamTV on Linux.

## Quick Start

Run the automated installation script:

```bash
chmod +x install_linux.sh
./install_linux.sh
```

This script will:
1. Detect your Linux distribution
2. Install Python 3.8+ and FFmpeg via package manager
3. Set up a virtual environment
4. Install all Python dependencies
5. Configure the platform
6. Initialize the database
7. Create launch scripts
8. Optionally create a systemd service
9. Optionally start the server

## Manual Installation

If you prefer to install manually:

### 1. Install System Dependencies

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv ffmpeg git
```

#### Fedora/RHEL/CentOS
```bash
sudo dnf install python3 python3-pip ffmpeg git
```

#### Arch Linux
```bash
sudo pacman -S python python-pip ffmpeg git
```

### 2. Set Up Virtual Environment

```bash
python3 -m venv ~/.streamtv/venv
source ~/.streamtv/venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### 4. Configure

```bash
cp config.example.yaml config.yaml
# Edit config.yaml as needed
nano config.yaml  # or use your preferred editor
```

### 5. Initialize Database

```bash
python3 -c "from streamtv.database.session import init_db; init_db()"
```

### 6. Create Your First Channel

After installation, you can create channels using:
- The web interface at http://localhost:8410/channels
- The API (see API documentation)
- YAML import files (see SCHEDULES.md)

---

#### INSTALL MACOS

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


---

#### QUICK START SWIFTUI

# StreamTV SwiftUI Installer - Quick Start

## 🚀 Building the Native macOS Installer

### Step 1: Build the Installer

**Option A: Using Xcode (Recommended)**
1. Open `StreamTVInstaller/StreamTVInstaller.xcodeproj` in Xcode
2. Select "My Mac" as destination
3. Press `Cmd+B` to build
4. The app will be in `StreamTVInstaller/build/StreamTV Installer.app`

**Option B: Using Build Script**
```bash
./build-installer.sh
```

### Step 2: Run the Installer

**Double-Click Method:**
1. Double-click `Install-StreamTV-SwiftUI.command`
2. The native SwiftUI installer will open
3. Click **"Start Installation"**

**Direct App Launch:**
1. Navigate to `StreamTVInstaller/build/StreamTV Installer.app`
2. Double-click the app

## ✨ Features

- **Native macOS Experience**: Built with SwiftUI
- **Beautiful Interface**: Follows macOS design guidelines
- **Smooth Animations**: Native macOS animations
- **Dark Mode**: Automatic dark mode support
- **Accessibility**: Full VoiceOver support

## 📋 What Gets Installed

Same as the Python installer:
- ✓ Python (opens installer if needed)
- ✓ FFmpeg (installs via Homebrew or direct download)
- ✓ Virtual environment
- ✓ Python dependencies
- ✓ Configuration
- ✓ Database
- ✓ Workspace directories ready for your channels
- ✓ Launch scripts

## ❓ Troubleshooting

### "Xcode not found"
Install Xcode from the App Store, then:
```bash
xcode-select --install
```

### "Build failed"
1. Make sure Xcode is up to date
2. Clean build: `rm -rf build/`
3. Rebuild in Xcode

### "App won't open"
Right-click → Open (to bypass Gatekeeper)

## 🎯 Advantages

- **Better Performance**: Native SwiftUI is faster
- **Modern UI**: Follows macOS Human Interface Guidelines
- **Better Integration**: Works seamlessly with macOS


---

#### QUICK START

# StreamTV Quick Start Guide for Linux

## 🚀 Easy Installation

### Automated Installation (Recommended)

1. **Make installer executable:**
   ```bash
   chmod +x install_linux.sh
   ```

2. **Run the installer:**
   ```bash
   ./install_linux.sh
   ```

3. **Follow the prompts:**
   - The installer will detect your Linux distribution
   - It will install Python and FFmpeg via your package manager
   - Installation will proceed automatically
   - You'll be asked if you want to create a systemd service

4. **Start the server:**
   ```bash
   ./start_server.sh
   ```
   Or if using systemd:
   ```bash
   sudo systemctl start streamtv
   ```

5. **Open Browser**: Go to http://localhost:8410

## 📋 What Gets Installed

The installer automatically:
- ✓ Detects your Linux distribution (Ubuntu/Debian, Fedora/RHEL, Arch, etc.)
- ✓ Installs Python 3.8+ via package manager
- ✓ Installs FFmpeg via package manager
- ✓ Creates virtual environment at `~/.streamtv/venv`
- ✓ Installs all Python packages
- ✓ Sets up configuration
- ✓ Initializes database
- ✓ Sets up workspace directories for your channels
- ✓ Creates launch scripts
- ✓ Optionally creates systemd service

## 🎯 After Installation

1. **Start StreamTV**: 
   ```bash
   ./start_server.sh
   ```
   Or if using systemd:
   ```bash
   sudo systemctl start streamtv
   sudo systemctl status streamtv  # Check status
   ```

2. **Open Browser**: Go to http://localhost:8410

3. **Explore the Web Interface**:
   - **Documentation**: Click "Documentation" in the sidebar to access all guides
   - **Streaming Logs**: Click "Streaming Logs" to view real-time logs and errors
   - **Self-Healing**: Click on any error in the logs to see details and auto-fix options

4. **Enjoy**: Your IPTV platform is ready!

## 🆕 Features

### Interactive Documentation

All documentation is available directly in the web interface:
- Click **"Documentation"** in the sidebar dropdown
- Browse guides: Quick Start, Beginner, Installation, API, Troubleshooting
- Click script buttons in documentation to run diagnostics

### Streaming Logs & Self-Healing

Monitor and fix issues automatically:

---

#### README

# Installation & Setup Documentation

Guides for installing and setting up StreamTV on macOS and other platforms.

---

## 🚀 Quick Start

**Start here**: [QUICK_START.md](QUICK_START.md)

---

## 📚 Documentation Files

### Quick Start Guides ⭐
- **[QUICK_START.md](QUICK_START.md)** - General quick start
- **[QUICK_START_SWIFTUI.md](QUICK_START_SWIFTUI.md)** - SwiftUI installer

### macOS Installation
- **[INSTALL_MACOS.md](INSTALL_MACOS.md)** - Automated macOS setup
- **[GUI_INSTALLER_README.md](GUI_INSTALLER_README.md)** - GUI installer guide
- **[SWIFTUI_INSTALLER_README.md](SWIFTUI_INSTALLER_README.md)** - SwiftUI installer details

### API Setup
- **[YOUTUBE_API_SETUP.md](YOUTUBE_API_SETUP.md)** - YouTube Data API configuration

---

## 🍎 macOS Quick Install

```bash
# Automated installer
./install_macos.sh

# OR SwiftUI GUI installer
./Install-StreamTV.command
```

---

## 🔗 Related Documentation

- [Main Documentation Index](INDEX.md)
- [Complete Installation Guide](INSTALLATION.md)
- [Troubleshooting](TROUBLESHOOTING.md)

---

**Start Installing**: [QUICK_START.md](QUICK_START.md)


---

#### SWIFTUI INSTALLER README

# StreamTV SwiftUI Installer for macOS

## Overview

The SwiftUI installer provides a **native macOS experience** with a beautiful, modern interface built using Apple's SwiftUI framework.

## Features

### Native macOS Experience

- **SwiftUI Interface**: Built with Apple's modern UI framework
- **Native Look & Feel**: Matches macOS design guidelines
- **Smooth Animations**: Native macOS animations and transitions
- **Accessibility**: Full VoiceOver and accessibility support
- **Dark Mode**: Automatic dark mode support

### Visual Status Indicators

Each module shows its status with native macOS icons:

- **Green Checkmark**: Module installed/updated successfully
- **Yellow Warning**: Module has issues but installation continued
- **Red Error**: Module installation failed

### Module Detection

The installer automatically detects:
- **Existing installations**: Checks if modules are already installed
- **Updates needed**: Identifies modules that need updating
- **Corrupted installations**: Detects and offers to fix corrupted modules

### Auto-Fix Capabilities

When issues are detected, the installer can:
- Recreate corrupted virtual environments
- Reinstall missing dependencies
- Fix configuration file issues
- Repair database corruption

## Building the Installer

### Option 1: Using Xcode (Recommended)

1. Open `StreamTVInstaller/StreamTVInstaller.xcodeproj` in Xcode
2. Select "My Mac" as the destination
3. Press `Cmd+B` to build
4. Press `Cmd+R` to run
5. The app will be built in `StreamTVInstaller/build/StreamTV Installer.app`

### Option 2: Using Build Script

```bash
./build-installer.sh
```

This will:
- Build the SwiftUI app
- Create a standalone `.app` bundle
- Place it in the `build/` directory

### Option 3: Using Swift Package Manager

```bash
cd StreamTVInstaller
swift build -c release
```

## Running the Installer

### Double-Click Method

1. **Build the installer** (see above)
2. **Double-click** `Install-StreamTV-SwiftUI.command`
3. The SwiftUI installer will open automatically
4. Click **"Start Installation"**
5. Wait for installation to complete
6. Click **"Fix Issues"** if any problems are detected (optional)

### Direct App Launch


---

#### YOUTUBE API SETUP

# YouTube Data API v3 Integration Guide

## Overview

StreamTV now integrates with the [YouTube Data API v3](https://developers.google.com/youtube) to improve reliability and resolve streaming issues. The API is used for:

- **Video validation** - Check if videos exist and are available before attempting to stream
- **Metadata retrieval** - Get accurate video information (title, description, thumbnails, etc.)
- **Error prevention** - Detect unavailable videos early to avoid unnecessary yt-dlp calls
- **Better error messages** - Provide clear feedback when videos are private, deleted, or unavailable

## Benefits

1. **Reduced Rate Limiting** - API validation prevents unnecessary yt-dlp requests
2. **Better Error Handling** - Know immediately if a video is unavailable
3. **Improved Reliability** - Validate videos before attempting to stream
4. **Enhanced Metadata** - Get accurate information from YouTube's official API

## Setup Instructions

### Step 1: Get a YouTube Data API v3 Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the YouTube Data API v3:
   - Navigate to "APIs & Services" > "Library"
   - Search for "YouTube Data API v3"
   - Click "Enable"
4. Create credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "API Key"
   - Copy your API key
   - (Optional) Restrict the API key to YouTube Data API v3 for security

### Step 2: Configure StreamTV

Add your API key to `config.yaml`:

```yaml
youtube:
  enabled: true
  quality: "best"
  extract_audio: false
  cookies_file: null
  use_authentication: false
  api_key: "YOUR_API_KEY_HERE"  # Add your API key
  oauth_client_id: null
  oauth_client_secret: null
  oauth_refresh_token: null
```

### Step 3: Restart StreamTV

Restart the StreamTV server for changes to take effect.

## How It Works

### With API Key (Recommended)

1. **Video Validation**: When a YouTube URL is requested, StreamTV first validates it using the YouTube Data API
2. **Availability Check**: The API checks if the video is public and available
3. **Metadata Retrieval**: If available, metadata is retrieved from the API (faster and more reliable)
4. **Stream URL Extraction**: yt-dlp is still used to get the actual streaming URL (API doesn't provide this)
5. **Error Prevention**: Unavailable videos are detected early, preventing unnecessary processing

### Without API Key (Fallback)

If no API key is configured, StreamTV falls back to the previous behavior:
- Uses yt-dlp for all operations
- No pre-validation
- May encounter more rate limiting issues

## API Quota

The YouTube Data API v3 has a default quota of **10,000 units per day**. Each API call consumes units:

- `videos.list` (get video info): **1 unit**
- `search.list` (search videos): **100 units**

For most use cases, the default quota is sufficient. If you need more:

---

### Troubleshooting Documentation

#### DATABASE ISSUES

# Database Troubleshooting Guide

Common database-related issues and their solutions.

## Database Connection Errors

### Symptoms
- `Database connection failed`
- `SQLite error`
- `database is locked`
- Server won't start

### Solutions

1. **Run database diagnostic:**
   - Use web interface: Run `check_database` script
   - Verifies database connectivity
   - Checks database integrity

2. **Check database file permissions:**
   ```bash
   ls -la streamtv.db
   chmod 644 streamtv.db  # If needed
   ```

3. **Check if database is locked:**
   ```bash
   # macOS/Linux
   lsof streamtv.db
   ```
   If locked, stop all StreamTV processes and try again.

4. **Verify database location:**
   - Check `config.yaml` for database path
   - Default: `sqlite:///./streamtv.db`
   - Ensure directory is writable

5. **Test database connection:**
   ```bash
   python3 -c "from streamtv.database.session import SessionLocal; db = SessionLocal(); print('OK'); db.close()"
   ```

## Database Corruption

### Symptoms
- `database disk image is malformed`
- Inconsistent data
- Queries fail unexpectedly
- Data appears corrupted

### Solutions

1. **Backup current database:**
   ```bash
   cp streamtv.db streamtv.db.backup
   ```

2. **Run repair script:**
   - Use web interface: Run `repair_database` script
   - Attempts to repair corrupted database
   - May recover some data

3. **If repair fails:**
   ```bash
   # Restore from backup
   cp streamtv.db.backup streamtv.db
   
   # OR recreate database
   rm streamtv.db
   python3 -c "from streamtv.database.session import init_db; init_db()"
   ```

4. **Re-import data:**
   - After recreating, re-import channels
   - Re-import media items
   - Recreate schedules

## Database Locked Errors

### Symptoms

---

#### FFMPEG ISSUES

# FFmpeg Troubleshooting Guide

Common FFmpeg-related issues and their solutions.

## FFmpeg Not Found

### Symptoms
- `ffmpeg: command not found`
- FFmpeg errors in logs
- Streaming fails immediately

### Solutions

1. **Verify FFmpeg installation:**
   ```bash
   which ffmpeg
   ffmpeg -version
   ```

2. **Install FFmpeg:**
   - See [Installation Issues](INSTALLATION_ISSUES.md) for platform-specific instructions
   - Run diagnostic: `check_ffmpeg` script

3. **Configure FFmpeg path:**
   ```yaml
   ffmpeg:
     ffmpeg_path: "/usr/local/bin/ffmpeg"  # Custom path if needed
   ```

## FFmpeg Codec Errors

### Symptoms
- "Codec not found" errors
- "Unsupported codec" messages
- Format not supported errors

### Solutions

1. **Check codec support:**
   ```bash
   ffmpeg -codecs | grep h264
   ffmpeg -codecs | grep aac
   ffmpeg -codecs | grep mp2
   ```

2. **Update FFmpeg:**
   - Newer versions have better codec support
   - Install latest version for your platform

3. **Verify required codecs:**
   - H.264 (video) - Required
   - AAC or MP2 (audio) - Required
   - MPEG-2 (for HDHomeRun output) - Required

4. **Check build configuration:**
   ```bash
   ffmpeg -buildconf
   ```
   Look for required codecs in configuration.

## FFmpeg Format Errors

### Symptoms
- "Error opening input" for specific formats
- "Invalid data found" errors
- Format not recognized

### Solutions

1. **Check format support:**
   ```bash
   ffmpeg -formats | grep mp4
   ffmpeg -formats | grep avi
   ```

2. **Test source file:**
   ```bash
   ffmpeg -i source_url -t 1 -f null -
   ```
   This tests if FFmpeg can read the source.

---

#### INSTALLATION ISSUES

# Installation Troubleshooting Guide

Common issues encountered during StreamTV installation and their solutions.

## Python Installation Issues

### Python Not Found

**Symptoms:**
- `python3: command not found`
- `Python version too old` error
- Installation script fails at Python check

**Solutions:**

**macOS:**
1. Download Python from [python.org](https://www.python.org/downloads/)
   - Choose the macOS installer for your architecture (Intel or Apple Silicon)
   - Run the installer and follow instructions
   - Verify: `python3 --version` (should show 3.8+)

2. Or use Homebrew:
   ```bash
   brew install python3
   ```

3. Run diagnostic: Use the web interface to run `check_python` script

**Windows:**
1. Download from [python.org](https://www.python.org/downloads/)
2. **Important**: Check "Add Python to PATH" during installation
3. Restart terminal/PowerShell after installation
4. Verify: `python --version`

**Linux:**
- Ubuntu/Debian: `sudo apt-get install python3 python3-pip`
- Fedora: `sudo dnf install python3 python3-pip`
- Arch: `sudo pacman -S python python-pip`

### Python Version Too Old

**Symptoms:**
- Error: "Python 3.8+ required"
- Current version is 3.7 or earlier

**Solutions:**
1. Upgrade Python to 3.8 or later
2. Verify version: `python3 --version`
3. If multiple Python versions installed, ensure `python3` points to 3.8+

## FFmpeg Installation Issues

### FFmpeg Not Found

**Symptoms:**
- `ffmpeg: command not found`
- FFmpeg errors in logs
- Streaming fails with codec errors

**Solutions:**

**macOS:**
1. **Apple Silicon (M1/M2/M3)**: Download from [evermeet.cx](https://evermeet.cx/ffmpeg/)
   ```bash
   curl -L -o /tmp/ffmpeg.zip https://evermeet.cx/ffmpeg/ffmpeg-6.1.1.zip
   unzip -q -o /tmp/ffmpeg.zip -d /tmp/
   sudo mv /tmp/ffmpeg /usr/local/bin/ffmpeg
   sudo chmod +x /usr/local/bin/ffmpeg
   ```

2. **Homebrew** (works for both Intel and Apple Silicon):
   ```bash
   brew install ffmpeg
   ```

3. Run diagnostic: Use web interface to run `check_ffmpeg` script

**Windows:**
1. Download from [ffmpeg.org](https://ffmpeg.org/download.html)
2. Extract to a folder (e.g., `C:\ffmpeg`)

---

#### NETWORK ISSUES

# Network & Connectivity Troubleshooting Guide

Common network and connectivity issues in StreamTV.

## DNS Resolution Errors

### Symptoms
- `[Errno 8] nodename nor servname provided, or not known`
- `Unable to resolve hostname`
- YouTube/Archive.org URLs fail to resolve

### Solutions

1. **Run connectivity diagnostic:**
   - Use web interface: Run `test_connectivity` script
   - Automatically detects DNS issues
   - Provides auto-fix options

2. **Flush DNS cache:**
   
   **macOS:**
   ```bash
   sudo dscacheutil -flushcache
   sudo killall -HUP mDNSResponder
   ```
   
   **Linux:**
   ```bash
   sudo systemd-resolve --flush-caches  # systemd
   # OR
   sudo service network-manager restart  # NetworkManager
   ```
   
   **Windows:**
   ```powershell
   ipconfig /flushdns
   ```

3. **Check DNS servers:**
   - Verify DNS server settings
   - Try using Google DNS (8.8.8.8, 8.8.4.4)
   - Test DNS resolution: `nslookup youtube.com`

4. **Test connectivity:**
   ```bash
   ping youtube.com
   ping archive.org
   curl https://www.google.com
   ```

5. **Auto-fix via web interface:**
   - Run `test_connectivity` script
   - If DNS issues detected, auto-fix option appears
   - Click to apply DNS cache flush (requires password)

## YouTube Streaming Issues

### Symptoms
- `yt-dlp not installed` errors
- `Unable to download API page`
- YouTube videos won't play
- Connection timeouts

### Solutions

1. **Install/update yt-dlp:**
   ```bash
   pip install yt-dlp
   # OR update
   pip install --upgrade yt-dlp
   ```
   Auto-fix available via web interface if detected.

2. **Check YouTube accessibility:**
   - Test in browser: https://www.youtube.com
   - Verify YouTube is accessible
   - Check for regional restrictions

3. **Test connectivity:**
   - Run `test_connectivity` script

---

#### PLEX INTEGRATION ISSUES

# Plex Integration Troubleshooting Guide

Common issues when integrating StreamTV with Plex Media Server.

## Plex Can't Find Tuner

### Symptoms
- Plex shows "No tuners found"
- Discovery URL doesn't work
- HDHomeRun device not appearing in Plex

### Solutions

1. **Verify StreamTV is running:**
   ```bash
   curl http://localhost:8410/hdhomerun/discover.json
   ```
   Should return JSON with device information.

2. **Check discovery URL:**
   - Use your server's IP address, not `localhost`
   - Format: `http://YOUR_IP:8410/hdhomerun/discover.json`
   - Example: `http://<your-lan-host>:8410/hdhomerun/discover.json`

3. **Verify SSDP is enabled:**
   ```yaml
   hdhomerun:
     enabled: true
     enable_ssdp: true  # Must be true for auto-discovery
   ```

4. **Check firewall:**
   - Port 8410 must be accessible
   - Port 1900 (SSDP) must be open if using auto-discovery
   - Test: `telnet YOUR_IP 8410`

5. **Manual tuner addition:**
   - Plex → Settings → Live TV & DVR
   - Add Tuner → Manual
   - Enter: `http://YOUR_IP:8410/hdhomerun/discover.json`

## Channels Not Appearing in Plex

### Symptoms
- Tuner found but no channels listed
- Channel scan shows 0 channels
- Channels exist in StreamTV but not in Plex

### Solutions

1. **Verify channels exist:**
   ```bash
   curl http://localhost:8410/api/channels
   ```
   Should return list of channels.

2. **Check channel lineup:**
   ```bash
   curl http://localhost:8410/hdhomerun/lineup.json
   ```
   Should return channel lineup.

3. **Rescan channels in Plex:**
   - Plex → Settings → Live TV & DVR
   - Click "Refresh Guide" or "Scan for Channels"
   - Wait for scan to complete

4. **Verify channel numbers:**
   - Channels must have valid numbers (e.g., "1", "2", "80")
   - Check in StreamTV web interface: http://localhost:8410/channels

5. **Check channel enablement:**
   - Ensure channels are enabled in StreamTV
   - Disabled channels won't appear in Plex

## "Error Tuning Channel" in Plex

### Symptoms
- Plex shows "Error tuning channel" for all channels
- Channels appear but won't play

---

#### STREAMING ISSUES

# Streaming Issues Troubleshooting Guide

Common issues with video streaming and playback in StreamTV.

## Channels Won't Play

### Symptoms
- Channel exists but shows "No stream available"
- Timeout errors when trying to play
- "Stream not found" message

### Solutions

1. **Verify channel is enabled:**
   - Check in web interface: http://localhost:8410/channels
   - Ensure channel has `enabled: true`
   - Disabled channels won't stream

2. **Check channel has content:**
   - Channel must have media items or schedule
   - Verify in web interface
   - Check schedule file exists if using schedules

3. **Verify schedule configuration:**
   - Check schedule file in `schedules/` directory
   - Ensure schedule is linked to channel
   - Validate schedule YAML syntax

4. **Test stream URL directly:**
   ```bash
   curl http://localhost:8410/api/channels/{channel_id}/stream
   ```
   Or use channel number:
   ```bash
   curl http://localhost:8410/hdhomerun/auto/v{channel_number}
   ```

5. **Check streaming logs:**
   - Access: http://localhost:8410/logs
   - Look for errors when accessing channel
   - Check FFmpeg errors

6. **Verify streaming mode:**
   - CONTINUOUS: Requires schedule file
   - ON_DEMAND: Can work with just media items
   - Check channel configuration

## Video Buffering or Stuttering

### Symptoms
- Video plays but buffers frequently
- Stuttering or choppy playback
- Long delays before playback starts

### Solutions

1. **Check network bandwidth:**
   - Test connection speed
   - Ensure sufficient bandwidth for streaming
   - Check for network congestion

2. **Reduce stream quality:**
   ```yaml
   youtube:
     quality: "medium"  # Instead of "best"
   ```
   Or in channel settings via web interface.

3. **Check FFmpeg performance:**
   - Monitor CPU usage during streaming
   - Check FFmpeg processes: `ps aux | grep ffmpeg`
   - Consider hardware acceleration if available

4. **Adjust buffer settings:**
   ```yaml
   streaming:
     buffer_size: 16384  # Increase buffer
     chunk_size: 2048    # Increase chunk size
   ```


---

#### TROUBLESHOOTING SCRIPTS

# Troubleshooting Scripts Documentation

StreamTV includes interactive troubleshooting scripts that use SwiftDialog to help diagnose and resolve issues. These scripts provide a user-friendly interface for common problems.

## Prerequisites

### SwiftDialog Installation

The troubleshooting scripts require SwiftDialog, a macOS dialog tool.

**Install via Homebrew:**
```bash
brew install --cask swiftdialog
```

**Manual Installation:**
1. Download from: https://github.com/swiftDialog/swiftDialog/releases
2. Install the `.pkg` file
3. Verify installation: `dialog --version`

## Available Scripts

### 1. Main Troubleshooting Script

**Location:** `scripts/troubleshoot_streamtv.sh`

**Purpose:** Comprehensive troubleshooting for all StreamTV issues

**Usage:**
```bash
cd "/path/to/StreamTV"
./scripts/troubleshoot_streamtv.sh
```

**Features:**
- Server status checking
- Channel issue diagnosis
- Streaming problem resolution
- Plex integration help
- Database troubleshooting
- Configuration validation
- Log viewing

**Menu Options:**

1. **Server Status**
   - Checks if StreamTV server is running
   - Tests server connectivity
   - Option to start server if not running

2. **Channel Issues**
   - Channel won't play
   - Channel starts from beginning
   - Channel has no content
   - Channel import failed
   - Other channel issues

3. **Streaming Issues**
   - Video won't play
   - Video keeps buffering
   - FFmpeg errors
   - Stream stops after first video
   - Other streaming issues

4. **Plex Integration**
   - Plex can't find tuner
   - Channels not appearing
   - Stream won't play
   - Guide not loading
   - Other Plex issues

5. **Database Issues**
   - Database integrity checks
   - Backup database
   - Reset database
   - View database info

6. **Configuration Issues**
   - Validate configuration
   - View configuration

---

### Authentication Documentation

#### AUTHENTICATION SYSTEM

# Authentication System Documentation

StreamTV includes comprehensive authentication support for both Archive.org and YouTube using a web-based interface.

## Overview

The authentication system provides:
- **Web interface login pages** for both services
- **Automatic credential storage** in macOS Keychain (Archive.org)
- **Automatic re-authentication** when sessions expire
- **Secure credential management** with proper storage and handling

## Archive.org Authentication

### Web Interface Login

**Access:** Settings → Archive.org (in sidebar) or `/api/auth/archive-org`

**Features:**
- Login form with username and password fields
- Shows current authentication status
- Logout button to remove credentials
- Automatic credential storage in Keychain (on macOS)

### Automatic Re-authentication

- Checks authentication status on server startup
- Re-prompts via SwiftDialog if authentication fails
- Automatically re-authenticates when accessing restricted content
- Handles session expiration gracefully

### API Endpoints

- `GET /api/auth/archive-org` - Login page
- `POST /api/auth/archive-org` - Login with credentials
- `DELETE /api/auth/archive-org` - Logout
- `GET /api/auth/archive-org/status` - Check authentication status

## YouTube Authentication

### Web Interface Login

**Access:** Settings → YouTube (in sidebar) or `/api/auth/youtube`

**Features:**
- Upload cookies file (cookies.txt format)
- Shows current authentication status
- Instructions for exporting cookies
- Remove authentication button

### Cookie File Method

**How to Export Cookies:**
1. Install browser extension:
   - Chrome/Edge: "Get cookies.txt LOCALLY"
   - Firefox: "cookies.txt"
2. Visit youtube.com and login
3. Click extension icon
4. Export cookies to cookies.txt file
5. Upload file via web interface

---

#### AUTHENTICATION

# Archive.org Authentication Guide

StreamTV supports authentication with Archive.org to access restricted content that requires a login.

## Configuration

To enable Archive.org authentication, edit your `config.yaml`:

```yaml
archive_org:
  enabled: true
  preferred_format: "h264"
  username: "your_username"  # Your Archive.org username
  password: "your_password"   # Your Archive.org password
  use_authentication: true    # Enable authentication
```

## Security Notes

⚠️ **Important Security Considerations:**

1. **Never commit credentials**: Make sure `config.yaml` is in `.gitignore` (it already is)
2. **Use environment variables**: For production, consider using environment variables instead of storing passwords in config files
3. **File permissions**: Ensure `config.yaml` has restricted permissions (e.g., `chmod 600 config.yaml`)

## How It Works

1. **Initial Login**: When authentication is enabled, StreamTV will automatically log in to Archive.org on first use
2. **Session Management**: The adapter maintains session cookies for authenticated requests
3. **Automatic Re-authentication**: If a session expires, StreamTV will automatically attempt to re-authenticate
4. **Transparent Usage**: Once configured, authentication works transparently - all Archive.org requests will use authenticated sessions

## Testing Authentication

You can test if authentication is working by:

1. Adding a restricted Archive.org item:
```bash
curl -X POST http://localhost:8410/api/media \
  -H "Content-Type: application/json" \
  -d '{
    "source": "archive_org",
    "url": "https://archive.org/details/RESTRICTED_ITEM_IDENTIFIER"
  }'
```

2. If authentication is working, you should be able to access the item. If not, you'll get a permission error.

## Troubleshooting

### Login Fails

**Symptoms**: Logs show "Archive.org login failed" or "Invalid credentials"

**Solutions**:
- Verify your username and password are correct
- Check that `use_authentication` is set to `true`
- Ensure Archive.org account is active and not locked
- Check network connectivity to Archive.org


---

#### PASSKEY AUTHENTICATION

# Apple Passkey Authentication Documentation

StreamTV now supports Apple Passkey (WebAuthn) authentication as a security layer for YouTube OAuth login, providing passwordless, biometric authentication.

## Overview

Apple Passkeys use WebAuthn technology to provide secure, passwordless authentication using:
- **Face ID** (iPhone/iPad with Face ID)
- **Touch ID** (MacBook with Touch ID)
- **Device Passcode** (fallback authentication)

Passkeys are stored securely in iCloud Keychain and sync across your Apple devices.

## How It Works

### Authentication Flow

1. **User initiates YouTube OAuth**
   - User clicks "Start OAuth with Passkey" on YouTube auth page
   - System checks if Passkey is registered

2. **Passkey Verification**
   - If registered: User authenticates with Face ID/Touch ID
   - If not registered: User creates a new Passkey first
   - Passkey verification confirms user identity

3. **Google OAuth**
   - After Passkey verification, user is redirected to Google OAuth
   - User authorizes StreamTV to access YouTube
   - OAuth tokens are stored securely

### Security Benefits

- **Phishing Resistant**: Passkeys use public-key cryptography
- **No Passwords**: Eliminates password-related security risks
- **Biometric Security**: Uses device biometrics (Face ID/Touch ID)
- **Device Bound**: Passkeys are tied to specific devices
- **Private**: Biometric data never leaves your device

## Setup

### Prerequisites

1. **Install webauthn library:**
   ```bash
   pip install webauthn
   ```

2. **Compatible Browser:**
   - Safari 16+ (macOS/iOS) - Full Passkey support
   - Chrome 108+ (macOS/Windows) - WebAuthn support
   - Edge 108+ (macOS/Windows) - WebAuthn support

3. **Device Requirements:**
   - macOS: Touch ID or device passcode
   - iOS/iPadOS: Face ID, Touch ID, or device passcode
   - Windows: Windows Hello (optional)

### Configuration


---

### Features Documentation

#### AUTO HEALER

# Auto-Healing System

StreamTV includes an intelligent auto-healing system that automatically monitors logs, detects errors, and applies fixes using AI-powered analysis.

## Features

🤖 **AI-Powered Analysis**: Uses Ollama AI to analyze errors and suggest fixes  
📊 **Pattern Detection**: Identifies recurring error patterns automatically  
🔧 **Automatic Fixes**: Applies known fixes for common issues  
📈 **Trend Analysis**: Tracks error trends over time  
💾 **Safe Backups**: Creates backups before applying any fixes  
🔄 **Continuous Monitoring**: Can run continuously to keep your system healthy  

## Requirements

### Ollama Setup

The auto-healer uses [Ollama](https://ollama.ai/) for AI-powered log analysis.

1. **Install Ollama**:
   ```bash
   # macOS
   brew install ollama
   
   # Linux
   curl -fsSL https://ollama.ai/install.sh | sh
   ```

2. **Start Ollama service**:
   ```bash
   ollama serve
   ```

3. **Pull the model** (recommended: llama3.2):
   ```bash
   ollama pull llama3.2:latest
   ```

### Python Dependencies

The auto-healer uses standard StreamTV dependencies (httpx, pyyaml, etc.) which are already installed.

## Configuration

Edit `config.yaml` to configure auto-healing:

```yaml
auto_healer:
  enabled: false  # Set to true to enable
  enable_ai: true  # Use AI for analysis
  ollama_url: http://localhost:11434
  ollama_model: llama3.2:latest
  check_interval: 30  # Minutes between checks
  apply_fixes: false  # true = auto-apply, false = dry-run
  max_fix_attempts: 3  # Max attempts per error
```

## Usage

### One-Time Health Check

---

#### ERSATZTV COMPLETE INTEGRATION

# Complete ErsatzTV Integration Status

This document confirms that all ErsatzTV-compatible features are fully integrated and operational in the StreamTV platform.

## ✅ Integration Status: COMPLETE

All ErsatzTV scheduling features have been successfully integrated and are actively used throughout the platform.

## Core Components

### 1. Schedule Parser (`streamtv/scheduling/parser.py`)

**Status:** ✅ Fully Integrated

**Features:**
- ✅ YAML import support (`import` directive)
- ✅ Reset instructions support (`reset` section)
- ✅ Content definitions parsing
- ✅ Sequence parsing
- ✅ Playout instructions parsing
- ✅ Base directory resolution for imports
- ✅ Recursive import processing

**Usage:**
```python
from streamtv.scheduling import ScheduleParser

schedule = ScheduleParser.parse_file(
    Path("schedules/mn-olympics-1980.yml"),
    base_dir=Path("schedules")
)
```

### 2. Schedule Engine (`streamtv/scheduling/engine.py`)

**Status:** ✅ Fully Integrated

**ErsatzTV Handlers Implemented:**
- ✅ `padToNext` - Pad to next time boundary (hour/half-hour)
- ✅ `padUntil` - Pad until specific time
- ✅ `waitUntil` - Wait until specific time
- ✅ `skipItems` - Skip items from collections
- ✅ `shuffleSequence` - Shuffle sequence items

**Additional Features:**
- ✅ Seeded random number generation (for consistency)
- ✅ Pre-roll, mid-roll, post-roll sequence support
- ✅ Duration-based filler with 10% tolerance
- ✅ Custom titles support
- ✅ Continuous playback generation
- ✅ Repeat logic

**Usage:**
```python
from streamtv.scheduling import ScheduleEngine

engine = ScheduleEngine(db, seed=12345)
playlist_items = engine.generate_playlist_from_schedule(
    channel, schedule, max_items=1000
)

---

#### ERSATZTV INTEGRATION

# ErsatzTV Integration - Enhanced Scheduling Features

This document describes the ErsatzTV-compatible features that have been integrated into the StreamTV platform.

## Overview

The platform now supports advanced scheduling features inspired by [ErsatzTV](https://github.com/ErsatzTV/ErsatzTV), allowing for more sophisticated channel programming while maintaining compatibility with direct streaming from YouTube and Archive.org.

## New Features

### 1. YAML Import Support

Schedule files can now import other YAML files to share common content definitions and sequences:

```yaml
import:
  - common-commercials.yml
  - shared-sequences.yml

content:
  - key: my_content
    collection: My Collection
    order: chronological
```

**How it works:**
- Imported files are processed first
- Content and sequences are merged (existing keys take precedence)
- Supports relative and absolute paths
- Imports are processed recursively

### 2. Advanced Scheduling Directives

#### `padToNext` - Pad to Next Time Boundary

Pads the schedule to the next hour or half-hour boundary:

```yaml
sequence:
  - key: my-sequence
    items:
      - padToNext: 30  # Pad to next 30-minute boundary
        content: filler_collection
        fallback: backup_filler
        filler_kind: Commercial
```

**Parameters:**
- `padToNext`: Minutes to pad to (e.g., 30 for half-hour, 60 for hour)
- `content`: Primary content collection to use for padding
- `fallback`: Fallback collection if primary is insufficient
- `filler_kind`: Type of filler (Commercial, Filler, etc.)
- `trim`: Whether to trim items to fit exactly
- `discard_attempts`: Number of items to skip if too long

#### `padUntil` - Pad Until Specific Time

Pads the schedule until a specific time:

```yaml

---

### Plex Documentation

#### PLEX API SCHEDULE INTEGRATION COMPLETE

# ✅ Plex API Schedule Integration - Complete!

## Status: Full Integration Active

Your Plex API integration for schedules and EPG has been successfully completed and is now active!

### ✅ Updated Configuration

```yaml
plex:
  enabled: true
  base_url: "http://localhost:32400"
  token: "HeyD3N9rKrtJDsRNL6-n"  ✅ Updated and active
  use_for_epg: true  ✅ Enabled for schedule integration
```

### ✅ What Has Been Integrated

1. **Plex Token Updated**
   - ✅ New token: `HeyD3N9rKrtJDsRNL6-n`
   - ✅ Token saved to config.yaml
   - ✅ Configuration verified

2. **Active Plex API Integration**
   - ✅ Plex API client initialized during EPG generation
   - ✅ Authentication with your Plex token
   - ✅ DVR detection for channel mapping
   - ✅ Schedule enhancement active

3. **EPG Generation Enhancements**
   - ✅ Plex-compatible XMLTV format
   - ✅ Channel mapping from Plex DVR (when available)
   - ✅ Enhanced metadata integration
   - ✅ Proper async client management

### 🔧 How Plex API is Used for Schedules

The EPG generation process now:

1. **Initializes Plex API Client**
   ```
   - Connects to: http://localhost:32400
   - Authenticates with token: HeyD3N9rKrtJDsRNL6-n
   - Logs successful connection
   ```

2. **Detects Plex DVRs**
   ```
   - Queries Plex for configured DVRs
   - Maps channels between StreamTV and Plex
   - Enhances channel metadata
   ```

3. **Generates Enhanced EPG**
   ```
   - Creates Plex-compatible XMLTV
   - Includes schedule data from StreamTV channels
   - Adds Plex metadata when available
   - Proper cleanup after generation
   ```

---

#### PLEX CHANNEL SCAN FIX

# Plex Channel Scan Not Showing New Channels - Fix

## Issue

After adding a new channel (e.g., Channel 80 - Magnum P.I.), rescanning with Plex tuner doesn't show the new channel.

## Root Cause

**Plex caches the HDHomeRun channel lineup** and doesn't always refresh it properly during a rescan.

---

## ✅ Verified Working

Channel 80 **IS** in the HDHomeRun lineup:

```json
{
    "GuideNumber": "80",
    "GuideName": "Magnum P.I. Complete Series",
    "URL": "http://localhost:8410/hdhomerun/auto/v80",
    "HD": 0
}
```

The channel is properly configured and exposed. Plex just needs to refresh its cache.

---

## Solution: Force Plex to Refresh

### Method 1: Remove and Re-add the DVR Source (Recommended)

This forces Plex to completely refresh the lineup:

1. **Open Plex Web Interface** (http://<your-tailscale-host>:32400/web)

2. **Go to Settings** → **Live TV & DVR**

3. **Find your StreamTV HDHomeRun device**

4. **Click the "..." menu** → **Remove Device**

5. **Wait 10 seconds**

6. **Click "Add DVR Source"** → **Select Network Device**

7. **Plex should auto-discover**: `StreamTV HDHomeRun (FFFFFFFF)`

8. **Click Continue** and follow the setup

9. **All 6 channels should now appear** (1980, 1984, 1988, 1992, 1994, **80**)

### Method 2: Restart Plex Media Server

Sometimes Plex needs a restart to refresh the lineup:

```bash
# On your Plex server machine
sudo systemctl restart plexmediaserver

---

#### PLEX CONNECTION FIX

# Plex Connection Test - Fix Applied ✅

## Issue Resolved

The Plex connection test was showing an error, but the connection is now working correctly after fixing the API client configuration.

### What Was Fixed

1. **Accept Header**: Changed from `application/json` to `application/xml` (Plex returns XML by default)
2. **Error Handling**: Improved error messages to provide specific diagnostics
3. **XML Parsing**: Added BOM handling for XML response parsing

### Connection Test Results

✅ **Connection Successful!**
- Server: Home PLEX
- Version: 1.42.2.10156-f737b826c
- URL: http://<your-tailscale-host>:32400
- Token: Configured (20 characters)

### Current Configuration

```yaml
plex:
  enabled: true
  base_url: http://<your-tailscale-host>:32400
  token: HeyD3N9rKrtJDsRNL6-n
  use_for_epg: true
```

### If You Still See Errors

1. **Refresh the Page**: The error message might be from a previous test
2. **Click "Test Connection" Again**: The improved error handling should now work
3. **Check Server Logs**: Look at `streamtv.log` for detailed error messages

### Improved Error Messages

The connection test now provides specific error messages:
- ✅ **Authentication errors**: "Authentication failed. Plex token is invalid or expired."
- ✅ **Connection errors**: "Could not connect to [URL]. Check if server is running..."
- ✅ **Timeout errors**: "Connection timed out. Server may be unreachable..."
- ✅ **HTTP errors**: Shows specific status codes and error details

### Test the Connection

You can test the connection manually:

```bash
# Test Plex server directly
curl "http://<your-tailscale-host>:32400/" \
  -H "X-Plex-Token: HeyD3N9rKrtJDsRNL6-n"

# Test via StreamTV API
curl -X POST http://localhost:8410/api/settings/plex/test
```

### Next Steps

1. **Refresh the Settings Page**: Clear any cached error messages

---

#### PLEX EPG INTEGRATION

# Plex EPG Integration Guide

## Overview

StreamTV now integrates with the [Plex Media Server API](https://developer.plex.tv/pms/#tag/EPG) to enhance EPG (Electronic Program Guide) generation and ensure full compatibility with Plex DVR functionality.

## Benefits

1. **Plex-Compatible XMLTV Format** - Ensures EPG data works seamlessly with Plex
2. **Enhanced Metadata** - Uses Plex API for channel mapping and validation
3. **Better Channel Information** - Leverages Plex's EPG data when available
4. **DVR Integration** - Compatible with Plex DVR functionality

## Configuration

### Step 1: Get Plex Authentication Token

1. Open Plex Media Server web interface
2. Go to Settings → Network
3. Enable "Show Advanced" if needed
4. Find your Plex token in the URL or use the API:
   ```bash
   # Get token from Plex server
   curl -X GET "http://YOUR_PLEX_SERVER:32400/api/v2/resources?includeHttps=1&X-Plex-Token=YOUR_TOKEN"
   ```

Alternatively, you can find your token in:
- Browser developer tools (Network tab) when accessing Plex
- Plex server logs
- Using Plex authentication flow

### Step 2: Configure StreamTV

Add Plex configuration to `config.yaml`:

```yaml
plex:
  enabled: true
  base_url: "http://<your-lan-host>:32400"  # Your Plex server URL
  token: "your-plex-token-here"  # Your Plex authentication token
  use_for_epg: true  # Enable EPG enhancement via Plex API
```

### Step 3: Restart StreamTV

Restart the server for changes to take effect.

## How It Works

### With Plex Integration Enabled

1. **Channel Validation**: Plex API validates channel mappings
2. **Metadata Enhancement**: Uses Plex EPG data when available
3. **Format Compliance**: Ensures XMLTV output is fully Plex-compatible
4. **Channel Mapping**: Maps StreamTV channels to Plex EPG channels

### Without Plex Integration

StreamTV generates standard XMLTV format that is compatible with Plex, but without Plex-specific enhancements.


---

#### PLEX INTEGRATION COMPLETE

# ✅ Plex Token Integration Complete!

## Status: Configuration Updated

Your Plex authentication token has been successfully integrated into StreamTV!

### Current Configuration

```yaml
plex:
  enabled: true
  base_url: "http://localhost:32400"
  token: "HeyD3N9rKrtJDsRNL6"  ✅ Configured
  use_for_epg: true
```

### ✅ What's Been Done

1. **Token Added**: Plex token has been saved to `config.yaml`
2. **Configuration Verified**: Settings load successfully
3. **EPG Enhancements Active**: All Plex-compatible features are enabled

### 🔧 Token Validation Note

If you're seeing authentication errors, the token might need to be:

1. **Longer**: Plex tokens are typically 20+ characters
   - Your current token: `HeyD3N9rKrtJDsRNL6` (16 characters)
   - Typical Plex tokens are longer alphanumeric strings

2. **Full Token**: Make sure you copied the complete token from:
   - Browser Developer Tools → Network → Request Headers → `X-Plex-Token`
   - Should be a long string like: `abcdefghijklmnopqrstuvwxyz1234567890`

3. **Alternative**: If the token is incomplete, you can:
   - Get the full token again using: `python3 scripts/get_plex_token.py`
   - Or check browser console: `window.localStorage.getItem('token')`

### 🎯 EPG Features Still Active

Even if the Plex API connection needs the full token, **all EPG enhancements are active**:

✅ **Plex-Compatible XMLTV Format**
- Proper channel IDs
- Multiple display names
- Absolute URLs for logos/thumbnails
- Language attributes on all fields

✅ **Enhanced Metadata**
- Required fields always included
- Standard XMLTV format
- At least one programme per channel

✅ **DVR Compatibility**
- Works seamlessly with Plex DVR
- Proper time formatting
- Valid XML structure

### 📝 Update Token (If Needed)


---

#### PLEX SCHEDULE INTEGRATION

# ✅ Plex API Schedule Integration Complete

## Status: Full Integration Enabled

Your Plex API integration for schedules/EPG has been successfully configured and activated!

### Current Configuration

```yaml
plex:
  enabled: true
  base_url: "http://localhost:32400"
  token: "HeyD3N9rKrtJDsRNL6-n"  ✅ Updated and configured
  use_for_epg: true  ✅ Active for schedule integration
```

### ✅ What's Been Integrated

1. **Plex API Client Integration**
   - ✅ Client initialized during EPG generation
   - ✅ Authentication with your Plex token
   - ✅ DVR detection and channel mapping support

2. **Schedule/EPG Enhancement**
   - ✅ Active use of Plex API during EPG generation
   - ✅ Channel mapping from Plex DVR (if configured)
   - ✅ Enhanced metadata from Plex sources

3. **Plex-Compatible Format**
   - ✅ XMLTV format optimized for Plex
   - ✅ Proper channel IDs and display names
   - ✅ Absolute URLs for media assets
   - ✅ Language attributes on all fields

### 🔧 How It Works

The EPG generation now:

1. **Initializes Plex API Client**
   - Connects to your Plex server at `http://localhost:32400`
   - Authenticates using your token
   - Logs successful connection

2. **Enhances Channel Mapping**
   - Detects configured Plex DVRs
   - Maps channels between StreamTV and Plex
   - Enhances channel metadata

3. **Generates EPG**
   - Creates Plex-compatible XMLTV format
   - Includes all schedule data from your channels
   - Adds enhanced metadata from Plex when available

### 📊 Integration Features

#### Active Features:
- ✅ **Plex API Connection**: Active during EPG generation
- ✅ **DVR Detection**: Automatically detects Plex DVRs
- ✅ **Channel Mapping**: Maps StreamTV channels to Plex EPG
- ✅ **Metadata Enhancement**: Uses Plex data when available

---

#### PLEX SETUP COMPLETE

# Plex API Integration - Setup Complete! ✅

## Current Status

Your Plex API integration has been configured with:

✅ **Enabled**: `true`  
✅ **Base URL**: `http://localhost:32400` (detected automatically)  
✅ **EPG Enhancement**: `true`  
⏳ **Token**: Needs to be configured (see below)

## Next Step: Get Your Plex Token

To complete the setup, you need to add your Plex authentication token.

### Quick Method

Run this helper script:
```bash
python3 scripts/get_plex_token.py
```

This will:
- Open your Plex Web App in a browser
- Show detailed instructions
- Guide you through extracting the token

### Manual Method

1. **Open Plex Web App**:
   - http://localhost:32400/web
   - OR https://app.plex.tv/desktop

2. **Open Browser Developer Tools**:
   - macOS: `Cmd + Option + I`
   - Windows/Linux: `F12`

3. **Go to Network Tab**

4. **Refresh the page**

5. **Find a request** and check:
   - Request Headers
   - Look for `X-Plex-Token` parameter
   - Copy the token value

### Alternative: Browser Console

1. Open Developer Tools → Console tab
2. Type: `window.localStorage.getItem('token')`
3. Press Enter
4. Copy the returned value

## Update Configuration

Once you have your token, update `config.yaml`:

```yaml
plex:
  enabled: true

---


## Additional Resources

- [Full Documentation Index](Documents/XCode Projects/StreamTV/StreamTV-Linux/docs/INDEX.md)
- [API Reference](Documents/XCode Projects/StreamTV/StreamTV-Linux/docs/API.md)
- [Troubleshooting Guide](Documents/XCode Projects/StreamTV/StreamTV-Linux/docs/TROUBLESHOOTING.md)
