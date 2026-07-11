# Dependency Bundling Guide

## Overview

StreamTV bundles Python and FFmpeg dependencies with the application to eliminate the need for users to manually install these dependencies. This improves the first-launch experience and reduces installation errors.

## Architecture

### Dependency Resolution Priority

The application uses a fallback strategy to find dependencies:

1. **Homebrew Cellar (macOS only)**: Checks `/opt/homebrew/Cellar/ffmpeg` for FFmpeg 7.1.1+
2. **Bundled Dependencies**: Extracted from app bundle to Application Support
3. **System Dependencies**: Uses system-installed Python/FFmpeg
4. **Error**: Shows installation guide if none found

### Bundle Structure

#### macOS (SwiftUI App)
```
StreamTV.app/Contents/
  Resources/
    python/
      Python.framework/          # Python 3.12 framework
    ffmpeg/
      ffmpeg                     # FFmpeg static binary
      ffprobe                    # FFprobe static binary
    streamtv/                    # Python modules (existing)
    requirements.txt              # Python dependencies (existing)
```

#### Windows
```
StreamTV/
  bundled/
    python/                      # Python 3.12 embeddable
      python.exe
      pythonw.exe
      python312.dll
      ...
    ffmpeg/                      # FFmpeg static build
      ffmpeg.exe
      ffprobe.exe
  streamtv/                      # Python modules
  requirements.txt
```

#### Linux
```
StreamTV/
  bundled/
    python/                      # Python 3.12 standalone
      bin/python3
      lib/python3.12/
      ...
    ffmpeg/                      # FFmpeg static build
      ffmpeg
      ffprobe
  streamtv/                      # Python modules
  requirements.txt
```

## Platform-Specific Implementation

### macOS

**Bundling Script**: `scripts/bundle-dependencies-macos.sh`

- Downloads Python 3.12 framework from python.org
- Downloads FFmpeg static build for macOS (Apple Silicon + Intel)
- Extracts and organizes into app bundle structure
- Signs bundled binaries (for notarization)

**Extraction Location**: `~/Library/Application Support/StreamTV/`

**Special Features**:
- Homebrew Cellar detection for FFmpeg (bypasses installation if version >= 7.1.1)
- Automatic extraction on first launch
- Progress indicators in FirstLaunchView

### Windows

**Bundling Script**: `scripts/bundle-dependencies-windows.ps1`

- Downloads Python 3.12 embeddable distribution
- Downloads FFmpeg static build for Windows
- Extracts to `bundled/` directory structure

**Extraction Location**: `%USERPROFILE%\.streamtv\`

**First Launch GUI**: `StreamTV-Windows/first_launch_gui.py`
- tkinter-based GUI
- Shows extraction progress
- Handles dependency extraction

### Linux

**Bundling Script**: `scripts/bundle-dependencies-linux.sh`

- Downloads Python 3.12 standalone build (or uses system Python wrapper)
- Downloads FFmpeg static build for Linux
- Extracts to `bundled/` directory structure

**Extraction Location**: `~/.streamtv/`

**First Launch GUI**: `StreamTV-Linux/first_launch_gui.py`
- tkinter or GTK-based GUI
- Shows extraction progress
- Handles dependency extraction

### Containers

**No Bundling**: Containers use system packages installed during Docker build.

See [BUNDLING.md](../StreamTV-Containers/docker-compose/BUNDLING.md) for details.

## Version Requirements

- **Python**: 3.10+ (bundled: 3.12.7)
- **FFmpeg**: 7.1.1+ (bundled: latest stable)

## Building with Bundled Dependencies

### macOS

1. Run bundling script:
   ```bash
   ./scripts/bundle-dependencies-macos.sh
   ```

2. Build app:
   ```bash
   ./StreamTVApp/build-app.sh
   ```

The bundling script is automatically called during the build process.

### Windows

1. Run bundling script:
   ```powershell
   .\scripts\bundle-dependencies-windows.ps1
   ```

2. Dependencies will be available in `bundled/` directory

### Linux

1. Run bundling script:
   ```bash
   ./scripts/bundle-dependencies-linux.sh
   ```

2. Dependencies will be available in `bundled/` directory

## Size Considerations

Bundled dependencies increase app size:

- **Python Framework**: ~50-80 MB
- **FFmpeg Binaries**: ~30-50 MB
- **Total Increase**: ~100-180 MB

This is acceptable for desktop applications and significantly improves user experience.

## Update Process

### Updating Bundled Dependencies

1. Update version numbers in bundling scripts
2. Run bundling script for target platform
3. Rebuild application
4. Test extraction process

### Updating Python Dependencies

Python dependencies (from `requirements.txt`) are installed into the virtual environment at first launch, not bundled. To update:

1. Update `requirements.txt`
2. Users will get updated dependencies on next launch (if venv is recreated)

## Troubleshooting

### macOS

**Issue**: Bundled dependencies not found
- **Solution**: Ensure bundling script ran successfully before build
- **Check**: Verify `StreamTV.app/Contents/Resources/python/` and `ffmpeg/` exist

**Issue**: Homebrew Cellar detection not working
- **Solution**: Ensure FFmpeg version is >= 7.1.1
- **Check**: Verify `/opt/homebrew/Cellar/ffmpeg` exists and contains valid binaries

### Windows

**Issue**: First launch GUI not appearing
- **Solution**: Ensure Python with tkinter is installed
- **Check**: Run `python -m tkinter` to test

**Issue**: Extraction fails
- **Solution**: Check file permissions and disk space
- **Check**: Verify `bundled/` directory exists and contains dependencies

### Linux

**Issue**: GTK GUI not working
- **Solution**: Install `python3-gi` or use tkinter version
- **Check**: Verify GUI library is available

## Related Documentation

- [FIRST_LAUNCH_SETUP.md](FIRST_LAUNCH_SETUP.md) - First launch process
- [BUNDLING.md](../StreamTV-Containers/docker-compose/BUNDLING.md) - Container bundling (no bundling)

