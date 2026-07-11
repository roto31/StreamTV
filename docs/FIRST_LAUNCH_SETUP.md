# First Launch Setup Guide

## Overview

StreamTV performs automatic dependency setup on first launch. This guide explains the process and how to troubleshoot issues.

## First Launch Process

### macOS

1. **Dependency Check**: App checks for Python and FFmpeg
2. **Homebrew Cellar Check**: Searches `/opt/homebrew/Cellar/ffmpeg` for FFmpeg 7.1.1+
3. **Bundled Extraction**: If not found, extracts bundled dependencies
4. **System Fallback**: Falls back to system installations if available
5. **Error Display**: Shows installation guide if dependencies not found

**UI**: SwiftUI `FirstLaunchView` with progress indicators

1. **First Launch GUI**: `first_launch_gui.py` launches automatically
2. **Dependency Check**: Checks for Python 3.10+ and FFmpeg 7.1.1+
3. **Bundled Extraction**: Extracts from `bundled/` directory if needed
4. **System Fallback**: Uses system installations if available
5. **Progress Display**: Shows extraction progress with progress bar

**UI**: tkinter-based GUI window

### Linux

1. **First Launch GUI**: `first_launch_gui.py` launches automatically
2. **Dependency Check**: Checks for Python 3.10+ and FFmpeg 7.1.1+
3. **Bundled Extraction**: Extracts from `bundled/` directory if needed
4. **System Fallback**: Uses system installations if available
5. **Progress Display**: Shows extraction progress with progress bar

**UI**: tkinter or GTK-based GUI window

## Dependency Resolution Flow

```
First Launch
    ↓
Check Homebrew Cellar (macOS only)
    ↓ [Found?] → Use Homebrew FFmpeg (if version >= 7.1.1)
    ↓ [Not Found?]
Check Bundled Dependencies
    ↓ [Found?] → Extract to Application Support → Use Bundled
    ↓ [Not Found?]
Check System Installation
    ↓ [Found?] → Use System
    ↓ [Not Found?]
Show Installation Guide
```

## Extraction Locations

### macOS
- **Python**: `~/Library/Application Support/StreamTV/python/`
- **FFmpeg**: `~/Library/Application Support/StreamTV/ffmpeg/`

- **Python**: `%USERPROFILE%\.streamtv\python\`
- **FFmpeg**: `%USERPROFILE%\.streamtv\ffmpeg\`

### Linux
- **Python**: `~/.streamtv/python/`
- **FFmpeg**: `~/.streamtv/ffmpeg/`

## Version Requirements

### Python
- **Minimum**: 3.10
- **Bundled**: 3.12.7
- **Check**: `python3 --version` or `python --version`

### FFmpeg
- **Minimum**: 7.1.1
- **Bundled**: Latest stable
- **Check**: `ffmpeg -version`

## Troubleshooting

### macOS

#### Issue: FirstLaunchView shows dependencies as missing

**Symptoms**:
- Python or FFmpeg marked as ❌
- "Please install the required dependencies" message

**Solutions**:
1. **Check Homebrew Cellar**: Verify `/opt/homebrew/Cellar/ffmpeg` exists
2. **Check Version**: Ensure FFmpeg version is >= 7.1.1
3. **Check Bundled**: Verify app bundle contains dependencies
4. **System Install**: Install Python/FFmpeg via Homebrew or python.org

#### Issue: Extraction fails

**Symptoms**:
- Progress bar stuck
- Error message in status label

**Solutions**:
1. **Check Permissions**: Ensure write access to Application Support
2. **Check Disk Space**: Ensure sufficient free space (~200 MB)
3. **Check Bundle**: Verify bundled dependencies exist in app bundle
4. **Manual Extraction**: Extract manually from app bundle if needed

#### Issue: Homebrew Cellar detection not working

**Symptoms**:
- FFmpeg found in Cellar but not detected
- Version check fails

**Solutions**:
1. **Check Version**: Ensure version is >= 7.1.1
2. **Check Path**: Verify `/opt/homebrew/Cellar/ffmpeg` exists
3. **Check Binaries**: Verify `bin/ffmpeg` and `bin/ffprobe` exist
4. **Manual Check**: Run `ffmpeg -version` to verify

#### Issue: First launch GUI doesn't appear

**Symptoms**:
- App launches but no GUI window
- Error in console about tkinter

**Solutions**:
1. **Install tkinter**: Ensure Python with tkinter support
2. **Check Python**: Verify Python 3.10+ is installed
3. **Manual Launch**: Run `python first_launch_gui.py` manually

#### Issue: Extraction fails

**Symptoms**:
- Progress bar stuck
- Error dialog appears

**Solutions**:
1. **Check Permissions**: Ensure write access to user directory
2. **Check Disk Space**: Ensure sufficient free space
3. **Check Bundle**: Verify `bundled/` directory exists
4. **Antivirus**: Check if antivirus is blocking file operations

### Linux

#### Issue: GUI library not available

**Symptoms**:
- Error about tkinter or GTK not found
- GUI doesn't launch

**Solutions**:
1. **Install tkinter**: `sudo apt-get install python3-tk` (Debian/Ubuntu)
2. **Install GTK**: `sudo apt-get install python3-gi` (Debian/Ubuntu)
3. **Check Python**: Verify Python 3.10+ is installed

#### Issue: Extraction fails

**Symptoms**:
- Progress bar stuck
- Error message

**Solutions**:
1. **Check Permissions**: Ensure write access to `~/.streamtv/`
2. **Check Disk Space**: Ensure sufficient free space
3. **Check Bundle**: Verify `bundled/` directory exists
4. **Check Executable**: Ensure extracted binaries have execute permissions

## Manual Setup

If automatic setup fails, you can manually set up dependencies:

### macOS

1. **Install Python**:
   ```bash
   brew install python3
   # or download from python.org
   ```

2. **Install FFmpeg**:
   ```bash
   brew install ffmpeg
   ```

3. **Verify**:
   ```bash
   python3 --version
   ffmpeg -version
   ```

1. **Install Python**: Download from [python.org](https://www.python.org/downloads/)
2. **Install FFmpeg**: Download from [ffmpeg.org](https://ffmpeg.org/download.html)
3. **Add to PATH**: Ensure both are in system PATH
4. **Verify**: Run `python --version` and `ffmpeg -version`

### Linux

1. **Install Python**:
   ```bash
   sudo apt-get install python3 python3-pip  # Debian/Ubuntu
   sudo yum install python3 python3-pip      # RHEL/CentOS
   ```

2. **Install FFmpeg**:
   ```bash
   sudo apt-get install ffmpeg  # Debian/Ubuntu
   sudo yum install ffmpeg      # RHEL/CentOS
   ```

3. **Verify**:
   ```bash
   python3 --version
   ffmpeg -version
   ```

## Resetting First Launch

To trigger first launch setup again:

### macOS
```bash
rm -rf ~/Library/Application\ Support/StreamTV
# Then relaunch app
```

```powershell
Remove-Item -Recurse -Force $env:USERPROFILE\.streamtv
# Then relaunch app
```

### Linux
```bash
rm -rf ~/.streamtv
# Then relaunch app
```

## Related Documentation

- [BUNDLING_DEPENDENCIES.md](BUNDLING_DEPENDENCIES.md) - Bundling process
- [Installation Guide](../README.md) - General installation
