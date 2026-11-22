"""Archive.org API tools for MCP server"""

import httpx
import logging
from typing import Optional, Dict, Any, List
from urllib.parse import urlencode

from .config import config

logger = logging.getLogger(__name__)


class HTTPClient:
    """HTTP client with connection pooling and retry logic"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=config.timeout,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
        )
        self._authenticated = False
    
    async def _ensure_authenticated(self):
        """Ensure authentication if credentials provided"""
        if not self._authenticated and (config.username and config.password):
            try:
                # Login to Archive.org
                login_data = {
                    "username": config.username,
                    "password": config.password
                }
                response = await self.client.post(
                    f"{config.base_url}/account/login",
                    data=login_data
                )
                response.raise_for_status()
                self._authenticated = True
                logger.info("Authenticated with Archive.org")
            except Exception as e:
                logger.warning(f"Failed to authenticate with Archive.org: {e}")
    
    async def request(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        json: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make HTTP request with retry logic"""
        if headers is None:
            headers = {}
        headers.setdefault("Accept", "application/json")
        
        await self._ensure_authenticated()
        
        for attempt in range(config.max_retries):
            try:
                response = await self.client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json,
                    headers=headers
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code < 500 or attempt == config.max_retries - 1:
                    raise
                logger.warning(f"Request failed, retrying ({attempt + 1}/{config.max_retries}): {e}")
            except httpx.RequestError as e:
                if attempt == config.max_retries - 1:
                    raise
                logger.warning(f"Request error, retrying ({attempt + 1}/{config.max_retries}): {e}")
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


# Global HTTP client instance
_http_client: Optional[HTTPClient] = None


async def get_client() -> HTTPClient:
    """Get or create HTTP client"""
    global _http_client
    if _http_client is None:
        _http_client = HTTPClient()
    return _http_client


# Tool implementations

async def archive_org_search(
    query: str,
    fields: Optional[str] = None,
    rows: int = 50,
    page: int = 1,
    sort: Optional[str] = None
) -> Dict[str, Any]:
    """Search Archive.org by query
    
    Args:
        query: Search query (e.g., "collection:tv OR collection:movies")
        fields: Comma-separated list of fields to return (default: identifier,title,creator,date,mediatype)
        rows: Number of results per page (default: 50, max: 10000)
        page: Page number (default: 1)
        sort: Sort field (e.g., "downloads desc", "date desc")
    
    Returns:
        Search results with items and metadata
    """
    client = await get_client()
    
    # Build query parameters for Advanced Search API
    params = {
        "q": query,
        "output": "json",
        "rows": min(rows, 10000),
        "page": page
    }
    
    if fields:
        params["fl"] = fields
    else:
        params["fl"] = "identifier,title,creator,date,mediatype,description,publicdate,downloads"
    
    if sort:
        params["sort"] = sort
    
    response = await client.request("GET", config.search_url, params=params)
    
    # Format response
    docs = response.get("response", {}).get("docs", [])
    num_found = response.get("response", {}).get("numFound", 0)
    
    return {
        "query": query,
        "total_results": num_found,
        "page": page,
        "rows_per_page": rows,
        "results": docs
    }


async def archive_org_browse_collection(collection_id: str) -> Dict[str, Any]:
    """Browse items in an Archive.org collection
    
    Args:
        collection_id: Collection identifier (e.g., "tv", "movies", "opensource_movies")
    
    Returns:
        Collection items and metadata
    """
    # Use search API to find items in collection
    query = f"collection:{collection_id}"
    return await archive_org_search(query, rows=100)


async def archive_org_get_item_metadata(identifier: str) -> Dict[str, Any]:
    """Get detailed metadata for an Archive.org item
    
    Args:
        identifier: Item identifier (e.g., "MagnumPI_1980_ABC_Primetime")
    
    Returns:
        Item metadata including files, metadata, and reviews
    """
    client = await get_client()
    
    url = f"{config.metadata_url}/{identifier}"
    response = await client.request("GET", url)
    
    return {
        "identifier": identifier,
        "metadata": response.get("metadata", {}),
        "files": response.get("files", []),
        "reviews": response.get("reviews", []),
        "server": response.get("server", ""),
        "dir": response.get("dir", "")
    }


async def archive_org_get_item_files(identifier: str, format_filter: Optional[str] = None) -> Dict[str, Any]:
    """Get file list for an Archive.org item
    
    Args:
        identifier: Item identifier
        format_filter: Filter by file format (e.g., "h264", "mp4", "mpeg4")
    
    Returns:
        List of files with metadata
    """
    metadata = await archive_org_get_item_metadata(identifier)
    files = metadata.get("files", [])
    
    if format_filter:
        # Filter files by format
        filtered_files = []
        for file_info in files:
            name = file_info.get("name", "").lower()
            if format_filter.lower() in name:
                filtered_files.append(file_info)
        files = filtered_files
    
    return {
        "identifier": identifier,
        "total_files": len(metadata.get("files", [])),
        "filtered_files": len(files),
        "format_filter": format_filter,
        "files": files
    }


async def archive_org_get_stream_url(identifier: str, filename: Optional[str] = None) -> Dict[str, Any]:
    """Get streaming URL for an Archive.org video file
    
    Args:
        identifier: Item identifier
        filename: Specific filename to stream (optional, will auto-detect if not provided)
    
    Returns:
        Streaming URL and file information
    """
    metadata = await archive_org_get_item_metadata(identifier)
    files = metadata.get("files", [])
    
    # Find video file
    video_file = None
    if filename:
        # Find specific file
        for file_info in files:
            if file_info.get("name") == filename:
                video_file = file_info
                break
    else:
        # Auto-detect best video file (prefer h264/mp4)
        preferred_formats = ["h264", "mp4", "mpeg4"]
        for format_name in preferred_formats:
            for file_info in files:
                name = file_info.get("name", "").lower()
                if format_name in name and file_info.get("format") in ["h.264", "MPEG4", "h264"]:
                    video_file = file_info
                    break
            if video_file:
                break
        
        # Fallback to first video file
        if not video_file:
            for file_info in files:
                if file_info.get("format") in ["h.264", "MPEG4", "h264", "Video"]:
                    video_file = file_info
                    break
    
    if not video_file:
        return {
            "identifier": identifier,
            "error": "No video file found",
            "available_files": [f.get("name") for f in files[:10]]
        }
    
    # Build streaming URL
    server = metadata.get("server", "")
    dir_path = metadata.get("dir", "")
    file_name = video_file.get("name", "")
    
    if server and dir_path:
        stream_url = f"https://{server}{dir_path}/{file_name}"
    else:
        stream_url = f"{config.base_url}/download/{identifier}/{file_name}"
    
    return {
        "identifier": identifier,
        "filename": file_name,
        "stream_url": stream_url,
        "file_size": video_file.get("size"),
        "format": video_file.get("format"),
        "duration": video_file.get("length")
    }

