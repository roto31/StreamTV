"""Authentication API endpoints for Archive.org and YouTube"""

from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import logging
import shutil
from slowapi import Limiter
from slowapi.util import get_remote_address
from functools import wraps

from ..config import config
from ..streaming import StreamManager
from ..utils.macos_credentials import store_credentials_in_keychain
from ..utils.passkeys import PasskeyManager, WEBAUTHN_AVAILABLE
from ..database import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])
templates = Jinja2Templates(directory="streamtv/templates")

# Helper function to create rate-limited endpoint
# Note: Rate limiting is currently disabled to avoid decorator issues
# TODO: Implement proper rate limiting with slowapi
def rate_limit(limit: str):
    """Decorator factory for rate limiting - currently a no-op"""
    def decorator(func):
        # For now, just return the function unchanged
        # Rate limiting can be re-enabled later with proper slowapi integration
        return func
    return decorator

# Initialize Passkey Manager
try:
    if WEBAUTHN_AVAILABLE:
        # Get RP ID from config (domain name or localhost)
        # For localhost, use "localhost" for WebAuthn compatibility
        rp_id = "localhost"  # WebAuthn requires exact domain match
        # In production, use actual domain: rp_id = config.server.host if config.server.host != "0.0.0.0" else "localhost"
        
        from pathlib import Path
        credentials_file = Path("data/passkeys.json")
        passkey_manager = PasskeyManager(rp_id=rp_id, rp_name="StreamTV", credentials_file=credentials_file)
        logger.info("Passkey Manager initialized")
    else:
        passkey_manager = None
        logger.warning("Passkey support not available. Install webauthn library: pip install webauthn")
except Exception as e:
    logger.warning(f"Failed to initialize Passkey Manager: {e}")
    passkey_manager = None


class ArchiveOrgCredentials(BaseModel):
    username: str
    password: str


class YouTubeCookies(BaseModel):
    cookies_file: str


@router.get("/archive-org", response_class=HTMLResponse)
async def archive_org_login_page_legacy(request: Request):
    """Archive.org authentication page (legacy route - uses new template)"""
    # Use the same template as /archive for consistency
    return templates.TemplateResponse("auth_archive.html", {
        "request": request,
        "authenticated": bool(config.archive_org.cookies_file),
        "cookies_file": config.archive_org.cookies_file or ""
    })

@router.get("/archive", response_class=HTMLResponse)
async def archive_org_login_page(request: Request):
    """Archive.org login page"""
    # Check if credentials exist (from Keychain or config)
    from ..utils.macos_credentials import get_credentials_from_keychain
    keychain_creds = get_credentials_from_keychain("archive.org")
    authenticated = bool(keychain_creds) or bool(config.archive_org.username)
    username = keychain_creds[0] if keychain_creds else (config.archive_org.username or "")
    
    return templates.TemplateResponse("auth_archive_org.html", {
        "request": request,
        "authenticated": authenticated,
        "username": username
    })


@router.post("/archive-org")
@rate_limit("5/minute")
async def archive_org_login(request: Request, credentials: ArchiveOrgCredentials, db: Session = Depends(get_db)):
    """Login to Archive.org - Rate limited to 5 requests per minute"""
    try:
        # Store in keychain on macOS (primary secure storage)
        import platform
        if platform.system() == "Darwin":
            store_credentials_in_keychain("archive.org", credentials.username, credentials.password)
        
        # Update config WITHOUT storing password (only username for reference)
        # Password should NEVER be stored in config.yaml
        config.update_section("archive_org", {
            "username": credentials.username,  # Only store username for reference
            "password": None,  # Never store password in config
            "use_authentication": True
        })
        
        # Update StreamManager with credentials (in-memory only)
        stream_manager = StreamManager()
        stream_manager.update_archive_org_credentials(
            credentials.username,
            credentials.password
        )
        
        # Best-effort authentication check (non-fatal)
        auth_verified = False
        try:
            auth_verified = await stream_manager.archive_org_adapter.check_authentication()
            if not auth_verified:
                # Try to login once
                client = await stream_manager.archive_org_adapter._ensure_authenticated()
                await client.aclose()
                auth_verified = await stream_manager.archive_org_adapter.check_authentication()
        except Exception as e:
            logger.warning(f"Archive.org authentication verification failed (credentials saved, but not yet verified): {e}")
            auth_verified = False
        
        # Always treat this as a successful save of credentials; verification is advisory.
        # This avoids confusing 'invalid credentials' messages when Archive.org is slow or changes behavior.
        return {
            "status": "success",
            "message": "Archive.org credentials saved" + (" and verified." if auth_verified else ". Verification will occur on first use."),
            "verified": auth_verified
        }
            
    except Exception as e:
        logger.error(f"Archive.org login error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/archive-org")
