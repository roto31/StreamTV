"""Download-first caching subsystem for StreamTV.

Eliminates API rate-limiting by downloading content to local cache via:
  - Archive.org: ia CLI tool (no API calls)
  - YouTube: yt-dlp with enforced rate limiting

Usage:
    from streamtv.cache import CacheManager, DownloadScheduler

    cache = CacheManager(db_session_factory)
    path = cache.get_cached_path("dQw4w9WgXcQ")   # None if not cached
    await cache.enqueue(media_item)                  # Queue for background download
"""

from .cache_manager import CacheManager
from .download_queue import DownloadQueue
from .download_scheduler import DownloadScheduler
from .archive_org_downloader import ArchiveOrgDownloader
from .archive_org_http_downloader import ArchiveOrgHttpDownloader
from .youtube_downloader import YouTubeDownloader

__all__ = [
    "CacheManager",
    "DownloadQueue",
    "DownloadScheduler",
    "ArchiveOrgDownloader",
    "ArchiveOrgHttpDownloader",
    "YouTubeDownloader",
    "bind_runtime",
    "get_runtime",
]

_runtime_cache_manager = None
_runtime_download_queue = None


def bind_runtime(cache_manager, download_queue) -> None:
    """Set process-wide cache handles from main.py lifespan startup."""
    global _runtime_cache_manager, _runtime_download_queue
    _runtime_cache_manager = cache_manager
    _runtime_download_queue = download_queue


def get_runtime():
    """Return (cache_manager, download_queue) or (None, None) if cache disabled."""
    return _runtime_cache_manager, _runtime_download_queue
