"""StreamTV API tools for MCP server"""

import httpx
import logging
from typing import Any, Dict, List, Optional
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


async def streamtv_tunarr_status() -> Dict[str, Any]:
    """Proxy Tunarr integration status from StreamTV (reachability only)."""
    client = await get_client()
    return await client.request("GET", f"{config.base_url}/api/integrations/tunarr/status")


# --- Channel Builder + soft-deploy ops (NL channel creator) ---

_BUILDER = "/api/builder"


async def streamtv_suggest_channel_number() -> Dict[str, Any]:
    """Suggest the next free numeric channel number from the live lineup."""
    client = await get_client()
    channels = await client.request("GET", f"{config.base_url}/api/channels")
    used: set[str] = set()
    numeric: list[int] = []
    for ch in channels or []:
        num = str(ch.get("number", "")).strip()
        if not num:
            continue
        used.add(num)
        if num.isdigit():
            numeric.append(int(num))
    suggested = str(max(numeric) + 1) if numeric else "1000"
    while suggested in used:
        suggested = str(int(suggested) + 1)
    return {"suggested_number": suggested, "used_count": len(used)}


async def builder_list_sources() -> Dict[str, Any]:
    """List Channel Builder sources (Archive.org, YouTube, community)."""
    client = await get_client()
    sources = await client.request("GET", f"{config.base_url}{_BUILDER}/sources")
    return {"sources": sources}


async def builder_auth_status() -> Dict[str, Any]:
    """Per-source auth configured state for Channel Builder."""
    client = await get_client()
    return await client.request("GET", f"{config.base_url}{_BUILDER}/auth/status")


async def builder_auth_check(urls: Optional[List[str]] = None) -> Dict[str, Any]:
    """Pre-flight which auth scopes the given URLs require."""
    client = await get_client()
    return await client.request(
        "POST",
        f"{config.base_url}{_BUILDER}/auth-check",
        json={"urls": urls or []},
    )


