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

