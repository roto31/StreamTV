"""Main application entry point"""

import logging
import os
from typing import Optional
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path
from sqlalchemy.orm import Session
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .config import config
from .database import init_db, get_db
from .api import api_router, iptv_router_instance, docs_router, logs_router
from .api.ollama import router as ollama_router
from .api.tuner_manager import tuner_router
from .hdhomerun import (
    hdhomerun_router,
    SSDPServer,
    HDHomeRunDiscoveryServer,
    ensure_stable_device_id,
)
from .runtime_lock import acquire_instance_lock, InstanceLockError
from .utils.logging_setup import setup_logging, log_system_info

# Configure comprehensive logging to console and ~/Library/Logs/StreamTV/
setup_logging(
    log_level=config.logging.level,
    log_to_console=True,
    log_to_file=True
)

logger = logging.getLogger(__name__)

# Log system information at startup
log_system_info()

# Persist a stable DeviceID before any discovery advertisement
config.hdhomerun.device_id = ensure_stable_device_id(config.hdhomerun.device_id)

# Global discovery servers
ssdp_server: SSDPServer = None
hdhr_discovery_server: HDHomeRunDiscoveryServer = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    global ssdp_server, hdhr_discovery_server
    
    # Startup
    logger.info("LIFESPAN: Starting lifespan function...")
    logger.info("Initializing StreamTV...")

    # yt-dlp version policy (non-fatal, log-only)
    try:
        import yt_dlp
        from streamtv.ffmpeg.constants import YTDLP_MIN_VERSION
        installed = yt_dlp.version.__version__
        if installed < YTDLP_MIN_VERSION:   # CalVer strings compare lexically
            logger.warning(
                f"yt-dlp {installed} is older than the recommended {YTDLP_MIN_VERSION}. "
                "Stale yt-dlp is the most common cause of sudden YouTube failures. "
                "Update with: pip install -U yt-dlp")
    except Exception as e:
        logger.warning(f"Could not verify yt-dlp version: {e}")

    logger.info("LIFESPAN: About to call init_db()...")
    init_db()
    logger.info("Database initialized")
    
    # Start SSDP server for HDHomeRun discovery if enabled
    if config.hdhomerun.enabled and config.hdhomerun.enable_ssdp:
        try:
            ssdp_server = SSDPServer(
                device_id=config.hdhomerun.device_id,
                friendly_name=config.hdhomerun.friendly_name
            )
            ssdp_server.start()
            logger.info("HDHomeRun SSDP server started")
        except Exception as e:
            logger.warning(f"Failed to start HDHomeRun SSDP server: {e}")
            logger.info("HDHomeRun device can still be accessed manually at /hdhomerun/discover.json")
    elif config.hdhomerun.enabled:
        logger.info("HDHomeRun enabled (SSDP disabled). Use /hdhomerun/discover.json for manual setup.")

    # Native HDHomeRun UDP discovery (port 65001) — Plex's primary scan path
    if config.hdhomerun.enabled:
        try:
            hdhr_discovery_server = HDHomeRunDiscoveryServer(
                device_id=config.hdhomerun.device_id,
                base_url=config.server.base_url,
                tuner_count=config.hdhomerun.tuner_count,
            )
            hdhr_discovery_server.start()
            app.state.hdhr_discovery = hdhr_discovery_server
            logger.info(
                "HDHomeRun native discovery started (UDP 65001, DeviceID=%s)",
                config.hdhomerun.device_id,
            )
        except Exception as e:
            logger.warning(f"Failed to start HDHomeRun port-65001 discovery: {e}")
    
    # Start continuous streaming for all enabled channels (ErsatzTV-style)
    # This is needed for both HDHomeRun and IPTV endpoints (Plex can use IPTV directly)
    try:
        logger.info("Starting channel manager initialization...")
        from streamtv.streaming.channel_manager import ChannelManager
        from streamtv.database.session import SessionLocal
        # Pass the session factory (SessionLocal) to ChannelManager
        # SessionLocal is a sessionmaker that creates sessions when called
        logger.info("Creating ChannelManager instance...")
        channel_manager = ChannelManager(SessionLocal)
        logger.info("Starting all channels...")
        await channel_manager.start_all_channels()
        # Store in app state for access from endpoints
        app.state.channel_manager = channel_manager
        logger.info("Started continuous streaming for all enabled channels (ErsatzTV-style)")
    except Exception as e:
        logger.warning(f"Failed to start continuous channel streaming: {e}", exc_info=True)
        logger.info("Channels will start on-demand when clients connect")
        app.state.channel_manager = None

    # Plex keeps its own EPG SQLite across restarts — re-fetch merged guide after playout resumes.
    try:
        from streamtv.plex.guide_reload import schedule_startup_plex_guide_reload

        schedule_startup_plex_guide_reload()
        logger.info("Scheduled Plex reloadGuide ~45s after startup")
    except Exception as e:
        logger.debug("Plex startup guide reload schedule skipped: %s", e)

    # Start download-first cache system (if enabled)
    if config.cache.enabled:
        try:
            from streamtv.database.session import SessionLocal
            from streamtv.cache import (
                CacheManager,
                DownloadQueue,
                DownloadScheduler,
                bind_runtime,
            )

            cache_manager = CacheManager(SessionLocal)
            download_queue = DownloadQueue(cache_manager, SessionLocal)
            download_scheduler = DownloadScheduler(
                cache_manager, download_queue, SessionLocal
            )

            await download_queue.start()
            await download_scheduler.start()

            app.state.cache_manager = cache_manager
            app.state.download_queue = download_queue
            app.state.download_scheduler = download_scheduler
            bind_runtime(cache_manager, download_queue)
            from streamtv.cache.playback_mode import playback_mode

            logger.info(
                f"Cache system started (playback_mode={playback_mode()})"
            )

            from .api.cache_files import configure_cache_serving, router as cache_files_router
            from pathlib import Path as _P

            _cache_dir = _P(config.cache.cache_directory).expanduser()
            _cache_dir.mkdir(parents=True, exist_ok=True)
            configure_cache_serving(_cache_dir)
            app.include_router(cache_files_router)
            logger.info(f"Cache file serving mounted at /cache/files → {_cache_dir}")
        except Exception as exc:
            logger.warning(f"Failed to start cache system: {exc}", exc_info=True)
            app.state.cache_manager = None
            app.state.download_queue = None
            app.state.download_scheduler = None
    else:
        app.state.cache_manager = None
        app.state.download_queue = None
        app.state.download_scheduler = None

    logger.info(f"StreamTV started on {config.server.host}:{config.server.port}")
    yield
    
    # Shutdown
    logger.info("Shutting down StreamTV...")
    if hasattr(app.state, 'channel_manager') and app.state.channel_manager:
        await app.state.channel_manager.stop_all_channels()
        logger.info("Stopped all continuous channel streams")
    if ssdp_server:
        ssdp_server.stop()
    if hdhr_discovery_server:
        hdhr_discovery_server.stop()
    if getattr(app.state, "download_queue", None):
        await app.state.download_queue.stop()
    if getattr(app.state, "download_scheduler", None):
        await app.state.download_scheduler.stop()
        logger.info("Cache system stopped")


