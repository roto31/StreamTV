# Installation

This guide covers installing StreamTV on macOS, Linux, and Windows.

## Contents

- [Requirements](#requirements)
- [macOS Installation](#macos-installation)
- [Linux Installation](#linux-installation)
- [Windows Installation](#windows-installation)
- [Docker Installation](#docker-installation)
- [Post-Installation](#post-installation)
- [Troubleshooting](#troubleshooting)

## Requirements

### System Requirements

- **Python**: 3.10 or higher
- **pip**: Python package manager
- **FFmpeg**: Optional, for advanced streaming features
- **Disk Space**: ~100MB for application + database

### Platform-Specific Requirements

#### macOS
- macOS 10.14 (Mojave) or later
- Xcode Command Line Tools (for some dependencies)

#### Linux
- Most modern distributions (Ubuntu 18.04+, Debian 10+, etc.)
- System package manager (apt, yum, etc.)

#### Windows
- Windows 10 or later
- Microsoft Visual C++ Redistributable (for some Python packages)

## macOS Installation

### Automated Installation (Recommended)

Use the provided installation script:

```bash
./install_macos.sh
```

This script automatically:
- Checks for Python 3.10+
- Installs Python if needed
- Installs FFmpeg
- Creates virtual environment
- Installs dependencies
- Sets up initial configuration

### Manual Installation

1. **Install Python 3.10+** (if not already installed):
   ```bash
   # Using Homebrew
   brew install python3
   
   # Or download from python.org
   ```

2. **Install FFmpeg** (optional but recommended):
   ```bash
   brew install ffmpeg
   ```

3. **Clone or download the repository**:
   ```bash
   git clone https://github.com/yourusername/streamtv.git
   cd streamtv
   ```

4. **Create virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

5. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

6. **Configure**:
   ```bash
   cp config.example.yaml config.yaml
   # Edit config.yaml as needed
   ```

7. **Run StreamTV**:
   ```bash
   python -m streamtv.main
   ```

## Linux Installation

### Ubuntu/Debian

1. **Install system dependencies**:
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip python3-venv ffmpeg git
   ```

2. **Clone repository**:
   ```bash
   git clone https://github.com/yourusername/streamtv.git
   cd streamtv
   ```

3. **Create virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

4. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure**:
   ```bash
   cp config.example.yaml config.yaml
   # Edit config.yaml as needed
   ```

6. **Run StreamTV**:
   ```bash
   python -m streamtv.main
   ```

### Fedora/RHEL/CentOS

1. **Install system dependencies**:
   ```bash
   sudo dnf install python3 python3-pip ffmpeg git
   ```

2. **Follow steps 2-6 from Ubuntu/Debian section**

### Arch Linux

1. **Install system dependencies**:
   ```bash
   sudo pacman -S python python-pip ffmpeg git
   ```

2. **Follow steps 2-6 from Ubuntu/Debian section**

## Windows Installation

### Using Python from python.org

1. **Download Python 3.10+** from [python.org](https://www.python.org/downloads/)
   - Check "Add Python to PATH" during installation

2. **Install Git** from [git-scm.com](https://git-scm.com/download/win)

3. **Open Command Prompt or PowerShell**:
   ```cmd
   git clone https://github.com/yourusername/streamtv.git
   cd streamtv
   ```

4. **Create virtual environment**:
   ```cmd
   python -m venv venv
   venv\Scripts\activate
   ```

5. **Install dependencies**:
   ```cmd
   pip install -r requirements.txt
   ```

6. **Configure**:
   ```cmd
   copy config.example.yaml config.yaml
   REM Edit config.yaml as needed
   ```

7. **Run StreamTV**:
   ```cmd
   python -m streamtv.main
   ```

### Using Windows Subsystem for Linux (WSL)

Follow the Linux installation instructions within WSL.

## Docker Installation

### Build from Source

1. **Clone repository**:
   ```bash
   git clone https://github.com/yourusername/streamtv.git
   cd streamtv
   ```

2. **Build Docker image**:
   ```bash
   docker build -t streamtv .
   ```

3. **Run container**:
   ```bash
   docker run -d \
     --name streamtv \
     -p 8410:8410 \
     -v $(pwd)/config.yaml:/app/config.yaml \
     -v $(pwd)/streamtv.db:/app/streamtv.db \
     streamtv
   ```

### Using Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.10'

services:
  streamtv:
    build: .
    ports:
      - "8410:8410"
    volumes:
      - ./config.yaml:/app/config.yaml
      - ./streamtv.db:/app/streamtv.db
    restart: unless-stopped
```

Run:
```bash
docker-compose up -d
```

## Post-Installation

### Verify Installation

1. **Check server is running**:
   ```bash
   curl http://localhost:8410/
   ```

2. **Access web interface**:
   Open http://localhost:8410 in your browser

3. **Check API documentation**:
   Open http://localhost:8410/docs

### Initial Setup

1. **Create your first channel**:
   ```bash
   curl -X POST http://localhost:8410/api/channels \
     -H "Content-Type: application/json" \
     -d '{"number": "1", "name": "My Channel", "group": "Entertainment"}'
   ```

2. **Add media**:
   ```bash
   curl -X POST http://localhost:8410/api/media \
     -H "Content-Type: application/json" \
     -d '{"source": "youtube", "url": "https://www.youtube.com/watch?v=VIDEO_ID"}'
   ```

3. **Access IPTV streams**:
   - M3U Playlist: http://localhost:8410/iptv/channels.m3u
   - EPG: http://localhost:8410/iptv/xmltv.xml

## Troubleshooting

### Python Not Found

**macOS/Linux**:
```bash
# Check Python version
python3 --version

# If not found, install Python
# macOS: brew install python3
# Linux: sudo apt install python3
```

**Windows**:
- Ensure Python is added to PATH during installation
- Or use full path: `C:\Python3x\python.exe`

### pip Not Found

```bash
# macOS/Linux
python3 -m ensurepip --upgrade

# Windows
python -m ensurepip --upgrade
```

### Port Already in Use

Change the port in `config.yaml`:
```yaml
server:
  port: 8500  # Change from 8410
```

### Database Errors

Delete the database file and restart:
```bash
rm streamtv.db
python -m streamtv.main
```

### FFmpeg Not Found

**macOS**:
```bash
brew install ffmpeg
```

**Linux**:
```bash
sudo apt install ffmpeg  # Ubuntu/Debian
sudo dnf install ffmpeg  # Fedora
```

**Windows**:
- Download from [ffmpeg.org](https://ffmpeg.org/download.html)
- Add to PATH

### Virtual Environment Issues

If activation fails:

**macOS/Linux**:
```bash
# Recreate virtual environment
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Windows**:
```cmd
rmdir /s venv
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Next Steps

- Read the [Quick Start Guide](Quick-Start)
- Check out [Configuration](Configuration) options
- Learn about [Creating Your First Channel](Creating-Your-First-Channel)

