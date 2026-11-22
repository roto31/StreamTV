"""Archive.org MCP Server - Main entry point"""

import asyncio
import logging
import sys

# MCP SDK imports
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent, Resource, ReadResourceResult, TextResourceContents
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
server = Server("archive-org-mcp-server")


# Register tools
@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available Archive.org tools"""
    return [
        Tool(
            name="archive_org_search",
            description="Search Archive.org by query",
            inputSchema={
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g., 'collection:tv OR collection:movies')"
                    },
                    "fields": {
                        "type": "string",
                        "description": "Comma-separated list of fields to return"
                    },
                    "rows": {
                        "type": "integer",
                        "description": "Number of results per page (default: 50, max: 10000)",
                        "default": 50
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number (default: 1)",
                        "default": 1
                    },
                    "sort": {
                        "type": "string",
                        "description": "Sort field (e.g., 'downloads desc', 'date desc')"
                    }
                }
            }
        ),
        Tool(
            name="archive_org_browse_collection",
            description="Browse items in an Archive.org collection",
            inputSchema={
                "type": "object",
                "required": ["collection_id"],
                "properties": {
                    "collection_id": {
                        "type": "string",
                        "description": "Collection identifier (e.g., 'tv', 'movies', 'opensource_movies')"
                    }
                }
            }
        ),
        Tool(
            name="archive_org_get_item_metadata",
            description="Get detailed metadata for an Archive.org item",
            inputSchema={
                "type": "object",
                "required": ["identifier"],
                "properties": {
                    "identifier": {
                        "type": "string",
                        "description": "Item identifier (e.g., 'MagnumPI_1980_ABC_Primetime')"
                    }
                }
            }
        ),
        Tool(
            name="archive_org_get_item_files",
            description="Get file list for an Archive.org item",
            inputSchema={
                "type": "object",
                "required": ["identifier"],
                "properties": {
                    "identifier": {
                        "type": "string",
                        "description": "Item identifier"
                    },
                    "format_filter": {
                        "type": "string",
                        "description": "Filter by file format (e.g., 'h264', 'mp4', 'mpeg4')"
                    }
                }
            }
        ),
        Tool(
            name="archive_org_get_stream_url",
            description="Get streaming URL for an Archive.org video file",
            inputSchema={
                "type": "object",
                "required": ["identifier"],
                "properties": {
                    "identifier": {
                        "type": "string",
                        "description": "Item identifier"
                    },
                    "filename": {
                        "type": "string",
                        "description": "Specific filename to stream (optional, will auto-detect if not provided)"
                    }
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
    """List all available Archive.org resources"""
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
    logger.info("Starting Archive.org MCP Server")
    logger.info(f"Base URL: {config.base_url}")
    logger.info(f"Metadata API: {config.metadata_url}")
    logger.info(f"Search API: {config.search_url}")
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())

