"""YouTube streaming adapter - streams directly without downloading"""

import httpx
import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError
from typing import Optional, Dict, Any
import logging
import asyncio
import time
import re
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
            # Validate cookies file has required cookies
            self._validate_cookies_file(cookies_file)
    
    def _validate_cookies_file(self, cookies_file: str):
        """Validate that cookies file contains required authentication cookies"""
        try:
            from pathlib import Path
            cookies_path = Path(cookies_file)
            if not cookies_path.exists():
                logger.warning(f"YouTube cookies file not found: {cookies_file}")
                return
            
            # Required cookies for YouTube authentication
            required_cookies = ['LOGIN_INFO', 'SID', 'HSID', 'SSID', 'APISID', 'SAPISID', '__Secure-1PSID', '__Secure-3PSID']
            found_cookies = set()
            
            with open(cookies_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    # Netscape cookie format: domain, flag, path, secure, expiration, name, value
                    parts = line.split('\t')
                    if len(parts) >= 6:
                        cookie_name = parts[5] if len(parts) > 5 else ''
                        if cookie_name in required_cookies:
                            found_cookies.add(cookie_name)
            
            missing_cookies = set(required_cookies) - found_cookies
            if missing_cookies:
                logger.warning(f"YouTube cookies file missing required cookies: {', '.join(missing_cookies)}")
                logger.warning(f"Cookies file: {cookies_file}")
                logger.warning("To fix: Export a complete cookies file from your browser after logging into YouTube.")
                logger.warning("See: https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies")
            else:
                logger.debug(f"YouTube cookies file validated: all required cookies present")
        except Exception as e:
            logger.debug(f"Error validating cookies file: {e}")
    
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
        ydl_opts = {**self._ydl_opts}
        # Ensure cookies file is explicitly set
        if self.cookies_file:
            ydl_opts['cookiefile'] = self.cookies_file
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
        """
        Synchronous helper to get stream URL (runs in thread pool)
        
        This method implements automatic format fallback for all YouTube channels.
        If the requested format (e.g., best[height<=1080]) is not available,
        it automatically tries more flexible formats (best) until one works.
        
        This ensures all channels using YouTube content can stream successfully
        even when specific quality formats aren't available for certain videos.
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
            # Fallback formats if specific format isn't available
            if 'height<=' in requested_format:
                # Try without height restriction
                format_selectors.append('best')
            # Add more permissive fallbacks
            format_selectors.append('worst/best')  # Accept worst if best not available
            format_selectors.append('worst')  # Just worst quality
            format_selectors.append('best')  # Final fallback before permissive attempts
        
        # Ensure cookies file is explicitly set (in case it wasn't copied properly)
        cookies_file = self.cookies_file
        
        # Try each format selector until one works
        last_error = None
        info = None
        for fmt_selector in format_selectors:
            try:
                # Create fresh options, explicitly excluding any format from base options
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'extract_flat': False,
                    'geo_bypass': True,
                    'geo_bypass_country': 'US',
                    'download': False,
                    'noplaylist': True,
                    'skip_download': True,
                    'format': fmt_selector,  # Explicitly set format for this attempt
                }
                
                if cookies_file:
                    ydl_opts['cookiefile'] = cookies_file
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
        
        # If we exhausted all format selectors, try one more time with very permissive format selectors
        if info is None:
            logger.warning(f"All format selectors failed for {url}, trying with very permissive format selectors...")
            
            # Try progressively more permissive formats
            permissive_formats = [
                'worst/best',  # Accept worst quality if best not available
                'worst',  # Just worst quality
                None,  # No format restriction - let yt-dlp auto-select
            ]
            
            for permissive_fmt in permissive_formats:
                try:
                    # Create fresh options
                    ydl_opts = {
                        'quiet': True,
                        'no_warnings': True,
                        'extract_flat': False,
                        'geo_bypass': True,
                        'geo_bypass_country': 'US',
                        'download': False,
                        'noplaylist': True,
                        'skip_download': True,
                    }
                    
                    # Only set format if specified (None means auto-select)
                    if permissive_fmt is not None:
                        ydl_opts['format'] = permissive_fmt
                    
                    if cookies_file:
                        ydl_opts['cookiefile'] = cookies_file
                    
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                        logger.info(f"Successfully extracted info with format '{permissive_fmt or 'auto-select'}' for {url}")
                        break  # Success, exit loop
                except Exception as fmt_error:
                    error_msg_fmt = str(fmt_error)
                    error_msg_fmt_clean = error_msg_fmt.replace('\x1b[0;31m', '').replace('\x1b[0m', '').replace('[0;31m', '').replace('[0m', '')
                    
                    # Check if it's still a format error
                    is_format_error = (
                        'Requested format is not available' in error_msg_fmt_clean or
                        'format is not available' in error_msg_fmt_clean.lower() or
                        'list-formats' in error_msg_fmt_clean.lower()
                    )
                    
                    if is_format_error and permissive_fmt != permissive_formats[-1]:
                        # Try next permissive format
                        logger.debug(f"Format '{permissive_fmt or 'auto-select'}' failed, trying next...")
                        continue
                    elif is_format_error:
                        # Last format also failed - video likely has no formats
                        logger.error(f"All format attempts failed for {url}. Video may have no available formats.")
                        logger.error(f"Last error: {error_msg_fmt_clean[:200]}")
                        raise ValueError(f"YouTube video has no available formats: {url}. The video may be restricted, region-locked, or unavailable.")
                    else:
                        # Non-format error, re-raise
                        raise
            
            # If we still don't have info after all permissive formats, raise error
            if info is None:
                error_msg_final = str(last_error) if last_error else "Unknown error"
                error_msg_final_clean = error_msg_final.replace('\x1b[0;31m', '').replace('\x1b[0m', '').replace('[0;31m', '').replace('[0m', '')
                logger.error(f"All format attempts (including permissive) failed for {url}: {error_msg_final_clean[:200]}")
                raise ValueError(f"YouTube video has no available formats: {url}. The video may be restricted, region-locked, or unavailable.")
        
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
                    logger.debug(f"Retrying with fallback format 'best' for {url}")
                    loop = asyncio.get_event_loop()
                    stream_url = await loop.run_in_executor(self._executor, self._get_stream_url_sync, url, 'best')
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
