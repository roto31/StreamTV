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
3. Add to PATH:
   - System Properties → Environment Variables
   - Add `C:\ffmpeg\bin` to PATH
4. Or use Chocolatey: `choco install ffmpeg`

**Linux:**
- Ubuntu/Debian: `sudo apt-get install ffmpeg`
- Fedora: `sudo dnf install ffmpeg`
- Arch: `sudo pacman -S ffmpeg`

### FFmpeg Version Issues

**Symptoms:**
- FFmpeg installed but wrong version
- Codec errors or format not supported

**Solutions:**
1. Check version: `ffmpeg -version`
2. Update to latest version (6.0+ recommended)
3. Verify codec support: `ffmpeg -codecs | grep h264`

## Virtual Environment Issues

### Import Errors After Installation

**Symptoms:**
- `ModuleNotFoundError` when starting server
- Packages not found despite installation

**Solutions:**
1. **Verify virtual environment is activated:**
   ```bash
   which python3  # Should point to venv Python
   ```

2. **Recreate virtual environment:**
   ```bash
   rm -rf ~/.streamtv/venv
   python3 -m venv ~/.streamtv/venv
   source ~/.streamtv/venv/bin/activate  # macOS/Linux
   # OR
   ~/.streamtv/venv/Scripts/activate  # Windows
   ```

3. **Reinstall dependencies:**
   ```bash
   pip install --upgrade pip setuptools wheel
   pip install -r requirements.txt
   ```

### Virtual Environment Not Found

**Symptoms:**
- `venv/bin/activate: No such file or directory`
- Installation script can't find virtual environment

**Solutions:**
1. Check if virtual environment was created:
   ```bash
   ls -la ~/.streamtv/venv  # macOS/Linux
   ```

2. Recreate if missing:
   ```bash
   python3 -m venv ~/.streamtv/venv
   ```

3. Run installation script again

## Port Conflicts

### Port Already in Use

**Symptoms:**
- `Address already in use` error
- Server won't start on port 8410

**Solutions:**
1. **Run diagnostic**: Use web interface `check_ports` script

2. **Change port in config.yaml:**
   ```yaml
   server:
     port: 8500  # Use different port
   ```

3. **Find and stop conflicting process:**
   ```bash
   # macOS/Linux
   lsof -i :8410
   kill -9 <PID>
   
   # Windows
   netstat -ano | findstr :8410
   taskkill /PID <PID> /F
   ```

4. **Stop existing StreamTV service:**
   ```bash
   # macOS
   launchctl unload ~/Library/LaunchAgents/com.streamtv.plist
   
   # Linux
   sudo systemctl stop streamtv
   ```

## Installation Script Failures

### Script Permission Denied

**Symptoms:**
- `Permission denied` when running install script
- Script won't execute

**Solutions:**
1. Make script executable:
   ```bash
   chmod +x install_macos.sh
   ```

2. Run with explicit interpreter:
   ```bash
   bash install_macos.sh
   # OR
   zsh install_macos.sh
   ```

### Script Hangs or Times Out

**Symptoms:**
- Installation script stops responding
- Hangs at dependency installation

**Solutions:**
1. Check internet connection
2. Try manual installation (see INSTALL.md)
3. Install dependencies one at a time:
   ```bash
   pip install fastapi
   pip install uvicorn
   # etc.
   ```

### Database Initialization Fails

**Symptoms:**
- `Database initialization failed`
- `Permission denied` on database file

**Solutions:**
1. Check directory permissions:
   ```bash
   ls -la .  # Check current directory permissions
   ```

2. Create database manually:
   ```bash
   python3 -c "from streamtv.database.session import init_db; init_db()"
   ```

3. Check disk space:
   ```bash
   df -h .  # macOS/Linux
   ```

## Post-Installation Verification

### Verify Installation

Run the verification script:
```bash
./verify-installation.sh
```

This checks:
- ✓ Python installation
- ✓ FFmpeg availability
- ✓ Virtual environment
- ✓ Dependencies installed
- ✓ Application code present
- ✓ Configuration file

### Common Post-Installation Issues

**Server won't start:**
1. Check logs: `tail -f streamtv.log`
2. Verify all dependencies: `pip list`
3. Test database: Run `check_database` script
4. Try running directly: `python3 -m streamtv.main`

**Web interface not accessible:**
1. Verify server is running: `ps aux | grep streamtv`
2. Check firewall settings
3. Verify port in config matches URL
4. Try `http://localhost:8410` first

**Configuration not loading:**
1. Check `config.yaml` exists
2. Validate YAML syntax
3. Compare with `config.example.yaml`
4. Check file permissions

## Getting Help

If installation issues persist:

1. **Check logs**: Review installation logs and error messages
2. **Run diagnostics**: Use all available diagnostic scripts
3. **System information**: Note your OS, Python version, FFmpeg version
4. **Error messages**: Copy exact error text
5. **Steps taken**: Document what you've tried

See also:
- [Main Troubleshooting Guide](../TROUBLESHOOTING.md)
- [Troubleshooting Scripts](TROUBLESHOOTING_SCRIPTS.md)
- [Installation Guide](../INSTALLATION.md)
