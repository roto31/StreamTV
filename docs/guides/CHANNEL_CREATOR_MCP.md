# Channel Creator MCP

Natural-language channel creation for StreamTV via the **stdio MCP** in `mcp_streamtv/` (Builder + soft-deploy tools) plus optional `mcp_archive_org/` for Archive.org discovery.

You do **not** need the streaming codebase in the model context. The live Channel Builder API compiles YAML, imports inventory, writes schedules, and resets playout.

## Prerequisites

- StreamTV listening on `http://127.0.0.1:8410` (production: LaunchAgent `com.streamtv`)
- Python deps: `pip install -r requirements-mcp-streamtv.txt` (and archive MCP if used)
- Optional: `STREAMTV_API_KEY` if `api_key_required` is enabled

```bash
export STREAMTV_BASE_URL=http://127.0.0.1:8410
# optional: export STREAMTV_API_KEY=...
```

## Intake UX

Agents must ask (unless URLs are already pasted):

> Search Archive.org and/or YouTube, or paste links you already have?

Then shortlist → confirm → `builder_build`. Full script: MCP resource `streamtv://prompts/channel-intake` or prompt name `channel_intake`. Cursor skill: `.cursor/skills/streamtv-channel-creator/SKILL.md`.

## Cursor

Add to Cursor MCP settings (project or user):

```json
{
  "mcpServers": {
    "streamtv": {
      "command": "python3",
      "args": ["-m", "mcp_streamtv.main"],
      "cwd": "/path/to/StreamTV",
      "env": {
        "STREAMTV_BASE_URL": "http://127.0.0.1:8410"
      }
    },
    "archive-org": {
      "command": "python3",
      "args": ["-m", "mcp_archive_org.main"],
      "cwd": "/path/to/StreamTV"
    }
  }
}
```

Use your checkout path and venv/`python3` as appropriate. Enable the **streamtv-channel-creator** skill when creating channels.

## Claude Desktop

In `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "streamtv": {
      "command": "python3",
      "args": ["-m", "mcp_streamtv.main"],
      "cwd": "/path/to/StreamTV",
      "env": {
        "STREAMTV_BASE_URL": "http://127.0.0.1:8410"
      }
    }
  }
}
```

Use the `channel_intake` prompt or read `streamtv://prompts/channel-intake` at the start of a channel-create chat.

## VS Code (Continue / Cline)

Point the MCP client at the same `python -m mcp_streamtv.main` stdio server and `STREAMTV_BASE_URL`. Attach the intake prompt as a custom instruction or system rule so Search vs Paste is always asked.

## Local models

MCP is model-agnostic. Tool-calling quality drives success.

| Hardware | Recommended model | Notes |
|----------|-------------------|--------|
| ~20–24 GB unified/VRAM | **Qwen3 32B** (`ollama pull qwen3:32b`) | Best default for this multi-step Builder flow |
| ~40+ GB | **Llama 3.3 70B** Q4 | Highest reliability; slower loops |
| ~8–16 GB | **Qwen3 8B** | Usable with stricter confirm gates; one tool call at a time |

Wire **Ollama** or **LM Studio** (tools-capable model) to Continue, Cline, Goose, or Cursor custom models, then attach this MCP the same way as above.

Local-model tips (also in the skill):

- Cap shortlists to 5–10
- Explicit “say **build** to proceed”
- Do not invent URLs or channel numbers on malformed tool args

## Archive.org — never `.ia.mp4` (Issue 24)

Internet Archive **derivative** URLs (`*.ia.mp4`) break compile and Plex tunes
(`LESSONS_LEARNED.md` Issue 24). The Channel Creator must:

1. List item files / metadata and pick a **canonical** `.mp4` (skip `*.ia.mp4`).
2. Pass `https://archive.org/download/<id>/<file>.mp4` (filename path required).
3. Rely on `builder_add_links`, which **raises** if any URL contains `.ia.mp4`.

See Cursor rule `streamtv-channel-creator-mcp.mdc` and skill `streamtv-channel-creator`.

## Builder tools (high level)

| Tool | Role |
|------|------|
| `streamtv_suggest_channel_number` | Next free number |
| `builder_create_draft` / `builder_update_draft` | Draft + channel info |
| `builder_add_links` | URLs (rejects `*.ia.mp4`; playlists expand on resolve) |
| `builder_resolve` / `builder_wait_job` | Metadata resolve |
| `builder_build` / `builder_wait_job` | Compile + import + playout reset |
| `streamtv_stream_restart` / `streamtv_playout_reset` | Soft deploy after create |

Resources: `streamtv://schema/unified-channel`, `streamtv://docs/channel-builder`, minimal YAML examples, stream-id / Archive URL rules.

## Soft deploy

After a successful build, Builder already resets playout. Use `streamtv_stream_restart` only if the stream needs a nudge. Do **not** `launchctl kickstart` for channel-data-only changes. See [SOFT_DEPLOY.md](SOFT_DEPLOY.md).

## ChatGPT (deferred)

Remote ChatGPT Custom GPT / Actions against a LAN `:8410` is **not** supported in this phase. It needs an authenticated HTTPS bridge (tunnel + API key) and must never expose cookies or private channel packs. Track as a follow-up; use Cursor / Claude Desktop / local Ollama clients for now.

## Security

- Keep `STREAMTV_API_KEY` and YouTube/Archive cookies on the operator machine
- Prefer `127.0.0.1` over LAN IPs in sandboxed clients
- Do not paste Netscape cookies into cloud chats
