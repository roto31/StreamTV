"""Channel Creator MCP host catalog for first-run offer."""

from __future__ import annotations

from typing import Any, Dict, List

# Mirrors scripts/channel_creator_mcp_hosts.zsh HOSTS=
MCP_HOSTS: List[Dict[str, str]] = [
    {"id": "cursor", "label": "Cursor", "group": "IDE"},
    {"id": "vscode", "label": "VS Code", "group": "IDE"},
    {"id": "continue", "label": "Continue", "group": "IDE"},
    {"id": "cline", "label": "Cline", "group": "IDE"},
    {"id": "claude-desktop", "label": "Claude Desktop", "group": "Desktop"},
    {"id": "claude-code", "label": "Claude Code", "group": "Desktop"},
    {"id": "lmstudio", "label": "LM Studio", "group": "Local LLM"},
    {"id": "goose", "label": "Goose", "group": "Local LLM"},
    {"id": "open-webui", "label": "Open WebUI", "group": "Browser"},
    {"id": "chatgpt", "label": "ChatGPT (remote)", "group": "Remote"},
    {"id": "claude-web", "label": "Claude web (remote)", "group": "Remote"},
]


def list_mcp_hosts() -> List[Dict[str, str]]:
    return list(MCP_HOSTS)


def mcp_host_ids() -> List[str]:
    return [h["id"] for h in MCP_HOSTS]


def validate_host_ids(hosts: List[str]) -> List[str]:
    known = set(mcp_host_ids())
    return [h for h in hosts if h in known]
