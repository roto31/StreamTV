@echo off
REM Verify StreamTV Installation for Windows

echo StreamTV Installation Verification
echo ====================================
echo.

REM Check Python
echo Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ✗ Python not found
    exit /b 1
) else (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo ✓ Found Python %PYTHON_VERSION%
)

REM Check FFmpeg
echo Checking FFmpeg...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo ✗ FFmpeg not found
    exit /b 1
) else (
    for /f "tokens=3" %%i in ('ffmpeg -version 2^>^&1 ^| findstr /r "ffmpeg version"') do set FFMPEG_VERSION=%%i
    echo ✓ Found FFmpeg %FFMPEG_VERSION%
)

REM Check virtual environment
echo Checking virtual environment...
if not exist "venv" (
    echo ✗ Virtual environment not found
    exit /b 1
) else (
    echo ✓ Virtual environment exists
)

REM Check dependencies
echo Checking Python dependencies...
call venv\Scripts\activate.bat
python -c "import fastapi, uvicorn, sqlalchemy" >nul 2>&1
if errorlevel 1 (
    echo ✗ Dependencies missing
    exit /b 1
) else (
    echo ✓ Dependencies installed
)

REM Check configuration
echo Checking configuration...
if exist "config.yaml" (
    echo ✓ Configuration file exists
) else (
    echo ⚠ Configuration file not found (will be created on first run)
)

REM Check application code
echo Checking application code...
if exist "streamtv\main.py" (
    echo ✓ Application code present
) else (
    echo ✗ Application code missing
    exit /b 1
)

echo.
echo ✓ All checks passed! StreamTV is ready to use.
echo.
echo To start the server:
echo   start_server.bat
echo   or
echo   start_server.ps1
