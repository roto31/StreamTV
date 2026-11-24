"""Live-apply Channel Creator MCP fragments to IDE / agent / LLM host configs.

Used by first-run ``POST /api/setup/mcp`` and ``channel_creator_mcp_hosts.zsh --mode apply``.
Remote hosts (ChatGPT / Claude web) cannot be patched in-app — we write operator
checklists under Application Support instead.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

SERVER_KEY = "streamtv-channel-creator"
CLAUDE_RUNTIME_DIRNAME = "mcp-runtime"


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def _backup(path: Path) -> Optional[Path]:
    if not path.is_file():
        return None
    bak = path.with_name(f"{path.name}.bak.{_stamp()}")
    shutil.copy2(path, bak)
    return bak


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return {}
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"{path} root must be a JSON object")
    return data


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _merge_mcp_servers(target: Path, fragment: Dict[str, Any]) -> None:
    incoming = fragment.get("mcpServers")
    if not isinstance(incoming, dict) or not incoming:
        raise ValueError("fragment mcpServers missing or empty")
    _backup(target)
    base = _read_json(target) if target.is_file() else {}
    servers = base.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        raise ValueError(f"{target}: mcpServers is not an object")
    servers.update(incoming)
    _write_json(target, base)


def _merge_vscode_servers(target: Path, fragment: Dict[str, Any]) -> None:
    incoming = fragment.get("servers")
    if not isinstance(incoming, dict) or not incoming:
        # Accept mcpServers-shaped fragments too.
        incoming = fragment.get("mcpServers")
        if isinstance(incoming, dict) and incoming:
            incoming = {
                name: {**cfg, "type": cfg.get("type", "stdio")}
                for name, cfg in incoming.items()
                if isinstance(cfg, dict)
            }
        else:
            raise ValueError("VS Code fragment servers/mcpServers missing")
    _backup(target)
    base = _read_json(target) if target.is_file() else {}
    servers = base.setdefault("servers", {})
    if not isinstance(servers, dict):
        raise ValueError(f"{target}: servers is not an object")
    servers.update(incoming)
    _write_json(target, base)


def _home() -> Path:
    return Path(os.path.expanduser("~"))


def _appsupport_streamtv() -> Path:
    return _home() / "Library" / "Application Support" / "StreamTV"


def _path_is_tcc_risky(path: Path) -> bool:
    """External volumes / non-home paths often fail Claude Desktop TCC (Errno 1)."""
    try:
        resolved = path.resolve()
    except OSError:
        return True
    home = _home().resolve()
    try:
        resolved.relative_to(home)
        return False
    except ValueError:
        return True


def ensure_claude_safe_runtime(repo: Path) -> Tuple[Path, Path]:
    """Build/refresh a home-local MCP runtime Claude Desktop can execute.

    Returns ``(python_bin, cwd)`` under
    ``~/Library/Application Support/StreamTV/mcp-runtime``.
    """
    runtime = _appsupport_streamtv() / CLAUDE_RUNTIME_DIRNAME
    venv = runtime / "venv"
    python = venv / "bin" / "python"
    src_pkg = repo / "mcp_streamtv"
    if not src_pkg.is_dir():
        raise FileNotFoundError(f"mcp_streamtv package missing at {src_pkg}")

    runtime.mkdir(parents=True, exist_ok=True)
    # Refresh package copy (Claude cannot import from /Volumes/…).
    dest_pkg = runtime / "mcp_streamtv"
    if dest_pkg.exists():
        shutil.rmtree(dest_pkg)
    shutil.copytree(
        src_pkg,
        dest_pkg,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"),
    )

    brew_py = Path("/opt/homebrew/bin/python3")
    py_create = str(brew_py if brew_py.is_file() else "python3")
    if not python.is_file():
        subprocess.run(
            [py_create, "-m", "venv", str(venv)],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )

    req = repo / "requirements-mcp-streamtv.txt"
    pip = venv / "bin" / "pip"
    cmd = [str(pip), "install", "-q", "-U", "pip"]
    subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=180)
    if req.is_file():
        subprocess.run(
            [str(pip), "install", "-q", "-r", str(req)],
            check=True,
            capture_output=True,
            text=True,
            timeout=300,
        )
    else:
        subprocess.run(
            [str(pip), "install", "-q", "mcp>=2.0.0", "httpx", "pydantic", "pydantic-settings"],
            check=True,
            capture_output=True,
            text=True,
            timeout=300,
        )

    # Claude Desktop often ignores MCP "cwd". Drop a .pth so site-packages
    # always sees mcp_streamtv regardless of process working directory.
    py_ver = subprocess.run(
        [str(python), "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
        capture_output=True,
        text=True,
        timeout=15,
        check=True,
    ).stdout.strip()
    site_pkgs = venv / "lib" / f"python{py_ver}" / "site-packages"
    site_pkgs.mkdir(parents=True, exist_ok=True)
    pth = site_pkgs / "streamtv_mcp_runtime.pth"
    pth.write_text(str(runtime) + "\n", encoding="utf-8")

    # Sanity: import must work from a foreign cwd (Claude Desktop behavior).
    probe = subprocess.run(
        [str(python), "-c", "import mcp_streamtv; print(mcp_streamtv.__file__)"],
        cwd="/tmp",
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if probe.returncode != 0:
        raise RuntimeError(
            f"Claude-safe MCP runtime import failed: {(probe.stderr or probe.stdout)[:400]}"
        )
    logger.info("Claude-safe MCP runtime ready at %s", runtime)
    return python, runtime


def _fragment_for_claude_desktop(fragment: Dict[str, Any], repo: Path) -> Dict[str, Any]:
    """Rewrite stdio command/cwd onto the home-local runtime."""
    python, cwd = ensure_claude_safe_runtime(repo)
    out = json.loads(json.dumps(fragment))  # deep copy via JSON
    servers = out.setdefault("mcpServers", {})
    block = servers.get(SERVER_KEY) or {}
    block["command"] = str(python)
    block["args"] = [
        "-m",
        "mcp_streamtv.main",
        "--profile",
        str((block.get("env") or {}).get("STREAMTV_MCP_PROFILE") or "guided"),
        "--transport",
        "stdio",
    ]
    block["cwd"] = str(cwd)
    env = dict(block.get("env") or {})
    env.setdefault("STREAMTV_BASE_URL", "http://127.0.0.1:8410")
    env.setdefault("STREAMTV_MCP_PROFILE", "guided")
    # Belt-and-suspenders if Claude strips cwd but keeps env.
    env["PYTHONPATH"] = str(cwd)
    block["env"] = env
    servers[SERVER_KEY] = block
    return out


def _write_checklist(host: str, fragment: Dict[str, Any], note: str) -> Path:
    dest_dir = _appsupport_streamtv() / "mcp-host-wiring"
    dest_dir.mkdir(parents=True, exist_ok=True)
    frag_path = dest_dir / f"{host}.json"
    _write_json(frag_path, fragment)
    readme = dest_dir / f"{host}.README.txt"
    readme.write_text(
        note.strip() + "\n\nFragment:\n  " + str(frag_path) + "\n",
        encoding="utf-8",
    )
    return frag_path


def _lmstudio_paths() -> List[Path]:
    """Prefer documented ~/.lmstudio; also patch ~/.cache/lm-studio when present."""
    paths: List[Path] = []
    primary = _home() / ".lmstudio" / "mcp.json"
    cache = _home() / ".cache" / "lm-studio" / "mcp.json"
    paths.append(primary)
    if cache.parent.is_dir() or cache.is_file():
        paths.append(cache)
    return paths


def _cline_settings_candidates() -> List[Path]:
    base = _home() / "Library" / "Application Support"
    rel = Path("User") / "globalStorage" / "saoudrizwan.claude-dev" / "settings" / "cline_mcp_settings.json"
    out: List[Path] = []
    for app in ("Code", "Code - Insiders", "Cursor", "VSCodium"):
        p = base / app / rel
        out.append(p)
    return out


def _continue_config() -> Path:
    return _home() / ".continue" / "config.json"


def _goose_config() -> Path:
    return _home() / ".config" / "goose" / "config.yaml"


def _claude_code_config() -> Path:
    return _home() / ".claude.json"


def apply_one(
    host: str,
    *,
    fragment_path: Path,
    repo: Path,
) -> Dict[str, Any]:
    """Apply one host. Returns result dict with ok/detail/paths."""
    if not fragment_path.is_file():
        return {"host": host, "ok": False, "error": f"missing fragment {fragment_path}"}

    fragment = _read_json(fragment_path)
    applied: List[str] = []

    try:
        if host == "cursor":
            dest = repo / ".cursor" / "mcp.json"
            _backup(dest)
            # Cursor wants mcpServers root — emit already has that shape.
            _write_json(dest, fragment if "mcpServers" in fragment else {"mcpServers": fragment})
            applied.append(str(dest))

        elif host == "vscode":
            dest = repo / ".vscode" / "mcp.json"
            _merge_vscode_servers(dest, fragment)
            applied.append(str(dest))

        elif host == "claude-desktop":
            dest = (
                _home()
                / "Library"
                / "Application Support"
                / "Claude"
                / "claude_desktop_config.json"
            )
            # Claude Desktop TCC blocks /Volumes/… venvs (PermissionError pyvenv.cfg).
            safe = _fragment_for_claude_desktop(fragment, repo)
            _merge_mcp_servers(dest, safe)
            applied.append(str(dest))
            applied.append(str(_appsupport_streamtv() / CLAUDE_RUNTIME_DIRNAME))

        elif host == "claude-code":
            # Prefer CLI when present; always merge ~/.claude.json as fallback/complement.
            dest = _claude_code_config()
            if "mcpServers" in fragment:
                _merge_mcp_servers(dest, fragment)
                applied.append(str(dest))
            cli = shutil.which("claude")
            if cli:
                server = (fragment.get("mcpServers") or {}).get(SERVER_KEY) or {}
                cmd = server.get("command")
                args = server.get("args") or ["-m", "mcp_streamtv.main", "--profile", "guided"]
                if cmd:
                    try:
                        subprocess.run(
                            [cli, "mcp", "add", SERVER_KEY, "--", cmd, *list(args)],
                            cwd=str(repo),
                            capture_output=True,
                            text=True,
                            timeout=60,
                            check=False,
                        )
                        applied.append(f"claude mcp add ({cli})")
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("claude mcp add failed: %s", exc)

        elif host == "lmstudio":
            for dest in _lmstudio_paths():
                _merge_mcp_servers(dest, fragment)
                applied.append(str(dest))

        elif host == "continue":
            # Continue: object map under mcpServers in config.json (newer) + dedicated file.
            dest = _continue_config()
            incoming = fragment.get("mcpServers")
            if isinstance(incoming, dict):
                _merge_mcp_servers(dest, fragment)
                applied.append(str(dest))
            # Also drop a dedicated server file Continue can import.
            dedicated = _home() / ".continue" / "mcpServers" / f"{SERVER_KEY}.json"
            dedicated.parent.mkdir(parents=True, exist_ok=True)
            _write_json(dedicated, fragment)
            applied.append(str(dedicated))

        elif host == "cline":
            wrote = False
            for dest in _cline_settings_candidates():
                # Only write into trees that already exist (extension installed).
                if dest.parent.parent.is_dir() or dest.is_file():
                    _merge_mcp_servers(dest, fragment)
                    applied.append(str(dest))
                    wrote = True
            if not wrote:
                # Seed Cursor globalStorage path (common with StreamTV.app operators).
                dest = _cline_settings_candidates()[2]  # Cursor
                _merge_mcp_servers(dest, fragment)
                applied.append(str(dest))

        elif host == "goose":
            # Goose primarily uses YAML; also write Cursor-shaped mcp.json sidecar.
            sidecar = _home() / ".config" / "goose" / "mcp.json"
            _merge_mcp_servers(sidecar, fragment)
            applied.append(str(sidecar))
            yaml_path = _goose_config()
            server = (fragment.get("mcpServers") or {}).get(SERVER_KEY) or {}
            if server and yaml_path.parent.is_dir():
                note = (
                    f"# StreamTV Channel Creator — add under extensions if not auto-loaded:\n"
                    f"# streamtv-channel-creator:\n"
                    f"#   enabled: true\n"
                    f"#   type: stdio\n"
                    f"#   cmd: {server.get('command')}\n"
                    f"#   args: {json.dumps(server.get('args') or [])}\n"
                    f"#   env: {json.dumps(server.get('env') or {})}\n"
                )
                tip = yaml_path.with_suffix(".streamtv-mcp.tip.txt")
                tip.write_text(note, encoding="utf-8")
                applied.append(str(tip))

        elif host == "open-webui":
            path = _write_checklist(
                host,
                fragment,
                """Open WebUI (loopback MCP):
