"""PBS live stream adapter - streams PBS live channels with authentication"""

import httpx
from typing import Optional, Dict, Any, AsyncIterator
import logging
import json
import re
from urllib.parse import urlparse, urljoin
from pathlib import Path
import asyncio

# Try to import Playwright for headless browser support
try:
    from playwright.async_api import async_playwright, Browser, Page, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Browser = None
    Page = None
    BrowserContext = None

logger = logging.getLogger(__name__)


class PBSAdapter:
    """Adapter for streaming PBS live channels"""
    
    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_authentication: bool = False,
        cookies_file: Optional[str] = None,
        use_headless_browser: bool = True
    ):
        self.username = username
        self.password = password
        self.cookies_file = cookies_file
        self.use_authentication = use_authentication and (bool(username and password) or bool(cookies_file))
        self.use_headless_browser = use_headless_browser and PLAYWRIGHT_AVAILABLE
        self._session_cookies: Optional[Dict[str, str]] = None
        self._authenticated = False
        self._playwright_context: Optional[BrowserContext] = None
        self._playwright_browser: Optional[Browser] = None
        self._playwright_cookies: list = []
        
        # Load cookies from file if provided (preferred method)
        if cookies_file:
            self._load_cookies_from_file()
            if use_authentication and not self._authenticated and not (username and password):
                logger.warning("PBS authentication enabled but cookies file not found. Please upload cookies via /api/auth/pbs")
                self.use_authentication = False
    
    def _load_cookies_from_file(self):
        """Load cookies from Netscape format cookies file"""
        try:
            cookies_path = Path(self.cookies_file)
            if not cookies_path.exists():
                logger.warning(f"PBS cookies file not found: {self.cookies_file}")
                logger.warning("To fix: Visit http://localhost:8410/api/auth/pbs and upload your PBS cookies file")
                return
            
            cookies = {}
            playwright_cookies = []  # For Playwright format
            
            with open(cookies_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue
                    
                    # Netscape format: domain flag path secure expiration name value
                    parts = line.split('\t')
                    if len(parts) >= 7:
                        domain = parts[0]
                        flag = parts[1] == 'TRUE'
                        path = parts[2]
                        secure = parts[3] == 'TRUE'
                        expiration = int(parts[4]) if parts[4].isdigit() else None
                        name = parts[5]
                        value = parts[6]
                        
                        cookies[name] = value
                        
                        # Also create Playwright cookie format
                        playwright_cookie = {
                            'name': name,
                            'value': value,
                            'domain': domain,
                            'path': path,
                            'secure': secure,
                            'httpOnly': False,
                        }
                        if expiration:
                            playwright_cookie['expires'] = expiration
                        playwright_cookies.append(playwright_cookie)
            
            if cookies:
                self._session_cookies = cookies
                self._playwright_cookies = playwright_cookies
                self._authenticated = True
                logger.info(f"Loaded {len(cookies)} cookies from {self.cookies_file}")
                logger.debug(f"Cookie names: {', '.join(cookies.keys())}")
            else:
                logger.warning(f"No valid cookies found in {self.cookies_file}")
        except Exception as e:
            logger.error(f"Error loading PBS cookies from file: {e}")
    
    async def _get_headless_browser(self) -> BrowserContext:
        """Get or create headless browser context with authentication"""
        if not self.use_headless_browser:
            raise RuntimeError("Headless browser not available or disabled")
        
        if self._playwright_context:
            return self._playwright_context
        
        try:
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(headless=True)
            self._playwright_browser = browser
            
            # Create context with cookies if available
            context_options = {
                'viewport': {'width': 1920, 'height': 1080},
                'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            if hasattr(self, '_playwright_cookies') and self._playwright_cookies:
                # Add cookies to context
                context = await browser.new_context(**context_options)
                # Add cookies for PBS domains
                for cookie in self._playwright_cookies:
                    try:
                        await context.add_cookies([cookie])
                    except Exception as e:
                        logger.debug(f"Could not add cookie {cookie.get('name')}: {e}")
                self._playwright_context = context
                logger.info(f"Created Playwright browser context with {len(self._playwright_cookies)} cookies")
            else:
                self._playwright_context = await browser.new_context(**context_options)
                logger.info("Created Playwright browser context (no cookies)")
            
            return self._playwright_context
        except Exception as e:
            logger.error(f"Error creating headless browser: {e}")
            raise
    
    async def _extract_stream_url_with_browser(self, url: str, channel_name: Optional[str] = None) -> str:
        """Extract stream URL using headless browser (for JavaScript-rendered pages)"""
        context = await self._get_headless_browser()
        page = await context.new_page()
        
        try:
            logger.info(f"Loading PBS page with headless browser...")
            
            # Monitor network requests for m3u8 URLs
            stream_urls = []
            
            def handle_response(response):
                """Capture m3u8 URLs from network requests"""
                try:
                    response_url = response.url
                    if '.m3u8' in response_url.lower():
                        stream_urls.append(response_url)
                        logger.debug(f"Found m3u8 URL in network request: {response_url[:100]}...")
                except Exception:
                    pass
            
            page.on('response', handle_response)
            
            # Navigate to PBS page
            await page.goto(url, wait_until='networkidle', timeout=30000)
            
            # Wait a bit for JavaScript to execute and load streams
            await asyncio.sleep(2)
            
            # Try to extract from JavaScript variables
            try:
                # Check if window.previews exists and has stream URLs
                previews_data = await page.evaluate('''() => {
                    if (typeof window.previews !== 'undefined') {
                        return window.previews;
                    }
                    return null;
                }''')
                
                if previews_data:
                    logger.debug(f"Found window.previews with keys: {list(previews_data.keys()) if isinstance(previews_data, dict) else 'array'}")
                    # Recursively search for m3u8 URLs
                    stream_url = self._find_m3u8_in_json(previews_data)
                    if stream_url:
                        logger.info(f"Found stream URL in window.previews: {stream_url[:100]}...")
                        return stream_url
            except Exception as e:
                logger.debug(f"Error extracting from window.previews: {e}")
            
            # Check for stream URLs in page content after JavaScript execution
            page_content = await page.content()
            m3u8_pattern = r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*'
            matches = re.finditer(m3u8_pattern, page_content, re.IGNORECASE)
            for match in matches:
                stream_url = match.group(0)
                if stream_url not in stream_urls:
                    stream_urls.append(stream_url)
                    logger.debug(f"Found m3u8 URL in page content: {stream_url[:100]}...")
            
            # Return first found stream URL
            if stream_urls:
                logger.info(f"Found {len(stream_urls)} stream URL(s), using first: {stream_urls[0][:100]}...")
                return stream_urls[0]
            
            # If no stream URLs found, try to get from video player
            try:
                # Look for video.js or similar player
                player_stream = await page.evaluate('''() => {
                    // Try to find video player and get source
                    const video = document.querySelector('video');
                    if (video && video.src) {
                        return video.src;
                    }
                    // Try video.js
                    if (typeof videojs !== 'undefined') {
                        const players = videojs.getPlayers();
                        for (const id in players) {
                            const player = players[id];
                            if (player.src && player.src().includes('.m3u8')) {
                                return player.src();
                            }
                        }
                    }
                    return null;
                }''')
                
                if player_stream and '.m3u8' in player_stream:
                    logger.info(f"Found stream URL from video player: {player_stream[:100]}...")
                    return player_stream
            except Exception as e:
                logger.debug(f"Error extracting from video player: {e}")
            
            raise ValueError("Could not find stream URL using headless browser")
            
        finally:
            await page.close()
    
    async def _ensure_authenticated(self) -> httpx.AsyncClient:
        """Ensure we have an authenticated session if authentication is enabled"""
        client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        
        if not self.use_authentication:
            return client
        
        # Reload cookies from file if available (in case they were updated)
        if self.cookies_file:
            self._load_cookies_from_file()
        
        # If we have cookies, use them
        if self._session_cookies:
            client.cookies.update(self._session_cookies)
            return client
        
        # Otherwise, try username/password login if available
        if self.username and self.password:
            try:
                # PBS login typically requires visiting the login page first
                # Then POST to login endpoint with credentials
                # This is station-specific, so we'll use a generic approach
                login_url = "https://account.pbs.org/accounts/login/"
                
                # Get login page to get CSRF token
                response = await client.get(login_url)
                if response.status_code == 200:
                    # Extract CSRF token from page (varies by PBS station)
                    csrf_match = re.search(r'name=["\']csrfmiddlewaretoken["\'] value=["\']([^"\']+)["\']', response.text)
                    csrf_token = csrf_match.group(1) if csrf_match else None
                    
                    if csrf_token:
                        # Attempt login
                        login_data = {
                            "username": self.username,
                            "password": self.password,
                            "csrfmiddlewaretoken": csrf_token
                        }
                        login_response = await client.post(login_url, data=login_data, follow_redirects=True)
                        
                        if login_response.status_code == 200 and "dashboard" in login_response.url.lower():
                            # Login successful, save cookies
                            self._session_cookies = dict(client.cookies)
                            self._authenticated = True
                            logger.info("PBS login successful")
                        else:
                            logger.warning("PBS login failed: Invalid credentials or login error")
                    else:
                        logger.warning("Could not extract CSRF token from PBS login page")
            except Exception as e:
                logger.error(f"Error during PBS login: {e}")
        
        return client
    
    def is_valid_url(self, url: str) -> bool:
        """Check if URL is a PBS live stream page or direct HLS stream"""
        pbs_domains = [
            'pbs.org',
            'pbskids.org',
            'livestream.pbskids.org',  # PBS Kids live stream CDN
            '.lls.pbs.org',  # PBS live stream CDN
            'pbs.org/video',
            'pbs.org/live'
        ]
        url_lower = url.lower()
        
        # Check if it's a PBS domain
        is_pbs_domain = any(domain in url_lower for domain in pbs_domains)
        
        # If it's a direct HLS URL (.m3u8) from a PBS domain, it's valid
        if is_pbs_domain and '.m3u8' in url_lower:
            return True
        
        # Otherwise, check if it's a PBS live stream page
        return is_pbs_domain and ('watch-live' in url_lower or 'live' in url_lower)
    
    async def get_stream_url(self, url: str, channel_name: Optional[str] = None) -> str:
        """
        Extract actual HLS/DASH stream URL from PBS live page
        
        PBS stations typically embed stream URLs in JavaScript or JSON data.
        We need to parse the page to find the actual stream manifest URL.
        
        If the URL is already a direct HLS stream (.m3u8), return it directly.
        """
        # If URL is already a direct HLS stream, return it as-is
        if '.m3u8' in url.lower():
            logger.info(f"URL is already a direct HLS stream: {url[:100]}...")
            return url
        
        client = await self._ensure_authenticated()
        
        try:
            # Fetch the PBS live page
            response = await client.get(url)
            response.raise_for_status()
            
            html_content = response.text
            
            # Method 1: Look for window.previews or similar data structures
            previews_patterns = [
                r'window\.previews\s*=\s*(\{.*?\});',  # Object format
                r'window\.previews\s*=\s*(\[.*?\]);',  # Array format
            ]
            
            for previews_pattern in previews_patterns:
                previews_match = re.search(previews_pattern, html_content, re.DOTALL)
                if previews_match:
                    try:
                        previews_data = json.loads(previews_match.group(1))
                        logger.debug(f"Found window.previews data with keys: {list(previews_data.keys()) if isinstance(previews_data, dict) else 'array'}")
                        
                        # If it's a dict, iterate through channels
                        if isinstance(previews_data, dict):
                            for channel_key in previews_data.keys():
                                channel_data = previews_data[channel_key]
                                if isinstance(channel_data, list) and len(channel_data) > 0:
                                    # Get first preview item
                                    first_item = channel_data[0]
                                    if isinstance(first_item, list) and len(first_item) > 0:
                                        preview_item = first_item[0]
                                        if isinstance(preview_item, dict):
                                            stream_url = self._find_m3u8_in_json(preview_item)
                                            if stream_url:
                                                logger.info(f"Found PBS stream URL in window.previews[{channel_key}]: {stream_url[:100]}...")
                                                return stream_url
                                            # Check for stream URL fields
                                            for key in ['url', 'stream', 'streamUrl', 'hlsUrl', 'manifestUrl', 'playlistUrl']:
                                                if key in preview_item and isinstance(preview_item[key], str):
                                                    if '.m3u8' in preview_item[key]:
                                                        stream_url = preview_item[key]
                                                        logger.info(f"Found PBS stream URL in window.previews[{channel_key}].{key}: {stream_url[:100]}...")
                                                        return stream_url
                        
                        # If it's an array, iterate through items
                        elif isinstance(previews_data, list):
                            for preview in previews_data:
                                if isinstance(preview, dict):
                                    stream_url = self._find_m3u8_in_json(preview)
                                    if stream_url:
                                        logger.info(f"Found PBS stream URL in window.previews: {stream_url[:100]}...")
                                        return stream_url
                    except (json.JSONDecodeError, KeyError, IndexError) as e:
                        logger.debug(f"Error parsing window.previews: {e}")
                        continue
            
            # Method 2: Look for JavaScript files that might contain stream URLs
            js_file_pattern = r'<script[^>]+src=["\']([^"\']+\.js[^"\']*)["\']'
            js_matches = re.finditer(js_file_pattern, html_content, re.IGNORECASE)
            for js_match in js_matches:
                js_url = js_match.group(1)
                # Only check JavaScript files from PBS domains
                if 'pbs.org' in js_url:
                    try:
                        # Make absolute URL if relative
                        if js_url.startswith('//'):
                            js_url = 'https:' + js_url
                        elif js_url.startswith('/'):
                            from urllib.parse import urljoin
                            js_url = urljoin(url, js_url)
                        
                        logger.debug(f"Checking JavaScript file: {js_url}")
                        js_response = await client.get(js_url, timeout=5.0)
                        js_content = js_response.text
                        
                        # Look for m3u8 URLs in JavaScript
                        m3u8_patterns = [
                            r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*',
                            r'["\']([^"\']+\.m3u8[^"\']*)["\']',
                        ]
                        for pattern in m3u8_patterns:
                            matches = re.finditer(pattern, js_content, re.IGNORECASE)
                            for match in matches:
                                stream_url = match.group(1) if match.groups() else match.group(0)
                                stream_url = stream_url.strip('"\'')
                                if stream_url.startswith('http') and '.m3u8' in stream_url:
                                    logger.info(f"Found PBS stream URL in JavaScript: {stream_url[:100]}...")
                                    return stream_url
                    except Exception as e:
                        logger.debug(f"Error checking JS file {js_url}: {e}")
                        continue
            
            # Method 3: Look for HLS manifest in JavaScript variables
            # Common patterns: var streamUrl = "...", streamUrl: "...", "streamUrl": "..."
            hls_patterns = [
                r'["\']streamUrl["\']\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'["\']hlsUrl["\']\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'["\']manifestUrl["\']\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'["\']playlistUrl["\']\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'\.m3u8[^"\']*["\']',
            ]
            
            for pattern in hls_patterns:
                matches = re.finditer(pattern, html_content, re.IGNORECASE)
                for match in matches:
                    stream_url = match.group(1) if match.groups() else match.group(0)
                    # Clean up the URL
                    stream_url = stream_url.strip('"\'')
                    if stream_url.startswith('http'):
                        logger.info(f"Found PBS stream URL: {stream_url[:100]}...")
                        return stream_url
            
            # Method 2: Look for JSON data embedded in page
            json_patterns = [
                r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>',
                r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
                r'window\.__DATA__\s*=\s*({.*?});',
            ]
            
            for pattern in json_patterns:
                matches = re.finditer(pattern, html_content, re.DOTALL)
                for match in matches:
                    try:
                        json_data = json.loads(match.group(1))
                        # Recursively search for .m3u8 URLs in JSON
                        stream_url = self._find_m3u8_in_json(json_data)
                        if stream_url:
                            logger.info(f"Found PBS stream URL in JSON: {stream_url[:100]}...")
                            return stream_url
                    except json.JSONDecodeError:
                        continue
            
            # Method 6: Look for video.js or similar player initialization
            videojs_pattern = r'videojs\([^)]+["\']([^"\']+\.m3u8[^"\']*)["\']'
            match = re.search(videojs_pattern, html_content, re.IGNORECASE)
            if match:
                stream_url = match.group(1).strip('"\'')
                if stream_url.startswith('http'):
                    logger.info(f"Found PBS stream URL in video.js: {stream_url[:100]}...")
                    return stream_url
            
            # Method 7: Look for iframe src that might contain stream
            iframe_pattern = r'<iframe[^>]+src=["\']([^"\']+)["\']'
            iframe_matches = re.finditer(iframe_pattern, html_content, re.IGNORECASE)
            for iframe_match in iframe_matches:
                iframe_url = iframe_match.group(1)
                if '.m3u8' in iframe_url or 'live' in iframe_url.lower():
                    # Recursively fetch iframe content
                    try:
                        iframe_response = await client.get(iframe_url)
                        iframe_stream = await self.get_stream_url(iframe_url)
                        if iframe_stream:
                            return iframe_stream
                    except Exception:
                        continue
            
            # Final fallback: Use headless browser for JavaScript-rendered pages
            if self.use_headless_browser:
                try:
                    logger.info("Attempting to extract stream URL using headless browser...")
                    stream_url = await self._extract_stream_url_with_browser(url, channel_name)
                    if stream_url:
                        return stream_url
                except Exception as e:
                    logger.warning(f"Headless browser extraction failed: {e}")
            
            logger.warning(f"Could not find stream URL in PBS page: {url}")
            raise ValueError(f"Could not extract stream URL from PBS page: {url}")
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching PBS page: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"Error extracting PBS stream URL: {e}")
            raise
    
    def _find_m3u8_in_json(self, data: Any) -> Optional[str]:
        """Recursively search for .m3u8 URLs in JSON data"""
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str) and '.m3u8' in value and value.startswith('http'):
                    return value
                result = self._find_m3u8_in_json(value)
                if result:
                    return result
        elif isinstance(data, list):
            for item in data:
                result = self._find_m3u8_in_json(item)
                if result:
                    return result
        return None
    
    async def stream_chunked(self, url: str) -> AsyncIterator[bytes]:
        """
        Stream chunks from PBS with authentication
        
        This is used for direct streaming when the stream URL is already known.
        """
        client = await self._ensure_authenticated()
        
        try:
            async with client.stream('GET', url) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    yield chunk
        except Exception as e:
            logger.error(f"Error streaming from PBS: {e}")
            raise
    
    async def get_channel_info(self, url: str) -> Dict[str, Any]:
        """Get information about a PBS live channel"""
        client = await self._ensure_authenticated()
        
        try:
            response = await client.get(url)
            response.raise_for_status()
            
            # Extract channel name from page title or metadata
            title_match = re.search(r'<title[^>]*>([^<]+)</title>', response.text, re.IGNORECASE)
            channel_name = title_match.group(1).strip() if title_match else "PBS Live Stream"
            
            return {
                "name": channel_name,
                "url": url,
                "authenticated": self._authenticated
            }
        except Exception as e:
            logger.error(f"Error getting PBS channel info: {e}")
            return {
                "name": "PBS Live Stream",
                "url": url,
                "authenticated": False
            }
    
    async def cleanup(self):
        """Clean up headless browser resources"""
        if self._playwright_context:
            try:
                await self._playwright_context.close()
                self._playwright_context = None
            except Exception as e:
                logger.debug(f"Error closing Playwright context: {e}")
        
        if self._playwright_browser:
            try:
                await self._playwright_browser.close()
                self._playwright_browser = None
            except Exception as e:
                logger.debug(f"Error closing Playwright browser: {e}")

