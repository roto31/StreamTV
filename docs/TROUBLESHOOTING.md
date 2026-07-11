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

### Port Already in Use

**Symptoms**: `Address already in use` or server won't start

**Solutions**:

1. Run diagnostic: [Run Script: check_ports](script:check_ports)
2. Change port in `config.yaml`:
   ```yaml
   server:
     port: 8500
   ```
3. **macOS**: Stop existing service:
   ```bash
   launchctl unload ~/Library/LaunchAgents/com.retro-tv-simulator.plist
   ```
4. **Linux**: Find and kill process:
   ```bash
   sudo lsof -i :8410
   sudo kill -9 <PID>
   ```
5. **Windows**: Find and kill process:
   ```powershell
   netstat -ano | findstr :8410
   taskkill /PID <PID> /F
   ```

### Virtual Environment Issues

**Symptoms**: Import errors, missing packages, or activation failures

**Solutions**:

1. Remove and recreate virtual environment:
   ```bash
   rm -rf ~/.streamtv/venv
   python3 -m venv ~/.streamtv/venv
   ```

2. Activate and reinstall dependencies:
   ```bash
   source ~/.streamtv/venv/bin/activate  # Linux/macOS
   # OR
   ~/.streamtv/venv/Scripts/activate  # Windows
   
   pip install --upgrade pip setuptools wheel
   pip install -r requirements.txt
   ```

3. Check Python path:
   ```bash
   which python3  # Should point to venv Python
   ```

## Network & Connectivity Issues

### DNS Resolution Errors

**Symptoms**: `[Errno 8] nodename nor servname provided, or not known` or `Unable to resolve hostname`

**Solutions**:

1. Run diagnostic: [Run Script: test_connectivity](script:test_connectivity)
2. **macOS**: Flush DNS cache:
   ```bash
   sudo dscacheutil -flushcache
   sudo killall -HUP mDNSResponder
   ```
3. **Linux**: Flush DNS cache:
   ```bash
   sudo systemd-resolve --flush-caches  # systemd
   # OR
   sudo service network-manager restart  # NetworkManager
   ```
4. **Windows**: Flush DNS cache:
   ```powershell
   ipconfig /flushdns
   ```
5. Check DNS servers in network settings
6. Try using Google DNS (8.8.8.8, 8.8.4.4)

### YouTube Streaming Issues

**Symptoms**: `yt-dlp not installed`, `Unable to download API page`, or YouTube videos won't play

**Solutions**:

1. Run diagnostic: [Run Script: test_connectivity](script:test_connectivity)
2. Install/update yt-dlp:
   ```bash
   pip install yt-dlp
   # OR update
   pip install --upgrade yt-dlp
   ```
3. Check YouTube accessibility in browser
4. Verify network connectivity to YouTube
5. Check firewall settings

### Archive.org Streaming Issues

**Symptoms**: Archive.org videos won't load or timeout errors

**Solutions**:

1. Run diagnostic: [Run Script: test_connectivity](script:test_connectivity)
2. Check Archive.org accessibility in browser
3. Verify network connectivity
4. Check if authentication is required (configure in settings)

## Database Issues

### Database Connection Errors

**Symptoms**: `Database connection failed`, `SQLite error`, or database locked

**Solutions**:

1. Run diagnostic: [Run Script: check_database](script:check_database)
2. Check database file permissions:
   ```bash
   ls -la streamtv.db
   chmod 644 streamtv.db  # If needed
   ```
3. Check if database is locked:
   ```bash
   # macOS/Linux
   lsof streamtv.db
   ```
4. Repair database: [Run Script: repair_database](script:repair_database)
5. Backup and recreate if corrupted:
   ```bash
   cp streamtv.db streamtv.db.backup
   rm streamtv.db
   python3 -c "from streamtv.database.session import init_db; init_db()"
   ```

### Database Corruption

**Symptoms**: `database disk image is malformed` or inconsistent data

**Solutions**:

1. Backup current database
2. Run repair: [Run Script: repair_database](script:repair_database)
3. If repair fails, restore from backup or recreate database
4. Re-import channels and media

## Streaming Issues

### Channels Won't Play

**Symptoms**: Channel exists but shows "No stream available" or timeout

**Solutions**:

1. Check channel is enabled in web interface
2. Verify channel has content (media items)
3. Check channel schedule is configured
4. View streaming logs for errors
5. Test stream URL directly:
   ```bash
   curl http://localhost:8410/api/channels/{channel_id}/stream
   ```

### Video Buffering or Stuttering

**Symptoms**: Video plays but buffers frequently or stutters

**Solutions**:

1. Check network bandwidth
2. Reduce stream quality in config:
   ```yaml
   youtube:
     quality: "medium"  # Instead of "best"
   ```
3. Check FFmpeg performance
4. Monitor system resources (CPU, RAM, disk I/O)
5. Check for network latency issues

### FFmpeg Errors

**Symptoms**: FFmpeg crashes, format errors, or codec issues

**Solutions**:

1. Update FFmpeg to latest version
2. Check FFmpeg supports required codecs:
   ```bash
   ffmpeg -codecs | grep h264
   ```
