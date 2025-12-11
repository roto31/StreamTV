# StreamTV macOS Distribution Checklist

## Pre-Distribution Verification

### Core Application Files
- [x] `streamtv/` - Core application code
- [x] `requirements.txt` - Python dependencies
- [x] `config.example.yaml` - Configuration template
- [x] `.gitignore` - Git ignore patterns

### Installation & Launch Scripts
- [x] `install_macos.sh` - Automated installation script
- [x] `Install-StreamTV.command` - Double-click installer launcher
- [x] `Start-StreamTV.command` - Double-click server launcher
- [x] `start_server.sh` - Server startup script
- [x] `create-dmg.sh` - DMG creation script (optional)

### Documentation
- [x] `README.md` - Main readme
- [x] `INSTALL.md` - Installation guide
- [x] `CHANGELOG.md` - Version history
- [x] `VERSION` - Version number

### Data & Configuration
- [x] `schedules/` - Example schedule files
- [x] `schemas/` - JSON schemas
- [x] `data/channel_icons/` - Channel icons
- [x] `data/channels_example.yaml` - Example channel configuration

### Scripts & Utilities
- [x] `scripts/` - Utility scripts

## Distribution Package Contents

### Required Files
1. **Application Code**: All Python modules in `streamtv/`
2. **Dependencies**: `requirements.txt`
3. **Configuration**: `config.example.yaml`
4. **Installation**: `install_macos.sh`
5. **Documentation**: README, INSTALL, CHANGELOG

### Optional Files
- Example schedules
- Channel icons
- Utility scripts

## Testing Checklist

Before distribution, verify:

1. **Installation**
   - [ ] Run `./install_macos.sh` on clean macOS system
   - [ ] Verify Python 3.8+ is detected/installed
   - [ ] Verify FFmpeg is detected/installed
   - [ ] Verify virtual environment is created
   - [ ] Verify dependencies are installed

2. **Configuration**
   - [ ] Verify `config.yaml` is created from example
   - [ ] Verify default settings work

3. **Server Startup**
   - [ ] Verify server starts without errors
   - [ ] Verify web interface is accessible
   - [ ] Verify API endpoints respond

4. **Functionality**
   - [ ] Verify HDHomeRun discovery works
   - [ ] Verify IPTV playlist generation
   - [ ] Verify channel streaming works
   - [ ] Verify Plex integration (if configured)

## Distribution Methods

### Option 1: ZIP Archive
```bash
cd StreamTV-macOS
zip -r ../StreamTV-macOS-v1.0.0.zip . -x "*.pyc" "__pycache__/*" ".DS_Store"
```

### Option 2: DMG Package
```bash
./create-dmg.sh
```

### Option 3: Git Repository
```bash
git init
git add .
git commit -m "StreamTV macOS Distribution v1.0.0"
```

## File Size Optimization

Before distribution:
- Remove `__pycache__/` directories
- Remove `*.pyc` files
- Remove `.DS_Store` files
- Remove development files (`.git/`, `.cursor/`)
- Remove virtual environments (`venv/`)
- Remove database files (`*.db`)

## Version Information

- **Version**: 1.0.0
- **Platform**: macOS 10.15+
- **Python**: 3.8+
- **FFmpeg**: 6.0+
