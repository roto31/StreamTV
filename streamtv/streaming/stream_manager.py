"""Stream manager for handling media streams"""

import httpx
from typing import Optional, AsyncIterator
import logging
from enum import Enum
import json
from datetime import datetime
from pathlib import Path

from .youtube_adapter import YouTubeAdapter
from .archive_org_adapter import ArchiveOrgAdapter
from .pbs_adapter import PBSAdapter
from .plex_adapter import PlexAdapter
from ..config import config
from ..utils.macos_credentials import get_credentials_from_keychain

logger = logging.getLogger(__name__)

# #region agent log
DEBUG_LOG_PATH = "/Users/roto1231/Documents/XCode Projects/StreamTV/.cursor/debug.log"
def _debug_log(location: str, message: str, data: dict, hypothesis_id: str):
    """Write debug log entry"""
    try:
        with open(DEBUG_LOG_PATH, "a") as f:
            log_entry = {
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": hypothesis_id,
                "location": location,
                "message": message,
                "data": data,
                "timestamp": int(datetime.now().timestamp() * 1000)
            }
            f.write(json.dumps(log_entry) + "\n")
    except Exception:
        pass
# #endregion


def find_cookies_file(site_name: str, cookies_dir: str = "data/cookies") -> Optional[str]:
    """
    Find cookies file for a site, checking both new format (site_name_cookies.txt) 
    and old format (youtube_cookies.txt, archive_cookies.txt, etc.)
    
    Args:
        site_name: Site name to look for (e.g., "www.youtube.com", "youtube.com", "archive.org")
        cookies_dir: Directory to search for cookies files
        
    Returns:
        Path to cookies file if found, None otherwise
    """
    from pathlib import Path
    
    cookies_path = Path(cookies_dir)
    if not cookies_path.exists():
        return None
    
    # Normalize site name (remove www. prefix for matching)
    normalized_name = site_name.replace("www.", "") if site_name.startswith("www.") else site_name
    
    # Try new format variations:
    # 1. Exact site_name_cookies.txt (e.g., www.youtube.com_cookies.txt)
    new_format_exact = cookies_path / f"{site_name}_cookies.txt"
    if new_format_exact.exists():
        return str(new_format_exact.absolute())
    
    # 2. Normalized site_name_cookies.txt (e.g., youtube.com_cookies.txt)
    new_format_normalized = cookies_path / f"{normalized_name}_cookies.txt"
    if new_format_normalized.exists():
        return str(new_format_normalized.absolute())
    
    # Fall back to old format based on site name
    old_formats = {
        "youtube.com": ["youtube_cookies.txt"],
        "archive.org": ["archive_cookies.txt", "archive.org_cookies.txt"],
        "pbs.org": ["pbs_cookies.txt", "pbs.org_cookies.txt"],
    }
    
    # Try to find matching old format
    for key, formats in old_formats.items():
        if key in normalized_name or normalized_name in key:
            for fmt in formats:
                old_format = cookies_path / fmt
                if old_format.exists():
                    return str(old_format.absolute())
    
    return None


class StreamSource(Enum):
    YOUTUBE = "youtube"
    ARCHIVE_ORG = "archive_org"
    PBS = "pbs"
    PLEX = "plex"
    UNKNOWN = "unknown"


