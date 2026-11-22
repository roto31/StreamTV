# Channel Creator MCP — setup helpers

Templates and emitted snippets for wiring `mcp_streamtv` (and optional
`mcp_archive_org`) into AI hosts.

## GitHub one-liner

```bash
curl -fsSL https://raw.githubusercontent.com/roto31/StreamTV/main/scripts/install_channel_creator_mcp.sh | bash
```

Non-interactive (Cursor apply, skip smoke until StreamTV is running):

```bash
curl -fsSL https://raw.githubusercontent.com/roto31/StreamTV/main/scripts/install_channel_creator_mcp.sh \
  | bash -s -- --platform cursor --apply --install-deps --no-smoke
```

## Interactive (existing checkout)

```bash
bash scripts/setup_channel_creator_mcp.sh
```

## Generator / remote checklist

```bash
zsh scripts/channel_creator_mcp_hosts.zsh --host all --mode emit --profile guided
zsh scripts/channel_creator_mcp_remote.zsh   # ChatGPT / Claude web tunnel
```

## Layout

| Path | Purpose |
|------|---------|
| `templates/` | Tracked placeholders (`__REPO_ROOT__`, `__PYTHON__`, `__BASE_URL__`) |
| `generated/` | Local emit output (gitignored; absolute paths) |

## Docs

- Wiki [Host wiring](https://github.com/roto31/StreamTV/wiki/Channel-Creator-MCP-Host-Wiring)
- [Host wiring guide](../../docs/guides/CHANNEL_CREATOR_MCP_HOST_WIRING.md)
- [Channel Creator MCP](../../docs/guides/CHANNEL_CREATOR_MCP.md)
- [HTTP auth](../../docs/guides/CHANNEL_CREATOR_MCP_AUTH.md)
