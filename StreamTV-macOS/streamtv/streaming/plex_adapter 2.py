"""Plex streaming adapter - streams directly from Plex Media Server"""

import httpx
from typing import Optional, Dict, Any, AsyncIterator
import logging
import re
from urllib.parse import urlparse
import json
from datetime import datetime

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


class PlexAdapter:
    """Adapter for streaming Plex media without downloading"""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None
    ):
        """
        Initialize Plex adapter
        
        Args:
            base_url: Plex Media Server base URL (e.g., "http://192.168.1.100:32400")
            token: Plex authentication token
        """
        self.base_url = base_url
        # Clean token - remove any trailing whitespace or periods that might cause issues
        self.token = token.strip().rstrip('.') if token else None
        self._client = httpx.AsyncClient(timeout=60.0, follow_redirects=True)
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        headers = {
            'Accept': '*/*',
            'X-Plex-Product': 'StreamTV',
            'X-Plex-Version': '1.0.0',
            'X-Plex-Client-Identifier': 'streamtv-streaming-client'
        }
        if self.token:
            headers['X-Plex-Token'] = self.token
        return headers
    
    def extract_rating_key(self, url: str) -> Optional[str]:
        """
        Extract Plex rating key from URL
        
        Examples:
            plex://server/library/metadata/12345 -> 12345
            http://server:32400/library/metadata/12345 -> 12345
        """
        # Handle plex:// URLs
        if url.startswith('plex://'):
            url = url.replace('plex://', 'http://')
        
        # Extract rating key from URL
        match = re.search(r'/library/metadata/(\d+)', url)
        if match:
            return match.group(1)
        
        # Try to extract from query parameters
        parsed = urlparse(url)
        if 'ratingKey' in parsed.query:
            return parsed.query.split('ratingKey=')[1].split('&')[0]
        
        return None
    
    def _add_token_to_url(self, stream_url: str) -> str:
        """Add X-Plex-Token query parameter to URL for FFmpeg compatibility"""
        # #region agent log
        _debug_log("plex_adapter.py:_add_token_to_url:entry", "Adding token to URL", {
            "has_token": bool(self.token),
            "token_length": len(self.token) if self.token else 0,
            "stream_url_base": stream_url.split('?')[0] if '?' in stream_url else stream_url
        }, "A")
        # #endregion
        
        if not self.token:
            # #region agent log
            _debug_log("plex_adapter.py:_add_token_to_url:error", "Token missing", {}, "A")
            # #endregion
            raise ValueError("Plex token is required for streaming. Please configure it in settings.")
        
        from urllib.parse import urlparse, urlencode, parse_qs, quote
        
        parsed = urlparse(stream_url)
        # Parse existing query parameters (parse_qs returns dict with list values)
        existing_params = parse_qs(parsed.query)
        # Convert to simple dict with single values (take first value from lists)
        query_params = {k: v[0] if isinstance(v, list) and len(v) > 0 else v for k, v in existing_params.items()}
        # Add token (as single string value) - ensure token is clean (no trailing whitespace/periods)
        clean_token = self.token.strip().rstrip('.')
        query_params['X-Plex-Token'] = clean_token
        
        # #region agent log
        _debug_log("plex_adapter.py:_add_token_to_url:before_encode", "Before URL encoding", {
            "has_existing_params": len(query_params) > 1,
            "token_added": 'X-Plex-Token' in query_params,
            "clean_token_length": len(clean_token)
        }, "A")
        # #endregion
        
        # Rebuild URL with token - urlencode handles dict with string values correctly
        new_query = urlencode(query_params, doseq=False)
        # Ensure path is properly encoded if it contains special characters
        encoded_path = quote(parsed.path, safe='/')
        final_url = f"{parsed.scheme}://{parsed.netloc}{encoded_path}?{new_query}"
        
        # #region agent log
        _debug_log("plex_adapter.py:_add_token_to_url:exit", "URL constructed", {
            "final_url_has_token": 'X-Plex-Token' in final_url,
            "url_length": len(final_url),
            "scheme": parsed.scheme,
            "netloc": parsed.netloc,
            "path_length": len(encoded_path)
        }, "A")
        # #endregion
        
        logger.debug(f"Constructed Plex stream URL (base): {parsed.scheme}://{parsed.netloc}{encoded_path}")  # Log without token
        return final_url
    
    async def get_stream_url(self, url: str) -> str:
        """
        Get direct stream URL for a Plex media item
        
        Args:
            url: Plex media URL (plex:// or http:// format)
        
        Returns:
            Direct stream URL that can be used for streaming (with authentication token in URL for FFmpeg)
        """
        if not self.base_url:
            raise ValueError("Plex base_url not configured")
        
        if not self.token:
            raise ValueError("Plex token is required for streaming. Please configure it in settings.")
        
        rating_key = self.extract_rating_key(url)
        if not rating_key:
            # #region agent log
            _debug_log("plex_adapter.py:get_stream_url:error", "Rating key extraction failed", {"url": url[:100]}, "C")
            # #endregion
            raise ValueError(f"Could not extract rating key from URL: {url}")
        
        # #region agent log
        _debug_log("plex_adapter.py:get_stream_url:entry", "Getting stream URL", {
            "rating_key": rating_key,
            "base_url": self.base_url,
            "has_token": bool(self.token)
        }, "C")
        # #endregion
        
        # Get media info to find the best stream
        try:
            media_url = f"{self.base_url}/library/metadata/{rating_key}"
            response = await self._client.get(media_url, headers=self._get_headers())
            response.raise_for_status()
            
            # #region agent log
            _debug_log("plex_adapter.py:get_stream_url:after_request", "Plex API response received", {
                "status_code": response.status_code,
                "response_length": len(response.text)
            }, "C")
            # #endregion
            
            # Parse XML response to get media parts
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.text)
            
            # #region agent log
            _debug_log("plex_adapter.py:get_stream_url:after_parse", "XML parsed", {
                "root_tag": root.tag,
                "root_children": [c.tag for c in root][:5]
            }, "C")
            # #endregion
            
            # Find the first Media element with a Part
            # Try multiple XPath patterns to find the Part
            media_elem = root.find('.//Media')
            if media_elem is None:
                # Try alternative: might be directly under Video
                media_elem = root.find('.//Video/Media')
            
            # #region agent log
            _debug_log("plex_adapter.py:get_stream_url:media_elem", "Media element search", {
                "media_elem_found": media_elem is not None,
                "media_elem_tag": media_elem.tag if media_elem is not None else None
            }, "C")
            # #endregion
            
            if media_elem is not None:
                # Try to find Part element - could be direct child or nested
                part_elem = media_elem.find('Part')
                if part_elem is None:
                part_elem = media_elem.find('.//Part')
                
                # #region agent log
                _debug_log("plex_adapter.py:get_stream_url:part_elem", "Part element search", {
                    "part_elem_found": part_elem is not None,
                    "part_key": part_elem.get('key')[:80] if part_elem is not None and part_elem.get('key') else None
                }, "C")
                # #endregion
                
                if part_elem is not None:
                    stream_url = part_elem.get('key')
                    if stream_url:
                        # Build full URL - ensure proper format
                        # Part keys are typically relative paths like "/library/parts/12345/file.mkv"
                        # or absolute paths like "/library/parts/12345/12345/file.mkv"
                        if stream_url.startswith('/'):
                            full_url = f"{self.base_url}{stream_url}"
                        elif stream_url.startswith('http://') or stream_url.startswith('https://'):
                            # Already a full URL
                            full_url = stream_url
                        else:
                            # Relative path - prepend base URL
                            full_url = f"{self.base_url}/{stream_url.lstrip('/')}"
            
                        # #region agent log
                        _debug_log("plex_adapter.py:get_stream_url:before_token", "Before adding token", {
                            "full_url_base": full_url.split('?')[0],
                            "stream_url_type": "relative" if stream_url.startswith('/') else "absolute"
                        }, "B")
                        # #endregion
                        
                        logger.debug(f"Using Part key for streaming: {stream_url[:80]}...")
                        # Add authentication token for FFmpeg
                        result_url = self._add_token_to_url(full_url)
                        
                        # #region agent log
                        _debug_log("plex_adapter.py:get_stream_url:success", "Stream URL generated", {
                            "result_url_has_token": 'X-Plex-Token' in result_url,
                            "result_url_length": len(result_url)
                        }, "B")
                        # #endregion
                        
                        return result_url
                else:
                    logger.warning(f"No Part element found in Media for rating_key {rating_key}. XML structure: {ET.tostring(media_elem)[:200]}")
                    # #region agent log
                    _debug_log("plex_adapter.py:get_stream_url:no_part", "No Part element found", {
                        "media_elem_children": [c.tag for c in media_elem][:10]
                    }, "C")
                    # #endregion
            else:
                logger.warning(f"No Media element found for rating_key {rating_key}. Root tag: {root.tag}, children: {[c.tag for c in root][:5]}")
                # #region agent log
                _debug_log("plex_adapter.py:get_stream_url:no_media", "No Media element found", {}, "C")
                # #endregion
            
            # Fallback: try using the rating key with /file endpoint
            # Note: /file endpoint may not work for all Plex setups, but it's worth trying
            logger.debug(f"Falling back to /file endpoint for rating_key {rating_key}")
            fallback_url = f"{self.base_url}/library/metadata/{rating_key}/file"
            
            # #region agent log
            _debug_log("plex_adapter.py:get_stream_url:fallback", "Using fallback URL", {
                "fallback_url_base": fallback_url
            }, "D")
            # #endregion
            
            return self._add_token_to_url(fallback_url)
            
        except Exception as e:
            logger.error(f"Error getting Plex stream URL for rating_key {rating_key}: {e}", exc_info=True)
            # Fallback to direct file access with token
            # Note: /file endpoint requires authentication token
            fallback_url = f"{self.base_url}/library/metadata/{rating_key}/file"
            try:
                return self._add_token_to_url(fallback_url)
            except Exception as url_error:
                logger.error(f"Error constructing fallback URL: {url_error}")
                raise ValueError(f"Failed to construct Plex stream URL: {url_error}")
    
    async def get_media_info(self, url: str) -> Dict[str, Any]:
        """
        Get media information from Plex
        
        Args:
            url: Plex media URL
        
        Returns:
            Dictionary with media information
        """
        if not self.base_url:
            raise ValueError("Plex base_url not configured")
        
        rating_key = self.extract_rating_key(url)
        if not rating_key:
            raise ValueError(f"Could not extract rating key from URL: {url}")
        
        try:
            media_url = f"{self.base_url}/library/metadata/{rating_key}"
            response = await self._client.get(media_url, headers=self._get_headers())
            response.raise_for_status()
            
            # Parse XML response
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.text)
            
            video_elem = root.find('.//Video')
            if video_elem is None:
                video_elem = root.find('.//Movie')
            if video_elem is None:
                video_elem = root.find('.//Episode')
            
            if video_elem is None:
                raise ValueError("Could not find video element in Plex response")
            
            info = {
                'title': video_elem.get('title', ''),
                'year': video_elem.get('year'),
                'duration': int(video_elem.get('duration', 0)) // 1000 if video_elem.get('duration') else None,
                'summary': video_elem.get('summary', ''),
                'thumb': video_elem.get('thumb', ''),
                'art': video_elem.get('art', ''),
                'ratingKey': rating_key
            }
            
            # Add show info for episodes
            if video_elem.tag == 'Episode':
                info['showTitle'] = video_elem.get('grandparentTitle', '')
                info['seasonNumber'] = video_elem.get('parentIndex')
                info['episodeNumber'] = video_elem.get('index')
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting Plex media info: {e}")
            raise
    
    async def stream_chunked(
        self,
        stream_url: str,
        start: Optional[int] = None,
        end: Optional[int] = None
    ) -> AsyncIterator[bytes]:
        """
        Stream media in chunks from Plex
        
        Args:
            stream_url: Direct stream URL from get_stream_url()
            start: Start byte position (for range requests)
            end: End byte position (for range requests)
        
        Yields:
            Bytes chunks of media data
        """
        headers = self._get_headers()
        
        # Add range header if specified
        if start is not None or end is not None:
            range_header = "bytes="
            range_header += str(start) if start is not None else "0"
            range_header += "-"
            range_header += str(end) if end is not None else ""
            headers['Range'] = range_header
        
        try:
            async with self._client.stream('GET', stream_url, headers=headers) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    yield chunk
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise ValueError("Plex authentication failed. Please check your token.")
            elif e.response.status_code == 404:
                raise ValueError(f"Plex media not found: {stream_url}")
            else:
                raise ValueError(f"Plex streaming error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Error streaming from Plex: {e}")
            raise
    
    async def close(self):
        """Close the HTTP client"""
        await self._client.aclose()

