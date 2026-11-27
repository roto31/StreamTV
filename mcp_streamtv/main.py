"""StreamTV MCP Server - Main entry point (MCP SDK 1.x and 2.x)."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from typing import Any, Callable, Optional

from .config import config
from . import tools
from . import resources
from . import guided
from .profiles import (
    DETAIL_TOOLS,
    GUIDED_TOOLS,
    annotations_for,
    resolve_profile,
    tools_for_profile,
)
from .schemas import normalize_schema, schema_from_signature

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Legacy tool name → short description (schemas inferred from function signatures on MCP 2.x)
LEGACY_TOOL_SPECS: list[tuple[str, str]] = [
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

DETAIL_SPECS: list[tuple[str, str]] = [
    ("builder_set_requirements", "Patch draft requirements and template fields"),
    ("builder_discover", "Discover Archive/YouTube candidates for a draft"),
    ("builder_inspect_candidates", "Inspect candidate files/durations"),
    ("builder_classify", "Classify candidates (air date, commercials, tier)"),
    ("builder_add_candidates", "Add candidates into the draft with a role"),
    ("builder_set_contains", "Set multi-program tape contents"),
    ("builder_plan", "Compile a plan preview and plan_token"),
    ("builder_exclude_candidates", "Record exclusions for SOURCES"),
    ("builder_set_break_plan", "Set break groups and rotation"),
    ("builder_validate", "Run gates G1–G6 without writing"),
    ("builder_report", "Write the §5.8 package files"),
    ("discover_youtube", "Ad-hoc YouTube search"),
    ("inspect_youtube_video", "Inspect one YouTube video"),
    ("discover_archive", "Ad-hoc Archive.org search"),
    ("inspect_archive_item", "Inspect one Archive.org item"),
]

# Back-compat alias used by older imports/tests
TOOL_SPECS = list(LEGACY_TOOL_SPECS)


def _all_specs() -> list[tuple[str, str]]:
    return list(guided.GUIDED_SPECS) + list(DETAIL_SPECS) + list(LEGACY_TOOL_SPECS)


def _active_specs(profile: str | None = None) -> list[tuple[str, str]]:
    profile_name = resolve_profile(profile)
    legacy_names = [n for n, _ in LEGACY_TOOL_SPECS]
    allowed = set(tools_for_profile(profile_name, legacy_names=legacy_names))
    # Ensure detail tools are known to tools_for_profile via DETAIL_TOOLS
    return [(n, d) for n, d in _all_specs() if n in allowed]


def _resolve_callable(name: str) -> Any | None:
    if name in guided.GUIDED_IMPL:
        return guided.GUIDED_IMPL[name]
    return getattr(tools, name, None)


def _json_result(result: Any) -> str:
    return json.dumps(result, default=str, indent=2)


async def _run_tool(name: str, arguments: Optional[dict] = None) -> Any:
    tool_func = _resolve_callable(name)
    if not tool_func:
        raise ValueError(f"Unknown tool: {name}")
    return await tool_func(**(arguments or {}))


def _make_tool_wrapper(name: str) -> Callable[..., Any]:
    """Bind tool name so MCPServer can introspect the real signature via wrap."""
    original = _resolve_callable(name)
    if original is None:
        raise ValueError(f"Unknown tool: {name}")

    async def _wrapper(**kwargs: Any) -> Any:
        return await original(**kwargs)

    _wrapper.__name__ = name
    _wrapper.__doc__ = original.__doc__
    _wrapper.__annotations__ = getattr(original, "__annotations__", {}).copy()
    try:
        import inspect

        _wrapper.__signature__ = inspect.signature(original)  # type: ignore[attr-defined]
    except Exception:
        pass
    return _wrapper


def _tool_input_schema(name: str) -> dict[str, Any]:
    fn = _resolve_callable(name)
    if fn is None:
        return {"type": "object", "properties": {}}
    return schema_from_signature(fn)


def build_mcp2_server(profile: str | None = None) -> Any:
    """Construct MCPServer with profile tools (shared by stdio + HTTP)."""
    from mcp.server import MCPServer

    profile_name = resolve_profile(profile)
    specs = _active_specs(profile_name)
    if profile_name == "full":
        logger.warning(
            "MCP profile=full exposes %s tools — may exceed Cursor's ~40 tool cap",
            len(specs),
        )

    server = MCPServer(
        name="streamtv-mcp-server",
        instructions=resources.CHANNEL_INTAKE_PROMPT,
    )

    for name, description in specs:
        if _resolve_callable(name) is None:
            logger.warning("Skipping missing tool: %s", name)
            continue
        kwargs: dict[str, Any] = {
            "name": name,
            "description": description[:400],
            "structured_output": True,
        }
        ann = annotations_for(name)
        try:
            server.add_tool(_make_tool_wrapper(name), annotations=ann, **kwargs)
        except TypeError:
            server.add_tool(_make_tool_wrapper(name), **kwargs)

    @server.resource(
        "streamtv://prompts/channel-intake",
        name="Channel Creator Intake",
        description="Search vs paste-links intake prompt",
        mime_type="text/markdown",
    )
    async def _intake_resource() -> str:
        return resources.CHANNEL_INTAKE_PROMPT

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

    @server.prompt(name="channel_intake", description="Channel Creator intake v2")
    async def channel_intake() -> str:
        return resources.CHANNEL_INTAKE_PROMPT

    @server.prompt(
        name="channel_intake_expert",
        description="Expert-only Channel Creator intake",
    )
    async def channel_intake_expert() -> str:
        return resources.CHANNEL_INTAKE_EXPERT

    @server.prompt(
        name="channel_intake_compact",
        description="Compact Channel Creator intake for small-context models",
    )
    async def channel_intake_compact() -> str:
        return resources.CHANNEL_INTAKE_COMPACT

    return server


def _load_jwks(*, inline_json: str = "", url: str = "") -> dict[str, Any]:
    raw = (inline_json or "").strip()
    if raw:
        return json.loads(raw)
    jwks_url = (url or "").strip()
    if not jwks_url:
        return {"keys": []}
    import httpx

    resp = httpx.get(jwks_url, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _load_oauth_jwks() -> tuple[str, dict[str, Any]]:
    """Load OAuth/OIDC JWKS (Auth0, Cloudflare Access as IdP, or custom).

    Returns (resolved_issuer, jwks).
    """
    from .auth_http import resolve_oauth_endpoints

    issuer, jwks_url = resolve_oauth_endpoints(
        provider=config.mcp_oauth_provider,
        team_or_domain=config.mcp_oauth_domain,
        issuer=config.mcp_oauth_issuer,
        jwks_url=config.mcp_oauth_jwks_url,
    )
    return issuer, _load_jwks(inline_json=config.mcp_oauth_jwks_json, url=jwks_url)


def _load_access_jwks() -> tuple[str, str, dict[str, Any]]:
    """Return (issuer, audience, jwks) for Cloudflare Access dual-lock."""
    from .auth_http import resolve_oauth_endpoints

    team = (config.mcp_access_team or config.mcp_oauth_domain or "").strip()
    issuer, jwks_url = resolve_oauth_endpoints(
        provider="cloudflare_access",
        team_or_domain=team,
        issuer=config.mcp_oauth_issuer,
        jwks_url=config.mcp_oauth_jwks_url,
    )
    audience = (config.mcp_access_audience or config.mcp_oauth_audience or "").strip()
    jwks = _load_jwks(inline_json=config.mcp_oauth_jwks_json, url=jwks_url)
    return issuer, audience, jwks


def build_http_app(
    *,
    profile: str | None = None,
    host: str = "127.0.0.1",
    port: int | None = None,
    path: str = "/mcp",
    auth: str = "none",
    bearer_token: str = "",
    allowed_hosts: list[str] | None = None,
    allowed_origins: list[str] | None = None,
) -> Any:
    """Starlette app for Streamable HTTP with auth middleware (§7A)."""
    from mcp.server.transport_security import TransportSecuritySettings
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    from .auth_http import make_auth_middleware, require_bearer_token, validate_bind_auth

    validate_bind_auth(host, auth)
    if auth in ("bearer", "dual"):
        bearer_token = require_bearer_token(bearer_token)

    bind_port = int(port or config.mcp_port or 8411)
    server = build_mcp2_server(profile)
    default_hosts = [
        f"{host}:{bind_port}",
        f"127.0.0.1:{bind_port}",
        f"localhost:{bind_port}",
        "127.0.0.1",
        "localhost",
        "testserver",
    ]
    default_origins = [
        f"http://{host}:{bind_port}",
        f"http://127.0.0.1:{bind_port}",
        f"http://localhost:{bind_port}",
        "http://testserver",
    ]
    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=allowed_hosts or default_hosts,
        allowed_origins=allowed_origins or default_origins,
    )
    mcp_app = server.streamable_http_app(
        streamable_http_path=path,
        transport_security=security,
        host=host,
    )

    oauth_issuer = (config.mcp_oauth_issuer or "").strip()
    oauth_audience = (config.mcp_oauth_audience or "").strip()
    oauth_jwks: dict[str, Any] = {"keys": []}
    access_issuer = ""
    access_audience = ""
    access_jwks: dict[str, Any] = {"keys": []}

    if auth == "oauth":
        oauth_issuer, oauth_jwks = _load_oauth_jwks()
        if not oauth_issuer or not oauth_audience or not (oauth_jwks.get("keys")):
            raise SystemExit(
                "ERROR: oauth mode needs STREAMTV_MCP_OAUTH_ISSUER (or provider+domain), "
                "STREAMTV_MCP_OAUTH_AUDIENCE, and JWKS (URL or STREAMTV_MCP_OAUTH_JWKS_JSON)"
            )
    elif auth == "dual":
        access_issuer, access_audience, access_jwks = _load_access_jwks()
        if not access_issuer or not access_audience or not (access_jwks.get("keys")):
            raise SystemExit(
                "ERROR: dual mode needs Cloudflare Access team "
                "(STREAMTV_MCP_ACCESS_TEAM or STREAMTV_MCP_OAUTH_DOMAIN), "
                "STREAMTV_MCP_ACCESS_AUDIENCE (AUD tag), and reachable Access JWKS "
                "(or STREAMTV_MCP_OAUTH_JWKS_JSON for tests)"
            )

    async def oauth_protected_resource(_request: Any) -> Any:
        return JSONResponse(
            {
                "resource": f"http://{host}:{bind_port}{path}",
                "authorization_servers": [oauth_issuer] if oauth_issuer else [],
                "scopes_supported": ["streamtv.read", "streamtv.write"],
            }
        )

    try:
        mcp_app.routes.append(
            Route("/.well-known/oauth-protected-resource", oauth_protected_resource)
        )
    except Exception:  # noqa: BLE001
        pass

    AuthMW = make_auth_middleware(
        auth=auth,
        bearer_token=bearer_token,
        oauth_issuer=oauth_issuer,
        oauth_audience=oauth_audience,
        oauth_jwks=oauth_jwks,
        access_issuer=access_issuer,
        access_audience=access_audience,
        access_jwks=access_jwks,
    )
    mcp_app.add_middleware(AuthMW)
    return mcp_app


def _run_mcp2_stdio(profile: str | None = None) -> None:
    server = build_mcp2_server(profile)
    profile_name = resolve_profile(profile)
    specs = _active_specs(profile_name)
    logger.info(
        "Starting StreamTV MCP Server (MCP 2.x stdio) profile=%s tools=%s",
        profile_name,
        len(specs),
    )
    logger.info("StreamTV API URL: %s", config.base_url)
    server.run(transport="stdio")


def _run_mcp2_http(
    *,
    profile: str | None,
    host: str,
    port: int,
    path: str,
    auth: str,
    bearer_token: str,
) -> None:
    import uvicorn

    from .auth_http import validate_bind_auth

    validate_bind_auth(host, auth)
    cfg_hosts = [h.strip() for h in config.mcp_allowed_hosts.split(",") if h.strip()]
    cfg_origins = [o.strip() for o in config.mcp_allowed_origins.split(",") if o.strip()]
    # Always allow the actual bind host:port (DNS-rebinding allowlist)
    cfg_hosts = list(
        dict.fromkeys(cfg_hosts + [f"{host}:{port}", f"127.0.0.1:{port}", f"localhost:{port}"])
    )
    cfg_origins = list(
        dict.fromkeys(
            cfg_origins
            + [
                f"http://{host}:{port}",
                f"http://127.0.0.1:{port}",
                f"http://localhost:{port}",
            ]
        )
    )
    app = build_http_app(
        profile=profile,
        host=host,
        port=port,
        path=path,
        auth=auth,
        bearer_token=bearer_token,
        allowed_hosts=cfg_hosts,
        allowed_origins=cfg_origins,
    )
    logger.info(
        "Starting StreamTV MCP Server (streamable-http) %s:%s%s auth=%s profile=%s",
        host,
        port,
        path,
        auth,
        resolve_profile(profile),
    )
    uvicorn.run(app, host=host, port=port, log_level="info")


def _run_mcp1(profile: str | None = None) -> None:
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
    specs = _active_specs(profile)
    schemas = {name: _tool_input_schema(name) for name, _ in specs}

    @server.list_tools()
    async def list_tools() -> list:
        out = []
        for name, description in specs:
            out.append(
                Tool(
                    name=name,
                    description=description[:400],
                    inputSchema=schemas.get(name) or {"type": "object", "properties": {}},
                )
            )
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
                    description="Channel Creator intake v2",
                    arguments=[],
                ),
                Prompt(
                    name="channel_intake_expert",
                    description="Expert intake",
                    arguments=[],
                ),
                Prompt(
                    name="channel_intake_compact",
                    description="Compact intake",
                    arguments=[],
                ),
            ]

        @server.get_prompt()
        async def get_prompt(name: str, arguments: Any = None):
            mapping = {
                "channel_intake": resources.CHANNEL_INTAKE_PROMPT,
                "channel_intake_expert": resources.CHANNEL_INTAKE_EXPERT,
                "channel_intake_compact": resources.CHANNEL_INTAKE_COMPACT,
            }
            if name not in mapping:
                raise ValueError(f"Unknown prompt: {name}")
            return GetPromptResult(
                description="StreamTV channel creator intake",
                messages=[
                    PromptMessage(
                        role="user",
                        content=TextContent(type="text", text=mapping[name]),
                    )
                ],
            )

    async def _main() -> None:
        logger.info("Starting StreamTV MCP Server (MCP 1.x) profile=%s", resolve_profile(profile))
        logger.info("StreamTV API URL: %s", config.base_url)
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )

    asyncio.run(_main())


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="StreamTV MCP server")
    parser.add_argument(
        "--profile",
        default=None,
        choices=["guided", "planner", "builder", "full"],
        help="Tool profile (default: guided / STREAMTV_MCP_PROFILE)",
    )
    parser.add_argument(
        "--transport",
        default=None,
        choices=["stdio", "http", "sse", "streamable-http"],
        help="stdio (default) | http/streamable-http | sse",
    )
    parser.add_argument("--host", default=None, help="HTTP bind host (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=None, help="HTTP port (default 8411)")
    parser.add_argument("--path", default=None, help="HTTP MCP path (default /mcp)")
    parser.add_argument(
        "--auth",
        default=None,
        choices=["none", "bearer", "oauth", "dual"],
        help="HTTP auth: none|bearer|oauth|dual (Access JWT + MCP token)",
    )
    args, _unknown = parser.parse_known_args(argv)

    transport = (
        args.transport
        or config.mcp_transport
        or "stdio"
    ).strip().lower()
    if transport == "http":
        transport = "streamable-http"
    profile = args.profile or config.mcp_profile or None
    host = args.host or config.mcp_host or "127.0.0.1"
    port = int(args.port or config.mcp_port or 8411)
    path = args.path or config.mcp_path or "/mcp"
    auth = (args.auth or config.mcp_auth or "none").strip().lower()

    try:
        from mcp.server import MCPServer  # noqa: F401
    except ImportError:
        if transport != "stdio":
            logger.error("SDK 2.x (MCPServer) required for --transport http; pin mcp>=2")
            sys.exit(2)
        _run_mcp1(profile)
        return

    if transport == "stdio":
        try:
            _run_mcp2_stdio(profile)
        except AttributeError:
            _run_mcp1(profile)
        return

    if transport == "sse":
        server = build_mcp2_server(profile)
        server.run(transport="sse", host=host, port=port)
        return

    if transport == "streamable-http":
        _run_mcp2_http(
            profile=profile,
            host=host,
            port=port,
            path=path,
            auth=auth,
            bearer_token=config.mcp_token or "",
        )
        return

    logger.error("Unknown transport: %s", transport)
    sys.exit(2)


if __name__ == "__main__":
    main()
