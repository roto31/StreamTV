"""Apply Channel Creator MCP host wiring non-interactively (first-run API)."""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from .mcp_apply_hosts import apply_hosts
from .mcp_offer import validate_host_ids

logger = logging.getLogger(__name__)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _emit_fragments(root: Path, hosts: List[str], profile: str) -> Dict[str, Any]:
    """Ensure generated JSON fragments exist (channel_creator_mcp_hosts.zsh emit)."""
    script = root / "scripts" / "channel_creator_mcp_hosts.zsh"
    if not script.is_file():
        return {"ok": False, "error": f"Missing {script}"}

    env = os.environ.copy()
    env["STREAMTV_MCP_SKIP_SMOKE"] = "1"
    results: List[Dict[str, Any]] = []
    overall = True
    for host in hosts:
        cmd = [
            "zsh",
            str(script),
            "--host",
            host,
            "--mode",
            "emit",
            "--profile",
            profile,
        ]
        proc = subprocess.run(
            cmd,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
            env=env,
        )
        ok = proc.returncode == 0
        if not ok:
            overall = False
            logger.error(
                "MCP emit failed host=%s rc=%s stderr=%s",
                host,
                proc.returncode,
                (proc.stderr or "")[:500],
            )
        results.append(
            {
                "host": host,
                "ok": ok,
                "returncode": proc.returncode,
                "stdout": (proc.stdout or "")[-1500:],
                "stderr": (proc.stderr or "")[-1500:],
            }
        )
    return {"ok": overall, "results": results}


def apply_mcp_hosts(hosts: List[str], *, profile: str = "guided") -> Dict[str, Any]:
    selected = validate_host_ids(hosts)
    if not selected:
        return {"ok": False, "error": "No valid MCP hosts selected", "hosts": []}

    root = _repo_root()
    out_dir = root / "scripts" / "channel-creator-mcp" / "generated"

    emit = _emit_fragments(root, selected, profile)
    if not emit.get("ok"):
        return {
            "ok": False,
            "hosts": selected,
            "phase": "emit",
            "emit": emit,
            "error": emit.get("error") or "emit failed",
        }

    applied = apply_hosts(selected, repo=root, out_dir=out_dir, profile=profile)
    return {
        "ok": bool(applied.get("ok")),
        "hosts": selected,
        "phase": "apply",
        "emit": emit,
        "results": applied.get("results") or [],
    }
