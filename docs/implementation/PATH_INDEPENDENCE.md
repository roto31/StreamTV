# Path Independence - Installation Scripts

## Overview

All StreamTV installation scripts are designed to work from **any location** on your system. You can:
- Move the installer to any folder
- Run it from a USB drive
- Run it from a network location
- Create shortcuts anywhere

## How It Works

### macOS Scripts

**install_gui.py:**
- Uses `__file__` and `Path.resolve()` to get absolute script path
- Handles symlinks correctly with `resolve()`
- Changes working directory to script location
- Sets PYTHONPATH to ensure imports work
- All file references use absolute paths

**install-gui.sh:**
- Uses `readlink -f` to resolve symlinks (with fallback for macOS)
- Gets absolute script directory
- Changes to script directory before execution
- Works from any location

**Install-StreamTV.command:**
- Uses proper path resolution for macOS
- Handles both GUI and terminal environments
- Works when double-clicked from Finder

## Testing Path Independence

### macOS

1. **Copy installer to different location:**
   ```bash
   cp install_gui.py /tmp/test/
   cd /tmp/test
   python3 install_gui.py
   ```

2. **Create symlink:**
   ```bash
   ln -s /path/to/StreamTV/install_gui.py ~/Desktop/install
   cd ~/Desktop
   python3 install
   ```

3. **Run from USB drive:**
   ```bash
   /Volumes/USB/StreamTV/install-gui.sh
   ```

4. **Double-click from anywhere:**
   - Move `Install-StreamTV.command` to Desktop
   - Double-click it
   - Works perfectly!

## Key Features

### Absolute Path Resolution

All scripts:
- ✅ Detect their own location automatically
- ✅ Resolve to absolute paths
- ✅ Handle symlinks correctly
- ✅ Work from any current directory

### Working Directory Management

Scripts:
- ✅ Change to script directory before execution
- ✅ Ensure relative imports work
- ✅ Set PYTHONPATH when needed
- ✅ Use absolute paths for all file operations

### Error Handling

If path resolution fails:
- ✅ Scripts show clear error messages
- ✅ Suggest checking file locations
- ✅ Provide troubleshooting steps

## Benefits

1. **User-Friendly**: Users can place installer anywhere
2. **Flexible**: Works from USB drives, network shares, etc.
3. **Reliable**: No dependency on current working directory
4. **Portable**: Easy to distribute and share

## Troubleshooting

### "File not found" errors

If you see file not found errors:
1. Make sure all StreamTV files are in the same directory
2. Don't move individual files - move the entire folder
3. Check that the installer script is in the StreamTV root directory

### Import errors (Python)

If you see Python import errors:
1. Make sure you're running from the StreamTV directory
2. Check that `streamtv` package is in the same directory
3. Verify PYTHONPATH is set correctly (handled automatically)

### Path resolution issues

If path resolution fails:
1. Check file permissions
2. Verify script is not corrupted
3. Try running from the StreamTV directory directly
4. Check if symlinks are broken: `readlink -f install_gui.py` (Linux) or `readlink install_gui.py` (macOS)

### Command file not working

If `Install-StreamTV.command` doesn't work:
1. Make sure it's executable: `chmod +x Install-StreamTV.command`
2. Right-click → Get Info → Check "Open with" is set to Terminal
3. Try running from Terminal: `./Install-StreamTV.command`

