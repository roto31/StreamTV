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


def _is_ia_mp4(name: str) -> bool:
    return str(name or "").lower().endswith(".ia.mp4")


def _canonical_download_url(identifier: str, filename: str) -> str:
    """Always archive.org/download/<id>/<urlencoded name> — never storage-node (D6)."""
    from urllib.parse import quote

    return (
        f"https://archive.org/download/{identifier}/"
        f"{quote(str(filename), safe='/')}"
    )


def _duration_seconds(raw: Any) -> Optional[int]:
    if raw is None or raw == "":
        return None
    try:
        seconds = int(float(raw))
    except (TypeError, ValueError):
        return None
    return seconds if seconds > 0 else None


async def archive_org_get_item_files(
    identifier: str,
    format_filter: Optional[str] = None,
    originals_only: bool = False,
    exclude_derivatives: bool = True,
) -> Dict[str, Any]:
    """Get file list for an Archive.org item.

    Args:
        identifier: Item identifier
        format_filter: Filter by extension/format token (e.g. ``mp4``). Does **not**
            match ``*.ia.mp4`` when filtering for ``mp4``.
        originals_only: Keep only files with ``source == "original"``.
        exclude_derivatives: Drop ``*.ia.mp4`` and ``source == "derivative"`` (default True).
    """
    metadata = await archive_org_get_item_metadata(identifier)
    files = list(metadata.get("files", []) or [])

    if exclude_derivatives:
        files = [
            f
            for f in files
            if not _is_ia_mp4(f.get("name", ""))
            and str(f.get("source") or "").lower() != "derivative"
        ]
    if originals_only:
        files = [
            f for f in files if str(f.get("source") or "").lower() == "original"
        ]

    if format_filter:
        token = format_filter.lower().lstrip(".")
        filtered_files = []
        for file_info in files:
            name = str(file_info.get("name", "")).lower()
            if _is_ia_mp4(name):
                continue
            # Prefer extension match: ".mp4" not substring of ".ia.mp4" (already dropped)
            # and not accidental "mp4" inside unrelated names without a real extension.
            if name.endswith(f".{token}") or token in str(file_info.get("format") or "").lower():
                filtered_files.append(file_info)
            elif token in name and not name.endswith(".ia.mp4"):
                # Legacy substring match for non-ia names (e.g. "h264").
                filtered_files.append(file_info)
        files = filtered_files

    return {
        "identifier": identifier,
        "total_files": len(metadata.get("files", []) or []),
        "filtered_files": len(files),
        "format_filter": format_filter,
        "originals_only": originals_only,
        "exclude_derivatives": exclude_derivatives,
        "files": files,
    }


async def archive_org_get_stream_url(
    identifier: str, filename: Optional[str] = None
) -> Dict[str, Any]:
    """Get streaming URL for an Archive.org video file.

    Always returns ``https://archive.org/download/<identifier>/<urlencoded>``.
    Never returns ``*.ia.mp4`` or storage-server-pinned hosts (D6 / Issues 24, 32).
    """
    metadata = await archive_org_get_item_metadata(identifier)
    files = list(metadata.get("files", []) or [])

    video_file = None
    if filename:
        for file_info in files:
            if file_info.get("name") == filename and not _is_ia_mp4(filename):
                video_file = file_info
                break
    else:
        # Prefer original MPEG4/mp4; never auto-pick *.ia.mp4.
        candidates = [
            f
            for f in files
            if not _is_ia_mp4(f.get("name", ""))
            and str(f.get("name", "")).lower().endswith((".mp4", ".mpeg4", ".mpg", ".mpeg"))
        ]
        originals = [
            f for f in candidates if str(f.get("source") or "").lower() == "original"
        ]
        pool = originals or candidates
        preferred_formats = {"mpeg4", "h.264", "h264", "mp4"}
        for file_info in pool:
            fmt = str(file_info.get("format") or "").lower()
            if fmt in preferred_formats or str(file_info.get("name", "")).lower().endswith(
                ".mp4"
            ):
                video_file = file_info
                break
        if not video_file and pool:
            video_file = pool[0]
        if not video_file:
            for file_info in files:
                if _is_ia_mp4(file_info.get("name", "")):
                    continue
                if file_info.get("format") in ["h.264", "MPEG4", "h264", "Video"]:
                    video_file = file_info
                    break

    if not video_file:
        return {
            "identifier": identifier,
            "error": "No video file found",
            "available_files": [
                f.get("name") for f in files[:10] if not _is_ia_mp4(f.get("name", ""))
            ],
        }

    file_name = video_file.get("name", "")
    if _is_ia_mp4(file_name):
        return {
            "identifier": identifier,
            "error": "Refusing *.ia.mp4 derivative URL (Issue 24)",
            "filename": file_name,
        }

    stream_url = _canonical_download_url(identifier, file_name)
    duration = _duration_seconds(video_file.get("length"))

    return {
        "identifier": identifier,
        "filename": file_name,
        "stream_url": stream_url,
        "file_size": video_file.get("size"),
        "format": video_file.get("format"),
        "duration": duration if duration is not None else video_file.get("length"),
        "length_seconds": duration,
    }

