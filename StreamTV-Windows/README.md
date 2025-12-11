# StreamTV - Windows Distribution

StreamTV is an efficient online media streaming platform that emulates HDHomeRun tuners for integration with Plex, Emby, and Jellyfin.

## What's Included

- **StreamTV Core**: Complete streaming platform
- **Installation Scripts**: Automated setup for Windows (PowerShell)
- **Documentation**: Complete guides and API documentation
- **Example Configurations**: Ready-to-use channel examples

## Quick Installation

### PowerShell Installation (Recommended)

1. **Open PowerShell as Administrator:**
   - Right-click Start menu → Windows PowerShell (Admin)
   - Or search for "PowerShell" → Right-click → Run as administrator

2. **Run the installer:**
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   .\install_windows.ps1
   ```

3. **Start the server:**
   ```powershell
   .\start_server.ps1
   ```
   Or double-click `start_server.bat`

4. **Access the web interface:**
   Open http://localhost:8410 in your browser

### Manual Installation

1. **Install Python 3.8+** from [python.org](https://www.python.org/downloads/)
   - Check "Add Python to PATH" during installation

2. **Install FFmpeg:**
   - Using Chocolatey: `choco install ffmpeg`
   - Using Scoop: `scoop install ffmpeg`
   - Or download from [ffmpeg.org](https://ffmpeg.org/download.html)

3. **Create virtual environment:**
   ```cmd
   python -m venv venv
   venv\Scripts\activate
   ```

4. **Install dependencies:**
   ```cmd
   pip install -r requirements.txt
   ```

5. **Configure:**
   ```cmd
   copy config.example.yaml config.yaml
   REM Edit config.yaml as needed
   ```

6. **Run StreamTV:**
   ```cmd
   python -m streamtv.main
   ```

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
StreamTV-Windows/
├── streamtv/              # Core application code
├── scripts/               # Utility scripts
├── docs/                  # Complete documentation
├── schedules/             # Schedule YAML files (empty - user creates)
├── data/                  # Data directory
│   ├── channel_icons/    # Channel icons
│   └── channels_example.yaml
├── schemas/               # JSON schemas for validation
├── config.example.yaml    # Example configuration
├── requirements.txt       # Python dependencies
├── install_windows.ps1    # Windows installer (PowerShell)
├── start_server.bat       # Start server (Batch)
├── start_server.ps1       # Start server (PowerShell)
├── verify-installation.bat # Verify installation
└── README.md              # This file
```

## Windows-Specific Notes

### PowerShell Execution Policy

If you encounter execution policy errors, run:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Running as a Service

To run StreamTV as a Windows service, you can use:
- **NSSM** (Non-Sucking Service Manager): https://nssm.cc/
- **Windows Task Scheduler**: Create a task that runs at startup

### Firewall Configuration

Windows Firewall may block the server. To allow it:
1. Open Windows Defender Firewall
2. Click "Allow an app or feature"
3. Add Python or the StreamTV executable

### Path Issues

If Python or FFmpeg are not found:
- Ensure they are added to your system PATH
- Restart PowerShell/Command Prompt after installation
- Verify with: `python --version` and `ffmpeg -version`

## Troubleshooting

See the [Troubleshooting Guide](docs/TROUBLESHOOTING.md) for common issues and solutions.

For Windows-specific issues, see:
- [Installation Issues](docs/troubleshooting/INSTALLATION_ISSUES.md)
- [Windows Troubleshooting Scripts](docs/troubleshooting/scripts/README.md)

## Documentation

Complete documentation is available in the `docs/` directory:
- [Quick Start Guide](docs/QUICKSTART.md)
- [Installation Guide](docs/INSTALLATION.md)
- [API Documentation](docs/API.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Full Documentation Index](docs/INDEX.md)

## Support

For issues, questions, or contributions:
- Check the documentation first
- Review troubleshooting guides
- Use the built-in diagnostic scripts

## License

See LICENSE file for details.
