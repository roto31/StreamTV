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
- **Access**: Click **"Streaming Logs"** in the Resources section
- **Real-Time Monitoring**: See logs as they happen
- **Error Detection**: Errors and warnings are automatically highlighted
- **Click for Details**: Click any error/warning to see full context and fix options
- **Self-Heal**: Automatically run fixes for common issues

## 🔧 Running as a Service

### Using Systemd (Recommended)

The installer can create a systemd service automatically. To set it up manually:

1. **Create service file:**
   ```bash
   sudo nano /etc/systemd/system/streamtv.service
   ```

2. **Add configuration:**
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

## 🔧 Troubleshooting

### Python Not Found

Install via package manager:
```bash
# Ubuntu/Debian
sudo apt install python3 python3-pip python3-venv

# Fedora/RHEL/CentOS
sudo dnf install python3 python3-pip

# Arch Linux
sudo pacman -S python python-pip
```

### FFmpeg Not Found

Install via package manager:
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# Fedora/RHEL/CentOS
sudo dnf install ffmpeg

# Arch Linux
sudo pacman -S ffmpeg
```

### Permission Denied

Make scripts executable:
```bash
chmod +x install_linux.sh
chmod +x start_server.sh
```

### Firewall Configuration

Allow port 8410:
```bash
# UFW (Ubuntu/Debian)
sudo ufw allow 8410/tcp

# Firewalld (Fedora/RHEL/CentOS)
sudo firewall-cmd --add-port=8410/tcp --permanent
sudo firewall-cmd --reload
```

### Port Already in Use

If port 8410 is in use, change it in `config.yaml`:
```yaml
server:
  port: 8411  # Use different port
```

## 📚 Next Steps

- [Linux Installation Guide](INSTALL_LINUX.md) - Detailed installation instructions
- [API Documentation](../API.md) - Complete API reference
- [Troubleshooting](../TROUBLESHOOTING.md) - Common issues and solutions
- [Full Documentation Index](../INDEX.md) - All available documentation

## 💡 Tips

- Use systemd for running as a background service
- Check logs with `journalctl -u streamtv -f` if using systemd
- Check `streamtv.log` for application logs
- Use `./verify-installation.sh` to check your setup
- Keep terminal open while testing (close only when using systemd)
