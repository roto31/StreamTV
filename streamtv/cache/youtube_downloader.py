"""YouTube downloader using yt-dlp with enforced rate limiting.

Why download instead of stream?
  - Direct stream URL extraction from YouTube is heavily rate-limited.
  - Downloads use a different request bucket and are far more resilient.
  - Selecting MP4 format lets Plex direct-play without server-side transcoding.
  - Playlist batching at 2 AM avoids peak-hour throttling.

YouTube ToS Notice:
    Downloading YouTube videos must comply with YouTube's Terms of Service.
    This feature is intended for personal, non-commercial use only.
    Do not redistribute downloaded content.
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlparse

import yt_dlp

from ..config import config
from ..ffmpeg.constants import youtube_format_selector
from ..youtube.ydl_opts import youtube_ydl_opts

logger = logging.getLogger(__name__)

# yt-dlp format specifiers — ordered by preference
_FORMAT_SPECS: dict[str, str] = {
    # H.264 in MP4 container — Plex direct-play, zero transcode
    "mp4": (
        "bestvideo[ext=mp4][vcodec^=avc]+bestaudio[ext=m4a]"
        "/bestvideo[ext=mp4]+bestaudio/best[ext=mp4]/best"
    ),
    # VP9/WebM — requires light transcode for Plex
    "webm": "bestvideo[ext=webm]+bestaudio[ext=webm]/best[ext=webm]/best",
    # Any best-quality format
    "best": "bestvideo+bestaudio/best",
    # 1080p cap MP4
    "1080p": (
        "bestvideo[height<=1080][ext=mp4][vcodec^=avc]"
        "+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best"
    ),
    # 720p cap MP4
    "720p": (
        "bestvideo[height<=720][ext=mp4][vcodec^=avc]"
        "+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best"
    ),
}


class YouTubeDownloader:
    """Download YouTube videos to local cache with strict rate limiting.

    Rate limiting strategy:
      - A shared asyncio.Lock serialises all download attempts (single worker).
      - A configurable delay (default 30 s) is enforced between downloads.
      - On rate-limit detection (yt-dlp raises DownloadError with 429), an
        extended cool-down period is applied before retrying.
    """

    # Shared across all instances — class-level state
    _last_download_time: float = 0.0
    _rate_limited_until: float = 0.0
    _lock: Optional[asyncio.Lock] = None

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir / "youtube"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._min_delay = config.cache.download_strategy.youtube_rate_limit_seconds
        self._cooldown = config.cache.download_strategy.youtube_rate_limit_cooldown_seconds

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def download_video(
        self,
        url: str,
        format_preference: Optional[str] = None,
    ) -> Optional[Path]:
        """Download a single YouTube video.

        Args:
            url: YouTube video URL or youtu.be short URL.
            format_preference: Key from _FORMAT_SPECS ("mp4", "webm", "best", "1080p", "720p").

        Returns:
            Path to the downloaded file, or None on failure.
        """
        video_id = self._extract_video_id(url)
        if not video_id:
            logger.error(f"Cannot extract video ID from: {url}")
            return None

        fmt = format_preference or config.cache.download_strategy.format_preference
        existing = self._find_existing(video_id)
        if existing:
            logger.info(f"Already cached: {video_id} → {existing}")
            return existing

        await self._acquire_rate_limit_slot()
        return await asyncio.get_event_loop().run_in_executor(
            None, self._download_sync, video_id, url, fmt
        )

    async def download_playlist(
        self,
        playlist_url: str,
        format_preference: Optional[str] = None,
        max_items: int = 100,
    ) -> list[Path]:
        """Download all videos in a YouTube playlist.

        Args:
            playlist_url: YouTube playlist URL.
            format_preference: Preferred format.
            max_items: Safety cap on number of downloads per run.

        Returns:
            List of Paths for successfully downloaded files.
        """
        entries = await self._list_playlist(playlist_url, max_items)
        logger.info(
            f"Playlist has {len(entries)} items, downloading up to {max_items}"
        )
        results: list[Path] = []
        for entry in entries[:max_items]:
            video_url = f"https://www.youtube.com/watch?v={entry['id']}"
            path = await self.download_video(video_url, format_preference)
            if path:
                results.append(path)
        return results

    async def list_playlist_ids(
        self, playlist_url: str, max_items: int = 500
    ) -> list[dict]:
        """Return metadata for all entries in a playlist without downloading."""
        return await self._list_playlist(playlist_url, max_items)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _download_sync(
        self, video_id: str, url: str, fmt: str
    ) -> Optional[Path]:
        """Blocking yt-dlp download (runs inside thread-pool executor)."""
        # RC-8: default "mp4" preference uses the shared H.264+AAC selector so
        # cached files are Plex direct-play (yt-dlp merges split streams itself).
        if fmt == "mp4":
            format_spec = youtube_format_selector(1080)
        else:
            format_spec = _FORMAT_SPECS.get(fmt, _FORMAT_SPECS["mp4"])
        output_template = str(self.cache_dir / f"{video_id}.%(ext)s")

        ydl_opts = youtube_ydl_opts(
            format=format_spec,
            outtmpl=output_template,
            quiet=True,
            no_warnings=True,
            noprogress=True,
            merge_output_format="mp4",
            postprocessors=[
                {
                    "key": "FFmpegVideoConvertor",
                    "preferedformat": "mp4",
                }
            ],
            **(
                {"cookiefile": config.youtube.cookies_file}
                if config.youtube.cookies_file
                else {}
            ),
        )

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            # Record successful download time for rate limiting
            YouTubeDownloader._last_download_time = time.time()
            result = self._find_existing(video_id)
            if result:
                logger.info(
                    f"Downloaded: {video_id} → {result.name} "
                    f"({result.stat().st_size / 1024 / 1024:.1f} MB)"
                )
            return result

        except yt_dlp.utils.DownloadError as exc:
            err_str = str(exc).lower()
            if "429" in err_str or "rate limit" in err_str or "too many" in err_str:
                logger.warning(
                    f"YouTube rate-limited for {video_id}. "
                    f"Backing off {self._cooldown}s."
                )
                YouTubeDownloader._rate_limited_until = (
                    time.time() + self._cooldown
                )
            else:
                logger.error(f"yt-dlp DownloadError for {video_id}: {exc}")
            return None

        except Exception as exc:
            logger.error(f"Unexpected error downloading {video_id}: {exc}")
            return None

    async def _list_playlist(
        self, playlist_url: str, max_items: int
    ) -> list[dict]:
        """Run yt-dlp playlist extraction in executor (flat, no download)."""
        ydl_opts = youtube_ydl_opts(
            quiet=True,
            no_warnings=True,
            extract_flat="in_playlist",
            playlistend=max_items,
        )
        try:
            info = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._extract_flat(playlist_url, ydl_opts),
            )
            entries = info.get("entries", []) or []
            return [e for e in entries if e and e.get("id")]
        except Exception as exc:
            logger.error(f"Playlist extraction failed for {playlist_url}: {exc}")
            return []

    @staticmethod
    def _extract_flat(url: str, opts: dict) -> dict:
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False) or {}

    def _find_existing(self, video_id: str) -> Optional[Path]:
        """Return a cached file for video_id if it exists (any extension)."""
        for ext in ["mp4", "webm", "mkv", "m4v"]:
            candidate = self.cache_dir / f"{video_id}.{ext}"
            if candidate.exists() and candidate.stat().st_size > 0:
                return candidate
        return None

    async def _acquire_rate_limit_slot(self) -> None:
        """Block until rate-limit constraints allow the next download."""
        # Lazy-initialise the async lock (must happen inside an event loop)
        if YouTubeDownloader._lock is None:
            YouTubeDownloader._lock = asyncio.Lock()

        async with YouTubeDownloader._lock:
            # Wait out any active cool-down period (e.g. after 429)
            now = time.time()
            if YouTubeDownloader._rate_limited_until > now:
                wait = YouTubeDownloader._rate_limited_until - now
                logger.warning(
                    f"YouTube rate-limit active. Waiting {wait:.0f}s …"
                )
                await asyncio.sleep(wait)

            # Enforce minimum delay between requests
            elapsed = time.time() - YouTubeDownloader._last_download_time
            if elapsed < self._min_delay:
                wait = self._min_delay - elapsed
                logger.debug(f"Rate-limiting: sleeping {wait:.1f}s")
                await asyncio.sleep(wait)

            YouTubeDownloader._last_download_time = time.time()

    @staticmethod
    def _extract_video_id(url: str) -> Optional[str]:
        """Extract the 11-character video ID from any YouTube URL format."""
        parsed = urlparse(url)
        host = parsed.hostname or ""

        # youtu.be/VIDEO_ID
        if host in ("youtu.be",):
            return parsed.path.lstrip("/").split("?")[0] or None

        # youtube.com/watch?v=VIDEO_ID
        if host == "youtube.com" or host.endswith(".youtube.com"):
            qs = parse_qs(parsed.query)
            vid = qs.get("v", [None])[0]
            if vid:
                return vid
            # youtube.com/shorts/VIDEO_ID
            parts = [p for p in parsed.path.split("/") if p]
            if len(parts) >= 2 and parts[-2] in ("shorts", "embed", "v"):
                return parts[-1]

        return None
