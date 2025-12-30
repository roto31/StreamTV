"""ErsatzTV MCP Server - Main entry point"""

import asyncio
import logging
import sys

# MCP SDK imports
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Resource, TextContent, ReadResourceResult, TextResourceContents
except ImportError:
    # Fallback for older MCP SDK versions
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
    except ImportError:
        logging.error("MCP SDK not installed. Install with: pip install mcp")
        sys.exit(1)

from .config import config
from . import resources

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create MCP server
server = Server("ersatztv-mcp-server")


# Register resources
@server.list_resources()
async def list_resources() -> list[Resource]:
    """List all available ErsatzTV resources"""
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
    logger.info("Starting ErsatzTV MCP Server")
    logger.info(f"GitHub URL: {config.github_url}")
    logger.info(f"Wiki URL: {config.wiki_url}")
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())

