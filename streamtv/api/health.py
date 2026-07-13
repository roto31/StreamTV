"""Comprehensive health check API endpoint"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pathlib import Path
import logging
import subprocess
import platform
import socket
import httpx
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import re

from ..database import get_db, Channel, MediaItem
from ..config import config

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


def check_ffmpeg() -> Dict[str, Any]:
    """Check FFmpeg installation and version"""
    try:
        ffmpeg_path = config.ffmpeg.ffmpeg_path or "ffmpeg"
        result = subprocess.run(
            [ffmpeg_path, "-version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            return {
                "status": "healthy",
                "installed": True,
                "path": ffmpeg_path,
                "version": version_line,
                "message": "FFmpeg is installed and working"
            }
        else:
            return {
                "status": "error",
                "installed": False,
                "message": f"FFmpeg returned error: {result.stderr[:200]}"
            }
    except FileNotFoundError:
        return {
            "status": "error",
            "installed": False,
            "message": "FFmpeg not found in PATH or configured path"
        }
    except Exception as e:
        return {
            "status": "error",
            "installed": False,
            "message": f"Error checking FFmpeg: {str(e)}"
        }


def check_database(db: Session) -> Dict[str, Any]:
    """Check database connectivity and integrity"""
    try:
        # Test query
        channel_count = db.query(Channel).count()
        media_count = db.query(MediaItem).count()
        enabled_channels = db.query(Channel).filter(Channel.enabled == True).count()
        
        # Check database file exists
        db_file = Path("streamtv.db")
        db_size = db_file.stat().st_size if db_file.exists() else 0
        
        return {
            "status": "healthy",
            "connected": True,
            "channels": channel_count,
            "enabled_channels": enabled_channels,
            "media_items": media_count,
            "database_size_mb": round(db_size / (1024 * 1024), 2),
            "message": f"Database connected: {channel_count} channels, {media_count} media items"
        }
    except Exception as e:
        return {
            "status": "error",
            "connected": False,
            "message": f"Database error: {str(e)}"
        }


def check_ports() -> Dict[str, Any]:
    """Check if required ports are available"""
    checks = {}
    ports_to_check = {
        "http": config.server.port,
        "ssdp": 1900 if config.hdhomerun.enabled and config.hdhomerun.enable_ssdp else None
    }
    
    for name, port in ports_to_check.items():
        if port is None:
            continue
            
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            
            if result == 0:
                checks[name] = {
                    "status": "healthy",
                    "port": port,
                    "listening": True,
                    "message": f"Port {port} is listening"
                }
            else:
                checks[name] = {
                    "status": "warning",
                    "port": port,
                    "listening": False,
                    "message": f"Port {port} is not accessible"
                }
        except Exception as e:
            checks[name] = {
                "status": "error",
                "port": port,
                "message": f"Error checking port {port}: {str(e)}"
            }
    
    return checks


def check_network_connectivity() -> Dict[str, Any]:
    """Check network connectivity to external services"""
    checks = {}
    
    # Check YouTube
    try:
        # Use simple socket test for sync check
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex(('www.youtube.com', 443))
        sock.close()
        checks["youtube"] = {
            "status": "healthy" if result == 0 else "warning",
            "reachable": result == 0,
            "message": "YouTube is reachable" if result == 0 else "Cannot reach YouTube (may be temporary)"
        }
    except Exception as e:
        checks["youtube"] = {
            "status": "error",
            "reachable": False,
            "message": f"Error checking YouTube: {str(e)}"
        }
    
    # Check Archive.org
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex(('archive.org', 443))
        sock.close()
        checks["archive_org"] = {
            "status": "healthy" if result == 0 else "warning",
            "reachable": result == 0,
            "message": "Archive.org is reachable" if result == 0 else "Cannot reach Archive.org (may be temporary)"
        }
    except Exception as e:
        checks["archive_org"] = {
            "status": "error",
            "reachable": False,
            "message": f"Error checking Archive.org: {str(e)}"
        }
    
    return checks


def analyze_log_errors(log_file: Path, hours: int = 24) -> Dict[str, Any]:
    """Analyze log file for errors and patterns (optimized for speed)"""
    if not log_file.exists():
        return {
            "status": "info",
            "message": "Log file not found",
            "errors": [],
            "warnings": []
        }
    
    try:
        errors = []
        warnings = []
        error_patterns = {
            "youtube_rate_limit": r"rate.?limit",
            "network_error": r"nodename nor servname|Failed to resolve hostname|Connection.*refused",
            "ffmpeg_error": r"FFmpeg.*error|FFmpeg.*failed|Error opening input",
            "database_error": r"database.*error|sql.*error|database.*locked",
            "authentication_error": r"401.*Unauthorized|authentication.*failed|Invalid.*token"
        }
        
        # Read last 500 lines only (faster) - use tail-like approach
        try:
            # Try to read from end of file (more efficient for large files)
            with open(log_file, 'rb') as f:
                # Go to end and read backwards
                f.seek(0, 2)  # Seek to end
                file_size = f.tell()
                
                # Read last 100KB (should be enough for ~500-1000 lines)
                read_size = min(100 * 1024, file_size)
                f.seek(max(0, file_size - read_size))
                content = f.read().decode('utf-8', errors='ignore')
                lines = content.split('\n')
                # Take last 500 lines
                recent_lines = lines[-500:] if len(lines) > 500 else lines
        except:
            # Fallback: read entire file if seek fails
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                recent_lines = lines[-500:] if len(lines) > 500 else lines
        
        for line in recent_lines:
            if not line.strip():
                continue
            line_lower = line.lower()
            if 'error' in line_lower:
                # Categorize error
                error_type = "unknown"
                for pattern_name, pattern in error_patterns.items():
                    if re.search(pattern, line_lower, re.IGNORECASE):
                        error_type = pattern_name
                        break
                
                errors.append({
                    "type": error_type,
                    "message": line.strip()[:150],  # Truncate long lines
                })
            elif 'warning' in line_lower and len(warnings) < 20:  # Limit warnings
                warnings.append({
                    "message": line.strip()[:150],
                })
        
        # Count by type
        error_counts = {}
        for error in errors:
            error_type = error["type"]
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        # Get most recent errors (last 5 only)
        recent_errors = errors[-5:] if len(errors) > 5 else errors
        
        return {
            "status": "healthy" if len(errors) == 0 else "warning",
            "total_errors": len(errors),
            "total_warnings": len(warnings),
            "error_counts": error_counts,
            "recent_errors": recent_errors,
            "message": f"Found {len(errors)} errors and {len(warnings)} warnings in recent logs"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error analyzing logs: {str(e)}",
            "errors": [],
            "warnings": []
        }


def extract_timestamp(line: str) -> Optional[str]:
    """Extract timestamp from log line"""
    # Try to match common log timestamp formats
    timestamp_patterns = [
        r'(\d{4}-\d{2}-\d{2}[\s,]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?)',
        r'\[(\d{4}-\d{2}-\d{2}[\s,]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?)\]'
    ]
    
    for pattern in timestamp_patterns:
        match = re.search(pattern, line)
        if match:
            return match.group(1)
    return None


def check_channels(db: Session) -> Dict[str, Any]:
    """Check channel status and schedules"""
    try:
        channels = db.query(Channel).filter(Channel.enabled == True).all()
        
        channel_status = []
        for channel in channels:
            # Check if schedule file exists
            schedule_file = Path(f"schedules/{channel.number}.yml")
            has_schedule = schedule_file.exists()
            
            channel_status.append({
                "number": channel.number,
                "name": channel.name,
                "playout_mode": channel.playout_mode.value if hasattr(channel.playout_mode, 'value') else str(channel.playout_mode),
                "has_schedule": has_schedule,
                "status": "healthy" if has_schedule else "warning"
            })
        
        return {
            "status": "healthy",
            "enabled_channels": len(channels),
            "channels": channel_status,
            "message": f"Found {len(channels)} enabled channels"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error checking channels: {str(e)}"
        }


def check_streaming_processes() -> Dict[str, Any]:
    """Check if FFmpeg streaming processes are running"""
    try:
        if platform.system() == "Darwin":  # macOS
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True,
                text=True,
                timeout=5
            )
            ffmpeg_count = result.stdout.count("ffmpeg")
            streamtv_count = result.stdout.count("streamtv")
            
            return {
                "status": "healthy",
                "ffmpeg_processes": ffmpeg_count,
                "streamtv_processes": streamtv_count,
                "message": f"Found {ffmpeg_count} FFmpeg processes and {streamtv_count} StreamTV processes"
            }
        else:
            # Linux/Windows
            result = subprocess.run(
                ["ps", "aux"] if platform.system() != "Windows" else ["tasklist"],
                capture_output=True,
                text=True,
                timeout=5
            )
            ffmpeg_count = result.stdout.lower().count("ffmpeg")
            streamtv_count = result.stdout.lower().count("streamtv")
            
            return {
                "status": "healthy",
                "ffmpeg_processes": ffmpeg_count,
                "streamtv_processes": streamtv_count,
                "message": f"Found {ffmpeg_count} FFmpeg processes and {streamtv_count} StreamTV processes"
            }
    except Exception as e:
        return {
            "status": "warning",
            "message": f"Could not check processes: {str(e)}"
        }


@router.get("/health/detailed")
async def detailed_health_check(
    request: Request,
    db: Session = Depends(get_db),
    analyze_logs: bool = True
):
    """Comprehensive health check of all platform components"""
    
    health_report = {
        "timestamp": datetime.utcnow().isoformat(),
        "overall_status": "healthy",
        "checks": {}
    }
    
    try:
        # 1. Server Status
        health_report["checks"]["server"] = {
            "status": "healthy",
            "host": config.server.host,
            "port": config.server.port,
            "base_url": config.server.base_url,
            "message": "Server is running"
        }
        
        # 2. FFmpeg Check
        health_report["checks"]["ffmpeg"] = check_ffmpeg()
        
        # 3. Database Check
        health_report["checks"]["database"] = check_database(db)
        
        # 4. Ports Check (quick)
        health_report["checks"]["ports"] = check_ports()
        
        # 5. Network Connectivity (quick socket tests)
        health_report["checks"]["network"] = check_network_connectivity()
        
        # 6. Channels Check
        health_report["checks"]["channels"] = check_channels(db)
        
        # 7. Streaming Processes (quick)
        health_report["checks"]["processes"] = check_streaming_processes()
        
        # 8. Log Analysis (optimized, can be slow - make it optional or limit)
        if analyze_logs:
            try:
                # Try multiple possible log file locations
                base_dir = Path(__file__).parent.parent.parent
                possible_log_files = [
                    base_dir / config.logging.file if config.logging.file else None,
                    base_dir / "server.log",
                    base_dir / "streamtv.log",
                    Path(config.logging.file) if config.logging.file and Path(config.logging.file).is_absolute() else None
                ]
                
                log_file = None
                for possible_file in possible_log_files:
                    if possible_file and possible_file.exists():
                        log_file = possible_file
                        break
                
                if log_file:
                    # Limit log analysis to prevent timeout
                    health_report["checks"]["logs"] = analyze_log_errors(log_file)
                else:
                    health_report["checks"]["logs"] = {
                        "status": "info",
                        "message": "Log file not found (this is normal if server just started)"
                    }
            except Exception as e:
                health_report["checks"]["logs"] = {
                    "status": "warning",
                    "message": f"Could not analyze logs: {str(e)}"
                }
        else:
            health_report["checks"]["logs"] = {
                "status": "info",
                "message": "Log analysis skipped"
            }
        
        # 9. Configuration Check
        config_issues = []
        if config.security.api_key_required and not config.security.access_token:
            config_issues.append("API key required but access_token not set (will allow access)")
        if config.youtube.enabled and not config.youtube.cookies_file:
            config_issues.append("YouTube enabled but no cookies file configured")
        if config.archive_org.enabled and config.archive_org.use_authentication and not config.archive_org.cookies_file:
            config_issues.append("Archive.org authentication enabled but no cookies file configured")
        
        health_report["checks"]["configuration"] = {
            "status": "healthy" if len(config_issues) == 0 else "warning",
            "issues": config_issues,
            "message": "Configuration is valid" if len(config_issues) == 0 else f"Found {len(config_issues)} configuration warnings"
        }
    except Exception as e:
        logger.error(f"Error during health check: {e}", exc_info=True)
        health_report["checks"]["health_check"] = {
            "status": "error",
            "message": f"Health check failed: {str(e)}"
        }
    
        # Calculate overall status
        statuses = [check.get("status", "unknown") for check in health_report["checks"].values()]
        if "error" in statuses:
            health_report["overall_status"] = "error"
        elif "warning" in statuses:
            health_report["overall_status"] = "warning"
        else:
            health_report["overall_status"] = "healthy"
        
        # Add summary
        health_report["summary"] = {
            "total_checks": len(health_report["checks"]),
            "healthy": sum(1 for check in health_report["checks"].values() if check.get("status") == "healthy"),
            "warnings": sum(1 for check in health_report["checks"].values() if check.get("status") == "warning"),
            "errors": sum(1 for check in health_report["checks"].values() if check.get("status") == "error")
        }
    except Exception as e:
        logger.error(f"Critical error in health check: {e}", exc_info=True)
        health_report["overall_status"] = "error"
        health_report["error"] = str(e)
    
    return health_report


@router.get("/health")
async def simple_health_check():
    """Simple health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