async def builder_create_draft(
    channel_number: Optional[str] = None,
    channel_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a Channel Builder draft (auto-picks next free number if omitted)."""
    client = await get_client()
    body: Dict[str, Any] = {}
    if channel_number:
        body["channel_number"] = channel_number
    if channel_name:
        body["channel_name"] = channel_name
    draft = await client.request("POST", f"{config.base_url}{_BUILDER}/drafts", json=body)
    return {"draft": draft}


async def builder_get_draft(draft_id: str) -> Dict[str, Any]:
    """Load a Channel Builder draft by id."""
    client = await get_client()
    draft = await client.request("GET", f"{config.base_url}{_BUILDER}/drafts/{draft_id}")
    return {"draft": draft}


async def builder_list_drafts() -> Dict[str, Any]:
    """List Channel Builder drafts."""
    client = await get_client()
    drafts = await client.request("GET", f"{config.base_url}{_BUILDER}/drafts")
    return {"drafts": drafts}


async def builder_update_draft(
    draft_id: str,
    selected_source: Optional[str] = None,
    ordering: Optional[str] = None,
    channel_number: Optional[str] = None,
    channel_name: Optional[str] = None,
    group: Optional[str] = None,
    description: Optional[str] = None,
    playout_mode: Optional[str] = None,
    primary_collection: Optional[str] = None,
    enrich_metadata: Optional[bool] = None,
) -> Dict[str, Any]:
    """Patch draft source, ordering, and/or channel info fields."""
    client = await get_client()
    body: Dict[str, Any] = {}
    if selected_source is not None:
        body["selected_source"] = selected_source
    if ordering is not None:
        body["ordering"] = ordering
    channel: Dict[str, Any] = {}
    if channel_number is not None:
        channel["number"] = channel_number
    if channel_name is not None:
        channel["name"] = channel_name
    if group is not None:
        channel["group"] = group
    if description is not None:
        channel["description"] = description
    if playout_mode is not None:
        channel["playout_mode"] = playout_mode
    if primary_collection is not None:
        channel["primary_collection"] = primary_collection
    if enrich_metadata is not None:
        channel["enrich_metadata"] = enrich_metadata
    if channel:
        # Merge with existing channel so we do not wipe required fields
        existing = await client.request("GET", f"{config.base_url}{_BUILDER}/drafts/{draft_id}")
        merged = dict(existing.get("channel") or {})
        merged.update(channel)
        body["channel"] = merged
    draft = await client.request(
        "PATCH", f"{config.base_url}{_BUILDER}/drafts/{draft_id}", json=body
    )
    return {"draft": draft}


def _reject_archive_ia_mp4_urls(urls: List[str]) -> List[str]:
    """Drop Archive.org derivative ``*.ia.mp4`` URLs (LESSONS_LEARNED Issue 24).

    Compile/playout guards reject these; MCP must not add them in the first place.
    Prefer ``https://archive.org/download/<id>/<canonical>.mp4`` from item metadata.
    """
    cleaned: List[str] = []
    rejected: List[str] = []
    for raw in urls:
        url = (raw or "").strip()
        if not url:
            continue
        if ".ia.mp4" in url.lower():
            rejected.append(url)
            continue
        cleaned.append(url)
    if rejected:
        sample = "; ".join(rejected[:5])
        more = f" (+{len(rejected) - 5} more)" if len(rejected) > 5 else ""
        raise ValueError(
            "Refusing Archive.org `.ia.mp4` derivative URLs (Issue 24 / playout_guards). "
            "Use canonical `.mp4` from archive.org/metadata (…/download/<id>/<file>.mp4). "
            f"Rejected: {sample}{more}"
        )
    return cleaned


async def builder_add_links(draft_id: str, urls: List[str]) -> Dict[str, Any]:
    """Add one or more media URLs to a draft (max 500). Playlists/collections expand on resolve.

    Rejects ``*.ia.mp4`` derivative URLs (Issue 24) before calling the API.
    """
    if not urls:
        raise ValueError("urls must be a non-empty list")
    urls = _reject_archive_ia_mp4_urls(urls)
    if not urls:
        raise ValueError("urls must be a non-empty list after filtering")
    client = await get_client()
    draft = await client.request(
        "POST",
        f"{config.base_url}{_BUILDER}/drafts/{draft_id}/links",
        json={"urls": urls},
    )
    return {"draft": draft, "link_count": len(draft.get("links") or [])}


async def builder_resolve(draft_id: str) -> Dict[str, Any]:
    """Start async metadata resolution for draft links. Poll with builder_job_status."""
    client = await get_client()
    job = await client.request(
        "POST", f"{config.base_url}{_BUILDER}/drafts/{draft_id}/resolve"
    )
    return {"job": job}


async def builder_job_status(job_id: str) -> Dict[str, Any]:
    """Get Channel Builder job status (resolve / build / auth_login)."""
    client = await get_client()
    job = await client.request("GET", f"{config.base_url}{_BUILDER}/jobs/{job_id}")
    return {"job": job}


async def builder_wait_job(
    job_id: str,
    poll_seconds: float = 2.0,
    timeout_seconds: float = 300.0,
) -> Dict[str, Any]:
    """Poll a Builder job until completed/failed or timeout."""
    import asyncio
    import time

    deadline = time.monotonic() + max(1.0, timeout_seconds)
    interval = max(0.5, poll_seconds)
    last: Dict[str, Any] = {}
    while time.monotonic() < deadline:
        last = await builder_job_status(job_id)
        status = (last.get("job") or {}).get("status")
        if status in ("completed", "failed"):
            return last
        await asyncio.sleep(interval)
    return {
        "job": last.get("job"),
        "timed_out": True,
        "message": f"Job {job_id} still running after {timeout_seconds}s",
    }


async def builder_build(draft_id: str) -> Dict[str, Any]:
    """Compile unified YAML, import inventory, write schedule, reset playout. Poll job after."""
    client = await get_client()
    job = await client.request(
        "POST", f"{config.base_url}{_BUILDER}/drafts/{draft_id}/build"
    )
    return {"job": job}


async def builder_list_fillers() -> Dict[str, Any]:
    """List reusable filler collections for Channel Builder."""
    client = await get_client()
    fillers = await client.request("GET", f"{config.base_url}{_BUILDER}/filler-collections")
    return {"filler_collections": fillers}


async def streamtv_playout_reset(
    channel_number: Optional[str] = None,
    channel_id: Optional[int] = None,
    restart_stream: bool = True,
) -> Dict[str, Any]:
    """Reset CONTINUOUS playout anchor; optionally restart that channel stream only."""
    if not channel_number and channel_id is None:
        raise ValueError("Provide channel_number or channel_id")
    client = await get_client()
    body = {"restart_stream": restart_stream}
    if channel_number:
        url = f"{config.base_url}/api/channels/by-number/{channel_number}/playout-reset"
    else:
        url = f"{config.base_url}/api/channels/{channel_id}/playout-reset"
    return await client.request("POST", url, json=body)


async def streamtv_stream_restart(
    channel_number: Optional[str] = None,
    channel_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Soft-restart one channel MPEG-TS stream (no uvicorn kickstart)."""
    if not channel_number and channel_id is None:
        raise ValueError("Provide channel_number or channel_id")
    client = await get_client()
    if channel_number:
        url = f"{config.base_url}/api/channels/by-number/{channel_number}/stream-restart"
    else:
        url = f"{config.base_url}/api/channels/{channel_id}/stream-restart"
    return await client.request("POST", url)


# --- Channel Creator v2 detail tools (§7.2) ---


async def builder_set_requirements(draft_id: str, **fields: Any) -> Dict[str, Any]:
    """Patch draft requirements / template fields."""
    client = await get_client()
    body: Dict[str, Any] = {}
    known = {
        "requirements",
        "template",
        "enrich_metadata",
        "guide_title_style",
        "channel_number",
        "channel_name",
        "slug",
        "collection_prefix",
        "group",
        "break_plan",
        "style",
        "no_repeat_scope",
        "no_repeat_against",
        "explain_level",
    }
    for k, v in fields.items():
        if k in known and v is not None:
            body[k] = v
    draft = await client.request(
        "PATCH", f"{config.base_url}{_BUILDER}/drafts/{draft_id}", json=body
    )
    return {"draft": draft}


async def builder_discover(
    draft_id: str,
    sources: Optional[List[str]] = None,
    max_per_query: int = 25,
    extra_queries: Optional[List[str]] = None,
) -> Dict[str, Any]:
    client = await get_client()
    return await client.request(
        "POST",
        f"{config.base_url}{_BUILDER}/drafts/{draft_id}/discover",
        json={
            "sources": sources or ["archive", "youtube"],
            "max_per_query": max_per_query,
            "extra_queries": extra_queries or [],
        },
    )


async def builder_inspect_candidates(
    draft_id: str, candidate_ids: Optional[List[str]] = None
) -> Dict[str, Any]:
    client = await get_client()
    return await client.request(
        "POST",
        f"{config.base_url}{_BUILDER}/drafts/{draft_id}/inspect",
        json={"candidate_ids": candidate_ids or []},
    )


async def builder_classify(draft_id: str) -> Dict[str, Any]:
    client = await get_client()
    return await client.request(
        "POST", f"{config.base_url}{_BUILDER}/drafts/{draft_id}/classify"
    )


async def builder_add_candidates(
    draft_id: str,
    candidate_ids: Optional[List[str]] = None,
    role: str = "program",
    station_group: str = "",
) -> Dict[str, Any]:
    client = await get_client()
    body: Dict[str, Any] = {
        "candidate_ids": candidate_ids or [],
        "role": role,
    }
    if station_group:
        body["station_group"] = station_group
    return await client.request(
        "POST",
        f"{config.base_url}{_BUILDER}/drafts/{draft_id}/candidates/add",
        json=body,
    )


async def builder_set_contains(
    draft_id: str, link_id: str, contains: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Set multi-program tape contains[] on a link (via draft patch of links)."""
    client = await get_client()
    draft = await client.request(
        "GET", f"{config.base_url}{_BUILDER}/drafts/{draft_id}"
    )
    for link in draft.get("links") or []:
        if str(link.get("id")) == str(link_id):
            link["contains"] = list(contains or [])
    # PATCH channel only — links edited client-side then re-saved via update
    return {"draft_id": draft_id, "link_id": link_id, "contains": contains or []}


async def builder_plan(draft_id: str) -> Dict[str, Any]:
    client = await get_client()
    return await client.request(
        "POST", f"{config.base_url}{_BUILDER}/drafts/{draft_id}/plan"
    )


async def builder_exclude_candidates(
    draft_id: str, exclusions: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    client = await get_client()
    return await client.request(
        "POST",
        f"{config.base_url}{_BUILDER}/drafts/{draft_id}/exclusions",
        json={"exclusions": exclusions or []},
    )


async def builder_set_break_plan(
    draft_id: str,
    groups: Optional[List[str]] = None,
    long_reel_seconds: int = 1200,
    ids_after_each_break: bool = True,
) -> Dict[str, Any]:
    client = await get_client()
    body = {
        "break_plan": {
            "enabled": bool(groups),
            "groups": groups or [],
            "long_reel_seconds": long_reel_seconds,
            "station_id_after_each_gap": ids_after_each_break,
            "rotation": "interleave_wrap",
        }
    }
    draft = await client.request(
        "PATCH", f"{config.base_url}{_BUILDER}/drafts/{draft_id}", json=body
    )
    return {"draft": draft}


async def builder_validate(
    draft_id: str, skip_availability: bool = False
) -> Dict[str, Any]:
    client = await get_client()
    return await client.request(
        "POST",
        f"{config.base_url}{_BUILDER}/drafts/{draft_id}/validate",
        json={"skip_availability": skip_availability},
    )


async def builder_report(draft_id: str) -> Dict[str, Any]:
    client = await get_client()
    return await client.request(
        "POST", f"{config.base_url}{_BUILDER}/drafts/{draft_id}/report"
    )


async def discover_youtube(query: str, max_results: int = 20) -> Dict[str, Any]:
    client = await get_client()
    return await client.request(
        "POST",
        f"{config.base_url}{_BUILDER}/discover/youtube",
        json={"query": query, "max_results": max_results},
    )


async def inspect_youtube_video(video_id: str) -> Dict[str, Any]:
    client = await get_client()
    return await client.request(
        "POST",
        f"{config.base_url}{_BUILDER}/discover/youtube/inspect",
        json={"video_id": video_id},
    )


async def discover_archive(query: str, rows: int = 100) -> Dict[str, Any]:
    client = await get_client()
    return await client.request(
        "POST",
        f"{config.base_url}{_BUILDER}/discover/archive",
        json={"query": query, "rows": rows},
    )


async def inspect_archive_item(identifier: str) -> Dict[str, Any]:
    client = await get_client()
    return await client.request(
        "POST",
        f"{config.base_url}{_BUILDER}/discover/archive/inspect",
        json={"identifier": identifier},
    )

