"""StreamTV MCP Server - Main entry point"""

import asyncio
import logging
import sys
from typing import Any

# MCP SDK imports
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent, Resource, ResourceTemplate, ReadResourceResult, TextResourceContents
except ImportError:
    # Fallback for older MCP SDK versions
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
    except ImportError:
        logging.error("MCP SDK not installed. Install with: pip install mcp")
        sys.exit(1)

from .config import config
from . import tools
from . import resources

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create MCP server
server = Server("streamtv-mcp-server")


# Register tools
@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available StreamTV tools"""
    return [
        Tool(
            name="streamtv_list_channels",
            description="List all StreamTV channels",
            inputSchema={
                "type": "object",
                "properties": {
                    "include_content_status": {
                        "type": "boolean",
                        "description": "Include 'has_content' field indicating if channel has schedules"
                    }
                }
            }
        ),
        Tool(
            name="streamtv_get_channel",
            description="Get a StreamTV channel by ID or number",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {"type": "integer", "description": "Channel ID"},
                    "channel_number": {"type": "string", "description": "Channel number"}
                }
            }
        ),
        Tool(
            name="streamtv_create_channel",
            description="Create a new StreamTV channel",
            inputSchema={
                "type": "object",
                "required": ["number", "name"],
                "properties": {
                    "number": {"type": "string", "description": "Channel number (must be unique)"},
                    "name": {"type": "string", "description": "Channel name"},
                    "group": {"type": "string", "description": "Channel group/category"},
                    "enabled": {"type": "boolean", "description": "Whether channel is enabled", "default": True},
                    "logo_path": {"type": "string", "description": "Path to channel logo"},
                    "playout_mode": {"type": "string", "enum": ["continuous", "on_demand"], "default": "continuous"}
                }
            }
        ),
        Tool(
            name="streamtv_update_channel",
            description="Update a StreamTV channel",
            inputSchema={
                "type": "object",
                "required": ["channel_id"],
                "properties": {
                    "channel_id": {"type": "integer", "description": "Channel ID to update"},
                    "number": {"type": "string", "description": "New channel number"},
                    "name": {"type": "string", "description": "New channel name"},
                    "group": {"type": "string", "description": "New channel group"},
                    "enabled": {"type": "boolean", "description": "New enabled status"},
                    "logo_path": {"type": "string", "description": "New logo path"},
                    "playout_mode": {"type": "string", "enum": ["continuous", "on_demand"]}
                }
            }
        ),
        Tool(
            name="streamtv_delete_channel",
            description="Delete a StreamTV channel",
            inputSchema={
                "type": "object",
                "required": ["channel_id"],
                "properties": {
                    "channel_id": {"type": "integer", "description": "Channel ID to delete"}
                }
            }
        ),
        Tool(
            name="streamtv_list_media",
            description="List StreamTV media items",
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {"type": "string", "enum": ["youtube", "archive_org", "pbs", "plex"], "description": "Filter by source"},
                    "skip": {"type": "integer", "description": "Number of items to skip", "default": 0},
                    "limit": {"type": "integer", "description": "Maximum number of items to return", "default": 100}
                }
            }
        ),
        Tool(
            name="streamtv_get_media",
            description="Get a StreamTV media item by ID",
            inputSchema={
                "type": "object",
                "required": ["media_id"],
                "properties": {
                    "media_id": {"type": "integer", "description": "Media item ID"}
                }
            }
        ),
        Tool(
            name="streamtv_add_media",
            description="Add a new media item to StreamTV from URL",
            inputSchema={
                "type": "object",
                "required": ["url"],
                "properties": {
                    "url": {"type": "string", "description": "Media URL (YouTube, Archive.org, PBS, or Plex)"},
                    "title": {"type": "string", "description": "Media title (optional, will be fetched if not provided)"},
                    "description": {"type": "string", "description": "Media description"},
                    "duration": {"type": "integer", "description": "Duration in seconds"},
                    "thumbnail": {"type": "string", "description": "Thumbnail URL"}
                }
            }
        ),
        Tool(
            name="streamtv_delete_media",
            description="Delete a StreamTV media item",
            inputSchema={
                "type": "object",
                "required": ["media_id"],
                "properties": {
                    "media_id": {"type": "integer", "description": "Media item ID to delete"}
                }
            }
        ),
        Tool(
            name="streamtv_list_collections",
            description="List all StreamTV collections",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="streamtv_create_collection",
            description="Create a new StreamTV collection",
            inputSchema={
                "type": "object",
                "required": ["name"],
                "properties": {
                    "name": {"type": "string", "description": "Collection name (must be unique)"},
                    "description": {"type": "string", "description": "Collection description"},
                    "collection_type": {"type": "string", "enum": ["manual", "smart", "multi"], "default": "manual"}
                }
            }
        ),
        Tool(
            name="streamtv_add_to_collection",
            description="Add a media item to a collection",
            inputSchema={
                "type": "object",
                "required": ["collection_id", "media_id"],
                "properties": {
                    "collection_id": {"type": "integer", "description": "Collection ID"},
                    "media_id": {"type": "integer", "description": "Media item ID to add"}
                }
            }
        ),
        Tool(
            name="streamtv_remove_from_collection",
            description="Remove a media item from a collection",
            inputSchema={
                "type": "object",
                "required": ["collection_id", "media_id"],
                "properties": {
                    "collection_id": {"type": "integer", "description": "Collection ID"},
                    "media_id": {"type": "integer", "description": "Media item ID to remove"}
                }
            }
        ),
        Tool(
            name="streamtv_list_schedules",
            description="List StreamTV schedules",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {"type": "integer", "description": "Filter by channel ID"}
                }
            }
        ),
        Tool(
            name="streamtv_get_schedule",
            description="Get a StreamTV schedule by ID",
            inputSchema={
                "type": "object",
                "required": ["schedule_id"],
                "properties": {
                    "schedule_id": {"type": "integer", "description": "Schedule ID"}
                }
            }
        ),
        Tool(
            name="streamtv_create_schedule",
            description="Create a new StreamTV schedule",
            inputSchema={
                "type": "object",
                "required": ["name", "channel_id"],
                "properties": {
                    "name": {"type": "string", "description": "Schedule name"},
                    "channel_id": {"type": "integer", "description": "Channel ID this schedule belongs to"},
                    "keep_multi_part_episodes_together": {"type": "boolean", "default": False},
                    "treat_collections_as_shows": {"type": "boolean", "default": False},
                    "shuffle_schedule_items": {"type": "boolean", "default": False},
                    "random_start_point": {"type": "boolean", "default": False}
                }
            }
        ),
        Tool(
            name="streamtv_update_schedule",
            description="Update a StreamTV schedule",
            inputSchema={
                "type": "object",
                "required": ["schedule_id"],
                "properties": {
                    "schedule_id": {"type": "integer", "description": "Schedule ID to update"},
                    "name": {"type": "string", "description": "New schedule name"},
                    "channel_id": {"type": "integer", "description": "New channel ID"},
                    "keep_multi_part_episodes_together": {"type": "boolean"},
                    "treat_collections_as_shows": {"type": "boolean"},
                    "shuffle_schedule_items": {"type": "boolean"},
                    "random_start_point": {"type": "boolean"}
                }
            }
        ),
        Tool(
            name="streamtv_get_playlist",
            description="Get StreamTV M3U playlist",
            inputSchema={
                "type": "object",
                "properties": {
                    "mode": {"type": "string", "enum": ["hls", "ts", "mixed"], "default": "mixed"},
                    "access_token": {"type": "string", "description": "Access token for authentication"}
                }
            }
        ),
        Tool(
            name="streamtv_get_epg",
            description="Get StreamTV XMLTV EPG",
            inputSchema={
                "type": "object",
                "properties": {
                    "access_token": {"type": "string", "description": "Access token for authentication"},
                    "plain": {"type": "boolean", "description": "Return plain XML without XSL stylesheet", "default": True}
                }
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""
    try:
        tool_func = getattr(tools, name, None)
        if not tool_func:
            return [TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]
        
        result = await tool_func(**arguments)
        return [TextContent(
            type="text",
            text=str(result)
        )]
    except Exception as e:
        logger.error(f"Error calling tool {name}: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]


# Register resources
@server.list_resources()
async def list_resources() -> list[Resource]:
    """List all available StreamTV resources"""
    resource_list = await resources.list_resources()
    return [
        Resource(
            uri=item["uri"],
            name=item["name"],
            description=item["description"],
            mimeType="text/markdown"
        )
        for item in resource_list
    ]


@server.read_resource()
async def read_resource(uri: str) -> ReadResourceResult:
    """Read a resource by URI"""
    try:
        resource_data = await resources.get_resource(uri)
        if resource_data:
            return ReadResourceResult(
                contents=[
                    TextResourceContents(
                        uri=uri,
                        text=resource_data["content"],
                        mimeType=resource_data.get("mimeType", "text/plain")
                    )
                ]
            )
        return ReadResourceResult(
            contents=[
                TextResourceContents(
                    uri=uri,
                    text=f"Resource not found: {uri}",
                    mimeType="text/plain"
                )
            ]
        )
    except Exception as e:
        logger.error(f"Error reading resource {uri}: {e}", exc_info=True)
        return ReadResourceResult(
            contents=[
                TextResourceContents(
                    uri=uri,
                    text=f"Error reading resource: {str(e)}",
                    mimeType="text/plain"
                )
            ]
        )


async def main():
    """Main entry point"""
    logger.info("Starting StreamTV MCP Server")
    logger.info(f"StreamTV API URL: {config.base_url}")
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())

