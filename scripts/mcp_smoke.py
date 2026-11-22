#!/usr/bin/env python3
"""Smoke-test StreamTV MCP over stdio or Streamable HTTP (§7B).

Usage:
  ./venv/bin/python scripts/mcp_smoke.py --transport stdio --profile guided
  ./venv/bin/python scripts/mcp_smoke.py --transport http --url http://127.0.0.1:8411/mcp \\
      --token "$STREAMTV_MCP_TOKEN" --profile guided
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _expect_tools(profile: str) -> set[str]:
    from mcp_streamtv.profiles import tools_for_profile
    from mcp_streamtv.main import LEGACY_TOOL_SPECS

    legacy = [n for n, _ in LEGACY_TOOL_SPECS]
    return set(tools_for_profile(profile, legacy_names=legacy))


async def _smoke_stdio(profile: str) -> dict:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    py = os.environ.get("STREAMTV_MCP_PYTHON") or sys.executable
    params = StdioServerParameters(
        command=py,
        args=["-m", "mcp_streamtv.main", "--profile", profile, "--transport", "stdio"],
        cwd=str(ROOT),
        env={**os.environ, "STREAMTV_MCP_PROFILE": profile},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            tools = await session.list_tools()
            names = [t.name for t in tools.tools]
            guide = await session.call_tool("channel_guide", {"compact": True})
            blob = json.dumps([t.model_dump() if hasattr(t, "model_dump") else t.name for t in tools.tools])
            return {
                "transport": "stdio",
                "init": str(init.serverInfo.name if hasattr(init, "serverInfo") else init),
                "tool_count": len(names),
                "tool_list_chars": len(blob),
                "tools": names,
                "channel_guide_ok": guide is not None,
            }


async def _smoke_http(url: str, profile: str, token: str) -> dict:
    import httpx
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    http_client = httpx.AsyncClient(headers=headers, timeout=30.0)

    async with streamable_http_client(url, http_client=http_client) as streams:
        # SDK may return (read, write) or TransportStreams
        if hasattr(streams, "read"):
            read, write = streams.read, streams.write
        else:
            read, write = streams[0], streams[1]
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            tools = await session.list_tools()
            names = [t.name for t in tools.tools]
            guide = await session.call_tool("channel_guide", {"compact": True})
            blob = json.dumps(
                [t.model_dump() if hasattr(t, "model_dump") else t.name for t in tools.tools]
            )
            result = {
                "transport": "http",
                "url": url,
                "init": str(init.serverInfo.name if hasattr(init, "serverInfo") else init),
                "tool_count": len(names),
                "tool_list_chars": len(blob),
                "tools": names,
                "channel_guide_ok": guide is not None,
            }
    await http_client.aclose()
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="StreamTV MCP smoke test")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--profile", default="guided")
    parser.add_argument("--url", default="http://127.0.0.1:8411/mcp")
    parser.add_argument("--token", default=os.environ.get("STREAMTV_MCP_TOKEN", ""))
    args = parser.parse_args()

    expected = _expect_tools(args.profile)
    try:
        if args.transport == "stdio":
            result = asyncio.run(_smoke_stdio(args.profile))
        else:
            result = asyncio.run(_smoke_http(args.url, args.profile, args.token))
    except Exception as exc:
        print(f"FAIL smoke: {exc}", file=sys.stderr)
        return 1

    got = set(result["tools"])
    missing = sorted(expected - got)
    extra = sorted(got - expected)
    ok = (
        result["channel_guide_ok"]
        and not missing
        and (args.profile != "guided" or result["tool_count"] == 11)
    )
    print(json.dumps({**result, "missing": missing, "extra": extra, "ok": ok}, indent=2))
    if args.profile == "guided" and result["tool_list_chars"] > 16000:
        print("FAIL: guided tools/list exceeds 16000 chars", file=sys.stderr)
        return 1
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
