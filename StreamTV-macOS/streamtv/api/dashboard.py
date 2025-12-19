"""
Dashboard Status API endpoints
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path
import subprocess
import shutil
import logging
import httpx
import asyncio
import re
import platform
from typing import Dict, Optional, List
from datetime import datetime, timedelta

from ..config import config
from ..streaming.stream_manager import StreamManager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Dashboard"])

# Get base directory (project root)
BASE_DIR = Path(__file__).parent.parent.parent

# Log file paths
LOG_DIR = BASE_DIR / "logs"
STREAMTV_LOG = LOG_DIR / "streamtv.log"

def parse_log_errors(service_name: str, lines: int = 100) -> List[str]:
    """Parse log file for errors related to a specific service"""
    errors = []
    # Try both log locations
    log_file = STREAMTV_LOG
    if platform.system() == "Darwin":
        macos_log = Path.home() / "Library" / "Logs" / "StreamTV" / "streamtv.log"
        if macos_log.exists():
            log_file = macos_log
    
    if not log_file.exists():
        return errors
    
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            # Read last N lines
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            
            # Patterns for each service
            patterns = {
                "archive_org": [
                    r"archive\.org.*error",
                    r"archive\.org.*failed",
                    r"archive.*authentication.*failed",
                    r"archive.*connection.*refused",
                    r"archive.*timeout",
                    r"archive.*unauthorized"
                ],
                "youtube": [
                    r"youtube.*error",
                    r"youtube.*failed",
                    r"youtube.*authentication.*failed",
                    r"youtube.*connection.*refused",
                    r"youtube.*timeout",
                    r"yt-dlp.*error",
                    r"yt-dlp.*failed"
                ],
                "plex": [
                    r"plex.*error",
                    r"plex.*failed",
                    r"plex.*connection.*refused",
                    r"plex.*timeout",
                    r"plex.*unauthorized",
                    r"plex.*library.*error"
                ],
                "ffmpeg": [
                    r"ffmpeg.*error",
                    r"ffmpeg.*failed",
                    r"ffmpeg.*not found",
                    r"codec.*not found",
                    r"encoder.*not found"
                ],
                "ollama": [
                    r"ollama.*error",
                    r"ollama.*failed",
                    r"ollama.*not found",
                    r"ollama.*connection.*refused"
                ],
                "streamtv": [
                    r"streamtv.*error",
                    r"streamtv.*failed",
                    r"api.*error",
                    r"api.*failed",
                    r"server.*error",
                    r"server.*failed"
                ],
                "auth": [
                    r"auth.*error",
                    r"auth.*failed",
                    r"authentication.*error",
                    r"authentication.*failed",
                    r"unauthorized",
                    r"401",
                    r"403"
                ]
            }
            
            service_patterns = patterns.get(service_name.lower(), [])
            for line in recent_lines:
                line_lower = line.lower()
                for pattern in service_patterns:
                    if re.search(pattern, line_lower, re.IGNORECASE):
                        # Extract timestamp and error message
                        timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                        if timestamp_match:
                            timestamp = timestamp_match.group(1)
                            # Get last 24 hours only
                            try:
                                log_time = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                                if datetime.now() - log_time < timedelta(hours=24):
                                    errors.append(line.strip())
                            except:
                                errors.append(line.strip())
                        else:
                            errors.append(line.strip())
                        break
    except Exception as e:
        logger.error(f"Error parsing logs for {service_name}: {e}")
    
    # Return unique errors (last 5)
    return list(dict.fromkeys(errors))[-5:]

async def check_archive_org_status() -> Dict:
    """Check Archive.org authentication and connection status"""
    status = {
        "authenticated": False,
        "connection_ok": False,
        "status": "red",  # red, yellow, green
        "errors": [],
        "username": None
    }
    
    try:
        # Check authentication - can be via username/password OR cookies file
        has_auth_config = False
        if config.archive_org.use_authentication:
            # Check for cookies file (preferred method)
            if config.archive_org.cookies_file:
                cookies_path = Path(config.archive_org.cookies_file)
                if cookies_path.exists():
                    status["authenticated"] = True
                    has_auth_config = True
            # Check for username/password authentication
            elif config.archive_org.username:
                status["username"] = config.archive_org.username
                has_auth_config = True
                stream_manager = StreamManager()
                try:
                    authenticated = await stream_manager.archive_org_adapter.check_authentication()
                    status["authenticated"] = authenticated
                except Exception as e:
                    logger.warning(f"Archive.org auth check failed: {e}")
                    status["authenticated"] = False
        
        # Check connection to archive.org
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("https://archive.org", follow_redirects=True)
                status["connection_ok"] = response.status_code == 200
        except Exception as e:
            logger.warning(f"Archive.org connection check failed: {e}")
            status["connection_ok"] = False
        
        # Parse errors from logs
        status["errors"] = parse_log_errors("archive_org")
        
        # Determine status color
        # Green: authenticated (via cookies or username) AND connection OK AND no errors
        if status["authenticated"] and status["connection_ok"] and not status["errors"]:
            status["status"] = "green"
        # Yellow: authenticated OR connection OK (partial functionality)
        elif status["authenticated"] or status["connection_ok"]:
            status["status"] = "yellow"
        else:
            status["status"] = "red"
            
    except Exception as e:
        logger.error(f"Error checking Archive.org status: {e}")
        status["errors"] = [str(e)]
        status["status"] = "red"
    
    return status

async def check_youtube_status() -> Dict:
    """Check YouTube authentication and connection status"""
    status = {
        "authenticated": False,
        "connection_ok": False,
        "status": "red",
        "errors": [],
        "cookies_file": None
    }
    
    try:
        # Check authentication
        if config.youtube.use_authentication and config.youtube.cookies_file:
            status["cookies_file"] = config.youtube.cookies_file
            cookies_path = Path(config.youtube.cookies_file)
            if cookies_path.exists():
                status["authenticated"] = True
        
        # Check connection to youtube.com
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("https://www.youtube.com", follow_redirects=True)
                status["connection_ok"] = response.status_code == 200
        except Exception as e:
            logger.warning(f"YouTube connection check failed: {e}")
            status["connection_ok"] = False
        
        # Parse errors from logs
        status["errors"] = parse_log_errors("youtube")
        
        # Determine status color
        if status["authenticated"] and status["connection_ok"] and not status["errors"]:
            status["status"] = "green"
        elif status["authenticated"] or status["connection_ok"]:
            status["status"] = "yellow"
        else:
            status["status"] = "red"
            
    except Exception as e:
        logger.error(f"Error checking YouTube status: {e}")
        status["errors"] = [str(e)]
        status["status"] = "red"
    
    return status

async def check_plex_status() -> Dict:
    """Check Plex status and library availability"""
    status = {
        "enabled": False,
        "library_available": False,
        "connection_ok": False,
        "status": "red",
        "errors": [],
        "base_url": None
    }
    
    try:
        # Check if Plex is enabled
        if config.plex.enabled and config.plex.base_url and config.plex.token:
            status["enabled"] = True
            status["base_url"] = config.plex.base_url
            
            # Check connection to Plex server
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    plex_url = f"{config.plex.base_url.rstrip('/')}/library/sections"
                    headers = {"X-Plex-Token": config.plex.token, "Accept": "application/json"}
                    response = await client.get(plex_url, headers=headers)
                    if response.status_code == 200:
                        status["connection_ok"] = True
                        # Check if libraries are available - try multiple response formats
                        try:
                            data = response.json()
                            # Check for MediaContainer.Directory (standard format)
                            if "MediaContainer" in data:
                                media_container = data["MediaContainer"]
                                # Check for Directory array
                                if "Directory" in media_container:
                                    libraries = media_container["Directory"]
                                    if isinstance(libraries, list):
                                        status["library_available"] = len(libraries) > 0
                                    elif isinstance(libraries, dict):
                                        # Sometimes it's a single library object
                                        status["library_available"] = True
                                # Also check size attribute (indicates libraries exist)
                                elif "size" in media_container and media_container.get("size", 0) > 0:
                                    status["library_available"] = True
                        except Exception as json_error:
                            # If JSON parsing fails, try XML response
                            try:
                                # Try XML format
                                plex_xml_url = f"{config.plex.base_url.rstrip('/')}/library/sections"
                                headers_xml = {"X-Plex-Token": config.plex.token, "Accept": "text/xml"}
                                xml_response = await client.get(plex_xml_url, headers=headers_xml)
                                if xml_response.status_code == 200:
                                    # If we get a 200 response, libraries are likely available
                                    status["library_available"] = True
                            except:
                                pass
            except Exception as e:
                logger.warning(f"Plex connection check failed: {e}")
                status["connection_ok"] = False
        
        # Parse errors from logs
        status["errors"] = parse_log_errors("plex")
        
        # Determine status color
        # Green: enabled, connected, libraries available, no errors
        if status["enabled"] and status["connection_ok"] and status["library_available"] and not status["errors"]:
            status["status"] = "green"
        # Yellow: enabled and (connected OR libraries available) - partial functionality
        elif status["enabled"] and (status["connection_ok"] or status["library_available"]):
            status["status"] = "yellow"
        else:
            status["status"] = "red"
            
    except Exception as e:
        logger.error(f"Error checking Plex status: {e}")
        status["errors"] = [str(e)]
        status["status"] = "red"
    
    return status

def check_ffmpeg_status() -> Dict:
    """Check FFmpeg installation and status"""
    status = {
        "installed": False,
        "version": None,
        "status": "red",
        "errors": []
    }
    
    try:
        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path:
            status["installed"] = True
            try:
                result = subprocess.run(
                    ["ffmpeg", "-version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    version_line = result.stdout.split('\n')[0] if result.stdout else "Unknown version"
                    status["version"] = version_line
                    status["status"] = "green"
                else:
                    status["status"] = "yellow"
            except Exception as e:
                logger.warning(f"FFmpeg version check failed: {e}")
                status["status"] = "yellow"
        else:
            status["status"] = "red"
        
        # Parse errors from logs
        status["errors"] = parse_log_errors("ffmpeg")
        
        # Update status based on errors
        if status["installed"] and status["status"] == "green" and status["errors"]:
            status["status"] = "yellow"
        elif not status["installed"]:
            status["status"] = "red"
            
    except Exception as e:
        logger.error(f"Error checking FFmpeg status: {e}")
        status["errors"] = [str(e)]
        status["status"] = "red"
    
    return status

def check_plex_api_status() -> Dict:
    """Check Plex API integration status"""
    status = {
        "enabled": False,
        "configured": False,
        "status": "red",
        "errors": []
    }
    
    try:
        if config.plex.enabled:
            status["enabled"] = True
            if config.plex.base_url and config.plex.token:
                status["configured"] = True
                status["status"] = "green"
            else:
                status["status"] = "yellow"
        else:
            status["status"] = "red"
        
        # Parse errors from logs
        status["errors"] = parse_log_errors("plex")
        
        # Update status based on errors
        if status["enabled"] and status["configured"] and status["errors"]:
            status["status"] = "yellow"
            
    except Exception as e:
        logger.error(f"Error checking Plex API status: {e}")
        status["errors"] = [str(e)]
        status["status"] = "red"
    
    return status

def check_ollama_status() -> Dict:
    """Check Ollama installation and integration status"""
    status = {
        "installed": False,
        "version": None,
        "integrated": False,
        "status": "red",
        "errors": []
    }
    
    try:
        # Check if Ollama is installed
        try:
            result = subprocess.run(
                ["ollama", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                status["installed"] = True
                version_line = result.stdout.strip() if result.stdout else "Unknown version"
                status["version"] = version_line
                
                # Check if models are installed (indicates integration)
                try:
                    models_result = subprocess.run(
                        ["ollama", "list"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if models_result.returncode == 0 and models_result.stdout:
                        lines = models_result.stdout.strip().split('\n')
                        if len(lines) > 1:  # Has models (header + at least one model)
                            status["integrated"] = True
                            status["status"] = "green"
                        else:
                            status["status"] = "yellow"  # Installed but no models
                    else:
                        status["status"] = "yellow"
                except:
                    status["status"] = "yellow"
            else:
                status["status"] = "red"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            status["installed"] = False
            status["status"] = "red"
        
        # Parse errors from logs
        status["errors"] = parse_log_errors("ollama")
        
        # Update status based on errors
        if status["installed"] and status["integrated"] and status["status"] == "green" and status["errors"]:
            status["status"] = "yellow"
        elif status["installed"] and not status["integrated"]:
            status["status"] = "yellow"
        elif not status["installed"]:
            status["status"] = "red"
            
    except Exception as e:
        logger.error(f"Error checking Ollama status: {e}")
        status["errors"] = [str(e)]
        status["status"] = "red"
    
    return status

async def check_streamtv_api_status() -> Dict:
    """Check StreamTV API status - always green if this endpoint is reachable"""
    status = {
        "available": True,
        "status": "green",
        "errors": []
    }
    
    try:
        # If we can reach this endpoint, API is working
        # Parse errors from logs to check for issues
        log_errors = parse_log_errors("streamtv")
        if log_errors:
            status["errors"].extend(log_errors)
            status["status"] = "yellow"
        
    except Exception as e:
        logger.error(f"Error checking StreamTV API status: {e}")
        status["errors"] = [str(e)]
        status["status"] = "yellow"
    
    return status

async def check_auth_apis_status() -> Dict:
    """Check Authentication APIs status"""
    status = {
        "available": True,
        "status": "green",
        "errors": []
    }
    
    try:
        # Parse errors from logs related to authentication
        log_errors = parse_log_errors("auth")
        if log_errors:
            status["errors"].extend(log_errors)
            status["status"] = "yellow"
        
        # Check if auth endpoints are accessible (if we can reach this, they should be too)
        # But check logs for auth-specific errors
        
    except Exception as e:
        logger.error(f"Error checking Auth APIs status: {e}")
        status["errors"] = [str(e)]
        status["status"] = "yellow"
    
    return status

@router.get("/dashboard/status")
async def get_dashboard_status():
    """Get comprehensive dashboard status for all components"""
    try:
        # Run all async checks in parallel
        archive_org_status, youtube_status, streamtv_api_status, auth_apis_status = await asyncio.gather(
            check_archive_org_status(),
            check_youtube_status(),
            check_streamtv_api_status(),
            check_auth_apis_status(),
            return_exceptions=True
        )
        
        # Handle exceptions
        if isinstance(archive_org_status, Exception):
            archive_org_status = {"status": "red", "errors": [str(archive_org_status)], "authenticated": False, "connection_ok": False}
        if isinstance(youtube_status, Exception):
            youtube_status = {"status": "red", "errors": [str(youtube_status)], "authenticated": False, "connection_ok": False}
        if isinstance(streamtv_api_status, Exception):
            streamtv_api_status = {"status": "red", "errors": [str(streamtv_api_status)], "available": False}
        if isinstance(auth_apis_status, Exception):
            auth_apis_status = {"status": "yellow", "errors": [str(auth_apis_status)], "available": True}
        
        # Run synchronous checks (with error handling)
        try:
            ffmpeg_status = check_ffmpeg_status()
        except Exception as e:
            ffmpeg_status = {"status": "red", "errors": [str(e)], "installed": False}
        
        try:
            plex_api_status = check_plex_api_status()
        except Exception as e:
            plex_api_status = {"status": "red", "errors": [str(e)], "enabled": False, "configured": False}
        
        # Plex status (optional, may fail if not configured)
        try:
            plex_status = await check_plex_status()
        except Exception as e:
            plex_status = {"status": "red", "errors": [str(e)], "enabled": False, "library_available": False, "connection_ok": False}
        
        return {
            "archive_org": archive_org_status,
            "youtube": youtube_status,
            "ffmpeg": ffmpeg_status,
            "plex_api": plex_api_status,
            "streamtv_api": streamtv_api_status,
            "auth_apis": auth_apis_status,
            "plex": plex_status
        }
    except Exception as e:
        logger.error(f"Error getting dashboard status: {e}")
        # Return minimal status even on error
        return {
            "archive_org": {"status": "red", "errors": [f"Status check failed: {str(e)}"], "authenticated": False, "connection_ok": False},
            "youtube": {"status": "red", "errors": [f"Status check failed: {str(e)}"], "authenticated": False, "connection_ok": False},
            "ffmpeg": {"status": "red", "errors": [f"Status check failed: {str(e)}"], "installed": False},
            "plex_api": {"status": "red", "errors": [f"Status check failed: {str(e)}"], "enabled": False, "configured": False},
            "streamtv_api": {"status": "red", "errors": [f"Status check failed: {str(e)}"], "available": False},
            "auth_apis": {"status": "red", "errors": [f"Status check failed: {str(e)}"], "available": False}
        }
