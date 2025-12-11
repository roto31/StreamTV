# Windows Installation Guide

Complete installation guide for StreamTV on Windows.

## Quick Start

Run the automated installation script:

```powershell
.\install_windows.ps1
```

**Note:** You may need to set the execution policy first:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

This script will:
1. Check and guide you to install Python 3.8+ if needed
2. Install FFmpeg (via Chocolatey, Scoop, or manual instructions)
3. Set up a virtual environment
4. Install all Python dependencies
5. Configure the platform
6. Initialize the database
7. Create launch scripts
8. Optionally start the server

## Manual Installation

If you prefer to install manually:

### 1. Install Python 3.8+

Download and install from [python.org](https://www.python.org/downloads/):
- Download the Windows installer
- **Important:** Check "Add Python to PATH" during installation
- Verify installation: Open PowerShell and run `python --version`

### 2. Install FFmpeg

#### Option A: Using Chocolatey (Recommended)

If you have Chocolatey installed:
```powershell
choco install ffmpeg
```

To install Chocolatey:
```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

#### Option B: Using Scoop

If you have Scoop installed:
```powershell
scoop install ffmpeg
```

To install Scoop:
```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
irm get.scoop.sh | iex
```

#### Option C: Manual Installation

1. Download FFmpeg from [ffmpeg.org](https://ffmpeg.org/download.html)
2. Extract to a folder (e.g., `C:\ffmpeg`)
3. Add to PATH:
   - Open System Properties → Environment Variables
   - Add `C:\ffmpeg\bin` to PATH
   - Restart PowerShell

### 3. Set Up Virtual Environment

Open PowerShell in the StreamTV directory:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

If you get an execution policy error:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 4. Install Dependencies

```powershell
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### 5. Configure

```powershell
Copy-Item config.example.yaml config.yaml
# Edit config.yaml as needed (using Notepad or your preferred editor)
```

### 6. Initialize Database

```powershell
python -c "from streamtv.database.session import init_db; init_db()"
```

### 7. Create Your First Channel

After installation, you can create channels using:
- The web interface at http://localhost:8410/channels
- The API (see API documentation)
- YAML import files (see SCHEDULES.md)

### 8. Start Server

**Option 1: Using Batch Script**
```cmd
start_server.bat
```

**Option 2: Using PowerShell Script**
```powershell
.\start_server.ps1
```

**Option 3: Direct Command**
```powershell
.\venv\Scripts\activate
python -m streamtv.main
```

## Installation Locations

- **Virtual Environment**: `%USERPROFILE%\.streamtv\venv`
- **Launch Script**: `%USERPROFILE%\.streamtv\start_server.bat`
- **Configuration**: `config.yaml` (in application directory)
- **Database**: `streamtv.db` (in application directory)
- **Logs**: `streamtv.log` (in application directory)

## Running as a Windows Service

### Using NSSM (Non-Sucking Service Manager)

1. Download NSSM from [nssm.cc](https://nssm.cc/download)
2. Extract and run:
   ```cmd
   nssm install StreamTV
   ```
3. Configure:
   - Path: `C:\path\to\venv\Scripts\python.exe`
   - Arguments: `-m streamtv.main`
   - Startup directory: `C:\path\to\StreamTV-Windows`
4. Start service:
   ```cmd
   nssm start StreamTV
   ```

### Using Task Scheduler

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger: "When the computer starts"
4. Set action: Start a program
   - Program: `C:\path\to\venv\Scripts\python.exe`
   - Arguments: `-m streamtv.main`
   - Start in: `C:\path\to\StreamTV-Windows`
5. Save and test

## Windows-Specific Configuration

### Firewall Configuration

Windows Firewall may block the server. To allow it:

1. Open Windows Defender Firewall
2. Click "Allow an app or feature through Windows Firewall"
3. Click "Change Settings" → "Allow another app"
4. Browse to Python executable or add port 8410

Or via PowerShell:
```powershell
New-NetFirewallRule -DisplayName "StreamTV" -Direction Inbound -LocalPort 8410 -Protocol TCP -Action Allow
```

### Path Issues

If Python or FFmpeg are not found:

1. Verify they're in PATH:
   ```powershell
   $env:PATH -split ';' | Select-String -Pattern "python|ffmpeg"
   ```

2. Add to PATH manually:
   - System Properties → Environment Variables
   - Edit PATH variable
   - Add Python and FFmpeg directories
   - Restart PowerShell

### PowerShell Execution Policy

If scripts won't run:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Troubleshooting

### Python Not Found

- Ensure Python is installed and added to PATH
- Restart PowerShell after installation
- Verify with: `python --version`

### FFmpeg Not Found

- Check PATH includes FFmpeg directory
- Restart PowerShell after adding to PATH
- Verify with: `ffmpeg -version`

### Port Already in Use

If port 8410 is already in use:
1. Change port in `config.yaml`:
   ```yaml
   server:
     port: 8411  # Use different port
   ```
2. Or stop the process using port 8410

### Virtual Environment Issues

If activation fails:
```powershell
# Remove and recreate
Remove-Item -Recurse -Force venv
python -m venv venv
.\venv\Scripts\Activate.ps1
```

## Next Steps

- [Quick Start Guide](../QUICKSTART.md)
- [Configuration Guide](../CONFIGURATION.md)
- [API Documentation](../API.md)
- [Troubleshooting](../TROUBLESHOOTING.md)