class StreamManager:
    """Manages streaming from different sources"""
    
    def __init__(self):
        # Find YouTube cookies file (try new format first, then fall back to config/old format)
        youtube_cookies = config.youtube.cookies_file
        if not youtube_cookies or not Path(youtube_cookies).exists():
            # Try to find cookies file with site name (try both www. and non-www. variants)
            found_cookies = find_cookies_file("www.youtube.com") or find_cookies_file("youtube.com")
            if found_cookies:
                youtube_cookies = found_cookies
                logger.info(f"Found YouTube cookies file: {youtube_cookies}")
        
        self.youtube_adapter = YouTubeAdapter(
            quality=config.youtube.quality,
            extract_audio=config.youtube.extract_audio,
            cookies_file=youtube_cookies,
            api_key=config.youtube.api_key  # YouTube Data API v3 key for validation
        ) if config.youtube.enabled else None
        
        # Archive.org adapter - load credentials from Keychain first, then config
        # NEVER store passwords in config.yaml - use Keychain on macOS
        archive_username = config.archive_org.username
        archive_password = config.archive_org.password
        
        # Try to load from Keychain first (secure storage)
        keychain_creds = get_credentials_from_keychain("archive.org")
        if keychain_creds:
            archive_username, archive_password = keychain_creds
            logger.info("Loaded Archive.org credentials from Keychain")
        elif config.archive_org.username and not config.archive_org.password:
            # Username in config but no password - credentials should be in Keychain
            # This is the secure configuration
            logger.debug("Archive.org username in config, password should be in Keychain")
        
        # Find Archive.org cookies file (try new format first, then fall back to config/old format)
        archive_cookies = config.archive_org.cookies_file
        if not archive_cookies or not Path(archive_cookies).exists():
            # Try to find cookies file with site name
            found_cookies = find_cookies_file("archive.org")
            if found_cookies:
                archive_cookies = found_cookies
                logger.info(f"Found Archive.org cookies file: {archive_cookies}")
        
        self.archive_org_adapter = ArchiveOrgAdapter(
            preferred_format=config.archive_org.preferred_format,
            username=archive_username,
            password=archive_password,
            use_authentication=config.archive_org.use_authentication and (bool(archive_username and archive_password) or bool(archive_cookies)),
            cookies_file=archive_cookies
        ) if config.archive_org.enabled else None
        
        # PBS adapter - load credentials from Keychain first, then config
        pbs_username = config.pbs.username
        pbs_password = config.pbs.password
        
        # Try to load from Keychain first (secure storage)
        pbs_keychain_creds = get_credentials_from_keychain("pbs.org")
        if pbs_keychain_creds:
            pbs_username, pbs_password = pbs_keychain_creds
            logger.info("Loaded PBS credentials from Keychain")
        elif config.pbs.username and not config.pbs.password:
            logger.debug("PBS username in config, password should be in Keychain")
        
        # Find PBS cookies file (try new format first, then fall back to config/old format)
        pbs_cookies = config.pbs.cookies_file
        if not pbs_cookies or not Path(pbs_cookies).exists():
            # Try to find cookies file with site name
            found_cookies = find_cookies_file("pbs.org")
            if found_cookies:
                pbs_cookies = found_cookies
                logger.info(f"Found PBS cookies file: {pbs_cookies}")
        
        self.pbs_adapter = PBSAdapter(
            username=pbs_username,
            password=pbs_password,
            use_authentication=config.pbs.use_authentication and (bool(pbs_username and pbs_password) or bool(pbs_cookies)),
            cookies_file=pbs_cookies,
            use_headless_browser=config.pbs.use_headless_browser
        ) if config.pbs.enabled else None
        
        # Plex adapter
        self.plex_adapter = PlexAdapter(
            base_url=config.plex.base_url,
            token=config.plex.token
        ) if config.plex.enabled and config.plex.base_url else None
    
    def update_archive_org_credentials(self, username: str, password: str):
        """Update Archive.org adapter credentials (e.g., after AppleScript prompt)"""
        if self.archive_org_adapter:
            self.archive_org_adapter.username = username
            self.archive_org_adapter.password = password
            self.archive_org_adapter.use_authentication = bool(username and password)
            # Reset authentication state to force re-login with new credentials
            self.archive_org_adapter._authenticated = False
            self.archive_org_adapter._session_cookies = None
    
    def detect_source(self, url: str) -> StreamSource:
        """Detect the source type from URL"""
        if self.youtube_adapter and self.youtube_adapter.is_valid_url(url):
            return StreamSource.YOUTUBE
        elif self.archive_org_adapter and self.archive_org_adapter.is_valid_url(url):
            return StreamSource.ARCHIVE_ORG
        elif self.pbs_adapter and self.pbs_adapter.is_valid_url(url):
            return StreamSource.PBS
        elif self.plex_adapter and ('plex://' in url or '/library/metadata/' in url):
            return StreamSource.PLEX
        return StreamSource.UNKNOWN
    
    async def get_stream_url(self, url: str, source: Optional[StreamSource] = None, channel_name: Optional[str] = None) -> str:
        """Get streaming URL for a media URL"""
        # #region agent log
        _debug_log("stream_manager.py:get_stream_url:entry", "Getting stream URL", {
            "url_base": url.split('?')[0][:100] if url else None,
            "is_plex": '/library/metadata/' in url if url else False,
            "has_plex_adapter": self.plex_adapter is not None
        }, "D")
        # #endregion
        
        if source is None:
            source = self.detect_source(url)
        
        # #region agent log
        _debug_log("stream_manager.py:get_stream_url:source_detected", "Source detected", {
            "source": source.name if source else None
        }, "D")
        # #endregion
        
        if source == StreamSource.YOUTUBE and self.youtube_adapter:
            result = await self.youtube_adapter.get_stream_url(url)
            # #region agent log
            _debug_log("stream_manager.py:get_stream_url:youtube", "YouTube URL generated", {
                "result_length": len(result) if result else 0
            }, "D")
            # #endregion
            return result
        elif source == StreamSource.ARCHIVE_ORG and self.archive_org_adapter:
            identifier = self.archive_org_adapter.extract_identifier(url)
            if identifier:
                filename = self.archive_org_adapter.extract_filename(url)
                result = await self.archive_org_adapter.get_stream_url(identifier, filename)
                # #region agent log
                _debug_log("stream_manager.py:get_stream_url:archive", "Archive.org URL generated", {
                    "result_length": len(result) if result else 0
                }, "D")
                # #endregion
                return result
        elif source == StreamSource.PBS and self.pbs_adapter:
            # Pass channel name to help PBS adapter select correct stream from window.previews
            result = await self.pbs_adapter.get_stream_url(url, channel_name=channel_name)
            # #region agent log
            _debug_log("stream_manager.py:get_stream_url:pbs", "PBS URL generated", {
                "result_length": len(result) if result else 0
            }, "D")
            # #endregion
            return result
        elif source == StreamSource.PLEX and self.plex_adapter:
            result = await self.plex_adapter.get_stream_url(url)
            # #region agent log
            _debug_log("stream_manager.py:get_stream_url:plex", "Plex URL generated", {
                "result_has_token": 'X-Plex-Token' in result if result else False,
                "result_length": len(result) if result else 0,
                "result_base": result.split('?')[0][:100] if result else None
            }, "D")
            # #endregion
            return result
        
        # #region agent log
        _debug_log("stream_manager.py:get_stream_url:error", "Unsupported source", {
            "source": source.name if source else None
        }, "D")
        # #endregion
        raise ValueError(f"Unsupported source or URL: {url}")
    
    async def get_media_info(self, url: str, source: Optional[StreamSource] = None) -> dict:
        """Get media information"""
        if source is None:
            source = self.detect_source(url)
        
        if source == StreamSource.YOUTUBE and self.youtube_adapter:
            return await self.youtube_adapter.get_video_info(url)
        elif source == StreamSource.ARCHIVE_ORG and self.archive_org_adapter:
            identifier = self.archive_org_adapter.extract_identifier(url)
            if identifier:
                return await self.archive_org_adapter.get_item_info(identifier)
        elif source == StreamSource.PLEX and self.plex_adapter:
            return await self.plex_adapter.get_media_info(url)
        
        raise ValueError(f"Unsupported source or URL: {url}")
    
    async def stream_chunked(
        self,
        stream_url: str,
        start: Optional[int] = None,
        end: Optional[int] = None,
        source: Optional[StreamSource] = None
    ) -> AsyncIterator[bytes]:
        """
        Stream media in chunks - streams directly from source without downloading to disk.
        All data is streamed in memory and never written to files.
        """
        # Auto-detect source if not provided
        if source is None:
            source = self.detect_source(stream_url)
        
        headers = {}
        if start is not None or end is not None:
            range_header = "bytes="
            if start is not None:
                range_header += str(start)
            range_header += "-"
            if end is not None:
                range_header += str(end)
            headers["Range"] = range_header
        
        # For Archive.org, use authenticated client if available
        is_archive_org = source == StreamSource.ARCHIVE_ORG or 'archive.org' in stream_url
        if is_archive_org and self.archive_org_adapter and self.archive_org_adapter.use_authentication:
            # Use authenticated session for Archive.org streams
            # NOTE: This streams directly in memory, no files are written
            client = await self.archive_org_adapter._ensure_authenticated()
            # Use the stream context manager - it handles response cleanup
            # Don't close the client - it's reused for subsequent requests
            async with client.stream('GET', stream_url, headers=headers, follow_redirects=True) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes(chunk_size=config.streaming.chunk_size):
                    yield chunk
        # For PBS, use authenticated client if available
        elif source == StreamSource.PBS and self.pbs_adapter:
            # Use authenticated session for PBS streams (even if authentication is not explicitly enabled,
            # we still use the PBS adapter's client which may have cookies loaded)
            if self.pbs_adapter.use_authentication or '.lls.pbs.org' in stream_url.lower():
                # For PBS streams, especially DRM-protected ones, use authenticated client
                async for chunk in self.pbs_adapter.stream_chunked(stream_url):
                    yield chunk
            else:
                # Fallback to standard streaming if no authentication needed
                async with httpx.AsyncClient(timeout=config.streaming.timeout, follow_redirects=True) as client:
                    async with client.stream('GET', stream_url, headers=headers) as response:
                        response.raise_for_status()
                        async for chunk in response.aiter_bytes(chunk_size=config.streaming.chunk_size):
                            yield chunk
        # For Plex, use Plex adapter
        elif source == StreamSource.PLEX and self.plex_adapter:
            async for chunk in self.plex_adapter.stream_chunked(stream_url, start, end):
                yield chunk
        else:
            # Standard streaming for other sources (YouTube, etc.)
            # NOTE: httpx streams directly in memory, no files are written to disk
            # Enable redirect following for Archive.org and other sources
            async with httpx.AsyncClient(timeout=config.streaming.timeout, follow_redirects=True) as client:
                async with client.stream('GET', stream_url, headers=headers) as response:
                    response.raise_for_status()
                    async for chunk in response.aiter_bytes(chunk_size=config.streaming.chunk_size):
                        yield chunk
