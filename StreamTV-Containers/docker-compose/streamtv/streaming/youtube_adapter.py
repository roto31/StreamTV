"""YouTube streaming adapter - streams directly without downloading"""

import httpx
import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError
from typing import Optional, Dict, Any
import logging
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta

from .youtube_api_client import YouTubeAPIClient

logger = logging.getLogger(__name__)


class YouTubeAdapter:
    """Adapter for streaming YouTube videos without downloading"""
    
    # Shared rate limit state across all instances (class-level)
    _shared_rate_limited_until: Optional[datetime] = None
    _shared_last_request_time: Optional[float] = None
    _shared_lock = asyncio.Lock() if hasattr(asyncio, 'Lock') else None
    
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
        
        # Instance-specific executor
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="youtube_adapter")  # Reduced to 1 worker to avoid parallel requests
        
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
        
        # Add cookies file if provided
        if cookies_file:
            self._ydl_opts['cookiefile'] = cookies_file
            logger.info(f"Using YouTube cookies file: {cookies_file}")
    
    def __del__(self):
        """Cleanup thread pool executor"""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)
    
    async def _wait_for_rate_limit(self):
        """Wait if we're currently rate-limited by YouTube (shared across all instances)"""
        if YouTubeAdapter._shared_rate_limited_until:
            now = datetime.utcnow()
            if now < YouTubeAdapter._shared_rate_limited_until:
                wait_seconds = (YouTubeAdapter._shared_rate_limited_until - now).total_seconds()
                logger.warning(f"YouTube rate limit active (shared), waiting {wait_seconds:.1f} seconds ({wait_seconds/60:.1f} minutes)...")
                await asyncio.sleep(wait_seconds)
                YouTubeAdapter._shared_rate_limited_until = None
            else:
                YouTubeAdapter._shared_rate_limited_until = None
    
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
        with yt_dlp.YoutubeDL(self._ydl_opts) as ydl:
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
            rate_limit_indicators = [
                'rate-limit', 'rate limit', 'rate-limited', 'rate limited',
                'been rate-limited', 'session has been rate-limited',
                'exceeded the rate limit', 'too many requests'
            ]
            is_rate_limited = any(indicator in error_msg.lower() for indicator in rate_limit_indicators)
            
            if is_rate_limited:
                # Set shared rate limit cooldown (1 hour)
                YouTubeAdapter._shared_rate_limited_until = datetime.utcnow() + timedelta(hours=1)
                logger.error(f"YouTube rate limit detected for {url}. Shared rate limit set - waiting up to 1 hour before retry.")
                raise ValueError(f"YouTube rate limit: Session rate-limited for up to 1 hour. {error_msg}")
            
            # Check for unavailable videos
            if 'Video unavailable' in error_msg or 'unavailable' in error_msg.lower():
                logger.warning(f"YouTube video unavailable: {url}")
                raise ValueError(f"YouTube video unavailable: {url}")
            
            logger.error(f"Error getting YouTube video info: {e}")
            raise
        except Exception as e:
            error_msg = str(e)
            rate_limit_indicators = [
                'rate-limit', 'rate limit', 'rate-limited', 'rate limited',
                'been rate-limited', 'session has been rate-limited',
                'exceeded the rate limit', 'too many requests'
            ]
            is_rate_limited = any(indicator in error_msg.lower() for indicator in rate_limit_indicators)
            
            if is_rate_limited:
                YouTubeAdapter._shared_rate_limited_until = datetime.utcnow() + timedelta(hours=1)
                logger.error(f"YouTube rate limit detected for {url}. Shared rate limit set - waiting up to 1 hour before retry.")
                raise ValueError(f"YouTube rate limit: Session rate-limited for up to 1 hour. {error_msg}")
            
            # Check for unavailable videos
            if 'Video unavailable' in error_msg or 'unavailable' in error_msg.lower():
                logger.warning(f"YouTube video unavailable: {url}")
                raise ValueError(f"YouTube video unavailable: {url}")
            
            logger.error(f"Error getting YouTube video info: {e}")
            raise
    
    def _get_stream_url_sync(self, url: str, format_id: Optional[str] = None) -> str:
        """Synchronous helper to get stream URL (runs in thread pool)"""
        ydl_opts = {
            **self._ydl_opts,
            'format': format_id or self._get_best_format(),
            'noplaylist': True,
            # CRITICAL: Ensure no downloading happens
            'download': False,
            'skip_download': True,
        }
        
        if self.extract_audio:
            ydl_opts['format'] = 'bestaudio/best'
        
        # Always use download=False to prevent any file downloads
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)  # Explicitly set download=False
            
            # Get the best available format URL
            if 'url' in info:
                # Check if it's a direct video URL (not HLS playlist)
                url_str = info['url']
                if 'm3u8' not in url_str.lower() and 'playlist' not in url_str.lower():
                    return url_str
            
            if 'formats' in info:
                # Find the best format - prefer direct video URLs over HLS
                formats = info['formats']
                
                # First, try to find a direct video format (not HLS/DASH)
                for fmt in formats:
                    protocol = fmt.get('protocol', '')
                    fmt_url = fmt.get('url', '')
                    fmt_id = fmt.get('format_id', '').lower()
                    
                    # Skip HLS and DASH formats for direct streaming
                    if 'm3u8' in fmt_url.lower() or 'playlist' in fmt_url.lower():
                        continue
                    if 'hls' in fmt_id or 'dash' in fmt_id:
                        continue
                    
                    # Prefer progressive formats (direct video files)
                    if protocol in ['https', 'http'] and fmt.get('vcodec') != 'none':
                        # Prefer formats with both video and audio
                        if fmt.get('acodec') != 'none':
                            return fmt_url
                
                # If no progressive format found, try any direct URL
                for fmt in formats:
                    protocol = fmt.get('protocol', '')
                    fmt_url = fmt.get('url', '')
                    if protocol in ['https', 'http']:
                        if 'm3u8' not in fmt_url.lower() and 'playlist' not in fmt_url.lower():
                            return fmt_url
                
                # Last resort: return the best available (might be HLS)
                if formats:
                    return formats[-1]['url']
            
            raise ValueError("No stream URL found")
    
    async def get_stream_url(self, url: str, format_id: Optional[str] = None) -> str:
        """Get direct streaming URL for YouTube video - streams only, never downloads (with rate limiting)"""
        # Pre-validate video with API if available
        if self.api_client:
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
        
        await self._wait_for_rate_limit()
        await self._apply_request_delay()
        
        try:
            loop = asyncio.get_event_loop()
            stream_url = await loop.run_in_executor(self._executor, self._get_stream_url_sync, url, format_id)
            return stream_url
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
                # Set shared rate limit cooldown (1 hour as recommended by YouTube)
                YouTubeAdapter._shared_rate_limited_until = datetime.utcnow() + timedelta(hours=1)
                logger.error(f"YouTube rate limit detected for {url}. Shared rate limit set - all instances will wait up to 1 hour. "
                           f"Using {self.request_delay}s delay between requests.")
                raise ValueError(f"YouTube rate limit: Session rate-limited for up to 1 hour. "
                               f"Consider adding -t sleep delay between video requests. {error_msg}")
            
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
        """Get format selector based on quality setting"""
        quality_map = {
            'best': 'best[height<=1080]',
            'worst': 'worst',
            '720p': 'best[height<=720]',
            '480p': 'best[height<=480]',
            '360p': 'best[height<=360]',
        }
        return quality_map.get(self.quality, 'best[height<=1080]')
    
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
