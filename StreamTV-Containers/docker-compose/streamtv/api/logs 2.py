"""
Streaming Logs API endpoints
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import logging
import re
import json
import asyncio
import os
import platform
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Logs"])

# Get base directory (project root)
BASE_DIR = Path(__file__).parent.parent.parent
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Error patterns to match troubleshooting scripts
ERROR_PATTERNS = {
    "check_python": [
        r"python.*not found",
        r"python.*error",
        r"python.*exception",
        r"no module named",
        r"import.*error",
        r"python.*version",
        r"python.*install"
    ],
    "check_ffmpeg": [
        r"ffmpeg.*not found",
        r"ffmpeg.*error",
        r"ffmpeg.*exception",
        r"ffmpeg.*failed",
        r"ffmpeg.*missing",
        r"codec.*not found",
        r"encoder.*not found"
    ],
    "check_database": [
        r"database.*error",
        r"database.*exception",
        r"sql.*error",
        r"database.*connection",
        r"database.*locked",
        r"database.*corrupt",
        r"sqlite.*error"
    ],
    "check_ports": [
        r"port.*in use",
        r"port.*already",
        r"address.*already",
        r"connection.*refused",
        r"cannot.*bind",
        r"port.*unavailable"
    ],
    "test_connectivity": [
        r"connection.*timeout",
        r"connection.*refused",
        r"network.*error",
        r"dns.*error",
        r"host.*unreachable",
        r"failed.*connect",
        r"youtube.*error",
        r"archive\.org.*error",
        r"nodename.*not known",
        r"servname.*not known",
        r"name resolution",
        r"unable to resolve",
        r"network.*unreachable",
        r"errno.*8",
        r"transport.*error"
    ],
    "repair_database": [
        r"database.*corrupt",
        r"database.*integrity",
        r"database.*repair",
        r"sqlite.*corrupt"
    ],
    "clear_cache": [
        r"cache.*error",
        r"cache.*full",
        r"cache.*corrupt",
        r"memory.*error"
    ]
}

def match_error_to_scripts(error_message: str) -> List[str]:
    """Match an error message to appropriate troubleshooting scripts"""
    error_lower = error_message.lower()
    matched_scripts = []
    
    for script_id, patterns in ERROR_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, error_lower, re.IGNORECASE):
                if script_id not in matched_scripts:
                    matched_scripts.append(script_id)
                break
    
    return matched_scripts

def parse_log_line(line: str) -> Dict:
    """Parse a log line and extract information"""
    # Common log formats:
    # 2024-11-30 14:30:45 - streamtv.api.iptv - ERROR - Error message
    # 2024-11-30 14:30:45,123 - streamtv.api.iptv - ERROR - Error message
    
    timestamp = None
    level = None
    logger_name = None
    message = line
    
    # Try to parse timestamp and level
    timestamp_match = re.match(r'(\d{4}-\d{2}-\d{2}[\s,]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?)', line)
    if timestamp_match:
        timestamp_str = timestamp_match.group(1).replace(',', '.')
        try:
            timestamp = datetime.strptime(timestamp_str.split('.')[0], '%Y-%m-%d %H:%M:%S')
        except:
            pass
    
    # Try to extract log level
    level_match = re.search(r'\s-\s(DEBUG|INFO|WARNING|ERROR|CRITICAL)\s-', line)
    if level_match:
        level = level_match.group(1)
        # Extract logger name (between timestamp and level)
        parts = line.split(' - ')
        if len(parts) >= 3:
            logger_name = parts[1] if len(parts) > 1 else None
            message = ' - '.join(parts[2:]) if len(parts) > 2 else line
    
    # Check if it's an error
    is_error = level in ['ERROR', 'CRITICAL'] or 'error' in line.lower() or 'exception' in line.lower()
    
    # Match to troubleshooting scripts if it's an error
    matched_scripts = []
    if is_error:
        matched_scripts = match_error_to_scripts(message)
    
    return {
        "raw": line,
        "timestamp": timestamp,
        "level": level or "INFO",
        "logger": logger_name,
        "message": message,
        "is_error": is_error,
        "matched_scripts": matched_scripts
    }

def get_log_file_path() -> Path:
    """Get the log file path from config, with fallbacks"""
    from ..config import config
    log_file = config.logging.file
    
    # List of possible log file locations to check
    possible_paths = []
    
    # Try absolute path first
    if Path(log_file).is_absolute():
        possible_paths.append(Path(log_file))
    else:
        # Try relative to BASE_DIR
        possible_paths.append(BASE_DIR / log_file)
        # Try in current directory
        possible_paths.append(Path(log_file))
        # Try in parent directory
        possible_paths.append(BASE_DIR.parent / log_file)
    
    # Also check for common log file names
    common_names = ["server.log", "streamtv.log", "app.log", "application.log"]
    for name in common_names:
        possible_paths.append(BASE_DIR / name)
        possible_paths.append(BASE_DIR.parent / name)
    
    # Return the first existing file, or the first path if none exist
    for path in possible_paths:
        if path.exists():
            return path
    
    # Return the primary expected path (will be created when logging starts)
    return BASE_DIR / log_file


def get_plex_logs_directory() -> Optional[Path]:
    """Get Plex Media Server logs directory, auto-detecting based on OS if not configured"""
    from ..config import config
    
    # If explicitly configured, use that
    if config.plex.logs_path:
        path = Path(config.plex.logs_path)
        if path.exists():
            return path
        logger.warning(f"Configured Plex logs path does not exist: {path}")
    
    # Auto-detect based on OS
    system = platform.system()
    home = Path.home()
    
    possible_paths = []
    
    if system == "Darwin":  # macOS
        possible_paths = [
            home / "Library" / "Logs" / "Plex Media Server",
            Path("/Users/Shared/Plex Media Server/Logs"),
        ]
    elif system == "Linux":
        possible_paths = [
            Path("/var/lib/plexmediaserver/Library/Application Support/Plex Media Server/Logs"),
            Path("/var/lib/plexmediaserver/Library/Application Support/Plex Media Server/Logs"),
            home / ".local" / "share" / "Plex Media Server" / "Logs",
            Path("/opt/plexmediaserver/Library/Application Support/Plex Media Server/Logs"),
        ]
    elif system == "Windows":
        local_appdata = os.getenv("LOCALAPPDATA", "")
        if local_appdata:
            possible_paths = [
                Path(local_appdata) / "Plex Media Server" / "Logs",
            ]
        # Also try common Windows paths
        possible_paths.extend([
            Path("C:/Users") / os.getenv("USERNAME", "") / "AppData" / "Local" / "Plex Media Server" / "Logs",
        ])
    
    # Check each possible path
    for path in possible_paths:
        if path.exists() and path.is_dir():
            logger.info(f"Found Plex logs directory: {path}")
            return path
    
    logger.warning("Could not find Plex Media Server logs directory. Please configure plex.logs_path in config.yaml")
    return None


def get_plex_log_files() -> List[Path]:
    """Get list of Plex log files, sorted by modification time (newest first)"""
    logs_dir = get_plex_logs_directory()
    if not logs_dir:
        return []
    
    log_files = []
    for file in logs_dir.iterdir():
        if file.is_file() and (file.suffix == '.log' or 'Plex Media Server' in file.name):
            log_files.append(file)
    
    # Sort by modification time, newest first
    log_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return log_files


def parse_plex_log_line(line: str) -> Dict:
    """Parse a Plex log line into structured data"""
    # Plex log format: [timestamp] LEVEL - message
    # Example: [2024-01-01 12:00:00.000] ERROR - Error message here
    
    parsed = {
        "raw": line,
        "timestamp": None,
        "level": "INFO",
        "message": line,
        "is_error": False
    }
    
    # Try to extract timestamp and level
    timestamp_match = re.match(r'\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)\]', line)
    if timestamp_match:
        try:
            timestamp_str = timestamp_match.group(1)
            # Parse timestamp (handle with or without microseconds)
            if '.' in timestamp_str:
                parsed["timestamp"] = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S.%f").isoformat()
            else:
                parsed["timestamp"] = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S").isoformat()
        except ValueError:
            pass
    
    # Extract log level
    level_match = re.search(r'\b(ERROR|WARN|WARNING|INFO|DEBUG|CRITICAL|FATAL)\b', line)
    if level_match:
        level = level_match.group(1).upper()
        if level == "WARN":
            level = "WARNING"
        parsed["level"] = level
        parsed["is_error"] = level in ["ERROR", "CRITICAL", "FATAL"]
    
    # Extract message (everything after timestamp and level)
    if timestamp_match:
        remaining = line[timestamp_match.end():].strip()
        # Remove level if present
        if level_match:
            remaining = re.sub(r'\b(ERROR|WARN|WARNING|INFO|DEBUG|CRITICAL|FATAL)\b\s*-\s*', '', remaining, count=1)
        parsed["message"] = remaining
    else:
        parsed["message"] = line
    
    return parsed

# Note: The /logs page route is handled in main.py to avoid conflicts

@router.get("/logs/{entry_id}", response_class=HTMLResponse)
async def log_entry_detail(entry_id: str, request: Request):
    """Log entry detail page with context and self-heal option"""
    import base64
    import urllib.parse
    
    try:
        # Decode entry_id (it's base64 encoded log line)
        decoded = base64.b64decode(entry_id).decode('utf-8')
        
        # Parse the log entry
        parsed = parse_log_line(decoded)
        
        # Get surrounding context (lines before and after)
        log_file = get_log_file_path()
        context_lines = []
        target_line_index = None
        
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    all_lines = f.readlines()
                    
                    # Find the line index
                    for i, line in enumerate(all_lines):
                        if line.strip() == decoded.strip():
                            target_line_index = i
                            # Get 20 lines before and after for context
                            start = max(0, i - 20)
                            end = min(len(all_lines), i + 21)
                            context_lines = [
                                {
                                    "line_number": j + 1,
                                    "content": all_lines[j].strip(),
                                    "is_target": j == i,
                                    "parsed": parse_log_line(all_lines[j].strip())
                                }
                                for j in range(start, end)
                            ]
                            break
            except Exception as e:
                logger.error(f"Error reading context: {e}")
        
        return templates.TemplateResponse(
            "log_detail.html",
            {
                "request": request,
                "title": f"Log Entry Detail - {parsed.get('level', 'INFO')}",
                "entry": parsed,
                "raw_line": decoded,
                "context_lines": context_lines,
                "target_line_index": target_line_index
            }
        )
    except Exception as e:
        logger.error(f"Error decoding log entry: {e}")
        raise HTTPException(status_code=400, detail="Invalid log entry ID")

@router.get("/api/logs/entries")
async def get_log_entries(lines: int = 500, filter_level: Optional[str] = None):
    """Get log entries as JSON"""
    log_file = get_log_file_path()
    
    if not log_file.exists():
        # Check if any log files exist in common locations
        checked_paths = [
            BASE_DIR / "server.log",
            BASE_DIR / "streamtv.log",
            BASE_DIR / "app.log",
            BASE_DIR.parent / "server.log",
            BASE_DIR.parent / "streamtv.log"
        ]
        
        existing_logs = [str(p) for p in checked_paths if p.exists()]
        
        # Try to create an empty log file if it doesn't exist
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            log_file.touch()
            logger.info(f"Created log file at {log_file}")
        except Exception as e:
            logger.warning(f"Could not create log file at {log_file}: {e}")
            message = f"Log file not found at: {log_file}"
            if existing_logs:
                message += f"\n\nFound log files at:\n" + "\n".join(f"  • {path}" for path in existing_logs)
                message += f"\n\nPlease update config.yaml to point to one of these files, or the log file will be created when the first log entry is written."
            else:
                message += f"\n\nThe log file will be created automatically when the first log entry is written."
            
            return {
                "entries": [{
                    "raw": message,
                    "timestamp": None,
                    "level": "WARNING",
                    "logger": "logs",
                    "message": message,
                    "is_error": False,
                    "matched_scripts": []
                }],
                "error": f"Log file not found at: {log_file}",
                "log_path": str(log_file),
                "checked_paths": [str(p) for p in checked_paths],
                "existing_logs": existing_logs
            }
    
    try:
        # Read last N lines
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        # Parse lines
        entries = []
        for line in recent_lines:
            parsed = parse_log_line(line.strip())
            if filter_level and parsed["level"] != filter_level:
                continue
            entries.append(parsed)
        
        return {
            "entries": entries,
            "total_lines": len(all_lines),
            "showing": len(entries)
        }
    except Exception as e:
        logger.error(f"Error reading log file: {e}")
        raise HTTPException(status_code=500, detail=f"Error reading log file: {str(e)}")

@router.get("/api/logs/stream")
async def stream_logs():
    """Stream logs in real-time (SSE)"""
    log_file = get_log_file_path()
    
    if not log_file.exists():
        async def error_generator():
            yield f"data: {json.dumps({'error': f'Log file not found at: {log_file}', 'log_path': str(log_file)})}\n\n"
        return StreamingResponse(error_generator(), media_type="text/event-stream")
    
    async def log_generator():
        import time
        import json
        
        # Read existing logs first
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            f.seek(0, 2)  # Seek to end
            last_position = f.tell()
        
        while True:
            try:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    f.seek(last_position)
                    new_lines = f.readlines()
                    last_position = f.tell()
                    
                    for line in new_lines:
                        if line.strip():
                            parsed = parse_log_line(line.strip())
                            yield f"data: {json.dumps(parsed)}\n\n"
                
                await asyncio.sleep(0.5)  # Check every 500ms
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                await asyncio.sleep(1)
    
    return StreamingResponse(log_generator(), media_type="text/event-stream")

@router.get("/api/logs/clear")
async def clear_logs():
    """Clear the log file"""
    log_file = get_log_file_path()
    
    try:
        if log_file.exists():
            log_file.write_text("")
        return {"success": True, "message": "Log file cleared"}
    except Exception as e:
        logger.error(f"Error clearing log file: {e}")
        raise HTTPException(status_code=500, detail=f"Error clearing log file: {str(e)}")


# Plex Logs Endpoints

@router.get("/plex/logs/directory")
async def get_plex_logs_directory_info():
    """Get information about Plex logs directory"""
    logs_dir = get_plex_logs_directory()
    if not logs_dir:
        return JSONResponse({
            "found": False,
            "message": "Plex logs directory not found. Please configure plex.logs_path in config.yaml",
            "possible_locations": {
                "macOS": "~/Library/Logs/Plex Media Server",
                "Linux": "/var/lib/plexmediaserver/Library/Application Support/Plex Media Server/Logs",
                "Windows": "%LOCALAPPDATA%\\Plex Media Server\\Logs"
            }
        })
    
    log_files = get_plex_log_files()
    return {
        "found": True,
        "directory": str(logs_dir),
        "log_files_count": len(log_files),
        "log_files": [{"name": f.name, "size": f.stat().st_size, "modified": f.stat().st_mtime} for f in log_files[:10]]
    }


@router.get("/plex/logs/files")
async def list_plex_log_files():
    """List available Plex log files"""
    log_files = get_plex_log_files()
    return {
        "files": [
            {
                "name": f.name,
                "path": str(f),
                "size": f.stat().st_size,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
            }
            for f in log_files
        ]
    }


@router.get("/plex/logs/entries")
async def get_plex_log_entries(
    lines: int = 500,
    filter_level: str = "",
    log_file: Optional[str] = None
):
    """Get Plex log entries"""
    logs_dir = get_plex_logs_directory()
    if not logs_dir:
        return JSONResponse({
            "error": "Plex logs directory not found",
            "entries": [],
            "message": "Please configure plex.logs_path in config.yaml or ensure Plex is installed"
        }, status_code=404)
    
    # Determine which log file to read
    log_files = get_plex_log_files()
    if not log_files:
        return JSONResponse({
            "error": "No Plex log files found",
            "entries": [],
            "directory": str(logs_dir)
        }, status_code=404)
    
    # Use specified file or default to most recent
    if log_file:
        target_file = logs_dir / log_file
        if not target_file.exists():
            return JSONResponse({
                "error": f"Log file not found: {log_file}",
                "entries": []
            }, status_code=404)
    else:
        target_file = log_files[0]  # Most recent
    
    try:
        entries = []
        with open(target_file, 'r', encoding='utf-8', errors='ignore') as f:
            # Read last N lines
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            
            for line in recent_lines:
                line = line.strip()
                if not line:
                    continue
                
                parsed = parse_plex_log_line(line)
                
                # Apply level filter
                if filter_level and parsed["level"] != filter_level:
                    continue
                
                entries.append(parsed)
        
        return {
            "entries": entries,
            "file": target_file.name,
            "total_lines": len(entries),
            "log_path": str(logs_dir)
        }
    except Exception as e:
        logger.error(f"Error reading Plex logs: {e}")
        return JSONResponse({
            "error": f"Error reading Plex logs: {str(e)}",
            "entries": [],
            "log_path": str(logs_dir)
        }, status_code=500)


@router.get("/plex/logs", response_class=HTMLResponse)
async def plex_logs_page(request: Request):
    """Plex logs viewer page"""
    return templates.TemplateResponse("plex_logs.html", {"request": request})

