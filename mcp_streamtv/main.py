"""StreamTV MCP Server - Main entry point (MCP SDK 1.x and 2.x)."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from typing import Any, Callable, Optional

from .config import config
from . import tools
from . import resources

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Tool name → short description (schemas inferred from function signatures on MCP 2.x)
TOOL_SPECS: list[tuple[str, str]] = [
    ("streamtv_list_channels", "List all StreamTV channels"),
    ("streamtv_get_channel", "Get a StreamTV channel by ID or number"),
    ("streamtv_create_channel", "Create an empty StreamTV channel shell (prefer Builder for content)"),
    ("streamtv_update_channel", "Update a StreamTV channel"),
    ("streamtv_delete_channel", "Delete a StreamTV channel"),
    ("streamtv_list_media", "List StreamTV media items"),
    ("streamtv_get_media", "Get a StreamTV media item by ID"),
    ("streamtv_add_media", "Add a media item from URL"),
    ("streamtv_delete_media", "Delete a StreamTV media item"),
    ("streamtv_list_collections", "List all StreamTV collections"),
    ("streamtv_create_collection", "Create a StreamTV collection"),
    ("streamtv_add_to_collection", "Add a media item to a collection"),
    ("streamtv_remove_from_collection", "Remove a media item from a collection"),
    ("streamtv_list_schedules", "List StreamTV schedules"),
    ("streamtv_get_schedule", "Get a StreamTV schedule by ID"),
    ("streamtv_create_schedule", "Create a StreamTV schedule shell"),
    ("streamtv_update_schedule", "Update a StreamTV schedule"),
    ("streamtv_get_playlist", "Get StreamTV M3U playlist"),
    ("streamtv_get_epg", "Get StreamTV XMLTV EPG"),
    ("streamtv_tunarr_status", "Tunarr sidecar status"),
    ("streamtv_tunarr_search", "Search Tunarr library via StreamTV proxy"),
    ("streamtv_tunarr_custom_shows", "List Tunarr custom shows"),
    ("streamtv_suggest_channel_number", "Suggest the next free numeric channel number"),
    ("builder_list_sources", "List Channel Builder sources (Archive.org, YouTube)"),
    ("builder_auth_status", "Per-source auth configured state"),
    ("builder_auth_check", "Pre-flight which auth scopes URLs require"),
    ("builder_create_draft", "Create a Channel Builder draft"),
    ("builder_get_draft", "Load a Channel Builder draft by id"),
    ("builder_list_drafts", "List Channel Builder drafts"),
    ("builder_update_draft", "Patch draft source, ordering, and/or channel info"),
    (
        "builder_add_links",
        "Add media URLs to a draft (rejects Archive.org *.ia.mp4 derivatives — Issue 24)",
    ),
    ("builder_resolve", "Start async metadata resolution for draft links"),
    ("builder_job_status", "Get Channel Builder job status"),
    ("builder_wait_job", "Poll a Builder job until completed/failed or timeout"),
    ("builder_build", "Compile YAML, import, write schedule, reset playout"),
    ("builder_list_fillers", "List reusable filler collections"),
    ("streamtv_playout_reset", "Reset CONTINUOUS playout anchor; optional stream restart"),
    ("streamtv_stream_restart", "Soft-restart one channel MPEG-TS stream"),
]


def _json_result(result: Any) -> str:
    return json.dumps(result, default=str, indent=2)


async def _run_tool(name: str, arguments: Optional[dict] = None) -> Any:
    tool_func = getattr(tools, name, None)
    if not tool_func:
        raise ValueError(f"Unknown tool: {name}")
    return await tool_func(**(arguments or {}))


def _make_tool_wrapper(name: str) -> Callable[..., Any]:
    """Bind tool name so MCPServer can introspect the real signature via wrap."""
    original = getattr(tools, name)

    async def _wrapper(**kwargs: Any) -> Any:
        return await original(**kwargs)

    _wrapper.__name__ = name
    _wrapper.__doc__ = original.__doc__
    _wrapper.__annotations__ = getattr(original, "__annotations__", {}).copy()
    # Preserve signature for schema generation
    try:
        import inspect

        _wrapper.__signature__ = inspect.signature(original)  # type: ignore[attr-defined]
    except Exception:
        pass
    return _wrapper


def _run_mcp2() -> None:
    from mcp.server import MCPServer

    server = MCPServer(
        name="streamtv-mcp-server",
        instructions=resources.CHANNEL_INTAKE_PROMPT,
    )

    for name, description in TOOL_SPECS:
        if not hasattr(tools, name):
            logger.warning("Skipping missing tool: %s", name)
            continue
        server.add_tool(
            _make_tool_wrapper(name),
            name=name,
            description=description,
            structured_output=True,
        )

    @server.resource(
        "streamtv://prompts/channel-intake",
        name="Channel Creator Intake",
        description="Search vs paste-links intake prompt",
        mime_type="text/markdown",
    )
    async def _intake_resource() -> str:
        return resources.CHANNEL_INTAKE_PROMPT

    # Register remaining file-backed resources
    for uri, loader in resources.RESOURCES.items():
        if uri == "streamtv://prompts/channel-intake":
            continue
        mime = "text/markdown"
        if "schema" in uri:
            mime = "application/json"
        elif "example" in uri or "config" in uri:
            mime = "text/yaml"

        def _bind(resource_uri: str, load_fn: Callable) -> Callable[[], Any]:
            async def _reader() -> str:
                data = await load_fn()
                if not data:
                    return f"Resource not found: {resource_uri}"
                return data.get("content") or ""

            return _reader

        server.resource(
            uri,
            name=uri.split("://")[-1].replace("/", " ").title(),
            description=f"StreamTV {uri.split('://')[-1]}",
            mime_type=mime,
        )(_bind(uri, loader))

    @server.prompt(
        name="channel_intake",
        description="Effortless Search vs Paste Links intake for creating a StreamTV channel",
    )
    async def channel_intake() -> str:
        return resources.CHANNEL_INTAKE_PROMPT

    logger.info("Starting StreamTV MCP Server (MCP 2.x)")
    logger.info("StreamTV API URL: %s", config.base_url)
    server.run(transport="stdio")


def _run_mcp1() -> None:
    """Legacy mcp.server.Server decorator API (SDK 1.x)."""
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp.types import (
            Tool,
            TextContent,
            Resource,
            ReadResourceResult,
            TextResourceContents,
        )
    except ImportError:
        logging.error("MCP SDK not installed. Install with: pip install mcp")
        sys.exit(1)

    try:
        from mcp.types import Prompt, PromptMessage, GetPromptResult

        has_prompts = True
    except ImportError:
        has_prompts = False

    server = Server("streamtv-mcp-server")

    # Minimal input schemas — prefer MCP 2.x for full signature inference
    empty = {"type": "object", "properties": {}}

    @server.list_tools()
    async def list_tools() -> list:
        out = []
        for name, description in TOOL_SPECS:
            out.append(Tool(name=name, description=description, inputSchema=empty))
        return out

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list:
        try:
            result = await _run_tool(name, arguments)
            return [TextContent(type="text", text=_json_result(result))]
        except Exception as e:
            logger.error("Error calling tool %s: %s", name, e, exc_info=True)
            return [TextContent(type="text", text=f"Error: {e}")]

    @server.list_resources()
    async def list_resources() -> list:
        resource_list = await resources.list_resources()
        return [
            Resource(
                uri=item["uri"],
                name=item["name"],
                description=item["description"],
                mimeType=item.get("mimeType", "text/markdown"),
            )
            for item in resource_list
        ]

    @server.read_resource()
    async def read_resource(uri: str) -> ReadResourceResult:
        try:
            resource_data = await resources.get_resource(uri)
            if resource_data:
                return ReadResourceResult(
                    contents=[
                        TextResourceContents(
                            uri=uri,
                            text=resource_data["content"],
                            mimeType=resource_data.get("mimeType", "text/plain"),
                        )
                    ]
                )
            return ReadResourceResult(
                contents=[
                    TextResourceContents(
                        uri=uri,
                        text=f"Resource not found: {uri}",
                        mimeType="text/plain",
                    )
                ]
            )
        except Exception as e:
            logger.error("Error reading resource %s: %s", uri, e, exc_info=True)
            return ReadResourceResult(
                contents=[
                    TextResourceContents(
                        uri=uri,
                        text=f"Error reading resource: {e}",
                        mimeType="text/plain",
                    )
                ]
            )

    if has_prompts:

        @server.list_prompts()
        async def list_prompts() -> list:
            return [
                Prompt(
                    name="channel_intake",
                    description="Effortless Search vs Paste Links intake for creating a StreamTV channel",
                    arguments=[],
                )
            ]

        @server.get_prompt()
        async def get_prompt(name: str, arguments: Any = None):
            if name != "channel_intake":
                raise ValueError(f"Unknown prompt: {name}")
            return GetPromptResult(
                description="StreamTV channel creator intake",
                messages=[
                    PromptMessage(
                        role="user",
                        content=TextContent(
                            type="text", text=resources.CHANNEL_INTAKE_PROMPT
                        ),
                    )
                ],
            )

    async def _main() -> None:
        logger.info("Starting StreamTV MCP Server (MCP 1.x)")
        logger.info("StreamTV API URL: %s", config.base_url)
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )

    asyncio.run(_main())


def main() -> None:
    try:
        from mcp.server import MCPServer  # noqa: F401

        _run_mcp2()
    except ImportError:
        _run_mcp1()
    except AttributeError:
        # Older packaging where Server existed but MCPServer did not
        _run_mcp1()


if __name__ == "__main__":
    main()
