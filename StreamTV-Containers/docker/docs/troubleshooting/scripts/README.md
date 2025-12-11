# Troubleshooting Scripts

This directory contains standalone troubleshooting scripts that can be run from the command line when the web UI is not available.

## Quick Start

All scripts can be run directly from this directory:

```bash
cd docs/troubleshooting/scripts
python3 check_python.py
python3 check_ffmpeg.py
python3 check_database.py
python3 check_ports.py
python3 test_connectivity.py
python3 repair_database.py
python3 clear_cache.py
```

Or from the StreamTV root directory:

```bash
python3 docs/troubleshooting/scripts/check_python.py
```

## Available Scripts

### Diagnostic Scripts

#### check_python.py
**Purpose:** Verifies Python installation and version

**Usage:**
```bash
python3 check_python.py
```

**What it checks:**
- Python version (requires 3.8+)
- Python executable path
- pip availability
- Virtual environment status

#### check_ffmpeg.py
**Purpose:** Verifies FFmpeg installation and version

**Usage:**
```bash
python3 check_ffmpeg.py
```

**What it checks:**
- FFmpeg installation
- FFmpeg version
- Required codec support (H.264, AAC, MP2)

#### check_database.py
**Purpose:** Checks database integrity and connectivity

**Usage:**
```bash
python3 check_database.py
```

**What it checks:**
- Database file existence
- Database connection
- Database contents (channels, media items, playlists)
- Database integrity

**Note:** Must be run from StreamTV root directory or with proper Python path.

#### check_ports.py
**Purpose:** Checks if required ports are available

**Usage:**
```bash
python3 check_ports.py
```

**What it checks:**
- StreamTV server port (default: 8410)
- HDHomeRun port (5004)
- Port availability

#### test_connectivity.py
**Purpose:** Tests network connectivity to media sources

**Usage:**
```bash
python3 test_connectivity.py
```

**What it checks:**
- DNS resolution (YouTube, Archive.org, etc.)
- HTTP/HTTPS connectivity
- YouTube accessibility
- yt-dlp installation and functionality

**Features:**
- Auto-detects DNS issues
- Provides fix recommendations
- Tests multiple domains

### Repair Scripts

#### repair_database.py
**Purpose:** Attempts to repair corrupted database

**Usage:**
```bash
python3 repair_database.py
```

**What it does:**
- Creates automatic backup before repair
- Runs SQLite integrity check
- Attempts VACUUM to optimize database
- Tries to recover corrupted data

**Warning:** Always creates a backup before attempting repair.

### Maintenance Scripts

#### clear_cache.py
**Purpose:** Clears application cache

**Usage:**
```bash
python3 clear_cache.py
```

**What it clears:**
- Application cache directories
- Python `__pycache__` directories
- Temporary cache files

### Interactive Scripts

#### troubleshoot_streamtv.sh
**Purpose:** Comprehensive interactive troubleshooting (requires SwiftDialog)

**Usage:**
```bash
./troubleshoot_streamtv.sh
```

**Features:**
- Server status checking
- Channel issue diagnosis
- Streaming problem resolution
- Plex integration help
- Database troubleshooting
- Configuration validation
- Log viewing

**Requirements:**
- SwiftDialog (install via: `brew install --cask swiftdialog`)

#### troubleshoot_plex.sh
**Purpose:** Specialized troubleshooting for Plex integration

**Usage:**
```bash
./troubleshoot_plex.sh
```

**Features:**
- Plex connection testing
- Tuner discovery verification
- Channel mapping checks
- EPG guide validation
- Stream testing

**Requirements:**
- SwiftDialog (install via: `brew install --cask swiftdialog`)

#### view-logs.sh
**Purpose:** View and search StreamTV logs

**Usage:**
```bash
./view-logs.sh              # View recent logs
./view-logs.sh search ERROR # Search for errors
./view-logs.sh open         # Open logs directory in Finder
```

**Features:**
- Real-time log viewing
- Error searching
- Log file navigation
- Open logs directory

## Running Scripts

### From Troubleshooting Directory

```bash
cd docs/troubleshooting/scripts
python3 check_python.py
```

### From StreamTV Root

```bash
python3 docs/troubleshooting/scripts/check_python.py
```

### Making Scripts Executable

```bash
chmod +x docs/troubleshooting/scripts/*.py
chmod +x docs/troubleshooting/scripts/*.sh
```

## Script Output

All scripts provide:
- Clear status messages (✓ for success, ✗ for errors, ⚠ for warnings)
- Detailed diagnostic information
- Actionable solutions
- Exit codes (0 for success, non-zero for errors)

## Integration with Web UI

These scripts are also available via the web interface:
- Access: http://localhost:8410/docs/troubleshooting
- Click script buttons to run diagnostics
- View results in browser

When the web UI is not available, use these command-line scripts instead.

## Troubleshooting the Scripts

### "Module not found" Errors

If you get import errors:
1. Make sure you're running from StreamTV root directory
2. Or set PYTHONPATH:
   ```bash
   export PYTHONPATH=/path/to/StreamTV:$PYTHONPATH
   python3 docs/troubleshooting/scripts/check_database.py
   ```

### "Permission denied" Errors

Make scripts executable:
```bash
chmod +x docs/troubleshooting/scripts/*.py
chmod +x docs/troubleshooting/scripts/*.sh
```

### Scripts Not Found

Ensure you're in the correct directory:
```bash
cd /path/to/StreamTV-macOS
python3 docs/troubleshooting/scripts/check_python.py
```

## See Also

- [Troubleshooting Scripts Documentation](../TROUBLESHOOTING_SCRIPTS.md)
- [Main Troubleshooting Guide](../../TROUBLESHOOTING.md)
- [Installation Issues](../INSTALLATION_ISSUES.md)
