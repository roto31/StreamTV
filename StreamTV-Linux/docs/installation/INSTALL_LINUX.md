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

- [Quick Start Guide](../QUICKSTART.md)
- [Configuration Guide](../CONFIGURATION.md)
- [API Documentation](../API.md)
- [Troubleshooting](../TROUBLESHOOTING.md)
