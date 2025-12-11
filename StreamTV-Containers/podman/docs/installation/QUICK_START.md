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
- ✓ Sets up workspace directories for your channels
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

