# Troubleshooting Scripts

Automated diagnostic tools for StreamTV.

## Overview

StreamTV includes interactive troubleshooting scripts that use SwiftDialog to help diagnose and fix common issues.

## Available Scripts

### StreamTV Troubleshooting

```bash
./scripts/troubleshoot_streamtv.sh
```

This script checks:
- Python installation and version
- Virtual environment setup
- Dependencies installation
- Database connectivity
- Configuration validity
- Server status
- Port availability
- Network connectivity

### Plex Troubleshooting

```bash
./scripts/troubleshoot_plex.sh
```

This script checks:
- Plex server connectivity
- HDHomeRun emulation status
- M3U playlist accessibility
- EPG generation
- Stream accessibility

## Using Troubleshooting Scripts

### Interactive Mode

The scripts use SwiftDialog for interactive diagnosis:

1. **Run the script:**
   ```bash
   ./scripts/troubleshoot_streamtv.sh
   ```

2. **Follow prompts:**
   - Script will check various components
   - Shows results in dialog boxes
   - Provides fix suggestions

3. **Apply fixes:**
   - Script may offer to apply fixes automatically
   - Review changes before applying
   - Restart services as needed

### Non-Interactive Mode

Run with `--quiet` flag:
```bash
./scripts/troubleshoot_streamtv.sh --quiet
```

Output will be to console only.

## What Gets Checked

### System Checks
- Python version (3.8+)
- Required system packages
- Disk space
- Permissions

### Application Checks
- Virtual environment
- Dependencies
- Configuration file
- Database
- Log files

### Network Checks
- Port availability
- Firewall rules
- DNS resolution
- Connectivity

### Service Checks
- Server status
- Process running
- Log errors
- Resource usage

## Fix Suggestions

The scripts provide fix suggestions for common issues:

### Missing Dependencies
```bash
# Script suggests:
pip install -r requirements.txt
```

### Configuration Issues
```bash
# Script suggests:
cp config.example.yaml config.yaml
# Edit config.yaml
```

### Database Issues
```bash
# Script suggests:
rm streamtv.db
python -m streamtv.main
```

### Port Conflicts
```bash
# Script suggests:
# Change port in config.yaml
server:
  port: 8500
```

## Manual Troubleshooting

If scripts don't resolve the issue:

1. **Check logs:**
   ```bash
   tail -f streamtv.log
   ```

2. **Verify configuration:**
   ```bash
   python -c "from streamtv.config import load_config; print(load_config())"
   ```

3. **Test database:**
   ```bash
   sqlite3 streamtv.db ".tables"
   ```

4. **Check network:**
   ```bash
   curl http://localhost:8410/
   ```

## Script Output

### Success
```
✓ Python 3.11.0 found
✓ Virtual environment active
✓ All dependencies installed
✓ Database connected
✓ Configuration valid
✓ Server running on port 8410
```

### Issues Found
```
✗ Python version too old (3.7)
  → Install Python 3.8+
  
✗ Missing dependency: fastapi
  → Run: pip install -r requirements.txt
  
✗ Port 8410 already in use
  → Change port in config.yaml
```

## Related Documentation

- [Troubleshooting Scripts Guide](../docs/TROUBLESHOOTING_SCRIPTS.md) - Detailed documentation
- [Troubleshooting](Troubleshooting) - General troubleshooting
- [Common Issues](Common-Issues) - Frequently encountered problems
- [Error Messages](Error-Messages) - Understanding errors

