"""YouTube streaming adapter - streams directly without downloading"""

import httpx
import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError
from typing import Optional, Dict, Any, Union
import logging
import asyncio
import time
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta

from streamtv.ffmpeg.constants import (
    YOUTUBE_URL_TTL_LIVE_SECONDS,
    YOUTUBE_URL_TTL_VOD_SECONDS,
    youtube_stream_selector,
)
from streamtv.youtube.ydl_opts import youtube_ydl_opts

from .youtube_api_client import YouTubeAPIClient

logger = logging.getLogger(__name__)

_FFMPEG_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class YouTubeAdapter:
    """Adapter for streaming YouTube videos without downloading"""
    
    # Shared rate limit state across all instances (class-level)
    _shared_rate_limited_until: Optional[datetime] = None
    _shared_last_request_time: Optional[float] = None
    _shared_lock = asyncio.Lock() if hasattr(asyncio, 'Lock') else None

    # video_id -> (resolved, monotonic_expiry); resolved is str OR (vurl, aurl) tuple
    _shared_url_cache: Dict[str, tuple] = {}
    
    def __init__(self, quality: str = "best", extract_audio: bool = False, cookies_file: Optional[str] = None, 
                 api_key: Optional[str] = None, request_delay: float = 5.0, rate_limit_delay: float = 3600.0):
        self.quality = quality
        self.extract_audio = extract_audio
        self.cookies_file = cookies_file
        self.api_key = api_key
        self.request_delay = request_delay  # Delay between requests (seconds) - increased to 5 seconds default
        self.rate_limit_delay = rate_limit_delay  # Delay when rate limited (seconds) - default 1 hour
        
        # Initialize YouTube API client for validation
        self.api_client = YouTubeAPIClient(api_key=api_key) if api_key else None
        
        # Instance-specific executor (background cache / ring buffer)
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="youtube_adapter")
        # Live tuner path must not queue behind ring-buffer yt-dlp (runtime: 126s tune wedge).
        self._tune_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="youtube_tune")
        
        self._ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'geo_bypass': True,
            'geo_bypass_country': 'US',
            # CRITICAL: Never download files, only extract stream URLs
            'download': False,  # Explicitly disable downloading
            'noplaylist': True,  # Don't download playlists
            'skip_download': True,  # Additional safeguard
        }
        # extractor_args + EJS/Deno applied in _build_ydl_opts via youtube_ydl_opts()
        # Add cookies file if provided
        if cookies_file:
            self._ydl_opts['cookiefile'] = cookies_file
            logger.info(f"Using YouTube cookies file: {cookies_file}")

        if self.request_delay > 0:
            self._ydl_opts['sleep_interval_requests'] = self.request_delay

    def _build_ydl_opts(
        self,
        *,
        fmt: Optional[str] = None,
        mpegts_tune: bool = False,
    ) -> Dict[str, Any]:
        """Merge base opts; PO-token-free player_client + optional EJS/Deno from config."""
        base = {
            k: v
            for k, v in self._ydl_opts.items()
            if k not in ("extractor_args", "noplaylist", "download", "skip_download")
        }
        opts: Dict[str, Any] = youtube_ydl_opts(
            **base,
            noplaylist=True,
            download=False,
            skip_download=True,
            socket_timeout=20 if mpegts_tune else 30,
        )
        if fmt:
            opts["format"] = fmt
        if mpegts_tune:
            opts["sleep_interval_requests"] = 0
            opts.pop("sleep_interval", None)
        if self.cookies_file:
            opts["cookiefile"] = self.cookies_file
        return opts
    
    def __del__(self):
        """Cleanup thread pool executor"""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)
        if hasattr(self, '_tune_executor'):
            self._tune_executor.shutdown(wait=False)

    @staticmethod
    def is_audio_only_stream_url(url: str) -> bool:
        """True when URL is YouTube audio-only (FFmpeg cannot mux to MPEG-TS video)."""
        lower = url.lower()
        if "mime=audio" in lower:
            return True
        if "itag=139" in lower or "itag=140" in lower or "itag=141" in lower:
            return True
        return False

    @staticmethod
    def is_googlevideo_url(url: str) -> bool:
        return "googlevideo.com" in url.lower()

    def ffmpeg_cookie_header(self) -> str:
        """Netscape cookies for FFmpeg googlevideo requests (Referer + Cookie)."""
        if not self.cookies_file:
            return ""
        path = Path(self.cookies_file)
        if not path.is_file():
            return ""
        pairs: list[str] = []
        try:
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) < 7:
                    continue
                domain, _flag, _p, _secure, _exp, name, value = parts[:7]
                if "youtube" in domain or "google.com" in domain:
                    pairs.append(f"{name}={value}")
        except OSError:
            return ""
        header = "; ".join(pairs)
        return header[:4096] if len(header) > 4096 else header

    def _cached_url_get(self, video_id: str) -> Optional[Union[str, tuple]]:
        import time as _t
        entry = YouTubeAdapter._shared_url_cache.get(video_id)
        if entry and _t.monotonic() < entry[1]:
            return entry[0]
        YouTubeAdapter._shared_url_cache.pop(video_id, None)
        return None

    def _cached_url_set(
        self, video_id: str, url: Union[str, tuple], is_live: bool = False
    ) -> None:
        import time as _t
        ttl = (
            YOUTUBE_URL_TTL_LIVE_SECONDS if is_live else YOUTUBE_URL_TTL_VOD_SECONDS
        )
        YouTubeAdapter._shared_url_cache[video_id] = (url, _t.monotonic() + ttl)
    
    async def _wait_for_rate_limit(self) -> None:
        """If YouTube session is rate-limited, fail fast — never block the event loop for an hour."""
        if not YouTubeAdapter._shared_rate_limited_until:
            return
        now = datetime.utcnow()
        if now >= YouTubeAdapter._shared_rate_limited_until:
            YouTubeAdapter._shared_rate_limited_until = None
            return
        remaining = (YouTubeAdapter._shared_rate_limited_until - now).total_seconds()
        raise ValueError(
            f"YouTube rate limit active ({remaining / 60:.1f} min remaining). "
            "Skipping yt-dlp until cooldown expires."
        )
    
    async def _apply_request_delay(self):
        """Apply delay between requests to avoid rate limiting (shared across all instances)"""
        if YouTubeAdapter._shared_lock:
            async with YouTubeAdapter._shared_lock:
                if YouTubeAdapter._shared_last_request_time:
                    elapsed = time.time() - YouTubeAdapter._shared_last_request_time
                    if elapsed < self.request_delay:
                        wait_time = self.request_delay - elapsed
                        await asyncio.sleep(wait_time)
                
                YouTubeAdapter._shared_last_request_time = time.time()
        else:
            # Fallback if lock not available
            if YouTubeAdapter._shared_last_request_time:
                elapsed = time.time() - YouTubeAdapter._shared_last_request_time
                if elapsed < self.request_delay:
                    wait_time = self.request_delay - elapsed
                    await asyncio.sleep(wait_time)
            YouTubeAdapter._shared_last_request_time = time.time()
    
    def _get_video_info_sync(self, url: str) -> Dict[str, Any]:
        """Synchronous helper to get video info (runs in thread pool)"""
        ydl_opts = self._build_ydl_opts()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                'id': info.get('id'),
                'title': info.get('title'),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail'),
                'description': info.get('description', ''),
                'uploader': info.get('uploader', ''),
                'upload_date': info.get('upload_date', ''),
                'view_count': info.get('view_count', 0),
                'url': url,
            }
    
    async def get_video_info(self, url: str) -> Dict[str, Any]:
        """Get video information without downloading (with rate limiting)"""
        # First, try to validate and get info from YouTube API if available
        if self.api_client:
            try:
                validation = await self.api_client.validate_video(url)
                if validation['valid'] and validation['available'] and validation['info']:
                    # Use API info as primary source
                    api_info = validation['info']
                    logger.debug(f"Got video info from YouTube API for {url}")
                    return {
                        'id': api_info.get('id'),
                        'title': api_info.get('title'),
                        'duration': api_info.get('duration', 0),
                        'thumbnail': api_info.get('thumbnail'),
                        'description': api_info.get('description', ''),
                        'uploader': api_info.get('uploader', ''),
                        'upload_date': api_info.get('upload_date', ''),
                        'view_count': api_info.get('view_count', 0),
                        'url': url,
                    }
                elif validation['valid'] and not validation['available']:
                    # Video exists but is not available (private, unlisted, etc.)
                    error_msg = validation.get('error', 'Video unavailable')
                    logger.warning(f"YouTube video unavailable via API: {error_msg}")
                    raise ValueError(f"YouTube video unavailable: {error_msg}")
            except Exception as e:
                # If API fails, fall back to yt-dlp
                logger.debug(f"YouTube API validation failed, falling back to yt-dlp: {e}")
        
        # Fall back to yt-dlp for info extraction
        await self._wait_for_rate_limit()
        await self._apply_request_delay()
        
        try:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(self._executor, self._get_video_info_sync, url)
            return info
        except DownloadError as e:
            error_msg = str(e)
            
            # Check for authentication errors first
            is_auth_error = 'Please sign in' in error_msg or 'sign in' in error_msg.lower() or \
                          'authentication' in error_msg.lower() or ('cookies' in error_msg.lower() and 'authentication' in error_msg.lower())
            
            if is_auth_error and self.cookies_file:
                logger.error(f"YouTube authentication error getting video info for {url}. Cookies file may be incomplete or expired.")
                logger.error(f"Cookies file: {self.cookies_file}")
                logger.error("To fix: Export a complete cookies file from your browser after logging into YouTube.")
                logger.error("Required cookies: LOGIN_INFO, SID, HSID, SSID, APISID, SAPISID, __Secure-1PSID, __Secure-3PSID")
                raise ValueError(f"YouTube authentication failed: Cookies file may be incomplete or expired. "
                               f"Please export a complete cookies file from your browser after logging into YouTube. "
                               f"See /api/auth/youtube for instructions.")
            elif is_auth_error:
                logger.error(f"YouTube authentication error getting video info for {url}. No cookies file configured.")
                raise ValueError(f"YouTube authentication required: Please upload a cookies file via /api/auth/youtube")
            
            rate_limit_indicators = [
                'rate-limit', 'rate limit', 'rate-limited', 'rate limited',
                'been rate-limited', 'session has been rate-limited',
                'exceeded the rate limit', 'too many requests'
            ]
            is_rate_limited = any(indicator in error_msg.lower() for indicator in rate_limit_indicators)
            
            if is_rate_limited:
                YouTubeAdapter._shared_rate_limited_until = datetime.utcnow() + timedelta(
                    seconds=self.rate_limit_delay
                )
                logger.error(
                    f"YouTube rate limit detected for {url}. Shared cooldown "
                    f"{self.rate_limit_delay / 60:.0f} min. Using {self.request_delay}s between requests."
                )
                raise ValueError(
                    f"YouTube rate limit: Session rate-limited. {error_msg}"
                )
            
            # Check for unavailable videos
            if 'Video unavailable' in error_msg or 'unavailable' in error_msg.lower():
                logger.warning(f"YouTube video unavailable: {url}")
                raise ValueError(f"YouTube video unavailable: {url}")
            
            logger.error(f"Error getting YouTube video info: {e}")
            raise
        except Exception as e:
            error_msg = str(e)
            
            # Check for authentication errors first
            is_auth_error = 'Please sign in' in error_msg or 'sign in' in error_msg.lower() or \
                          'authentication' in error_msg.lower() or ('cookies' in error_msg.lower() and 'authentication' in error_msg.lower())
            
            if is_auth_error and self.cookies_file:
                logger.error(f"YouTube authentication error getting video info for {url}. Cookies file may be incomplete or expired.")
                logger.error(f"Cookies file: {self.cookies_file}")
                logger.error("To fix: Export a complete cookies file from your browser after logging into YouTube.")
                logger.error("Required cookies: LOGIN_INFO, SID, HSID, SSID, APISID, SAPISID, __Secure-1PSID, __Secure-3PSID")
                raise ValueError(f"YouTube authentication failed: Cookies file may be incomplete or expired. "
                               f"Please export a complete cookies file from your browser after logging into YouTube. "
                               f"See /api/auth/youtube for instructions.")
            elif is_auth_error:
                logger.error(f"YouTube authentication error getting video info for {url}. No cookies file configured.")
                raise ValueError(f"YouTube authentication required: Please upload a cookies file via /api/auth/youtube")
            
            rate_limit_indicators = [
                'rate-limit', 'rate limit', 'rate-limited', 'rate limited',
                'been rate-limited', 'session has been rate-limited',
                'exceeded the rate limit', 'too many requests'
            ]
            is_rate_limited = any(indicator in error_msg.lower() for indicator in rate_limit_indicators)
            
            if is_rate_limited:
                YouTubeAdapter._shared_rate_limited_until = datetime.utcnow() + timedelta(
                    seconds=self.rate_limit_delay
                )
                logger.error(
                    f"YouTube rate limit detected for {url}. Shared cooldown "
                    f"{self.rate_limit_delay / 60:.0f} min."
                )
                raise ValueError(f"YouTube rate limit: Session rate-limited. {error_msg}")
            
            # Check for unavailable videos
            if 'Video unavailable' in error_msg or 'unavailable' in error_msg.lower():
                logger.warning(f"YouTube video unavailable: {url}")
                raise ValueError(f"YouTube video unavailable: {url}")
            
            logger.error(f"Error getting YouTube video info: {e}")
            raise
    
    def _get_stream_url_sync(
        self,
        url: str,
        format_id: Optional[str] = None,
        *,
        mpegts_tune: bool = False,
    ) -> Union[str, tuple[str, str]]:
        """
        Synchronous helper to get stream URL (runs in thread pool)
        
        This method implements automatic format fallback for all YouTube channels.
        If the requested format is not available, it automatically tries more
        flexible formats ('best') until one works.
        
        Returns a single URL, or a (video_url, audio_url) tuple when the merged
        selector matched split DASH streams (dual-input FFmpeg downstream).
        """
        # Try with requested format first, then fallback to more flexible formats
        format_selectors = []
        if format_id:
            format_selectors.append(format_id)
        elif self.extract_audio:
            format_selectors.append('bestaudio/best')
        else:
            # Try quality-specific format first, then fallback to more flexible options
            requested_format = self._get_best_format()
            format_selectors.append(requested_format)
            # Fallback format if specific format isn't available
            if 'height<=' in requested_format:
                format_selectors.append('best')
        
        # Ensure cookies file is explicitly set (in case it wasn't copied properly)
        cookies_file = self.cookies_file
        
        # Try each format selector until one works
        last_error = None
        info = None
        for fmt_selector in format_selectors:
            try:
                ydl_opts = self._build_ydl_opts(fmt=fmt_selector, mpegts_tune=mpegts_tune)
                if cookies_file:
                    logger.debug(f"Using cookies file for stream URL extraction: {cookies_file}")
                
                # Always use download=False to prevent any file downloads
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)  # Explicitly set download=False
                    logger.debug(f"Successfully extracted info with format '{fmt_selector}' for {url}")
                    break  # Success, exit the loop
            except (DownloadError, ExtractorError) as e:
                error_msg = str(e)
                # Remove ANSI color codes for better matching (handle both \x1b and [ codes)
                error_msg_clean = error_msg
                # Remove common ANSI escape sequences
                ansi_escape = re.compile(r'\x1b\[[0-9;]*m|\[0;31m|\[0m')
                error_msg_clean = ansi_escape.sub('', error_msg_clean)
                
                # Check for format not available errors - be very permissive in detection
                is_format_error = (
                    'Requested format is not available' in error_msg_clean or 
                    'format is not available' in error_msg_clean.lower() or
                    ('format' in error_msg_clean.lower() and 'not available' in error_msg_clean.lower()) or
                    'no format' in error_msg_clean.lower() or
                    ('unable to download' in error_msg_clean.lower() and 'format' in error_msg_clean.lower()) or
                    'list-formats' in error_msg_clean.lower() or  # This appears in the error message
                    'use --list-formats' in error_msg_clean.lower()  # Another indicator
                )
                
                if is_format_error:
                    logger.debug(f"Format '{fmt_selector}' not available for {url}, trying next format... (error: {error_msg_clean[:150]})")
                    last_error = e
                    continue  # Try next format
                else:
                    # Other error, re-raise
                    logger.debug(f"Non-format error with format '{fmt_selector}' for {url}: {error_msg_clean[:150]}")
                    raise
        
        # If we exhausted all format selectors, try one more time with no format restriction
        if info is None:
            logger.warning(f"All format selectors failed for {url}, trying with no format restriction (let yt-dlp auto-select)...")
            try:
                ydl_opts = self._build_ydl_opts(mpegts_tune=mpegts_tune)
                if cookies_file:
                    ydl_opts['cookiefile'] = cookies_file
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    logger.info(f"Successfully extracted info with auto-selected format for {url}")
            except Exception as final_error:
                error_msg_final = str(final_error)
                # Remove ANSI codes
                error_msg_final_clean = error_msg_final.replace('\x1b[0;31m', '').replace('\x1b[0m', '').replace('[0;31m', '').replace('[0m', '')
                logger.error(f"Final fallback (auto-select format) also failed for {url}: {error_msg_final_clean[:200]}")
                
                # If it's still a format error, the video might truly have no available formats
                if 'format' in error_msg_final_clean.lower() and 'not available' in error_msg_final_clean.lower():
                    logger.error(f"Video {url} appears to have no streamable formats available. This may be a restricted or unavailable video.")
                    raise ValueError(f"YouTube video has no available formats: {url}. The video may be restricted, region-locked, or unavailable.")
                
                if last_error:
                    raise last_error
                raise ValueError(f"Failed to extract video info: {error_msg_final_clean[:200]}")
        
        # Resolution result handling (RC-9). An m3u8/HLS URL is a first-class
        # result — FFmpeg consumes it natively; Phase-3 probe gating handles it.
        requested = info.get('requested_formats')
        if requested:
            # Merged selector matched split DASH streams — two URLs.
            video_url: Optional[str] = None
            audio_url: Optional[str] = None
            for fmt in requested:
                if (fmt.get('vcodec') or 'none') != 'none':
                    video_url = fmt.get('url')
                else:
                    audio_url = fmt.get('url')
            if video_url and audio_url:
                return (video_url, audio_url)
            if video_url:
                return video_url

        if info.get('url'):
            return info['url']

        formats = [f for f in (info.get('formats') or []) if f.get('url')]
        if formats:
            # yt-dlp orders formats best-last
            return formats[-1]['url']

        raise ValueError(
            f"No stream URL in yt-dlp result for {url} "
            f"(formats={len(info.get('formats') or [])})"
        )
    
    async def get_stream_url(
        self,
        url: str,
        format_id: Optional[str] = None,
        *,
        tune_priority: bool = False,
        force_refresh: bool = False,
    ) -> Union[str, tuple[str, str]]:
        """Get direct streaming URL for YouTube video - streams only, never downloads."""
        tune_timeout = 25.0 if tune_priority else 45.0
        _t0 = time.monotonic()

        # Pre-validate video with API if available (skip on live tune — saves seconds).
        if self.api_client and not tune_priority:
            try:
                validation = await self.api_client.validate_video(url)
                if validation['valid'] and not validation['available']:
                    error_msg = validation.get('error', 'Video unavailable')
                    logger.warning(f"YouTube video unavailable: {error_msg}")
                    raise ValueError(f"YouTube video unavailable: {error_msg}")
            except ValueError:
                # Re-raise validation errors
                raise
            except Exception as e:
                # If API validation fails, continue with yt-dlp
                logger.debug(f"YouTube API validation failed, continuing with yt-dlp: {e}")

        # RC-5: signed-URL TTL cache. A cache hit must NOT consume the
        # rate-limit delay — that is the point.
        video_id = self.extract_video_id(url)
        if video_id and not format_id:
            if force_refresh:
                YouTubeAdapter._shared_url_cache.pop(video_id, None)
            else:
                cached = self._cached_url_get(video_id)
                if cached:
                    logger.debug(f"YouTube URL cache hit for {video_id}")
                    return cached

        if not tune_priority:
            await self._wait_for_rate_limit()
            await self._apply_request_delay()
        
        executor = self._tune_executor if tune_priority else self._executor
        
        try:
            loop = asyncio.get_event_loop()
            stream_url = await asyncio.wait_for(
                loop.run_in_executor(
                    executor,
                    lambda: self._get_stream_url_sync(
                        url, format_id, mpegts_tune=tune_priority
                    ),
                ),
                timeout=tune_timeout,
            )
            if isinstance(stream_url, str) and self.is_audio_only_stream_url(
                stream_url
            ):
                raise ValueError(f"YouTube returned audio-only URL for MPEG-TS: {url}")
            logger.debug(
                "YouTube URL resolved in %.2fs (tune_priority=%s)",
                time.monotonic() - _t0,
                tune_priority,
            )
            if video_id and not format_id:
                self._cached_url_set(video_id, stream_url)
            return stream_url
        except asyncio.TimeoutError:
            raise ValueError(
                f"YouTube URL resolution timed out after {tune_timeout:.0f}s (tune_priority={tune_priority})"
            )
        except (DownloadError, ExtractorError, Exception) as e:
            error_msg = str(e)
            
            # Check for rate limiting - look for various patterns YouTube uses
            rate_limit_indicators = [
                'rate-limit', 'rate limit', 'rate-limited', 'rate limited',
                'been rate-limited', 'session has been rate-limited',
                'exceeded the rate limit', 'too many requests',
                'try again later'  # YouTube often includes this with rate limits
            ]
            
            is_rate_limited = any(indicator in error_msg.lower() for indicator in rate_limit_indicators)
            
            # Check for unavailable videos first (but distinguish from rate limits)
            is_unavailable = ('Video unavailable' in error_msg or 'unavailable' in error_msg.lower()) and \
                           not is_rate_limited and 'try again later' not in error_msg.lower()
            
            if is_rate_limited:
                YouTubeAdapter._shared_rate_limited_until = datetime.utcnow() + timedelta(
                    seconds=self.rate_limit_delay
                )
                logger.error(
                    f"YouTube rate limit detected for {url}. Shared cooldown "
                    f"{self.rate_limit_delay / 60:.0f} min. Using {self.request_delay}s between requests."
                )
                raise ValueError(
                    f"YouTube rate limit: Session rate-limited. "
                    f"Consider adding -t sleep delay between video requests. {error_msg}"
                )
            
            # Check for authentication errors
            is_auth_error = 'Please sign in' in error_msg or 'sign in' in error_msg.lower() or \
                          'authentication' in error_msg.lower() or 'cookies' in error_msg.lower()
            
            if is_auth_error and self.cookies_file:
                logger.error(f"YouTube authentication error for {url}. Cookies file exists but may be incomplete or expired.")
                logger.error(f"Cookies file: {self.cookies_file}")
                logger.error("To fix: Export a complete cookies file from your browser after logging into YouTube.")
                logger.error("Required cookies: LOGIN_INFO, SID, HSID, SSID, APISID, SAPISID, __Secure-1PSID, __Secure-3PSID")
                logger.error("See: https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies")
                raise ValueError(f"YouTube authentication failed: Cookies file may be incomplete or expired. "
                               f"Please export a complete cookies file from your browser after logging into YouTube. "
                               f"See /api/auth/youtube for instructions.")
            elif is_auth_error:
                logger.error(f"YouTube authentication error for {url}. No cookies file configured.")
                logger.error("To fix: Upload a cookies file via /api/auth/youtube")
                raise ValueError(f"YouTube authentication required: Please upload a cookies file via /api/auth/youtube")
            
            # Check for format not available errors - these should be handled by fallback logic
            is_format_error = 'Requested format is not available' in error_msg or 'format is not available' in error_msg.lower()
            if is_format_error:
                logger.warning(f"YouTube format not available for {url}: {error_msg}")
                logger.info("This should be handled by format fallback logic. If you see this, the fallback may have failed.")
                # Try one more time with a very permissive format
                try:
                    logger.debug(f"Retrying with permissive stream selector for {url}")
                    loop = asyncio.get_event_loop()
                    stream_url = await asyncio.wait_for(
                        loop.run_in_executor(
                            executor,
                            lambda: self._get_stream_url_sync(
                                url,
                                youtube_stream_selector(720),
                                mpegts_tune=True,
                            ),
                        ),
                        timeout=tune_timeout,
                    )
                    return stream_url
                except Exception as retry_error:
                    logger.error(f"Fallback format also failed for {url}: {retry_error}")
                    raise ValueError(f"YouTube format not available: No compatible format found for {url}. {error_msg}")
            
            # Check for placeholder/unavailable videos (but not rate limit errors)
            if 'PLACEHOLDER' in error_msg or is_unavailable:
                logger.warning(f"YouTube video unavailable (placeholder or removed): {url}")
                raise ValueError(f"YouTube video unavailable: {url}")
            
            # Log the error
            if isinstance(e, DownloadError):
                logger.error(f"YouTube DownloadError getting stream URL for {url}: {error_msg}")
            elif isinstance(e, ExtractorError):
                logger.error(f"YouTube ExtractorError getting stream URL for {url}: {error_msg}")
            else:
                logger.error(f"Error getting YouTube stream URL for {url}: {error_msg}")
            raise
    
    def _get_best_format(self) -> str:
        """H.264+AAC-preferring selector; HLS-friendly for PO-token-free clients."""
        quality_heights = {'best': 1080, '720p': 720, '480p': 480, '360p': 360}
        if self.quality == 'worst':
            return 'worst'
        return youtube_stream_selector(quality_heights.get(self.quality, 1080))
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL"""
        try:
            parsed = urlparse(url)
            if parsed.hostname in ['youtube.com', 'www.youtube.com', 'youtu.be', 'm.youtube.com']:
                if parsed.path == '/watch':
                    return parse_qs(parsed.query).get('v', [None])[0]
                elif parsed.path.startswith('/embed/'):
                    return parsed.path.split('/')[2]
                elif parsed.hostname == 'youtu.be':
                    return parsed.path[1:]
        except Exception as e:
            logger.error(f"Error extracting YouTube video ID: {e}")
        return None
    
    def is_valid_url(self, url: str) -> bool:
        """Check if URL is a valid YouTube URL"""
        return self.extract_video_id(url) is not None
