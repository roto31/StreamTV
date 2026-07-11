# Installation Guide

Complete installation documentation for all platforms.

## Quick Start

# StreamTV Quick Start Guide for macOS

## 🚀 Easy Installation (Double-Click Method)

### For macOS Users

**Option 1: SwiftUI Installer (Native macOS - Recommended)**

1. **Build the installer first** (see BUILD_SWIFTUI.md or use Xcode)
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

- **SwiftUI**: `Install-StreamTV-SwiftUI.command` - Native macOS experience (requires build)
- **Python GUI**: `Install-StreamTV.command` - Python-based GUI (no build needed)
- **Shell Script**: `./install-gui.sh` - Run from Terminal
- **Command-Line**: `./install_macos.sh` - Traditional installer

## 📋 What Gets Installed

The installer automatically:
- ✓ Checks for Python (opens installer if needed)
- ✓ Checks for FFmpeg (installs via Homebrew or direct download)
- ✓ Creates virtual environment
- ✓ Installs all Python packages
- ✓ Sets up configuration
- ✓ Initializes database
- ✓ Creates default channels
- ✓ Creates launch scripts
- ✓ **Optional**: AI Troubleshooting Assistant (Ollama) - Prompts during installation

## 🎯 After Installation

1. **Start StreamTV**: Run `~/.streamtv/start_server.sh` or `./start_server.sh`
2. **Open Browser**: Go to http://localhost:8410
3. **Explore the Web Interface**:
   - **Documentation**: Click "Documentation" in the sidebar to access all guides
   - **Streaming Logs**: Click "Streaming Logs" to view real-time logs and errors
   - **Self-Healing**: Click on any error in the logs to see details and auto-fix options
4. **Enjoy**: Your IPTV platform is ready!

## 🆕 New Features

### Interactive Documentation

All documentation is now available directly in the web interface:

- Click **"Documentation"** in the sidebar dropdown
- Browse guides: Quick Start, Beginner, Installation, Path Independence, GUI Installer, SwiftUI Installer
- Click script buttons in documentation to run diagnostics
- Access troubleshooting guides from the **"Troubleshooting"** dropdown

### Streaming Logs & Self-Healing

Monitor and fix issues automatically:

- **Access**: Click **"Streaming Logs"** in the Resources section
- **Real-Time Monitoring**: See logs as they happen (Server-Sent Events)
- **Error Detection**: Errors and warnings are automatically highlighted
- **Click for Details**: Click any error/warning to see:
  - Full error context (20 lines before/after)
  - Matched troubleshooting scripts
  - **"Self-Heal" button** to automatically run fixes
- **Auto-Fix Prompts**: When scripts detect fixable issues (e.g., missing yt-dlp, DNS issues), you'll be prompted to apply fixes automatically

### AI-Powered Troubleshooting Assistant

During installation, you'll be prompted to optionally install Ollama for AI-powered troubleshooting:

- **What is it?**: An AI assistant that analyzes errors and suggests fixes
- **Storage**: ~9 GB total (Ollama base + AI model)
- **Cost**: 100% free - runs entirely on your Mac
- **Models**: The installer scans your hardware and shows available models
- **Recommended**: Mistral 7B (~4GB) - best balance of quality and size
- **Skip**: You can skip this and install later if desired

**Features**:
- Analyzes log errors and provides explanations
- Suggests fixes based on your system configuration
- Learns from patterns in your logs
- Completely private - no data leaves your Mac

### Interactive Troubleshooting

Run diagnostic scripts directly from the web interface:

- **From Documentation**: Click script buttons (e.g., "Run Script: test_connectivity")
- **From Logs**: Click "Self-Heal" on error detail pages
- **Available Scripts**:
  - Network diagnostics (with DNS auto-fix for macOS)
  - Python/FFmpeg verification
  - Database integrity checks
  - Port availability checks

## ❓ Troubleshooting

### "tkinter not found"
- On macOS, tkinter should be included with Python
- If missing, reinstall Python from python.org

### "Python not found"
- The installer will download and open Python installer automatically
- After installation, run the installer again

### "FFmpeg not found"
- The installer will try Homebrew first
- Then direct download for Apple Silicon
- Or provide manual installation instructions

### "Permission denied"
Make files executable:
```bash
chmod +x Install-StreamTV.command
chmod +x install-gui.sh
```

### GUI Doesn't Open
1. Make sure you're not running via SSH
2. Check Python and tkinter are installed
3. Try running from Terminal: `./install-gui.sh`

## 📚 More Information

- See `README.md` for full documentation
- See `GUI_INSTALLER_README.md` for detailed GUI installer info
- See `PATH_INDEPENDENCE.md` for path independence details


---

## GUI INSTALLER README

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
- ✓ Creates default channels
- ✓ Creates launch scripts and launchd service

## Troubleshooting

### "tkinter not found"

On macOS, tkinter should be included with Python. If you see this error:
1. Reinstall Python from python.org (not Homebrew Python)
2. Or install tkinter separately (rarely needed)

### "Python not found"

The installer will:
1. Download Python installer automatically
2. Open the installer for you
3. After installation, run the installer again

### "FFmpeg not found"

