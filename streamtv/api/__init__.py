"""API routes and controllers"""

from fastapi import APIRouter

from .channels import router as channels_router
from .media import router as media_router
from .collections import router as collections_router
from .playlists import router as playlists_router
from .schedules import router as schedules_router
from .schedule_items import router as schedule_items_router
from .import_api import router as import_router
from .playouts import router as playouts_api_router
from .settings import router as settings_router
from .auth import router as auth_router
from .iptv import router as iptv_router
from . import docs as docs_module
from . import logs as logs_module
from .scripts import router as scripts_router
from .ollama import router as ollama_router
from .health import router as health_router
from .dashboard import router as dashboard_router
from .export_api import router as export_router
from .resolutions import router as resolutions_router
from .ffmpeg_profiles import router as ffmpeg_profiles_router
from .watermarks import router as watermarks_router

api_router = APIRouter(prefix="/api")

api_router.include_router(channels_router, tags=["Channels"])
api_router.include_router(media_router, tags=["Media"])
api_router.include_router(collections_router, tags=["Collections"])
api_router.include_router(playlists_router, tags=["Playlists"])
api_router.include_router(schedules_router, tags=["Schedules"])
api_router.include_router(schedule_items_router, tags=["Schedule Items"])
api_router.include_router(import_router, tags=["Import"])
api_router.include_router(playouts_api_router, tags=["Playouts"])
api_router.include_router(settings_router, tags=["Settings"])
api_router.include_router(auth_router, tags=["Authentication"])
api_router.include_router(scripts_router, tags=["Scripts"])
api_router.include_router(ollama_router, tags=["Ollama"])
api_router.include_router(health_router, tags=["Health"])
api_router.include_router(dashboard_router, tags=["Dashboard"])
api_router.include_router(export_router, tags=["Export"])
api_router.include_router(resolutions_router, tags=["Resolutions"])
api_router.include_router(ffmpeg_profiles_router, tags=["FFmpeg Profiles"])
api_router.include_router(watermarks_router, tags=["Watermarks"])

# IPTV router is separate (no /api prefix)
iptv_router_instance = iptv_router

# Documentation router (no /api prefix)
docs_router = docs_module.router

# Logs router (no /api prefix for page, but /api/logs for endpoints)
logs_router = logs_module.router

__all__ = ["api_router", "iptv_router_instance", "docs_router", "logs_router"]
