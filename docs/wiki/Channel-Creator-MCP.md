# Channel Creator MCP

Natural-language channel creation for StreamTV via a stdio **MCP** that drives the
Channel Builder HTTP API. The AI host never needs the streaming/FFmpeg source tree.

## Canonical docs

| Doc | Contents |
|-----|----------|
| [Channel Creator MCP](https://github.com/roto31/StreamTV/blob/main/docs/guides/CHANNEL_CREATOR_MCP.md) | Platform overview, create → tune signal paths, tools, Archive `.ia.mp4` ban |
| [Host wiring](https://github.com/roto31/StreamTV/blob/main/docs/guides/CHANNEL_CREATOR_MCP_HOST_WIRING.md) | **Cursor, VS Code, Claude Desktop, ChatGPT (deferred), local models** — configs + diagrams + all-in-one setup script |
| [Channel Builder](https://github.com/roto31/StreamTV/blob/main/docs/channel-builder.md) | Web/API Builder |
| [ARCHITECTURE.md](https://github.com/roto31/StreamTV/blob/main/ARCHITECTURE.md) | §8 Channel Creator MCP |
| [Soft deploy](https://github.com/roto31/StreamTV/blob/main/docs/guides/SOFT_DEPLOY.md) | Stream restart without uvicorn kickstart |

## Create → tune signal path

```mermaid
flowchart LR
  NL["Natural language"] --> Host["AI host + MCP"]
  Host --> Builder["Builder API"]
  Builder --> YAML["Unified + schedule"]
  YAML --> DB["Import DB"]
  DB --> Playout["ChannelManager"]
  Playout --> Tune["HDHomeRun / IPTV"]
  Tune --> Client["Plex / Emby / Jellyfin"]
```

## Which host to use

```mermaid
flowchart TD
  Start["Want NL channel create"] --> Q{"Where do you work?"}
  Q -->|IDE| CursorOrVS["Cursor or VS Code"]
  Q -->|Desktop chat| Claude["Claude Desktop"]
  Q -->|Offline GPU| Local["Ollama + Continue or Cline"]
  Q -->|ChatGPT| Defer["Deferred — needs HTTPS bridge"]
  CursorOrVS --> Wire["Wire mcp_streamtv stdio"]
  Claude --> Wire
  Local --> Model["Qwen3 32B recommended"]
  Model --> Wire
  Wire --> API["StreamTV on 127.0.0.1:8410"]
```

| Host | Recommended | Config sketch |
|------|-------------|-----------------|
| **Cursor** | Best | MCP servers + skill `streamtv-channel-creator` |
| **VS Code** | Continue or Cline + same MCP | System rule = intake prompt |
| **Claude Desktop** | `claude_desktop_config.json` | Prompt `channel_intake` |
| **Local** | **Qwen3 32B**; Llama 3.3 70B if 40+ GB; Qwen3 8B if tight | Same MCP; stricter “say **build**” |
| **ChatGPT** | Not in this release | Future Actions / remote MCP only |

Full JSON examples and verify steps: [Host wiring guide](https://github.com/roto31/StreamTV/blob/main/docs/guides/CHANNEL_CREATOR_MCP_HOST_WIRING.md).

## Optional all-in-one setup script

```bash
bash scripts/setup_channel_creator_mcp.sh
```

```mermaid
flowchart TD
  Start["setup_channel_creator_mcp.sh"] --> Platform{"Platform menu"}
  Platform --> Mode{"Apply / Dry-run / Emit"}
  Mode --> Shared["Shared entries"]
  Shared --> Path["That platform only"]
```

Prompts for platform and mode (no flags required). See [Host wiring — Setup script](https://github.com/roto31/StreamTV/blob/main/docs/guides/CHANNEL_CREATOR_MCP_HOST_WIRING.md).

## Quick start (any host)

1. Run StreamTV on `http://127.0.0.1:8410`
2. Prefer: `bash scripts/setup_channel_creator_mcp.sh` — or manually `pip install -r requirements-mcp-streamtv.txt`
3. Register `python3 -m mcp_streamtv.main` (cwd = StreamTV checkout, env `STREAMTV_BASE_URL`)
4. Optional: `mcp_archive_org` for Archive discovery
5. Ask to create a channel → answer **Search vs Paste** → confirm shortlist → **build**

## Hard rules

- Prefer Builder over hand-written YAML for new URL-based channels
- **Never** use Archive.org `*.ia.mp4` derivative URLs — canonical
  `…/download/<id>/<file>.mp4` only
- Soft deploy / stream-restart after create — not a full process kickstart for data-only changes
