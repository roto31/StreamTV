# StreamTV Server Startup Script for Windows (PowerShell)

# Get the directory where this script is located
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $SCRIPT_DIR

# Check if virtual environment exists
if (-not (Test-Path "venv")) {
    Write-Host "❌ Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please run: python -m venv venv"
    Write-Host "Then: .\venv\Scripts\Activate.ps1"
    Write-Host "Then: pip install -r requirements.txt"
    exit 1
}

# Use venv Python directly
$VENV_PYTHON = Join-Path $SCRIPT_DIR "venv\Scripts\python.exe"

# Check if venv Python exists
if (-not (Test-Path $VENV_PYTHON)) {
    Write-Host "❌ Virtual environment Python not found at $VENV_PYTHON" -ForegroundColor Red
    exit 1
}

# Check if FastAPI is installed using venv Python
try {
    & $VENV_PYTHON -c "import fastapi" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "FastAPI not found"
    }
} catch {
    Write-Host "❌ FastAPI not found in virtual environment!" -ForegroundColor Red
    Write-Host "Installing dependencies..."
    & $VENV_PYTHON -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Dependencies installed" -ForegroundColor Green
}

# Start the server
Write-Host "🚀 Starting StreamTV server..." -ForegroundColor Cyan
& $VENV_PYTHON -m streamtv.main