3. Check FFmpeg logs in streaming logs
4. Verify source video format is supported
5. Try different FFmpeg options in config

## Configuration Issues

### Configuration File Errors

**Symptoms**: `YAML syntax error`, `Invalid configuration`, or config not loading

**Solutions**:

1. Validate YAML syntax:
   ```bash
   python3 -c "import yaml; yaml.safe_load(open('config.yaml'))"
   ```
2. Check indentation (YAML is sensitive to spaces)
3. Verify all required fields are present
4. Compare with `config.example.yaml`
5. Reset to defaults if needed

### Settings Not Saving

**Symptoms**: Changes in web interface don't persist

**Solutions**:

1. Check file permissions on `config.yaml`
2. Verify write access to config directory
3. Check for syntax errors preventing save
4. Restart server after changes
5. Check logs for save errors

## Service/Background Process Issues

### Server Won't Start

**Symptoms**: Server fails to start or crashes immediately

**Solutions**:

1. Check logs: `tail -f streamtv.log`
2. Verify Python and dependencies are installed
3. Check port availability: [Run Script: check_ports](script:check_ports)
4. Verify database is accessible: [Run Script: check_database](script:check_database)
5. Check configuration file syntax
6. Try running directly:
   ```bash
   python3 -m streamtv.main
   ```

### Service Won't Stay Running

**Symptoms**: Service starts but stops immediately

**Solutions**:

1. **macOS**: Check LaunchAgent logs:
   ```bash
   log show --predicate 'process == "streamtv"' --last 1h
   ```

2. **Linux**: Check systemd logs:
   ```bash
   journalctl -u streamtv -n 50
   ```

3. **Windows**: Check Event Viewer for errors

4. Verify service configuration file syntax
5. Check for permission issues
6. Verify working directory is correct

## Performance Issues

### High CPU Usage

**Symptoms**: Server uses excessive CPU resources

**Solutions**:

1. Reduce number of concurrent streams
2. Lower stream quality settings
3. Check for infinite loops in logs
4. Monitor FFmpeg processes
5. Consider hardware limitations

### High Memory Usage

**Symptoms**: Server uses excessive RAM

**Solutions**:

1. Reduce buffer sizes in config:
   ```yaml
   streaming:
     buffer_size: 4096  # Reduce from default
   ```
2. Limit concurrent connections
3. Check for memory leaks in logs
4. Restart server periodically
5. Monitor with system tools

### Slow Response Times

**Symptoms**: Web interface is slow or API calls timeout

**Solutions**:

1. Check database performance
2. Optimize database queries
3. Check network latency
4. Monitor system resources
5. Consider database indexing improvements

## Getting Help

### Before Asking for Help

1. **Check Logs**: Always check streaming logs first
2. **Run Diagnostics**: Use the diagnostic scripts above
3. **Check Documentation**: Review installation and configuration guides
4. **Search Issues**: Check if others have encountered the same problem

### Information to Provide

When asking for help, include:

1. **Error Messages**: Exact error text from logs
2. **System Information**: OS, Python version, FFmpeg version
3. **Configuration**: Relevant parts of `config.yaml` (remove sensitive data)
4. **Steps to Reproduce**: What you did before the error occurred
5. **Diagnostic Results**: Output from diagnostic scripts

### Support Resources

- **Web Interface**: Use the built-in troubleshooting tools
- **Streaming Logs**: Check real-time logs with error detection
- **Self-Healing**: Use automatic fix suggestions
- **AI Troubleshooting**: Install Ollama for AI-powered help
- **Documentation**: Browse guides in the web interface
- **GitHub Issues**: Report bugs and request features

## Advanced Troubleshooting

### Debug Mode

Enable debug logging for more detailed information:

```yaml
logging:
  level: "DEBUG"
  file: "streamtv.log"
```

### Manual Testing

Test individual components:

1. **Test Database**:
   ```bash
   python3 -c "from streamtv.database.session import SessionLocal; db = SessionLocal(); print('OK')"
   ```

2. **Test API**:
   ```bash
   curl http://localhost:8410/health
   curl http://localhost:8410/api/channels
   ```

3. **Test Streaming**:
   ```bash
   curl http://localhost:8410/api/channels/{channel_id}/stream
   ```

### Log Analysis

Analyze logs for patterns:

```bash
# Find errors
grep -i error streamtv.log

# Find warnings
grep -i warning streamtv.log

# Monitor in real-time
tail -f streamtv.log | grep -i error
```

## Prevention

### Best Practices

1. **Regular Backups**: Backup database and configuration regularly
2. **Monitor Logs**: Check logs periodically for warnings
3. **Keep Updated**: Update dependencies and StreamTV regularly
4. **Test Changes**: Test configuration changes before deploying
5. **Document Changes**: Keep notes of configuration changes

### Maintenance

1. **Clear Cache**: [Run Script: clear_cache](script:clear_cache) periodically
2. **Check Database**: [Run Script: check_database](script:check_database) regularly
3. **Monitor Resources**: Watch CPU, RAM, and disk usage
4. **Review Logs**: Check for recurring errors or warnings
5. **Update Dependencies**: Keep Python packages updated

---

*For platform-specific troubleshooting, see the installation guides in the Documentation section.*