1) Start MCP HTTP:  python -m mcp_streamtv.main --transport http --host 127.0.0.1 --port 8411 --auth none --profile guided
2) In Open WebUI → Admin → Settings → Tools / MCP, add URL http://127.0.0.1:8411/mcp
3) Do not expose :8411 without auth.""",
            )
            applied.append(str(path))

        elif host in ("chatgpt", "claude-web"):
            path = _write_checklist(
                host,
                fragment,
                f"""{host} is remote — cannot patch the web app from StreamTV first-run.
1) Run MCP HTTP with auth≠none on a tunnel (see CHANNEL_CREATOR_MCP_AUTH.md).
2) Paste MCP URL + auth from the fragment JSON into ChatGPT Developer mode / Claude web connectors.
3) Never put auth=none on a public URL; never tunnel StreamTV :8410.""",
            )
            applied.append(str(path))

        else:
            return {"host": host, "ok": False, "error": f"unknown host {host}"}

    except Exception as exc:  # noqa: BLE001
        logger.exception("apply failed host=%s", host)
        return {"host": host, "ok": False, "error": str(exc), "paths": applied}

    return {"host": host, "ok": True, "paths": applied}


def apply_hosts(
    hosts: List[str],
    *,
    repo: Path,
    out_dir: Path,
    profile: str = "guided",
) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    overall = True
    for host in hosts:
        frag = out_dir / f"{host}.{profile}.json"
        result = apply_one(host, fragment_path=frag, repo=repo)
        results.append(result)
        if not result.get("ok"):
            overall = False
        else:
            logger.info("MCP applied host=%s paths=%s", host, result.get("paths"))
    return {"ok": overall, "hosts": hosts, "results": results}


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    p = argparse.ArgumentParser(description="Apply StreamTV Channel Creator MCP host fragments")
    p.add_argument("--host", required=True, help="host id or comma-separated list")
    p.add_argument("--repo", required=True, type=Path)
    p.add_argument("--out-dir", required=True, type=Path)
    p.add_argument("--profile", default="guided")
    args = p.parse_args(argv)
    hosts = [h.strip() for h in args.host.split(",") if h.strip()]
    result = apply_hosts(hosts, repo=args.repo, out_dir=args.out_dir, profile=args.profile)
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
