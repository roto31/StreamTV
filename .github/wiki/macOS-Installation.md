# macOS Installation

Automated installation guide for macOS users.

## Quick Install

Use the automated installation script:

```bash
./install_macos.sh
```

This script automatically handles:
- Python 3.8+ installation check
- FFmpeg installation
- Virtual environment setup
- Dependency installation
- Initial configuration
- Channel creation

## What the Script Does

1. **Checks for Python 3.8+**
   - If not found, provides installation instructions
   - Verifies Python version

2. **Installs FFmpeg**
   - Uses Homebrew if available
   - Provides manual installation instructions if needed

3. **Creates Virtual Environment**
   - Sets up isolated Python environment
   - Activates the environment

4. **Installs Dependencies**
   - Installs all required Python packages
   - Handles dependency conflicts

5. **Configures StreamTV**
   - Creates `config.yaml` from example
   - Sets up default configuration

6. **Creates Initial Channels**
   - Sets up Winter Olympics channels (1980, 1984, 1988, 1992, 1994)
   - Imports media collections

## Manual Installation

If you prefer manual installation or the script fails:

### 1. Install Python

**Using Homebrew:**
```bash
brew install python3
```

**Or download from python.org:**
- Visit https://www.python.org/downloads/
- Download Python 3.8+ for macOS
- Run the installer

### 2. Install FFmpeg

**Using Homebrew:**
```bash
brew install ffmpeg
```

**Or download from ffmpeg.org:**
- Visit https://ffmpeg.org/download.html
- Download macOS build
- Add to PATH

### 3. Clone Repository

```bash
git clone https://github.com/yourusername/streamtv.git
cd streamtv
```

### 4. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 5. Install Dependencies

```bash
pip install -r requirements.txt
```

### 6. Configure

```bash
cp config.example.yaml config.yaml
# Edit config.yaml as needed
```

### 7. Run StreamTV

```bash
python -m streamtv.main
```

## Post-Installation

### Verify Installation

1. **Check server is running:**
   ```bash
   curl http://localhost:8410/
   ```

2. **Access web interface:**
   Open http://localhost:8410 in your browser

3. **Check API documentation:**
   Open http://localhost:8410/docs

### Create Channels

The installation script may create initial channels. To create manually:

```bash
python3 scripts/create_channel.py
```

### Import Media

```bash
# Import media items
python3 scripts/import_olympics_data.py

# Import collections
python3 scripts/import_collections.py
```

## Troubleshooting

### Python Not Found

**Check Python installation:**
```bash
python3 --version
```

**If not found:**
```bash
brew install python3
```

### FFmpeg Not Found

**Check FFmpeg installation:**
```bash
ffmpeg -version
```

**If not found:**
```bash
brew install ffmpeg
```

### Port Already in Use

Change port in `config.yaml`:
```yaml
server:
  port: 8500  # Change from 8410
```

### Permission Errors

**Virtual environment:**
```bash
chmod +x venv/bin/activate
source venv/bin/activate
```

**Scripts:**
```bash
chmod +x install_macos.sh
chmod +x scripts/*.sh
```

### Homebrew Not Installed

Install Homebrew:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Xcode Command Line Tools

If you see errors about missing tools:
```bash
xcode-select --install
```

## Uninstallation

To uninstall StreamTV:

1. **Stop the server** (if running)

2. **Remove virtual environment:**
   ```bash
   deactivate
   rm -rf venv
   ```

3. **Remove database** (optional):
   ```bash
   rm streamtv.db
   ```

4. **Remove configuration** (optional):
   ```bash
   rm config.yaml
   ```

Or use the uninstall script:
```bash
./uninstall_macos.sh
```

## Next Steps

- Read the [Quick Start Guide](Quick-Start)
- Check [Configuration](Configuration) options
- Learn about [Creating Your First Channel](Creating-Your-First-Channel)
- Explore [Schedules](Schedules) for advanced programming

## Additional Resources

- [Installation Guide](Installation) - General installation for all platforms
- [Beginner Guide](../docs/BEGINNER_GUIDE.md) - For new users
- [Troubleshooting](Troubleshooting) - Common issues

