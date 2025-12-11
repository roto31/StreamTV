# StreamTV - Linux Distribution

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

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure:**
   ```bash
   cp config.example.yaml config.yaml
   # Edit config.yaml as needed
   ```

5. **Run StreamTV:**
   ```bash
   python3 -m streamtv.main
   ```

## Running as a Systemd Service

The installer can create a systemd service for you. To set it up manually:

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
StreamTV-Linux/
├── streamtv/              # Core application code
├── scripts/               # Utility scripts
├── docs/                  # Complete documentation
├── schedules/             # Schedule YAML files (empty - user creates)
├── data/                  # Data directory
│   ├── channel_icons/     # Channel icons
│   └── channels_example.yaml
├── schemas/               # JSON schemas for validation
├── config.example.yaml     # Example configuration
├── requirements.txt        # Python dependencies
├── install_linux.sh       # Linux installer
├── start_server.sh         # Start server script
├── verify-installation.sh  # Verify installation
└── README.md               # This file
```

## Linux-Specific Notes

### Distribution Support

StreamTV supports:
- **Ubuntu/Debian**: Full support via apt
- **Fedora/RHEL/CentOS**: Full support via dnf
- **Arch Linux**: Full support via pacman
- **Other distributions**: Manual installation required

### Permissions

- The installer creates files in `~/.streamtv/`
- For systemd service, ensure the user has proper permissions
- Log files are created in the application directory

### Firewall Configuration

If using a firewall (ufw, firewalld, etc.), allow port 8410:
```bash
# UFW
sudo ufw allow 8410/tcp

# Firewalld
sudo firewall-cmd --add-port=8410/tcp --permanent
sudo firewall-cmd --reload
```

### SELinux

If SELinux is enabled and causing issues:
```bash
# Check SELinux status
getenforce

# If enforcing, you may need to set appropriate contexts
# or run in permissive mode for testing
```

## Troubleshooting

See the [Troubleshooting Guide](docs/TROUBLESHOOTING.md) for common issues and solutions.

For Linux-specific issues, see:
- [Installation Issues](docs/troubleshooting/INSTALLATION_ISSUES.md)
- [Linux Troubleshooting Scripts](docs/troubleshooting/scripts/README.md)

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
