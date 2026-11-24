"""First-run setup API tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


def test_setup_status(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("STREAMTV_DATA_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    from streamtv.main import app

    client = TestClient(app)
    r = client.get("/api/setup/status")
    assert r.status_code == 200
    body = r.json()
    assert "setup_done" in body
    assert "mcp_hosts" in body
    assert body["current_port"] >= 1


def test_setup_complete_and_factory_reset(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("STREAMTV_DATA_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    # Fresh import path — use existing app
    from streamtv.setup import first_run_state as frs
    from streamtv.setup import plex_codecs as plex_mod
    from streamtv.main import app

    # Do not block complete on this host's real Plex install during unit tests
    monkeypatch.setattr(
        plex_mod,
        "verify_aac_codecs",
        lambda home=None: plex_mod.PlexCodecStatus(
            detected=False,
            ok=True,
            detail="skip",
            codecs_root="/tmp",
            skipped=True,
        ),
    )

    client = TestClient(app)
    # clear any markers in tmp
    frs.clear_setup_done()
    r = client.post("/api/setup/complete")
    assert r.status_code == 200
    assert r.json()["setup_done"] is True
    assert (tmp_path / frs.SETUP_DONE_FILENAME).is_file()

    r2 = client.post("/api/setup/factory-reset", json={"confirm": True})
    assert r2.status_code == 200
    assert r2.json()["setup_done"] is False


def test_setup_complete_blocks_when_plex_codecs_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("STREAMTV_DATA_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    from streamtv.setup import first_run_state as frs
    from streamtv.setup import plex_codecs as plex_mod
    from streamtv.main import app

    frs.clear_setup_done()
    monkeypatch.setattr(
        plex_mod,
        "verify_aac_codecs",
        lambda home=None: plex_mod.PlexCodecStatus(
            detected=True,
            ok=False,
            detail="missing libaac_decoder.dylib",
            codecs_root="/tmp/Codecs",
            build_hint="deadbeef",
        ),
    )
    # setup.py imports verify_aac_codecs into its namespace
    import streamtv.api.setup as setup_api

    monkeypatch.setattr(
        setup_api,
        "verify_aac_codecs",
        lambda home=None: plex_mod.PlexCodecStatus(
            detected=True,
            ok=False,
            detail="missing libaac_decoder.dylib",
            codecs_root="/tmp/Codecs",
            build_hint="deadbeef",
        ),
    )

    client = TestClient(app)
    r = client.post("/api/setup/complete")
    assert r.status_code == 409
    detail = r.json()["detail"]
    assert detail["error"] == "plex_codecs_missing"
    assert frs.is_setup_done() is False


def test_setup_status_includes_plex_and_ytdlp(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("STREAMTV_DATA_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    from streamtv.main import app

    client = TestClient(app)
    r = client.get("/api/setup/status")
    assert r.status_code == 200
    body = r.json()
    assert "plex_codecs" in body
    assert "yt_dlp" in body
    assert "detected" in body["plex_codecs"]
    assert "ok" in body["yt_dlp"]


def test_updates_status() -> None:
    from streamtv.main import app

    client = TestClient(app)
    r = client.get("/api/updates/status")
    assert r.status_code == 200
    body = r.json()
    assert "current_version" in body
    assert "install_mode" in body


def test_apply_mcp_hosts_claude_desktop_merge(tmp_path: Path, monkeypatch) -> None:
    """Regression: apply must merge into Claude Desktop config, not only emit JSON."""
    import json

    from streamtv.setup import mcp_runner

    fake_home = tmp_path / "home"
    claude_dir = fake_home / "Library" / "Application Support" / "Claude"
    claude_dir.mkdir(parents=True)
    live = claude_dir / "claude_desktop_config.json"
    live.write_text(json.dumps({"preferences": {"sidebarMode": "chat"}}), encoding="utf-8")
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("STREAMTV_MCP_SKIP_SMOKE", "1")

    result = mcp_runner.apply_mcp_hosts(["claude-desktop"])
    assert result["ok"] is True, result
    merged = json.loads(live.read_text(encoding="utf-8"))
    assert "mcpServers" in merged
    assert "streamtv-channel-creator" in merged["mcpServers"]
    assert "preferences" in merged


def test_mcp_apply_all_first_run_hosts(tmp_path: Path, monkeypatch) -> None:
    """Every startup-screen host gets a live apply path (file merge or checklist)."""
    import json

    from streamtv.setup import mcp_apply_hosts, mcp_offer

    fake_home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(fake_home))
    (fake_home / "Library" / "Application Support" / "Claude").mkdir(parents=True)
    (fake_home / ".lmstudio").mkdir(parents=True)
    (fake_home / ".continue").mkdir(parents=True)
    (fake_home / ".config" / "goose").mkdir(parents=True)
    (
        fake_home
        / "Library"
        / "Application Support"
        / "Cursor"
        / "User"
        / "globalStorage"
        / "saoudrizwan.claude-dev"
    ).mkdir(parents=True)

    repo = tmp_path / "repo"
    out = repo / "scripts" / "channel-creator-mcp" / "generated"
    out.mkdir(parents=True)
    (repo / ".cursor").mkdir()
    (repo / ".vscode").mkdir()

    safe_py = fake_home / "Library/Application Support/StreamTV/mcp-runtime/venv/bin/python"
    safe_cwd = fake_home / "Library/Application Support/StreamTV/mcp-runtime"
    safe_py.parent.mkdir(parents=True)
    safe_py.write_text("", encoding="utf-8")

    def _fake_runtime(_repo: Path):
        return safe_py, safe_cwd

    monkeypatch.setattr(mcp_apply_hosts, "ensure_claude_safe_runtime", _fake_runtime)

    stdio_frag = {
        "mcpServers": {
            "streamtv-channel-creator": {
                "command": "/usr/bin/python3",
                "args": ["-m", "mcp_streamtv.main", "--profile", "guided"],
                "cwd": str(repo),
                "env": {"STREAMTV_BASE_URL": "http://127.0.0.1:8410"},
            }
        }
    }
    vscode_frag = {
        "servers": {
            "streamtv-channel-creator": {
                "type": "stdio",
                "command": "/usr/bin/python3",
                "args": ["-m", "mcp_streamtv.main"],
            }
        }
    }
    remote_frag = {"app_url": "https://example.invalid/mcp", "auth": "oauth"}

    for host in mcp_offer.mcp_host_ids():
        if host == "vscode":
            (out / f"{host}.guided.json").write_text(json.dumps(vscode_frag), encoding="utf-8")
        elif host in ("chatgpt", "claude-web", "open-webui"):
            (out / f"{host}.guided.json").write_text(json.dumps(remote_frag), encoding="utf-8")
        else:
            (out / f"{host}.guided.json").write_text(json.dumps(stdio_frag), encoding="utf-8")

    result = mcp_apply_hosts.apply_hosts(
        mcp_offer.mcp_host_ids(),
        repo=repo,
        out_dir=out,
        profile="guided",
    )
    assert result["ok"] is True, result
    by_host = {r["host"]: r for r in result["results"]}
    for host in mcp_offer.mcp_host_ids():
        assert by_host[host]["ok"] is True, by_host[host]
        assert by_host[host].get("paths"), host

    claude = json.loads(
        (fake_home / "Library/Application Support/Claude/claude_desktop_config.json").read_text()
    )["mcpServers"]["streamtv-channel-creator"]
    assert str(safe_py) == claude["command"]
    assert str(safe_cwd) == claude["cwd"]
    assert "streamtv-channel-creator" in json.loads(
        (repo / ".cursor/mcp.json").read_text()
    )["mcpServers"]
    assert "streamtv-channel-creator" in json.loads(
        (repo / ".vscode/mcp.json").read_text()
    )["servers"]
    assert (fake_home / "Library/Application Support/StreamTV/mcp-host-wiring/chatgpt.json").is_file()
