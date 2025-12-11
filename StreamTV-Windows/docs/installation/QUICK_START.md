# StreamTV Quick Start Guide for Windows

## 🚀 Easy Installation

### PowerShell Installation (Recommended)

1. **Open PowerShell as Administrator:**
   - Right-click Start menu → Windows PowerShell (Admin)
   - Or search for "PowerShell" → Right-click → Run as administrator

2. **Set Execution Policy (if needed):**
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

3. **Run the installer:**
   ```powershell
   cd C:\path\to\StreamTV-Windows
   .\install_windows.ps1
   ```

4. **Follow the prompts:**
   - The installer will check for Python and FFmpeg
   - If missing, it will guide you to install them
   - Installation will proceed automatically

5. **Start the server:**
   ```powershell
   .\start_server.ps1
   ```
   Or double-click `start_server.bat`

6. **Open Browser**: Go to http://localhost:8410

## 📋 What Gets Installed

The installer automatically:
- ✓ Checks for Python (guides installation if needed)
- ✓ Checks for FFmpeg (installs via Chocolatey/Scoop or guides manual installation)
- ✓ Creates virtual environment at `%USERPROFILE%\.streamtv\venv`
- ✓ Installs all Python packages
- ✓ Sets up configuration
- ✓ Initializes database
- ✓ Sets up workspace directories for your channels
- ✓ Creates launch scripts

## 🎯 After Installation

1. **Start StreamTV**: 
   - Double-click `start_server.bat`
   - Or run `.\start_server.ps1` in PowerShell
   - Or use: `%USERPROFILE%\.streamtv\start_server.bat`

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
- **Access**: Click **"Streaming Logs"** in the Resources section
- **Real-Time Monitoring**: See logs as they happen
- **Error Detection**: Errors and warnings are automatically highlighted
- **Click for Details**: Click any error/warning to see full context and fix options
- **Self-Heal**: Automatically run fixes for common issues

## 🔧 Troubleshooting

### PowerShell Execution Policy

If you get an execution policy error:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Python Not Found

- Ensure Python is installed from [python.org](https://www.python.org/downloads/)
- Check "Add Python to PATH" during installation
- Restart PowerShell after installation
- Verify: `python --version`

### FFmpeg Not Found

Install via:
- **Chocolatey**: `choco install ffmpeg`
- **Scoop**: `scoop install ffmpeg`
- **Manual**: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

### Port Already in Use

If port 8410 is in use, change it in `config.yaml`:
```yaml
server:
  port: 8411  # Use different port
```

## 📚 Next Steps

- [Windows Installation Guide](INSTALL_WINDOWS.md) - Detailed installation instructions
- [API Documentation](../API.md) - Complete API reference
- [Troubleshooting](../TROUBLESHOOTING.md) - Common issues and solutions
- [Full Documentation Index](../INDEX.md) - All available documentation

## 💡 Tips

- Use PowerShell for better script support
- Keep PowerShell window open while server is running
- Check logs in `streamtv.log` for detailed information
- Use `verify-installation.bat` to check your setup
