"""Archive.org streaming adapter - streams directly without downloading"""

import httpx
from typing import Optional, Dict, Any, List
import logging
import json
from urllib.parse import urlparse, urlencode, unquote
import re

logger = logging.getLogger(__name__)


class ArchiveOrgAdapter:
    """Adapter for streaming Archive.org videos without downloading"""
    
    def __init__(
        self, 
        preferred_format: str = "h264",
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_authentication: bool = False,
        cookies_file: Optional[str] = None
    ):
        self.preferred_format = preferred_format
        self.base_url = "https://archive.org"
        self.api_url = f"{self.base_url}/metadata"
        self.username = username
        self.password = password
        self.cookies_file = cookies_file
        self.use_authentication = use_authentication and (username and password or cookies_file)
        self._session_cookies: Optional[Dict[str, str]] = None
        self._authenticated = False
        
        # Load cookies from file if provided (preferred method)
        if cookies_file:
            self._load_cookies_from_file()
            # If authentication is required but cookies file doesn't exist, disable auth
            if use_authentication and not self._authenticated and not (username and password):
                logger.warning("Archive.org authentication enabled but cookies file not found. Please upload cookies via /api/auth/archive")
                self.use_authentication = False
    
    def _load_cookies_from_file(self):
        """Load cookies from Netscape format cookies file (like YouTube)"""
        try:
            from pathlib import Path
            cookies_path = Path(self.cookies_file)
            if not cookies_path.exists():
                logger.warning(f"Archive.org cookies file not found: {self.cookies_file}")
                logger.warning("To fix: Visit http://localhost:8410/api/auth/archive and upload your Archive.org cookies file")
                return
            
            cookies = {}
            with open(cookies_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue
                    
                    # Netscape format: domain flag path secure expiration name value
                    parts = line.split('\t')
                    if len(parts) >= 7:
                        name = parts[5]
                        value = parts[6]
                        cookies[name] = value
            
            if cookies:
                self._session_cookies = cookies
                self._authenticated = True
                logger.info(f"Loaded {len(cookies)} cookies from {self.cookies_file}")
                logger.debug(f"Cookie names: {', '.join(cookies.keys())}")
            else:
                logger.warning(f"No valid cookies found in {self.cookies_file}")
        except Exception as e:
            logger.error(f"Error loading Archive.org cookies from file: {e}")
    
    async def _ensure_authenticated(self) -> httpx.AsyncClient:
        """Ensure we have an authenticated session if authentication is enabled"""
        client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        
        if self.use_authentication:
            # If cookies file is provided, use those cookies (preferred method)
            if self.cookies_file:
                # Always reload cookies from file to ensure they're fresh
                # This handles the case where cookies were uploaded after StreamManager was created
                self._load_cookies_from_file()
                
                if self._session_cookies:
                    for name, value in self._session_cookies.items():
                        client.cookies.set(name, value)
                    logger.info(f"Using {len(self._session_cookies)} cookies from file for Archive.org authentication")
                    logger.debug(f"Cookie names: {', '.join(list(self._session_cookies.keys())[:5])}...")  # Log first 5 cookie names
                    return client
                else:
                    logger.warning("No cookies loaded from file, authentication may fail")
                    # Fall through to programmatic login attempt
            
            # Otherwise, try programmatic login (fallback)
            if not self._authenticated:
                # Try to login
                try:
                    await self._login(client)
                except Exception as e:
                    logger.warning(f"Failed to authenticate with Archive.org: {e}")
                    # Continue without authentication if login fails
                    self.use_authentication = False
            else:
                # Verify authentication is still valid
                is_valid = await self.check_authentication()
                if not is_valid:
                    # Try to re-authenticate
                    logger.debug("Archive.org session expired, re-authenticating...")
                    await self._login(client)
            
            # Add cookies to client if authenticated
            if self._authenticated and self._session_cookies:
                # Update client cookies with session cookies
                for name, value in self._session_cookies.items():
                    client.cookies.set(name, value)
        
        return client
    
    async def _login(self, client: httpx.AsyncClient) -> bool:
        """Login to Archive.org and get session cookies"""
        if not self.username or not self.password:
            return False
        
        try:
            # First, get the login page to extract any CSRF tokens or required fields
            login_page_url = f"{self.base_url}/account/login"
            login_page_response = await client.get(login_page_url)
            login_page_response.raise_for_status()
            
            # Try to extract CSRF token if present (Archive.org may use it)
            csrf_token = None
            page_content = login_page_response.text
            csrf_match = re.search(r'name=["\']csrf_token["\']\s+value=["\']([^"\']+)["\']', page_content)
            if not csrf_match:
                csrf_match = re.search(r'csrf[_-]?token["\']?\s*[:=]\s*["\']([^"\']+)["\']', page_content, re.IGNORECASE)
            if csrf_match:
                csrf_token = csrf_match.group(1)
            
            # Archive.org login form data
            login_data = {
                'username': self.username,
                'password': self.password,
            }
            
            if csrf_token:
                login_data['csrf_token'] = csrf_token
            
            # Post login credentials
            login_response = await client.post(
                login_page_url,
                data=login_data,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Referer': login_page_url,
                    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
                },
                follow_redirects=True
            )
            
            # Extract cookies from the response
            cookies = {}
            for cookie in client.cookies.jar:
                cookies[cookie.name] = cookie.value
            
            # Check for session cookies that indicate successful login
            # Archive.org typically sets cookies like 'logged-in-sig', 'logged-in-user', etc.
            has_session = any(
                'logged-in' in name.lower() or 
                'session' in name.lower() or 
                'auth' in name.lower()
                for name in cookies.keys()
            )
            
            # Also check if we were redirected away from login page (success)
            final_url = str(login_response.url)
            is_success = (
                'login' not in final_url.lower() and  # Redirected away from login
                login_response.status_code == 200
            )
            
            if has_session or (is_success and cookies):
                self._session_cookies = cookies
                self._authenticated = True
                logger.info("Successfully authenticated with Archive.org")
                return True
            else:
                # Check response content for error messages
                response_text = login_response.text.lower()
                if any(keyword in response_text for keyword in ['error', 'invalid', 'incorrect', 'failed']):
                    logger.error("Archive.org login failed: Invalid credentials or login error")
                    return False
                else:
                    logger.warning("Archive.org login response unclear, assuming not authenticated")
                    return False
            
        except Exception as e:
            logger.error(f"Error during Archive.org login: {e}")
            return False
    
    async def check_authentication(self) -> bool:
        """Check if authentication is still valid"""
        if not self._authenticated or not self._session_cookies:
            return False
        
        try:
            # Create a client with existing cookies to check authentication
            client = httpx.AsyncClient(timeout=30.0, follow_redirects=False)
            try:
                # Add existing session cookies
                for name, value in self._session_cookies.items():
                    client.cookies.set(name, value)
                
                # Try checking account info endpoint
                # Note: This endpoint may not exist or may return 404, so handle gracefully
                response = await client.get(f"{self.base_url}/account/info", follow_redirects=False)
                
                # If endpoint doesn't exist (404), assume authentication check is not available
                # and continue assuming authentication is still valid
                if response.status_code == 404:
                    logger.debug("Archive.org /account/info endpoint not found (404), skipping auth check")
                    return True  # Assume still authenticated since we can't verify
                
                # If we get redirected to login, we're not authenticated
                if response.status_code == 302:
                    location = str(response.headers.get('Location', '')).lower()
                    if 'login' in location:
                        self._authenticated = False
                        self._session_cookies = None
                        return False
                
                # 200 means authenticated
                return response.status_code == 200
            finally:
                await client.aclose()
        except Exception as e:
            # If check fails, log but don't invalidate authentication
            # The endpoint may not be available, so we'll only invalidate on actual errors
            logger.debug(f"Archive.org authentication check failed: {e}, assuming still authenticated")
            # Don't invalidate on network errors - only invalidate if we get a clear auth failure
            return True  # Assume still authenticated
    
    async def get_item_info(self, identifier: str) -> Dict[str, Any]:
        """Get item information from Archive.org"""
        try:
            client = await self._ensure_authenticated()
            
            try:
                # Archive.org metadata API format
                url = f"{self.base_url}/metadata/{identifier}"
                headers = {"Accept": "application/json"}
                
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                metadata = data.get('metadata', {})
                files = data.get('files', [])
                
                # Find video files
                video_files = self._find_video_files(files)
                
                return {
                    'identifier': identifier,
                    'title': metadata.get('title', ''),
                    'description': metadata.get('description', ''),
                    'creator': metadata.get('creator', ''),
                    'date': metadata.get('date', ''),
                    'mediatype': metadata.get('mediatype', ''),
                    'collection': metadata.get('collection', []),
                    'video_files': video_files,
                    'url': f"{self.base_url}/details/{identifier}",
                }
            finally:
                await client.aclose()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                logger.error(f"Access forbidden for {identifier}. Authentication may be required or expired.")
                # Try to re-authenticate if we have credentials
                if self.use_authentication and self.username and self.password:
                    logger.info("Attempting to re-authenticate with Archive.org...")
                    self._authenticated = False
                    self._session_cookies = None
                    client = await self._ensure_authenticated()
                    await client.aclose()
                    # Retry the request
                    try:
                        return await self.get_item_info(identifier)
                    except Exception:
                        pass
                raise PermissionError(f"Access denied to {identifier}. Check if authentication is configured correctly.")
            elif e.response.status_code == 401:
                logger.error(f"Unauthorized access to {identifier}. Login may have failed.")
                # Try to re-authenticate
                if self.use_authentication and self.username and self.password:
                    logger.info("Attempting to re-authenticate with Archive.org...")
                    self._authenticated = False
                    self._session_cookies = None
                    client = await self._ensure_authenticated()
                    await client.aclose()
                    # Retry the request
                    try:
                        return await self.get_item_info(identifier)
                    except Exception:
                        pass
                raise PermissionError(f"Authentication required for {identifier}.")
            else:
                logger.error(f"Error getting Archive.org item info: {e}")
                raise
        except Exception as e:
            logger.error(f"Error getting Archive.org item info: {e}")
            raise
    
    def _find_video_files(self, files: List[Dict]) -> List[Dict[str, Any]]:
        """Find video files in the item"""
        video_extensions = ['.mp4', '.webm', '.mkv', '.avi', '.mov', '.m4v']
        video_files = []
        
        for file_info in files:
            filename = file_info.get('name', '')
            if any(filename.lower().endswith(ext) for ext in video_extensions):
                # Check if it's a video format we prefer
                format_match = self.preferred_format.lower() in filename.lower()
                
                # Convert size to int, handling string values from Archive.org API
                size_value = file_info.get('size', 0)
                try:
                    if isinstance(size_value, str):
                        size_value = int(size_value) if size_value else 0
                    elif size_value is None:
                        size_value = 0
                    else:
                        size_value = int(size_value)
                except (ValueError, TypeError):
                    size_value = 0
                
                video_files.append({
                    'name': filename,
                    'size': size_value,
                    'format': file_info.get('format', ''),
                    'source': file_info.get('source', ''),
                    'preferred': format_match,
                })
        
        # Sort by preferred format first, then by size (larger = better quality usually)
        video_files.sort(key=lambda x: (not x['preferred'], -x['size']))
        return video_files
    
    async def get_stream_url(self, identifier: str, filename: Optional[str] = None) -> str:
        """Get direct streaming URL for Archive.org item - streams only, never downloads"""
        try:
            item_info = await self.get_item_info(identifier)
            video_files = item_info.get('video_files', [])
            
            if not video_files:
                raise ValueError(f"No video files found for identifier: {identifier}")
            
            # Use specified filename or prefer the best one
            if filename:
                selected_file = next((f for f in video_files if f['name'] == filename), None)
                if not selected_file:
                    raise ValueError(f"File {filename} not found in identifier: {identifier}")
            else:
                selected_file = video_files[0]  # Already sorted by preference
            
            # Archive.org streaming URL format
            # NOTE: This returns a direct stream URL, not a download URL
            # The /download/ endpoint supports HTTP range requests for streaming
            # No files are downloaded to disk - streaming happens in memory via httpx
            
            # Properly URL-encode the filename (Archive.org expects spaces as %20, etc.)
            from urllib.parse import quote
            encoded_filename = quote(selected_file['name'], safe='')
            stream_url = f"{self.base_url}/download/{identifier}/{encoded_filename}"
            
            # Validate the URL by following redirects and checking if the file exists
            client = await self._ensure_authenticated()
            try:
                # Do a HEAD request to follow redirects and validate the URL
                response = await client.head(stream_url, follow_redirects=True, timeout=10.0)
                
                # If we get a redirect, use the final URL
                if response.status_code in [301, 302, 303, 307, 308]:
                    redirect_url = response.headers.get('Location')
                    if redirect_url:
                        # Handle relative redirects
                        if redirect_url.startswith('/'):
                            redirect_url = f"{self.base_url}{redirect_url}"
                        stream_url = redirect_url
                        logger.info(f"Archive.org redirected to: {stream_url}")
                    else:
                        logger.warning(f"Archive.org returned {response.status_code} but no Location header")
                
                # Check if the final URL is accessible
                final_response = await client.head(stream_url, follow_redirects=True, timeout=10.0)
                if final_response.status_code == 404:
                    # File not found, try the original filename without encoding (some files might not need encoding)
                    alt_url = f"{self.base_url}/download/{identifier}/{selected_file['name']}"
                    alt_response = await client.head(alt_url, follow_redirects=True, timeout=10.0)
                    if alt_response.status_code == 200:
                        stream_url = alt_url
                        logger.info(f"Using alternative URL format: {stream_url}")
                    else:
                        logger.error(f"File not found at {stream_url} or {alt_url} for identifier: {identifier}")
                        raise ValueError(f"Video file not accessible: {selected_file['name']} in {identifier}")
                elif final_response.status_code not in [200, 206]:  # 206 is Partial Content (range requests)
                    logger.warning(f"Archive.org returned status {final_response.status_code} for {stream_url}")
            finally:
                await client.aclose()
            
            return stream_url
        except Exception as e:
            logger.error(f"Error getting Archive.org stream URL: {e}")
            raise
    
    def extract_filename(self, url: str) -> Optional[str]:
        """Extract filename from Archive.org URL (supports details/download paths)"""
        try:
            parsed = urlparse(url)
            if parsed.hostname and 'archive.org' in parsed.hostname:
                path_parts = [p for p in parsed.path.split('/') if p]
                if 'details' in path_parts:
                    idx = path_parts.index('details')
                    if idx + 2 < len(path_parts):
                        filename = path_parts[idx + 2]
                        return unquote(filename).replace('+', ' ')
                elif 'download' in path_parts:
                    idx = path_parts.index('download')
                    if idx + 2 < len(path_parts):
                        filename = path_parts[idx + 2]
                        return unquote(filename).replace('+', ' ')
        except Exception as e:
            logger.error(f"Error extracting Archive.org filename: {e}")
        return None

    def extract_identifier(self, url: str) -> Optional[str]:
        """Extract identifier from Archive.org URL"""
        try:
            parsed = urlparse(url)
            if 'archive.org' in parsed.hostname:
                # URL formats:
                # https://archive.org/details/identifier
                # https://archive.org/download/identifier/filename
                path_parts = [p for p in parsed.path.split('/') if p]
                if 'details' in path_parts:
                    idx = path_parts.index('details')
                    if idx + 1 < len(path_parts):
                        return path_parts[idx + 1]
                elif 'download' in path_parts:
                    idx = path_parts.index('download')
                    if idx + 1 < len(path_parts):
                        return path_parts[idx + 1]
        except Exception as e:
            logger.error(f"Error extracting Archive.org identifier: {e}")
        return None
    
    def is_valid_url(self, url: str) -> bool:
        """Check if URL is a valid Archive.org URL"""
        return self.extract_identifier(url) is not None
