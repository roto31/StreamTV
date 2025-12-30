"""StreamTV API tools for MCP server"""

import httpx
import logging
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from .config import config

logger = logging.getLogger(__name__)


class HTTPClient:
    """HTTP client with connection pooling and retry logic"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=config.timeout,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
        )
    
    async def request(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        json: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        as_text: bool = False
    ):
        """Make HTTP request with retry logic"""
        if headers is None:
            headers = {}
        if config.api_key:
            params = params or {}
            params["access_token"] = config.api_key
        
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
                if as_text:
                    return response.text
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

async def streamtv_list_channels(include_content_status: bool = False) -> Dict[str, Any]:
    """List all StreamTV channels
    
    Args:
        include_content_status: If True, includes 'has_content' field indicating if channel has schedules
    
    Returns:
        List of channel objects
    """
    client = await get_client()
    params = {}
    if include_content_status:
        params["include_content_status"] = "true"
    
    response = await client.request("GET", f"{config.base_url}/api/channels", params=params)
    return {"channels": response}


async def streamtv_get_channel(channel_id: Optional[int] = None, channel_number: Optional[str] = None) -> Dict[str, Any]:
    """Get a StreamTV channel by ID or number
    
    Args:
        channel_id: Channel ID (optional if channel_number provided)
        channel_number: Channel number (optional if channel_id provided)
    
    Returns:
        Channel object
    """
    if not channel_id and not channel_number:
        raise ValueError("Either channel_id or channel_number must be provided")
    
    client = await get_client()
    if channel_number:
        url = f"{config.base_url}/api/channels/number/{channel_number}"
    else:
        url = f"{config.base_url}/api/channels/{channel_id}"
    
    response = await client.request("GET", url)
    return {"channel": response}


async def streamtv_create_channel(
    number: str,
    name: str,
    group: Optional[str] = None,
    enabled: bool = True,
    logo_path: Optional[str] = None,
    playout_mode: str = "continuous"
) -> Dict[str, Any]:
    """Create a new StreamTV channel
    
    Args:
        number: Channel number (must be unique)
        name: Channel name
        group: Channel group/category (optional)
        enabled: Whether channel is enabled (default: True)
        logo_path: Path to channel logo (optional)
        playout_mode: Playout mode - "continuous" or "on_demand" (default: "continuous")
    
    Returns:
        Created channel object
    """
    client = await get_client()
    data = {
        "number": number,
        "name": name,
        "enabled": enabled,
        "playout_mode": playout_mode
    }
    if group:
        data["group"] = group
    if logo_path:
        data["logo_path"] = logo_path
    
    response = await client.request("POST", f"{config.base_url}/api/channels", json=data)
    return {"channel": response}


async def streamtv_update_channel(
    channel_id: int,
    number: Optional[str] = None,
    name: Optional[str] = None,
    group: Optional[str] = None,
    enabled: Optional[bool] = None,
    logo_path: Optional[str] = None,
    playout_mode: Optional[str] = None
) -> Dict[str, Any]:
    """Update a StreamTV channel
    
    Args:
        channel_id: Channel ID to update
        number: New channel number (optional)
        name: New channel name (optional)
        group: New channel group (optional)
        enabled: New enabled status (optional)
        logo_path: New logo path (optional)
        playout_mode: New playout mode (optional)
    
    Returns:
        Updated channel object
    """
    client = await get_client()
    data = {}
    if number is not None:
        data["number"] = number
    if name is not None:
        data["name"] = name
    if group is not None:
        data["group"] = group
    if enabled is not None:
        data["enabled"] = enabled
    if logo_path is not None:
        data["logo_path"] = logo_path
    if playout_mode is not None:
        data["playout_mode"] = playout_mode
    
    response = await client.request("PUT", f"{config.base_url}/api/channels/{channel_id}", json=data)
    return {"channel": response}


async def streamtv_delete_channel(channel_id: int) -> Dict[str, Any]:
    """Delete a StreamTV channel
    
    Args:
        channel_id: Channel ID to delete
    
    Returns:
        Success message
    """
    client = await get_client()
    await client.request("DELETE", f"{config.base_url}/api/channels/{channel_id}")
    return {"message": f"Channel {channel_id} deleted successfully"}


async def streamtv_list_media(
    source: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> Dict[str, Any]:
    """List StreamTV media items
    
    Args:
        source: Filter by source (youtube, archive_org, pbs, plex) (optional)
        skip: Number of items to skip for pagination (default: 0)
        limit: Maximum number of items to return (default: 100)
    
    Returns:
        List of media item objects
    """
    client = await get_client()
    params = {"skip": skip, "limit": limit}
    if source:
        params["source"] = source
    
    response = await client.request("GET", f"{config.base_url}/api/media", params=params)
    return {"media_items": response}


async def streamtv_get_media(media_id: int) -> Dict[str, Any]:
    """Get a StreamTV media item by ID
    
    Args:
        media_id: Media item ID
    
    Returns:
        Media item object
    """
    client = await get_client()
    response = await client.request("GET", f"{config.base_url}/api/media/{media_id}")
    return {"media_item": response}


async def streamtv_add_media(
    url: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    duration: Optional[int] = None,
    thumbnail: Optional[str] = None
) -> Dict[str, Any]:
    """Add a new media item to StreamTV from URL
    
    Args:
        url: Media URL (YouTube, Archive.org, PBS, or Plex)
        title: Media title (optional, will be fetched if not provided)
        description: Media description (optional)
        duration: Duration in seconds (optional)
        thumbnail: Thumbnail URL (optional)
    
    Returns:
        Created media item object
    """
    client = await get_client()
    data = {"url": url}
    if title:
        data["title"] = title
    if description:
        data["description"] = description
    if duration:
        data["duration"] = duration
    if thumbnail:
        data["thumbnail"] = thumbnail
    
    response = await client.request("POST", f"{config.base_url}/api/media", json=data)
    return {"media_item": response}


async def streamtv_delete_media(media_id: int) -> Dict[str, Any]:
    """Delete a StreamTV media item
    
    Args:
        media_id: Media item ID to delete
    
    Returns:
        Success message
    """
    client = await get_client()
    await client.request("DELETE", f"{config.base_url}/api/media/{media_id}")
    return {"message": f"Media item {media_id} deleted successfully"}


async def streamtv_list_collections() -> Dict[str, Any]:
    """List all StreamTV collections
    
    Returns:
        List of collection objects
    """
    client = await get_client()
    response = await client.request("GET", f"{config.base_url}/api/collections")
    return {"collections": response}


async def streamtv_create_collection(
    name: str,
    description: Optional[str] = None,
    collection_type: str = "manual"
) -> Dict[str, Any]:
    """Create a new StreamTV collection
    
    Args:
        name: Collection name (must be unique)
        description: Collection description (optional)
        collection_type: Collection type - "manual", "smart", or "multi" (default: "manual")
    
    Returns:
        Created collection object
    """
    client = await get_client()
    data = {"name": name, "collection_type": collection_type}
    if description:
        data["description"] = description
    
    response = await client.request("POST", f"{config.base_url}/api/collections", json=data)
    return {"collection": response}


async def streamtv_add_to_collection(collection_id: int, media_id: int) -> Dict[str, Any]:
    """Add a media item to a collection
    
    Args:
        collection_id: Collection ID
        media_id: Media item ID to add
    
    Returns:
        Success message
    """
    client = await get_client()
    await client.request("POST", f"{config.base_url}/api/collections/{collection_id}/items/{media_id}")
    return {"message": f"Media item {media_id} added to collection {collection_id}"}


async def streamtv_remove_from_collection(collection_id: int, media_id: int) -> Dict[str, Any]:
    """Remove a media item from a collection
    
    Args:
        collection_id: Collection ID
        media_id: Media item ID to remove
    
    Returns:
        Success message
    """
    client = await get_client()
    await client.request("DELETE", f"{config.base_url}/api/collections/{collection_id}/items/{media_id}")
    return {"message": f"Media item {media_id} removed from collection {collection_id}"}


async def streamtv_list_schedules(channel_id: Optional[int] = None) -> Dict[str, Any]:
    """List StreamTV schedules
    
    Args:
        channel_id: Filter by channel ID (optional)
    
    Returns:
        List of schedule objects
    """
    client = await get_client()
    params = {}
    if channel_id:
        params["channel_id"] = channel_id
    
    response = await client.request("GET", f"{config.base_url}/api/schedules", params=params)
    return {"schedules": response}


async def streamtv_get_schedule(schedule_id: int) -> Dict[str, Any]:
    """Get a StreamTV schedule by ID
    
    Args:
        schedule_id: Schedule ID
    
    Returns:
        Schedule object
    """
    client = await get_client()
    response = await client.request("GET", f"{config.base_url}/api/schedules/{schedule_id}")
    return {"schedule": response}


async def streamtv_create_schedule(
    name: str,
    channel_id: int,
    keep_multi_part_episodes_together: bool = False,
    treat_collections_as_shows: bool = False,
    shuffle_schedule_items: bool = False,
    random_start_point: bool = False
) -> Dict[str, Any]:
    """Create a new StreamTV schedule
    
    Args:
        name: Schedule name
        channel_id: Channel ID this schedule belongs to
        keep_multi_part_episodes_together: Keep multi-part episodes together (default: False)
        treat_collections_as_shows: Treat collections as shows (default: False)
        shuffle_schedule_items: Shuffle schedule items (default: False)
        random_start_point: Random start point (default: False)
    
    Returns:
        Created schedule object
    """
    client = await get_client()
    data = {
        "name": name,
        "channel_id": channel_id,
        "keep_multi_part_episodes_together": keep_multi_part_episodes_together,
        "treat_collections_as_shows": treat_collections_as_shows,
        "shuffle_schedule_items": shuffle_schedule_items,
        "random_start_point": random_start_point
    }
    
    response = await client.request("POST", f"{config.base_url}/api/schedules", json=data)
    return {"schedule": response}


async def streamtv_update_schedule(
    schedule_id: int,
    name: Optional[str] = None,
    channel_id: Optional[int] = None,
    keep_multi_part_episodes_together: Optional[bool] = None,
    treat_collections_as_shows: Optional[bool] = None,
    shuffle_schedule_items: Optional[bool] = None,
    random_start_point: Optional[bool] = None
) -> Dict[str, Any]:
    """Update a StreamTV schedule
    
    Args:
        schedule_id: Schedule ID to update
        name: New schedule name (optional)
        channel_id: New channel ID (optional)
        keep_multi_part_episodes_together: Keep multi-part episodes together (optional)
        treat_collections_as_shows: Treat collections as shows (optional)
        shuffle_schedule_items: Shuffle schedule items (optional)
        random_start_point: Random start point (optional)
    
    Returns:
        Updated schedule object
    """
    client = await get_client()
    data = {}
    if name is not None:
        data["name"] = name
    if channel_id is not None:
        data["channel_id"] = channel_id
    if keep_multi_part_episodes_together is not None:
        data["keep_multi_part_episodes_together"] = keep_multi_part_episodes_together
    if treat_collections_as_shows is not None:
        data["treat_collections_as_shows"] = treat_collections_as_shows
    if shuffle_schedule_items is not None:
        data["shuffle_schedule_items"] = shuffle_schedule_items
    if random_start_point is not None:
        data["random_start_point"] = random_start_point
    
    response = await client.request("PUT", f"{config.base_url}/api/schedules/{schedule_id}", json=data)
    return {"schedule": response}


async def streamtv_get_playlist(mode: str = "mixed", access_token: Optional[str] = None) -> Dict[str, Any]:
    """Get StreamTV M3U playlist
    
    Args:
        mode: Playlist mode - "hls", "ts", or "mixed" (default: "mixed")
        access_token: Access token for authentication (optional, uses config if not provided)
    
    Returns:
        M3U playlist content
    """
    client = await get_client()
    params = {"mode": mode}
    if access_token:
        params["access_token"] = access_token
    
    response = await client.request("GET", f"{config.base_url}/iptv/channels.m3u", params=params, as_text=True)
    return {"playlist": response}


async def streamtv_get_epg(access_token: Optional[str] = None, plain: bool = True) -> Dict[str, Any]:
    """Get StreamTV XMLTV EPG
    
    Args:
        access_token: Access token for authentication (optional, uses config if not provided)
        plain: Return plain XML without XSL stylesheet (default: True)
    
    Returns:
        XMLTV EPG content
    """
    client = await get_client()
    params = {"plain": "true" if plain else "false"}
    if access_token:
        params["access_token"] = access_token
    
    response = await client.request("GET", f"{config.base_url}/iptv/xmltv.xml", params=params, as_text=True)
    return {"epg": response}