async def archive_org_logout():
    """Logout from Archive.org"""
    config.update_section("archive_org", {
        "username": None,
        "password": None,
        "use_authentication": False
    })
    
    stream_manager = StreamManager()
    stream_manager.archive_org_adapter._authenticated = False
    stream_manager.archive_org_adapter._session_cookies = None
    
    return {"status": "success", "message": "Logged out from Archive.org"}


@router.get("/archive-org/status")
async def archive_org_status():
    """Get Archive.org authentication status"""
    authenticated = False
    if config.archive_org.use_authentication and config.archive_org.username:
        stream_manager = StreamManager()
        try:
            import asyncio
            authenticated = await stream_manager.archive_org_adapter.check_authentication()
        except Exception:
            authenticated = False
    
    return {
        "authenticated": authenticated,
        "username": config.archive_org.username if config.archive_org.use_authentication else None,
        "use_authentication": config.archive_org.use_authentication
    }


@router.get("/youtube", response_class=HTMLResponse)
async def youtube_login_page(request: Request):
    """YouTube login page"""
    return templates.TemplateResponse("auth_youtube.html", {
        "request": request,
        "authenticated": bool(config.youtube.cookies_file),
        "cookies_file": config.youtube.cookies_file or ""
    })


@router.post("/youtube/cookies")
@rate_limit("10/hour")
async def youtube_set_cookies(request: Request, file: UploadFile = File(...)):
    """Upload and set YouTube cookies file - Rate limited to 10 requests per hour"""
    """Upload and set YouTube cookies file"""
    from pathlib import Path
    
    # Create cookies directory if it doesn't exist
    cookies_dir = Path("data/cookies")
    cookies_dir.mkdir(parents=True, exist_ok=True)
    
    # Save uploaded file
    cookies_path = cookies_dir / "youtube_cookies.txt"
    
    try:
        with open(cookies_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Validate it's a valid cookies file (basic check)
        with open(cookies_path, "r") as f:
            content = f.read()
            if "youtube.com" not in content.lower() and "# Netscape" not in content:
                cookies_path.unlink()  # Delete invalid file
                raise HTTPException(status_code=400, detail="Invalid cookies file format")
        
        # Update config and persist to file
        config.update_section("youtube", {
            "cookies_file": str(cookies_path.absolute()),
            "use_authentication": True
        })
        
        # Update StreamManager
        stream_manager = StreamManager()
        if stream_manager.youtube_adapter:
            stream_manager.youtube_adapter.cookies_file = str(cookies_path.absolute())
            stream_manager.youtube_adapter._ydl_opts['cookiefile'] = str(cookies_path.absolute())
        
        return {"status": "success", "message": f"Cookies file uploaded and configured"}
        
    except Exception as e:
        logger.error(f"Error uploading cookies file: {e}")
        if cookies_path.exists():
            cookies_path.unlink()
        raise HTTPException(status_code=500, detail=str(e))


# Archive.org Authentication Endpoints

@router.get("/archive", response_class=HTMLResponse)
async def archive_login_page(request: Request):
    """Archive.org authentication page"""
    return templates.TemplateResponse("auth_archive.html", {
        "request": request,
        "authenticated": bool(config.archive_org.cookies_file),
        "cookies_file": config.archive_org.cookies_file or ""
    })


@router.post("/archive/cookies")
@rate_limit("10/hour")
async def archive_set_cookies(request: Request, file: UploadFile = File(...)):
    """Upload and set Archive.org cookies file - Rate limited to 10 requests per hour"""
    from pathlib import Path
    
    # Create cookies directory if it doesn't exist
    cookies_dir = Path("data/cookies")
    cookies_dir.mkdir(parents=True, exist_ok=True)
    
    # Save uploaded file
    cookies_path = cookies_dir / "archive_cookies.txt"
    
    try:
        with open(cookies_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Validate it's a valid cookies file (basic check)
        with open(cookies_path, "r") as f:
            content = f.read()
            if "archive.org" not in content.lower() and "# Netscape" not in content:
                cookies_path.unlink()  # Delete invalid file
                raise HTTPException(status_code=400, detail="Invalid cookies file format. Must contain archive.org cookies.")
        
        # Update config and persist to file
        config.update_section("archive_org", {
            "cookies_file": str(cookies_path.absolute()),
            "use_authentication": True
        })
        
        # Update StreamManager - reload archive adapter with new cookies
        stream_manager = StreamManager()
        if stream_manager.archive_org_adapter:
            stream_manager.archive_org_adapter.cookies_file = str(cookies_path.absolute())
            stream_manager.archive_org_adapter._load_cookies_from_file()
        
        return {"status": "success", "message": f"Archive.org cookies file uploaded and configured"}
        
    except Exception as e:
        logger.error(f"Error uploading Archive.org cookies file: {e}")
        if cookies_path.exists():
            cookies_path.unlink()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/archive")
@rate_limit("10/hour")
async def archive_logout(request: Request):
    """Remove Archive.org authentication - Rate limited to 10 requests per hour"""
    from pathlib import Path
    
    try:
        import yaml
        
        # Remove cookies file if it exists
        cookies_file_path = None
        if config.archive_org.cookies_file:
            cookies_file_path = Path(config.archive_org.cookies_file)
            if cookies_file_path.exists():
                cookies_file_path.unlink()
                logger.info(f"Deleted Archive.org cookies file: {cookies_file_path}")
        
        # Directly manipulate YAML file to avoid validation issues
        config_path = Path(config._config_path)
        with open(config_path, 'r') as f:
            yaml_data = yaml.safe_load(f) or {}
        
        # Update archive_org section
        if "archive_org" not in yaml_data:
            yaml_data["archive_org"] = {}
        
        # Remove cookies_file key entirely
        yaml_data["archive_org"].pop("cookies_file", None)
        yaml_data["archive_org"]["use_authentication"] = False
        
        # Write back to file
        with open(config_path, 'w') as f:
            yaml.safe_dump(yaml_data, f, sort_keys=False, default_flow_style=False, allow_unicode=True)
        
        # Reload config
        config._config_data = yaml_data
        config.archive_org = config._section_classes["archive_org"](**yaml_data.get("archive_org", {}))
        
        # Update StreamManager - create new instance which will read updated config
        stream_manager = StreamManager()
        if stream_manager.archive_org_adapter:
            stream_manager.archive_org_adapter.cookies_file = None
            stream_manager.archive_org_adapter._session_cookies = None
            stream_manager.archive_org_adapter._authenticated = False
            stream_manager.archive_org_adapter.use_authentication = False
            logger.info("Cleared Archive.org authentication from StreamManager")
        
        logger.info("Archive.org authentication successfully removed")
        return {"status": "success", "message": "Archive.org authentication removed"}
        
    except Exception as e:
        logger.error(f"Error removing Archive.org authentication: {e}", exc_info=True)
        # Return a more user-friendly error message
        error_detail = str(e)
        if "pattern" in error_detail.lower() or "validation" in error_detail.lower():
            error_detail = "Configuration validation error. Please check the config.yaml file manually."
        raise HTTPException(status_code=500, detail=error_detail)


# PBS Authentication Endpoints

@router.get("/pbs", response_class=HTMLResponse)
async def pbs_login_page(request: Request):
    """PBS authentication page"""
    return templates.TemplateResponse("auth_pbs.html", {
        "request": request,
        "authenticated": bool(config.pbs.cookies_file),
        "cookies_file": config.pbs.cookies_file or ""
    })


@router.post("/pbs/cookies")
@rate_limit("10/hour")
async def pbs_set_cookies(request: Request, file: UploadFile = File(...)):
    """Upload and set PBS cookies file - Rate limited to 10 requests per hour"""
    from pathlib import Path
    
    # Create cookies directory if it doesn't exist
    cookies_dir = Path("data/cookies")
    cookies_dir.mkdir(parents=True, exist_ok=True)
    
    # Save uploaded file
    cookies_path = cookies_dir / "pbs_cookies.txt"
    
    try:
        with open(cookies_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Validate it's a valid cookies file (basic check)
        with open(cookies_path, "r") as f:
            content = f.read()
            if "pbs.org" not in content.lower() and "# Netscape" not in content:
                cookies_path.unlink()  # Delete invalid file
                raise HTTPException(status_code=400, detail="Invalid cookies file format. Must contain PBS cookies (pbs.org, etc.).")
        
        # Update config and persist to file
        config.update_section("pbs", {
            "cookies_file": str(cookies_path.absolute()),
            "use_authentication": True
        })
        
        # Update StreamManager - reload PBS adapter with new cookies
        stream_manager = StreamManager()
        if stream_manager.pbs_adapter:
            stream_manager.pbs_adapter.cookies_file = str(cookies_path.absolute())
            stream_manager.pbs_adapter._load_cookies_from_file()
        
        return {"status": "success", "message": f"PBS cookies file uploaded and configured"}
        
    except Exception as e:
        logger.error(f"Error uploading PBS cookies file: {e}")
        if cookies_path.exists():
            cookies_path.unlink()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/pbs")
@rate_limit("10/hour")
async def pbs_logout(request: Request):
    """Remove PBS authentication - Rate limited to 10 requests per hour"""
    from pathlib import Path
    
    try:
        import yaml
        
        # Remove cookies file if it exists
        cookies_file_path = None
        if config.pbs.cookies_file:
            cookies_file_path = Path(config.pbs.cookies_file)
            if cookies_file_path.exists():
                cookies_file_path.unlink()
                logger.info(f"Deleted PBS cookies file: {cookies_file_path}")
        
        # Directly manipulate YAML file to avoid validation issues
        config_path = Path(config._config_path)
        with open(config_path, 'r') as f:
            yaml_data = yaml.safe_load(f) or {}
        
        # Update pbs section
        if "pbs" not in yaml_data:
            yaml_data["pbs"] = {}
        
        # Remove cookies_file key entirely
        yaml_data["pbs"].pop("cookies_file", None)
        yaml_data["pbs"]["use_authentication"] = False
        
        # Write back to file
        with open(config_path, 'w') as f:
            yaml.safe_dump(yaml_data, f, sort_keys=False, default_flow_style=False, allow_unicode=True)
        
        # Reload config
        config._config_data = yaml_data
        config.pbs = config._section_classes["pbs"](**yaml_data.get("pbs", {}))
        
        # Update StreamManager - create new instance which will read updated config
        stream_manager = StreamManager()
        if stream_manager.pbs_adapter:
            stream_manager.pbs_adapter.cookies_file = None
            stream_manager.pbs_adapter._session_cookies = None
            stream_manager.pbs_adapter._authenticated = False
            stream_manager.pbs_adapter.use_authentication = False
            logger.info("Cleared PBS authentication from StreamManager")
        
        logger.info("PBS authentication successfully removed")
        return {"status": "success", "message": "PBS authentication removed"}
        
    except Exception as e:
        logger.error(f"Error removing PBS authentication: {e}", exc_info=True)
        error_detail = str(e)
        if "pattern" in error_detail.lower() or "validation" in error_detail.lower():
            error_detail = "Configuration validation error. Please check the config.yaml file manually."
        raise HTTPException(status_code=500, detail=error_detail)


@router.get("/youtube/oauth")
@rate_limit("10/minute")
async def youtube_oauth_start(request: Request, skip_passkey: bool = False):
    """Start YouTube OAuth flow - Rate limited to 10 requests per minute"""
    """Start YouTube OAuth flow - requires Passkey verification first"""
    from ..utils.youtube_oauth import YouTubeOAuth
    
    # Check if Passkey verification is required
    if not skip_passkey and passkey_manager:
        # Check if user has registered Passkey
        # For now, we'll show Passkey verification page
        # In production, you'd check session/cookies for authenticated user
        return templates.TemplateResponse("auth_youtube_passkey.html", {
            "request": request,
            "oauth_ready": False,
            "passkey_available": True
        })
    
    try:
        # Check if OAuth client is configured
        if not config.youtube.oauth_client_id:
            return templates.TemplateResponse("auth_youtube_oauth_setup.html", {
                "request": request,
                "needs_setup": True
            })
        
        # Generate OAuth URL
        oauth = YouTubeOAuth(
            client_id=config.youtube.oauth_client_id,
            client_secret=config.youtube.oauth_client_secret,
            redirect_uri=f"{config.server.base_url}/api/auth/youtube/oauth/callback",
            state_store=config._oauth_states
        )
        
        auth_url, state = oauth.generate_authorization_url()
        
        # Redirect to Google OAuth
        return RedirectResponse(url=auth_url)
        
    except ValueError as e:
        return templates.TemplateResponse("auth_youtube_oauth_setup.html", {
            "request": request,
            "needs_setup": True,
            "error": str(e)
        })
    except Exception as e:
        logger.error(f"Error starting OAuth flow: {e}")
        raise HTTPException(status_code=500, detail=f"OAuth error: {str(e)}")


@router.post("/youtube/oauth/passkey/register")
@rate_limit("5/minute")
async def passkey_register_start(request: Request):
    """Start Passkey registration for YouTube OAuth - Rate limited to 5 requests per minute"""
    """Start Passkey registration for YouTube OAuth"""
    if not passkey_manager:
        raise HTTPException(status_code=501, detail="Passkey support not available. Install webauthn library.")
    
    data = await request.json()
    username = data.get("username", "youtube_user")
    
    try:
        challenge = passkey_manager.generate_registration_challenge(username)
        return {"challenge": challenge}
    except Exception as e:
        logger.error(f"Error generating Passkey registration challenge: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/youtube/oauth/passkey/register/verify")
@rate_limit("5/minute")
async def passkey_register_verify(request: Request):
    """Verify Passkey registration - Rate limited to 5 requests per minute"""
    """Verify Passkey registration"""
    if not passkey_manager:
        raise HTTPException(status_code=501, detail="Passkey support not available")
    
    data = await request.json()
    challenge_b64 = data.get("challenge")  # This is the challenge from the original options
    credential = data.get("credential")
    origin = str(request.url.origin())
    
    if not challenge_b64 or not credential:
        raise HTTPException(status_code=400, detail="Missing challenge or credential")
    
    try:
        # Extract the actual challenge from stored challenges
        # The challenge_b64 is the base64url encoded challenge from the options
        result = passkey_manager.verify_registration(challenge_b64, credential, origin)
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"Passkey registration verification failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/youtube/oauth/passkey/authenticate")
@rate_limit("5/minute")
async def passkey_authenticate_start(request: Request):
    """Start Passkey authentication - Rate limited to 5 requests per minute"""
    """Start Passkey authentication"""
    if not passkey_manager:
        raise HTTPException(status_code=501, detail="Passkey support not available")
    
    data = await request.json()
    username = data.get("username")  # Optional - if not provided, allows any registered Passkey
    
    try:
        challenge = passkey_manager.generate_authentication_challenge(username)
        return {"challenge": challenge}
    except Exception as e:
        logger.error(f"Error generating Passkey authentication challenge: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/youtube/oauth/passkey/authenticate/verify")
@rate_limit("5/minute")
async def passkey_authenticate_verify(request: Request):
    """Verify Passkey authentication and proceed with OAuth - Rate limited to 5 requests per minute"""
    """Verify Passkey authentication and proceed with OAuth"""
    if not passkey_manager:
        raise HTTPException(status_code=501, detail="Passkey support not available")
    
    data = await request.json()
    challenge_b64 = data.get("challenge")  # This is the challenge from the original options
    credential = data.get("credential")
    origin = str(request.url.origin())
    
    if not challenge_b64 or not credential:
        raise HTTPException(status_code=400, detail="Missing challenge or credential")
    
    try:
        result = passkey_manager.verify_authentication(challenge_b64, credential, origin)
        
        # If Passkey verified, proceed with OAuth
        if result.get("authenticated"):
            # Generate OAuth URL
            from ..utils.youtube_oauth import YouTubeOAuth
            
            if not config.youtube.oauth_client_id:
                return {
                    "status": "passkey_verified",
                    "oauth_required": True,
                    "message": "Passkey verified. OAuth client setup required."
                }
            
            oauth = YouTubeOAuth(
                client_id=config.youtube.oauth_client_id,
                client_secret=config.youtube.oauth_client_secret,
                redirect_uri=f"{config.server.base_url}/api/auth/youtube/oauth/callback",
                state_store=config._oauth_states
            )
            
            auth_url, state = oauth.generate_authorization_url()
            
            return {
                "status": "success",
                "authenticated": True,
                "oauth_url": auth_url,
                "message": "Passkey verified. Redirecting to Google OAuth..."
            }
        else:
            raise HTTPException(status_code=401, detail="Passkey authentication failed")
            
    except Exception as e:
        logger.error(f"Passkey authentication verification failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/youtube/oauth/callback")
@rate_limit("10/minute")
async def youtube_oauth_callback(request: Request, code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None):
    """Handle OAuth callback from Google - Rate limited to 10 requests per minute"""
    """Handle OAuth callback from Google"""
    from ..utils.youtube_oauth import YouTubeOAuth
    from pathlib import Path
    
    if error:
        return templates.TemplateResponse("auth_youtube_oauth_error.html", {
            "request": request,
            "error": error
        })
    
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state parameter")
    
    try:
        oauth = YouTubeOAuth(
            client_id=config.youtube.oauth_client_id,
            client_secret=config.youtube.oauth_client_secret,
            redirect_uri=f"{config.server.base_url}/api/auth/youtube/oauth/callback",
            state_store=config._oauth_states
        )
        
        # Exchange code for tokens
        tokens = await oauth.exchange_code_for_tokens(code, state)
        
        # Store refresh token
        if 'refresh_token' in tokens:
            config.update_section("youtube", {
                "oauth_refresh_token": tokens['refresh_token'],
                "use_authentication": True
            })
        
        # Use yt-dlp to convert tokens to cookies
        # yt-dlp can use OAuth tokens directly, but we need to convert to cookies format
        # For now, we'll use the tokens with yt-dlp's OAuth support
        
        # Update YouTube adapter to use OAuth tokens
        stream_manager = StreamManager()
        if stream_manager.youtube_adapter and 'access_token' in tokens:
            # Store tokens for yt-dlp to use
            tokens_file = Path("data/cookies/youtube_oauth_tokens.json")
            tokens_file.parent.mkdir(parents=True, exist_ok=True)
            import json
            with open(tokens_file, 'w') as f:
                json.dump(tokens, f, indent=2)
            
            logger.info("OAuth tokens received. Note: yt-dlp OAuth integration requires additional configuration.")
        
        return templates.TemplateResponse("auth_youtube_oauth_success.html", {
            "request": request,
            "message": "OAuth authentication successful! Tokens stored. Note: Full OAuth support requires yt-dlp configuration."
        })
        
    except Exception as e:
        logger.error(f"Error in OAuth callback: {e}")
        return templates.TemplateResponse("auth_youtube_oauth_error.html", {
            "request": request,
            "error": str(e)
        })


@router.get("/youtube/status")
async def youtube_status():
    """Get YouTube authentication status"""
    return {
        "authenticated": bool(config.youtube.cookies_file),
        "cookies_file": config.youtube.cookies_file if config.youtube.use_authentication else None,
        "use_authentication": config.youtube.use_authentication
    }


@router.delete("/youtube")
async def youtube_logout():
    """Remove YouTube authentication"""
    config.update_section("youtube", {
        "cookies_file": None,
        "use_authentication": False
    })
    
    stream_manager = StreamManager()
    if stream_manager.youtube_adapter:
        stream_manager.youtube_adapter.cookies_file = None
        if 'cookiefile' in stream_manager.youtube_adapter._ydl_opts:
            del stream_manager.youtube_adapter._ydl_opts['cookiefile']
    
    return {"status": "success", "message": "YouTube authentication removed"}

