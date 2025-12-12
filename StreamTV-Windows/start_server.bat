@echo off
REM StreamTV Server Startup Script for Windows

REM Get the directory where this script is located
cd /d "%~dp0"

REM Check if virtual environment exists
if not exist "venv" (
    echo ❌ Virtual environment not found!
    echo Please run: python -m venv venv
    echo Then: venv\Scripts\activate
    echo Then: pip install -r requirements.txt
    exit /b 1
)

REM Use venv Python directly
set VENV_PYTHON=%~dp0venv\Scripts\python.exe

REM Check if venv Python exists
if not exist "%VENV_PYTHON%" (
    echo ❌ Virtual environment Python not found at %VENV_PYTHON%
    exit /b 1
)

REM Check if FastAPI is installed using venv Python
"%VENV_PYTHON%" -c "import fastapi" 2>nul
if errorlevel 1 (
    echo ❌ FastAPI not found in virtual environment!
    echo Installing dependencies...
    "%VENV_PYTHON%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo ❌ Failed to install dependencies
        exit /b 1
    )
    echo ✅ Dependencies installed
)

REM Start the server
echo 🚀 Starting StreamTV server...
"%VENV_PYTHON%" -m streamtv.main
