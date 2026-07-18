"""Stream manager for handling media streams"""

import os
import httpx
from pathlib import Path
from typing import Optional, AsyncIterator
import logging
from enum import Enum
import json
from datetime import datetime

from .youtube_adapter import YouTubeAdapter
from .archive_org_adapter import ArchiveOrgAdapter
from .pbs_adapter import PBSAdapter
from .plex_adapter import PlexAdapter
from ..config import config
from ..utils.macos_credentials import (
    get_credentials_from_keychain,
    resolve_archive_org_login_email,
)
from ..utils.youtube_cookies import ensure_netscape_cookies

logger = logging.getLogger(__name__)

class StreamSource(Enum):
    YOUTUBE = "youtube"
    ARCHIVE_ORG = "archive_org"
    PBS = "pbs"
    PLEX = "plex"
    UNKNOWN = "unknown"

class StreamManager:
    """Manages streaming from different sources"""
    
    def __init__(self):
        youtube_cookies = ensure_netscape_cookies(
            config.youtube.cookies_file,
            config.youtube.cookies_json_file,
        )
        self.youtube_adapter = YouTubeAdapter(
            quality=config.youtube.quality,
            extract_audio=config.youtube.extract_audio,
            cookies_file=youtube_cookies,
            api_key=config.youtube.api_key,
            request_delay=float(getattr(config.youtube, "request_delay", 5.0) or 5.0),
            rate_limit_delay=float(
                getattr(config.youtube, "rate_limit_backoff_max", 3600.0) or 3600.0
            ),
        ) if config.youtube.enabled else None
        
        # Archive.org adapter credential resolution (order of precedence):
        #   1. macOS Keychain (desktop, most secure)
        #   2. config.yaml archive_org.{username,password,cookies_file}
        #   3. Environment variables (headless / cloud / secret-managed setups):
        #        STREAMTV_ARCHIVE_ORG_USERNAME / STREAMTV_ARCHIVE_ORG_PASSWORD
        #        STREAMTV_ARCHIVE_ORG_COOKIES_FILE (path to Netscape cookies.txt)
        #   4. Default cookies file at data/cookies/archive_org_cookies.txt if present
        # Passwords are NEVER written to config.yaml; env vars / Keychain / cookies only.
        preferred_email = config.archive_org.username or os.getenv(
            "STREAMTV_ARCHIVE_ORG_USERNAME"
        )
        archive_username = preferred_email
        archive_password = config.archive_org.password or os.getenv(
            "STREAMTV_ARCHIVE_ORG_PASSWORD"
        )

        # Keychain (macOS): password from Passwords app; login ID is the email.
        keychain_creds = None
        if preferred_email:
            keychain_creds = get_credentials_from_keychain(
                "archive.org", account=preferred_email
            )
        if not keychain_creds:
            keychain_creds = get_credentials_from_keychain("archive.org")
        if keychain_creds:
            kc_user, archive_password = keychain_creds
            archive_username = resolve_archive_org_login_email(kc_user, preferred_email)
            logger.info(
                "Loaded Archive.org credentials from Keychain (login as %s)",
                archive_username,
            )

        # Resolve cookies file: config -> env -> default location
        archive_cookies_file = (
            config.archive_org.cookies_file
            or os.getenv("STREAMTV_ARCHIVE_ORG_COOKIES_FILE")
        )
        if not archive_cookies_file:
            for candidate in (
                Path("data/cookies/archive.org_cookies.txt"),
                Path("data/cookies/archive_org_cookies.txt"),
                Path("data/cookies/archive_cookies.txt"),
            ):
                if candidate.exists():
                    archive_cookies_file = str(candidate)
                    break

        has_creds = bool(archive_username and archive_password)
        has_cookies = bool(archive_cookies_file and Path(archive_cookies_file).exists())
        # Auto-enable authentication whenever we actually have a way to authenticate,
        # so headless/env-configured deployments work without a manual toggle.
        archive_use_auth = (config.archive_org.use_authentication or has_creds or has_cookies) and (has_creds or has_cookies)
        if archive_use_auth:
            logger.info(
                "Archive.org authentication enabled (%s)",
                "cookies file" if has_cookies else "username/password",
            )

        self.archive_org_adapter = ArchiveOrgAdapter(
            preferred_format=config.archive_org.preferred_format,
            username=archive_username,
            password=archive_password,
            use_authentication=archive_use_auth,
            cookies_file=archive_cookies_file
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
        
        self.pbs_adapter = PBSAdapter(
            username=pbs_username,
            password=pbs_password,
            use_authentication=config.pbs.use_authentication and (bool(pbs_username and pbs_password) or bool(config.pbs.cookies_file)),
            cookies_file=config.pbs.cookies_file,
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

    @staticmethod
    def _coerce_stream_source(source: object | None) -> StreamSource | None:
        """Accept StreamManager or database StreamSource enums (and raw values)."""
        if source is None:
            return None
        if isinstance(source, StreamSource):
            return source
        value = source.value if hasattr(source, "value") else source
        try:
            return StreamSource(value)
        except ValueError:
            return StreamSource.UNKNOWN
    
    async def get_stream_url(
        self,
        url: str,
        source: Optional[StreamSource] = None,
        channel_name: Optional[str] = None,
        *,
        tune_priority: bool = False,
        force_refresh: bool = False,
    ) -> str:
        """Get streaming URL for a media URL"""
        
        source = self._coerce_stream_source(source)
        if source is None:
            source = self.detect_source(url)
        
        
        if source == StreamSource.YOUTUBE and self.youtube_adapter:
            result = await self.youtube_adapter.get_stream_url(
                url,
                tune_priority=tune_priority,
                force_refresh=force_refresh,
            )
            return result
        elif source == StreamSource.ARCHIVE_ORG and self.archive_org_adapter:
            identifier = self.archive_org_adapter.extract_identifier(url)
            if identifier:
                filename = self.archive_org_adapter.extract_filename(url)
                result = await self.archive_org_adapter.get_stream_url(identifier, filename)
                return result
        elif source == StreamSource.PBS and self.pbs_adapter:
            # Pass channel name to help PBS adapter select correct stream from window.previews
            result = await self.pbs_adapter.get_stream_url(url, channel_name=channel_name)
            return result
        elif source == StreamSource.PLEX and self.plex_adapter:
            result = await self.plex_adapter.get_stream_url(url)
            return result
        
        raise ValueError(f"Unsupported source or URL: {url}")
    
    async def get_media_info(self, url: str, source: Optional[StreamSource] = None) -> dict:
        """Get media information"""
        source = self._coerce_stream_source(source)
        if source is None:
            source = self.detect_source(url)
        
        if source == StreamSource.YOUTUBE and self.youtube_adapter:
            return await self.youtube_adapter.get_video_info(url)
        elif source == StreamSource.ARCHIVE_ORG and self.archive_org_adapter:
            identifier = self.archive_org_adapter.extract_identifier(url)
            if identifier:
                return await self.archive_org_adapter.get_item_info(identifier)
        elif source == StreamSource.PBS and self.pbs_adapter:
            return await self.pbs_adapter.get_channel_info(url)
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
