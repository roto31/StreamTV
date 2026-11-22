# Channel Creator MCP — setup helpers

Templates and emitted snippets for wiring `mcp_streamtv` (and optional
`mcp_archive_org`) into AI hosts.

## All-in-one installer

From the StreamTV repo root:

```bash
bash scripts/setup_channel_creator_mcp.sh
```

Interactive flow (no flags required):

1. **Platform** — Cursor / VS Code Continue / Cline / Claude Desktop / Local / ChatGPT
2. **Mode** — Apply / Dry-run / Emit only
3. **Shared entries** — repo path, Python, base URL, Archive MCP, deps

Optional automation flags: `--platform`, `--apply`, `--dry-run`, `--emit-only`,
`--base-url`, `--python`, `--repo-root`, `--with-archive`, `--install-deps`.

## Layout

| Path | Purpose |
|------|---------|
| `templates/` | Tracked placeholders (`__REPO_ROOT__`, `__PYTHON__`, `__BASE_URL__`) |
| `generated/` | Local emit output (gitignored; absolute paths) |

## Docs

- [Host wiring guide](../../docs/guides/CHANNEL_CREATOR_MCP_HOST_WIRING.md)
- [Channel Creator MCP](../../docs/guides/CHANNEL_CREATOR_MCP.md)