# Create FastAPI app
app = FastAPI(
    title="StreamTV",
    description="Efficient Online Media Streamer - Stream from YouTube and Archive.org",
    version="1.0.0",
    lifespan=lifespan
)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware with restricted origins
# Get allowed origins from environment or config, default to localhost only
cors_origins_env = os.getenv("CORS_ORIGINS", "")
if cors_origins_env:
    allowed_origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]
else:
    # Default to localhost and the configured base_url
    allowed_origins = [
        "http://localhost:8410",
        "http://127.0.0.1:8410",
        config.server.base_url
    ]
    # Remove duplicates while preserving order
    allowed_origins = list(dict.fromkeys(allowed_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # Restricted to specific origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With", "X-CSRF-Token", "X-API-Key"],
)

# Add security middleware (order matters - add after CORS, before routes)
from .middleware.security import SecurityHeadersMiddleware, APIKeyMiddleware, CSRFProtectionMiddleware

# Security headers middleware (adds CSP, HSTS, etc.)
app.add_middleware(SecurityHeadersMiddleware)

# CSRF protection middleware (for web forms)
# Exempt API endpoints (they use API key auth) and IPTV endpoints
app.add_middleware(
    CSRFProtectionMiddleware,
    exempt_paths=[
        "/api/",
        "/iptv/",
        "/tuners",
        "/cache/files/",
        "/docs",
        "/redoc",
        "/openapi.json",
    ],
)

# API key authentication middleware
# Exempt paths that don't need API key (public endpoints, docs, IPTV streams)
exempt_api_paths = [
    "/api/auth/",  # Authentication endpoints
    "/api/health/",  # Health checks
    "/iptv/",  # IPTV endpoints (may use query param tokens)
    "/tuners",  # Tunarr/HDHR proxy for Plex GUI add (no API key)
    "/cache/files/",  # Cached media served to local FFmpeg / Plex
    "/docs",  # API documentation
    "/redoc",  # API documentation
    "/openapi.json",  # OpenAPI schema
]

# For API endpoints, allow query parameter tokens per docs/API.md specification
# This enables ?access_token=TOKEN support for all API endpoints
app.add_middleware(
    APIKeyMiddleware,
    token=config.security.access_token,
    required=config.security.api_key_required,
    exempt_paths=exempt_api_paths,
    allow_query_param=True  # Enable query param tokens per API specification
)

# Include routers
app.include_router(api_router)
app.include_router(iptv_router_instance)


@app.get("/xmltv.xml")
async def root_xmltv(
    access_token: Optional[str] = None,
    request: Request = None,
    plain: bool = True,
    db: Session = Depends(get_db),
):
    """Plex XMLTV clients often request /xmltv.xml at the HDHomeRun device root."""
    from .api.iptv import get_epg

    return await get_epg(
        access_token=access_token, request=request, plain=plain, db=db
    )


app.include_router(docs_router)
app.include_router(logs_router)
app.include_router(ollama_router)  # Ollama routes (some are at root level like /ollama)

# Tuner manager: proxy Tunarr (etc.) for Plex GUI Add Device
if config.tuner_manager.enabled:
    app.include_router(tuner_router)
    logger.info(
        "Tuner manager enabled — Plex add URLs at /tuners (proxy prefix %s)",
        config.tuner_manager.listen_path_prefix,
    )

# Include HDHomeRun router if enabled
if config.hdhomerun.enabled:
    app.include_router(hdhomerun_router)
    logger.info("HDHomeRun emulation enabled")
    
    # Add root-level HDHomeRun endpoints for clients that expect them at root
    # (Some HDHomeRun clients look for these at /discover.json instead of /hdhomerun/discover.json)
    
    @app.get("/discover.json")
    async def root_discover(request: Request, db: Session = Depends(get_db)):
        """Root-level HDHomeRun discover endpoint"""
        from .hdhomerun.api import discover
        return await discover(request, db)
    
    @app.get("/lineup.json")
    async def root_lineup(request: Request, db: Session = Depends(get_db)):
        """Root-level HDHomeRun lineup endpoint"""
        from .hdhomerun.api import lineup
        return await lineup(request, db)
    
    @app.get("/lineup_status.json")
    async def root_lineup_status():
        """Root-level HDHomeRun lineup status endpoint"""
        from .hdhomerun.api import lineup_status
        return await lineup_status()

    @app.get("/auto/v{channel_number}")
    async def root_auto_stream(
        channel_number: str,
        request: Request,
        db: Session = Depends(get_db),
    ):
        """Root-level HDHomeRun tune endpoint (Plex expects /auto/vN at device root)."""
        from .hdhomerun.api import stream_channel
        return await stream_channel(channel_number, request, db)

# Setup templates with auto-escaping enabled for XSS protection
templates_dir = Path(__file__).parent / "templates"
_version_file = Path(__file__).parent.parent / "VERSION"
_app_version = _version_file.read_text(encoding="utf-8").strip() if _version_file.exists() else "0.0.0"
if templates_dir.exists():
    # Jinja2Templates enables auto-escaping by default for security
    templates = Jinja2Templates(directory=str(templates_dir))
    templates.env.globals["app_version"] = _app_version
else:
    templates = None

# Mount static files for channel icons
channel_icons_dir = Path(__file__).parent.parent / "data" / "channel_icons"
channel_icons_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static/channel_icons", StaticFiles(directory=str(channel_icons_dir)), name="channel_icons")

# Channel Builder SPA (built assets from frontend/builder/dist)
builder_dist = Path(__file__).parent.parent / "frontend" / "builder" / "dist"
if builder_dist.exists():
    app.mount("/builder/assets", StaticFiles(directory=str(builder_dist / "assets")), name="builder_assets")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root endpoint - Web interface

    Always show the dashboard, which will display authentication status
    and allow users to configure authentication if needed.
    """
    if not templates:
        # Fallback to JSON if templates not available
        return {
            "name": "StreamTV",
            "version": "1.0.0",
            "description": "Efficient Online Media Streamer",
            "endpoints": {
                "api": "/api",
                "iptv_playlist": "/iptv/channels.m3u",
                "epg": "/iptv/xmltv.xml",
                "docs": "/docs"
            }
        }

    # Always show the dashboard - it will display authentication status
    # and provide links to authentication setup pages if needed
    return templates.TemplateResponse(request, "index.html")


@app.get("/auth/setup", response_class=HTMLResponse)
async def auth_setup_page(request: Request):
    """Explicit authentication setup page (Archive.org + YouTube)"""
    if templates:
        return templates.TemplateResponse(request, "auth_setup.html")
    else:
        return HTMLResponse("<h1>Authentication Setup</h1><p>Templates not available. Use /api/auth/archive-org and /api/auth/youtube</p>")


@app.get("/channels", response_class=HTMLResponse)
async def channels_page(request: Request):
    """Channels management page"""
    if templates:
        return templates.TemplateResponse(request, "channels.html")
    else:
        return HTMLResponse("<h1>Channels Management</h1><p>Templates not available. Use API at /api/channels</p>")


@app.get("/plex-logs", response_class=HTMLResponse)
async def plex_logs_page(request: Request):
    """Plex server logs viewer page"""
    if templates:
        return templates.TemplateResponse(request, "plex_logs.html")
    else:
        return HTMLResponse("<h1>Plex Server Logs</h1><p>Templates not available. Use API at /api/plex/logs</p>")


@app.get("/test-stream", response_class=HTMLResponse)
async def test_stream_page(request: Request):
    """Test stream page"""
    if templates:
        return templates.TemplateResponse(request, "test_stream.html")
    else:
        return HTMLResponse("<h1>Test Stream</h1><p>Templates not available.</p>")


@app.get("/player", response_class=HTMLResponse)
async def player_page(request: Request):
    """IPTV player page"""
    if templates:
        return templates.TemplateResponse(request, "player.html")
    else:
        return HTMLResponse("<h1>IPTV Player</h1><p>Templates not available.</p>")


@app.get("/media", response_class=HTMLResponse)
async def media_page(request: Request):
    """Media library page"""
    if templates:
        return templates.TemplateResponse(request, "media.html")
    else:
        return HTMLResponse("<h1>Media Library</h1><p>Templates not available. Use API at /api/media</p>")


@app.get("/collections", response_class=HTMLResponse)
async def collections_page(request: Request):
    """Collections management page"""
    if templates:
        return templates.TemplateResponse(request, "collections.html")
    else:
        return HTMLResponse("<h1>Collections</h1><p>Templates not available. Use API at /api/collections</p>")


@app.get("/playlists", response_class=HTMLResponse)
async def playlists_page(request: Request):
    """Playlists management page"""
    if templates:
        return templates.TemplateResponse(request, "playlists.html")
    else:
        return HTMLResponse("<h1>Playlists</h1><p>Templates not available. Use API at /api/playlists</p>")


@app.get("/settings", response_class=HTMLResponse)
async def settings_index_page(request: Request):
    """Settings overview hub"""
    if templates:
        return templates.TemplateResponse(request, "settings.html")
    return HTMLResponse("<h1>Settings</h1><p>Templates not available.</p>")


@app.get("/settings/auth", response_class=HTMLResponse)
async def settings_auth_hub_page(request: Request):
    """Source authentication hub"""
    if templates:
        return templates.TemplateResponse(request, "settings_auth.html")
    return HTMLResponse("<h1>Source Authentication</h1><p>Templates not available.</p>")


@app.get("/cache", response_class=HTMLResponse)
async def cache_status_page(request: Request):
    """Cache operator status page"""
    if templates:
        return templates.TemplateResponse(request, "cache.html")
    return HTMLResponse("<h1>Cache</h1><p>Templates not available. Use API at /api/cache/stats</p>")


@app.get("/settings/ffmpeg", response_class=HTMLResponse)
async def settings_ffmpeg_page(request: Request):
    """FFmpeg settings page"""
    if templates:
        return templates.TemplateResponse(request, "settings_ffmpeg.html")
    else:
        return HTMLResponse("<h1>FFmpeg Settings</h1><p>Templates not available. Use API at /api/settings/ffmpeg</p>")


@app.get("/settings/hdhr", response_class=HTMLResponse)
async def settings_hdhr_page(request: Request):
    """HDHomeRun settings page"""
    if templates:
        return templates.TemplateResponse(request, "settings_hdhr.html")
    else:
        return HTMLResponse("<h1>HDHomeRun Settings</h1><p>Templates not available. Use API at /api/settings/hdhr</p>")


@app.get("/settings/playout", response_class=HTMLResponse)
async def settings_playout_page(request: Request):
    """Playout settings page"""
    if templates:
        return templates.TemplateResponse(request, "settings_playout.html")
    else:
        return HTMLResponse("<h1>Playout Settings</h1><p>Templates not available. Use API at /api/settings/playout</p>")


@app.get("/settings/plex", response_class=HTMLResponse)
async def settings_plex_page(request: Request):
    """Plex API integration settings page"""
    if templates:
        return templates.TemplateResponse(request, "settings_plex.html")
    else:
        return HTMLResponse("<h1>Plex API Integration</h1><p>Templates not available. Use API at /api/settings/plex</p>")


@app.get("/settings/resolutions", response_class=HTMLResponse)
async def settings_resolutions_page(request: Request):
    """Resolutions management page"""
    if templates:
        return templates.TemplateResponse(request, "settings_resolutions.html")
    else:
        return HTMLResponse("<h1>Resolutions</h1><p>Templates not available. Use API at /api/resolutions</p>")


@app.get("/settings/ffmpeg-profiles", response_class=HTMLResponse)
async def settings_ffmpeg_profiles_page(request: Request):
    """FFmpeg profiles management page"""
    if templates:
        return templates.TemplateResponse(request, "settings_ffmpeg_profiles.html")
    else:
        return HTMLResponse("<h1>FFmpeg Profiles</h1><p>Templates not available. Use API at /api/ffmpeg-profiles</p>")


@app.get("/settings/watermarks", response_class=HTMLResponse)
async def settings_watermarks_page(request: Request):
    """Watermarks management page"""
    if templates:
        return templates.TemplateResponse(request, "settings_watermarks.html")
    else:
        return HTMLResponse("<h1>Watermarks</h1><p>Templates not available. Use API at /api/watermarks</p>")


@app.get("/import", response_class=HTMLResponse)
async def import_page(request: Request):
    """Channel import page"""
    if templates:
        return templates.TemplateResponse(request, "import.html")
    else:
        return HTMLResponse("<h1>Import Channels</h1><p>Templates not available. Use API at /api/import/channels/yaml</p>")


@app.get("/builder")
@app.get("/builder/{path:path}")
async def builder_spa(path: str = ""):
    """Channel Builder React SPA."""
    from fastapi.responses import FileResponse

    index = Path(__file__).parent.parent / "frontend" / "builder" / "dist" / "index.html"
    if index.exists():
        return FileResponse(index)
    return HTMLResponse(
        "<h1>Channel Builder</h1>"
        "<p>Frontend not built. Run: <code>cd frontend/builder && npm install && npm run build</code></p>"
        "<p>API is available at <a href='/docs#/Channel%20Builder'>/api/builder</a></p>",
        status_code=200,
    )


@app.get("/schedules", response_class=HTMLResponse)
async def schedules_page(request: Request):
    """Schedules management page"""
    if templates:
        return templates.TemplateResponse(request, "schedules.html")
    else:
        return HTMLResponse("<h1>Schedules</h1><p>Templates not available.</p>")


@app.get("/schedules/{schedule_id}/items", response_class=HTMLResponse)
async def schedule_items_page(request: Request, schedule_id: int):
    """Schedule items editor page"""
    if templates:
        return templates.TemplateResponse(request, "schedule_items.html", {
            "schedule_id": schedule_id,
        })
    else:
        return HTMLResponse(f"<h1>Schedule Items</h1><p>Schedule ID: {schedule_id}</p><p>Templates not available.</p>")


@app.get("/playouts", response_class=HTMLResponse)
async def playouts_page(request: Request):
    """Playouts management page"""
    if templates:
        return templates.TemplateResponse(request, "playouts.html")
    else:
        return HTMLResponse("<h1>Playouts</h1><p>Templates not available.</p>")


@app.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request):
    """Streaming logs viewer page"""
    if templates:
        return templates.TemplateResponse(request, "logs.html")
    else:
        return HTMLResponse("<h1>Streaming Logs</h1><p>Templates not available. Use API at /api/logs/entries</p>")


@app.get("/health")
async def health(request: Request):
    """Simple health check endpoint - use /api/health/detailed for comprehensive check"""
    from datetime import datetime
    discovery = getattr(request.app.state, "hdhr_discovery", None)
    payload = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "device_id": config.hdhomerun.device_id,
    }
    if discovery is not None:
        payload["hdhr_discovery"] = discovery.status
    return payload


@app.get("/health-check", response_class=HTMLResponse)
async def health_check_page(request: Request):
    """Health check page"""
    if templates:
        return templates.TemplateResponse(request, "health_check.html")
    else:
        return HTMLResponse("<h1>Health Check</h1><p>Templates not available. Use API at /api/health/detailed</p>")


@app.get("/favicon.ico")
async def favicon():
    """Favicon endpoint - returns 204 to prevent 404 errors"""
    return Response(status_code=204)


@app.get("/apple-touch-icon.png")
@app.get("/apple-touch-icon-precomposed.png")
async def apple_touch_icon():
    """Apple touch icon endpoint - returns 204 to prevent 404 errors"""
    return Response(status_code=204)


if __name__ == "__main__":
    import uvicorn
    import os
    from pathlib import Path as _Path

    # Refuse a second instance before binding (Errno 48 / mid-stream drops)
    _pidfile = _Path(os.getenv("STREAMTV_PIDFILE", ".streamtv.pid"))
    try:
        acquire_instance_lock(
            pidfile=_pidfile,
            host=config.server.host,
            port=config.server.port,
        )
    except InstanceLockError as exc:
        logger.error("%s", exc)
        raise SystemExit(1) from exc

    # Disable reload by default to avoid multiprocessing spawn issues on macOS
    # Set STREAMTV_RELOAD=1 environment variable to enable reload
    use_reload = os.getenv("STREAMTV_RELOAD") == "1"
    uvicorn.run(
        "streamtv.main:app",
        host=config.server.host,
        port=config.server.port,
        reload=use_reload,
        reload_excludes=["venv/*", "*.pyc", "__pycache__/*", ".git/*", "data/*", "*.db"] if use_reload else None,
        reload_dirs=["./streamtv"] if use_reload else None,  # Only watch streamtv directory
        log_config=None  # Use our custom logging configuration
    )
