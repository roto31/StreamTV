@echo off
REM View StreamTV Logs (Windows)

if "%1"=="open" (
    if exist "logs" (
        explorer logs
    ) else (
        echo Logs directory not found
    )
    exit /b 0
)

if "%1"=="search" (
    if "%2"=="" (
        echo Usage: view-logs.bat search SEARCH_TERM
        exit /b 1
    )
    findstr /i "%2" streamtv.log 2>nul
    if errorlevel 1 (
        echo No matches found for "%2"
    )
    exit /b 0
)

REM Default: show recent logs
if exist "streamtv.log" (
    echo Recent log entries:
    echo ====================
    powershell -Command "Get-Content streamtv.log -Tail 50"
) else (
    echo Log file not found: streamtv.log
    echo.
    echo Logs will be created when the server starts.
)