The installer will try:
1. Homebrew installation (if Homebrew is installed)
2. Direct download for Apple Silicon
3. Manual installation instructions if both fail

### Permission Errors

If you see permission errors:
1. Make files executable: `chmod +x Install-StreamTV.command`
2. For system-wide installation, you may need to run with sudo (not recommended)

### GUI Doesn't Open

If the GUI doesn't open:
1. Make sure you're not running via SSH
2. Check that Python and tkinter are installed
3. Try running from Terminal: `./install-gui.sh`
4. Check Console.app for error messages

## After Installation

Once installation is complete:
1. Start StreamTV using `~/.streamtv/start_server.sh`
2. Or run: `./start_server.sh` (if in StreamTV directory)
3. Access the web interface at: http://localhost:8410
4. Enjoy your IPTV streaming platform!

## Command-Line Alternative

If you prefer command-line installation:
```bash
./install_macos.sh
```

## Path Independence

The installer works from any location:
- Move it to any folder
- Run from USB drive
- Create shortcuts anywhere
- Works even if symlinked

See `PATH_INDEPENDENCE.md` for details.


---

## INSTALL MACOS

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
7. Create default channels
8. Create launch scripts
9. Optionally start the server

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

### 7. Create Channels

```bash
python3 scripts/create_channel.py
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

---

## QUICK START SWIFTUI

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
- ✓ Default channels
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

## SWIFTUI INSTALLER README

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

1. Navigate to `StreamTVInstaller/build/StreamTV Installer.app`
2. **Double-click** the app
3. The installer will open

### From Terminal

```bash
open "build/StreamTV Installer.app"
```

## Requirements

- **macOS**: 11.0 (Big Sur) or later
- **Xcode**: 13.0 or later (for building)
- **Swift**: 5.5 or later

## What Gets Installed

The installer automatically:
- ✓ Checks for Python (opens installer if needed)
- ✓ Checks for FFmpeg (installs via Homebrew or direct download)
- ✓ Creates virtual environment
- ✓ Installs all Python packages
- ✓ Sets up configuration
- ✓ Initializes database
- ✓ Creates default channels
- ✓ Creates launch scripts and launchd service

## Advantages Over Tkinter

### Native Experience
- **Better Performance**: Native SwiftUI is faster than Tkinter
- **Modern UI**: Follows macOS Human Interface Guidelines
- **Better Integration**: Works seamlessly with macOS features

### User Experience
- **Smooth Animations**: Native macOS animations
- **Dark Mode**: Automatic dark mode support
- **Accessibility**: Full VoiceOver support
- **Native Dialogs**: Uses macOS native alert dialogs

### Development
- **Type Safety**: Swift's type system prevents errors
- **Modern Language**: Swift is Apple's modern language
- **Better Tooling**: Xcode provides excellent debugging

## Troubleshooting

### "Xcode not found"

To build the SwiftUI installer, you need Xcode:
1. Install Xcode from the App Store
2. Open Xcode and accept the license
3. Install command line tools: `xcode-select --install`

### "Build failed"

If the build fails:
1. Make sure Xcode is up to date
2. Check that all Swift files are in `StreamTVInstaller/` directory
3. Try cleaning the build: `rm -rf build/`
4. Rebuild using Xcode

### "App won't open"

If the app won't open:
1. Right-click the app → Open (to bypass Gatekeeper)
2. Check System Preferences → Security & Privacy
3. Make sure the app is notarized (for distribution)


---

## YOUTUBE API SETUP

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
1. Go to Google Cloud Console
2. Navigate to "APIs & Services" > "Quotas"
3. Request a quota increase

## Troubleshooting

### API Key Invalid

**Error**: `YouTube API quota exceeded or API key invalid`

**Solutions**:
1. Verify your API key is correct in `config.yaml`
2. Ensure YouTube Data API v3 is enabled in Google Cloud Console
3. Check API key restrictions (if any) allow YouTube Data API v3

### Quota Exceeded

**Error**: `YouTube API quota exceeded`

**Solutions**:
1. Wait for quota reset (daily at midnight Pacific Time)
2. Request quota increase in Google Cloud Console
3. StreamTV will fall back to yt-dlp-only mode

### Video Not Found

**Error**: `YouTube video not found via API`

**Possible Causes**:
- Video ID is invalid
- Video has been deleted
- Video is private/unlisted (if not authenticated)

**Solutions**:
- Verify the YouTube URL is correct
- Check if video is still available on YouTube
- For private videos, use cookies authentication

## Features

### Video Validation

The API validates videos before attempting to stream:

```python
# Example validation result
{
    'valid': True,
    'video_id': 'dQw4w9WgXcQ',
    'available': True,
    'info': {
        'title': 'Video Title',
        'duration': 212,
        'thumbnail': 'https://...',
        ...
    },
    'error': None
}
```

### Enhanced Error Messages

With API integration, you get clearer error messages:

- **Before**: "Error getting YouTube video info"
- **After**: "YouTube video unavailable: Video is private"

### Metadata Quality

API-provided metadata is more accurate:

---

## Related Pages

- [macOS](macOS)
- [Windows](Windows)
- [Linux](Linux)
- [Home](Home)
