# StreamTV Windows Installation Script
# PowerShell script for automated installation on Windows

#Requires -Version 5.1

$ErrorActionPreference = "Stop"

# Colors for output
function Write-Header {
    param([string]$Message)
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host $Message -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Write-Error {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor Red
}

function Write-Info {
    param([string]$Message)
    Write-Host "ℹ $Message" -ForegroundColor Blue
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠ $Message" -ForegroundColor Yellow
}

# Configuration
$INSTALL_DIR = "$env:USERPROFILE\.streamtv"
$PYTHON_MIN_VERSION = "3.8"
$VENV_DIR = "$INSTALL_DIR\venv"
$APP_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path

# Function to check Python version
function Test-PythonVersion {
    try {
        $pythonVersion = python --version 2>&1
        if ($pythonVersion -match "Python (\d+)\.(\d+)") {
            $major = [int]$matches[1]
            $minor = [int]$matches[2]
            $minMajor = [int]$PYTHON_MIN_VERSION.Split('.')[0]
            $minMinor = [int]$PYTHON_MIN_VERSION.Split('.')[1]
            
            if ($major -gt $minMajor -or ($major -eq $minMajor -and $minor -ge $minMinor)) {
                Write-Success "Python $($pythonVersion -replace 'Python ', '') found"
                return $true
            }
        }
    } catch {
        # Python not found
    }
    return $false
}

# Function to install Python
function Install-Python {
    Write-Info "Python 3.8+ not found. Please install from python.org..."
    Write-Info "Opening Python download page..."
    Start-Process "https://www.python.org/downloads/"
    Write-Warning "After installing Python, run this script again."
    Write-Info "Make sure to check 'Add Python to PATH' during installation."
    exit 1
}

# Function to check FFmpeg
function Test-FFmpeg {
    try {
        $ffmpegVersion = ffmpeg -version 2>&1 | Select-Object -First 1
        if ($ffmpegVersion -match "ffmpeg version") {
            Write-Success "FFmpeg found"
            return $true
        }
    } catch {
        # FFmpeg not found
    }
    return $false
}

# Function to install FFmpeg
function Install-FFmpeg {
    Write-Info "FFmpeg not found. Installing options:"
    Write-Info "1. Using Chocolatey (if installed): choco install ffmpeg"
    Write-Info "2. Using Scoop (if installed): scoop install ffmpeg"
    Write-Info "3. Manual download: https://ffmpeg.org/download.html"
    Write-Info ""
    
    # Try Chocolatey
    if (Get-Command choco -ErrorAction SilentlyContinue) {
        Write-Info "Attempting to install FFmpeg via Chocolatey..."
        choco install ffmpeg -y
        if (Test-FFmpeg) {
            Write-Success "FFmpeg installed via Chocolatey"
            return
        }
    }
    
    # Try Scoop
    if (Get-Command scoop -ErrorAction SilentlyContinue) {
        Write-Info "Attempting to install FFmpeg via Scoop..."
        scoop install ffmpeg
        if (Test-FFmpeg) {
            Write-Success "FFmpeg installed via Scoop"
            return
        }
    }
    
    Write-Error "Please install FFmpeg manually from https://ffmpeg.org/download.html"
    Write-Info "Or install a package manager:"
    Write-Info "  Chocolatey: https://chocolatey.org/install"
    Write-Info "  Scoop: https://scoop.sh/"
    exit 1
}

# Function to setup virtual environment
function Setup-Venv {
    Write-Info "Setting up virtual environment..."
    
    if (Test-Path $VENV_DIR) {
        Write-Warning "Virtual environment already exists at $VENV_DIR"
        $response = Read-Host "Do you want to recreate it? (y/N)"
        if ($response -eq 'y' -or $response -eq 'Y') {
            Remove-Item -Recurse -Force $VENV_DIR
        } else {
            Write-Info "Using existing virtual environment"
            return
        }
    }
    
    python -m venv $VENV_DIR
    Write-Success "Virtual environment created at $VENV_DIR"
}

# Function to activate virtual environment
function Activate-Venv {
    & "$VENV_DIR\Scripts\Activate.ps1"
    Write-Success "Virtual environment activated"
}

# Function to upgrade pip
function Update-Pip {
    Write-Info "Upgrading pip..."
    python -m pip install --upgrade pip setuptools wheel --quiet
    Write-Success "pip upgraded"
}

# Function to install dependencies
function Install-Dependencies {
    Write-Info "Installing Python dependencies..."
    
    $requirementsFile = Join-Path $APP_DIR "requirements.txt"
    if (-not (Test-Path $requirementsFile)) {
        Write-Error "requirements.txt not found at $requirementsFile"
        exit 1
    }
    
    pip install -r $requirementsFile
    Write-Success "Python dependencies installed"
}

# Function to setup configuration
function Setup-Config {
    Write-Info "Setting up configuration..."
    
    $configFile = Join-Path $APP_DIR "config.yaml"
    $exampleConfig = Join-Path $APP_DIR "config.example.yaml"
    
    if (-not (Test-Path $configFile)) {
        if (Test-Path $exampleConfig) {
            Copy-Item $exampleConfig $configFile
            Write-Success "Configuration file created from example"
        } else {
            Write-Warning "No example configuration found, creating default config..."
            @"
server:
  host: "0.0.0.0"
  port: 8410
  base_url: "http://localhost:8410"

database:
  url: "sqlite:///./streamtv.db"

streaming:
  buffer_size: 8192
  chunk_size: 1024
  timeout: 30
  max_retries: 3

youtube:
  enabled: true
  quality: "best"
  extract_audio: false

archive_org:
  enabled: true
  preferred_format: "h264"
  username: null
  password: null
  use_authentication: false

security:
  api_key_required: false
  access_token: null

logging:
  level: "INFO"
  file: "streamtv.log"
"@ | Out-File -FilePath $configFile -Encoding UTF8
            Write-Success "Default configuration file created"
        }
    } else {
        Write-Info "Configuration file already exists"
    }
}

# Function to initialize database
function Initialize-Database {
    Write-Info "Initializing database..."
    
    Set-Location $APP_DIR
    python -c "from streamtv.database.session import init_db; init_db(); print('Database initialized')"
    
    Write-Success "Database initialized"
}

# Function to create launch script
function Create-LaunchScript {
    Write-Info "Creating launch script..."
    
    $launchScript = Join-Path $INSTALL_DIR "start_server.bat"
    @"
@echo off
cd /d "$APP_DIR"
call "$VENV_DIR\Scripts\activate.bat"
python -m streamtv.main
"@ | Out-File -FilePath $launchScript -Encoding ASCII
    
    Write-Success "Launch script created at $launchScript"
}

# Function to create PowerShell launch script
function Create-PowerShellLaunchScript {
    Write-Info "Creating PowerShell launch script..."
    
    $launchScript = Join-Path $INSTALL_DIR "start_server.ps1"
    @"
# StreamTV Server Startup Script
Set-Location "$APP_DIR"
& "$VENV_DIR\Scripts\python.exe" -m streamtv.main
"@ | Out-File -FilePath $launchScript -Encoding UTF8
    
    Write-Success "PowerShell launch script created at $launchScript"
}

# Main installation function
function Main {
    Write-Header "StreamTV - Windows Installation"
    
    # Check Windows version
    $osVersion = [System.Environment]::OSVersion.Version
    Write-Info "Windows version: $($osVersion.ToString())"
    
    # Create install directory
    if (-not (Test-Path $INSTALL_DIR)) {
        New-Item -ItemType Directory -Path $INSTALL_DIR | Out-Null
    }
    
    # Step 1: Check/Install Python
    Write-Header "Step 1: Checking Python Installation"
    if (-not (Test-PythonVersion)) {
        Install-Python
    }
    
    # Step 2: Check/Install FFmpeg
    Write-Header "Step 2: Checking FFmpeg Installation"
    if (-not (Test-FFmpeg)) {
        Install-FFmpeg
    }
    
    # Step 3: Setup virtual environment
    Write-Header "Step 3: Setting Up Virtual Environment"
    Setup-Venv
    Activate-Venv
    
    # Step 4: Upgrade pip
    Write-Header "Step 4: Upgrading pip"
    Update-Pip
    
    # Step 5: Install dependencies
    Write-Header "Step 5: Installing Python Dependencies"
    Install-Dependencies
    
    # Step 6: Setup configuration
    Write-Header "Step 6: Setting Up Configuration"
    Setup-Config
    
    # Step 7: Initialize database
    Write-Header "Step 7: Initializing Database"
    Initialize-Database
    
    # Step 8: Create launch scripts
    Write-Header "Step 8: Creating Launch Scripts"
    Create-LaunchScript
    Create-PowerShellLaunchScript
    
    # Installation complete
    Write-Header "Installation Complete!"
    
    Write-Host ""
    Write-Success "StreamTV has been installed successfully!"
    Write-Host ""
    Write-Info "Installation directory: $INSTALL_DIR"
    Write-Info "Virtual environment: $VENV_DIR"
    Write-Info "Application directory: $APP_DIR"
    Write-Host ""
    Write-Info "To start the server:"
    Write-Host "  $INSTALL_DIR\start_server.bat"
    Write-Host "  or"
    Write-Host "  $INSTALL_DIR\start_server.ps1"
    Write-Host ""
    Write-Info "Or run directly:"
    Write-Host "  cd $APP_DIR"
    Write-Host "  $VENV_DIR\Scripts\activate"
    Write-Host "  python -m streamtv.main"
    Write-Host ""
    Write-Info "Access the server at: http://localhost:8410"
    Write-Info "API documentation: http://localhost:8410/docs"
    Write-Host ""
    
    # Ask if user wants to start server
    $response = Read-Host "Would you like to start the server now? (y/N)"
    if ($response -eq 'y' -or $response -eq 'Y') {
        Write-Info "Starting server..."
        Set-Location $APP_DIR
        & "$VENV_DIR\Scripts\python.exe" -m streamtv.main
    } else {
        Write-Info "You can start the server later using the launch script"
    }
    
    Write-Host ""
    Write-Success "Installation finished successfully!"
}

# Run main function
Main
