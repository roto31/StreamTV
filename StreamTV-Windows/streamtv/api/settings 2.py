"""Settings API endpoints"""

from fastapi import APIRouter

from ..config import config
from .schemas import (
    FFmpegSettingsResponse, 
    FFmpegSettingsUpdate,
    HDHomeRunSettingsResponse,
    HDHomeRunSettingsUpdate,
    PlayoutSettingsResponse,
    PlayoutSettingsUpdate,
    PlexSettingsResponse,
    PlexSettingsUpdate
)

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("/ffmpeg", response_model=FFmpegSettingsResponse)
def get_ffmpeg_settings():
    """Return current FFmpeg settings"""
    return config.ffmpeg


@router.put("/ffmpeg", response_model=FFmpegSettingsResponse)
def update_ffmpeg_settings(settings: FFmpegSettingsUpdate):
    """Update FFmpeg settings and persist to config file"""
    update_payload = {k: v for k, v in settings.model_dump(exclude_unset=True).items()}
    config.update_section("ffmpeg", update_payload)
    return config.ffmpeg


@router.get("/hdhr", response_model=HDHomeRunSettingsResponse)
def get_hdhr_settings():
    """Return current HDHomeRun settings"""
    return config.hdhomerun


@router.put("/hdhr", response_model=HDHomeRunSettingsResponse)
def update_hdhr_settings(settings: HDHomeRunSettingsUpdate):
    """Update HDHomeRun settings and persist to config file"""
    update_payload = {k: v for k, v in settings.model_dump(exclude_unset=True).items()}
    config.update_section("hdhomerun", update_payload)
    return config.hdhomerun


@router.get("/playout", response_model=PlayoutSettingsResponse)
def get_playout_settings():
    """Return current Playout settings"""
    return config.playout


@router.put("/playout", response_model=PlayoutSettingsResponse)
def update_playout_settings(settings: PlayoutSettingsUpdate):
    """Update Playout settings and persist to config file"""
    update_payload = {k: v for k, v in settings.model_dump(exclude_unset=True).items()}
    config.update_section("playout", update_payload)
    return config.playout


@router.get("/plex", response_model=PlexSettingsResponse)
def get_plex_settings():
    """Return current Plex API settings"""
    return config.plex


@router.put("/plex", response_model=PlexSettingsResponse)
def update_plex_settings(settings: PlexSettingsUpdate):
    """Update Plex API settings and persist to config file"""
    update_payload = {k: v for k, v in settings.model_dump(exclude_unset=True).items()}
    config.update_section("plex", update_payload)
    return config.plex


@router.post("/plex/test")
async def test_plex_connection():
    """Test Plex API connection"""
    import asyncio
    import httpx
    from xml.etree import ElementTree as ET
    from ..streaming.plex_api_client import PlexAPIClient
    
    if not config.plex.enabled:
        return {"success": False, "error": "Plex integration is not enabled. Please enable it first."}
    
    if not config.plex.base_url:
        return {"success": False, "error": "Plex server base_url is not configured. Please enter your Plex server URL."}
    
    if not config.plex.token:
        return {"success": False, "error": "Plex authentication token is not configured. Please enter your Plex token."}
    
    # Validate URL format
    base_url = config.plex.base_url.strip().rstrip('/')
    if not base_url.startswith(('http://', 'https://')):
        return {"success": False, "error": f"Invalid URL format: {base_url}. URL must start with http:// or https://"}
    
    try:
        async with PlexAPIClient(
            base_url=base_url,
            token=config.plex.token
        ) as client:
            # Get server info - this will raise ValueError with specific error messages
            server_info = await client.get_server_info()
            
            if not server_info:
                return {"success": False, "error": "Could not retrieve server information. Please check your base_url and token."}
            
            # Try to get DVRs (this may fail if DVR is not set up, which is OK)
            dvrs_count = 0
            try:
                dvrs = await client.get_dvrs()
                dvrs_count = len(dvrs) if dvrs else 0
            except Exception:
                # DVR check is optional - don't fail if DVR is not configured
                pass
            
            return {
                "success": True,
                "server_info": server_info,
                "dvrs_count": dvrs_count,
                "message": "Connection successful!"
            }
            
    except ValueError as e:
        # ValueError from get_server_info contains specific error message
        return {"success": False, "error": str(e)}
    except httpx.ConnectError as e:
        return {"success": False, "error": f"Could not connect to {base_url}. Error: {str(e)}. Check if the Plex server is running and the URL is correct."}
    except httpx.TimeoutException:
        return {"success": False, "error": f"Connection to {base_url} timed out after 10 seconds. The server may be unreachable or slow to respond."}
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "Unauthorized" in error_msg:
            return {"success": False, "error": "Authentication failed. The Plex token is invalid or expired. Please check your token."}
        elif "Connect" in error_msg or "connect" in error_msg.lower():
            return {"success": False, "error": f"Could not connect to {base_url}. Check if the Plex server is running and accessible."}
        return {"success": False, "error": f"Connection failed: {error_msg}"}

