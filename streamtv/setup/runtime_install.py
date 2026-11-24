"""Universal first-run runtime install (LaunchAgents + workdir validation)."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

APP_SUPPORT = Path.home() / "Library" / "Application Support" / "StreamTV"
TUNARRAM = Path("/Volumes/TunarrRAM")


@dataclass
class WorkdirValidation:
    ok: bool
    workdir: str
    mode: str  # app_support | repo
    detail: str
    has_venv: bool = False
    has_streamtv: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_app_support_workdir() -> Path:
    return APP_SUPPORT


def validate_workdir(path: str | Path, *, mode: str = "repo") -> WorkdirValidation:
    workdir = Path(path).expanduser()
    if not workdir.is_dir():
        return WorkdirValidation(
            ok=False,
            workdir=str(workdir),
            mode=mode,
            detail="directory does not exist — clone or build the repo first (advanced mode)",
        )
    venv_py = workdir / "venv" / "bin" / "python3"
    if not venv_py.is_file():
        venv_py = workdir / "venv" / "bin" / "python"
    has_venv = venv_py.is_file()
    has_pkg = (workdir / "streamtv").is_dir() or (workdir / "streamtv" / "__init__.py").is_file()
    if not has_venv:
        return WorkdirValidation(
            ok=False,
            workdir=str(workdir),
            mode=mode,
            detail="missing venv/bin/python — run: python3 -m venv venv && ./venv/bin/pip install -r requirements.txt",
            has_venv=False,
            has_streamtv=has_pkg,
        )
    if not has_pkg and mode == "repo":
        return WorkdirValidation(
            ok=False,
            workdir=str(workdir),
            mode=mode,
            detail="streamtv package not found in workdir",
            has_venv=True,
            has_streamtv=False,
        )
    return WorkdirValidation(
        ok=True,
        workdir=str(workdir.resolve()),
        mode=mode,
        detail="ok",
        has_venv=True,
        has_streamtv=has_pkg,
    )


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _run_script(script: Path, *args: str, cwd: Optional[Path] = None) -> dict[str, Any]:
    if not script.is_file():
        return {"ok": False, "detail": f"missing {script}"}
    try:
        proc = subprocess.run(
            ["bash", str(script), *args],
            cwd=str(cwd or _repo_root()),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "detail": str(exc)}
    out = ((proc.stdout or "") + (proc.stderr or "")).strip()[-800:]
    return {"ok": proc.returncode == 0, "detail": out or f"exit {proc.returncode}"}


def install_com_streamtv(*, workdir: str | Path) -> dict[str, Any]:
    script = _repo_root() / "scripts" / "install-com-streamtv-launchagent.sh"
    return _run_script(script, "--workdir", str(Path(workdir).expanduser().resolve()))


def install_ytdlp_upgrade_agent() -> dict[str, Any]:
    script = _repo_root() / "scripts" / "install-yt-dlp-upgrade-launchagent.sh"
    return _run_script(script)


def install_tunarr_ram_heal_if_present() -> dict[str, Any]:
    if not TUNARRAM.is_dir():
        return {
            "ok": True,
            "skipped": True,
            "detail": "TunarrRAM not mounted — heal agent skipped (universal default)",
        }
    cache = TUNARRAM / "streamtv-cache"
    cache.mkdir(parents=True, exist_ok=True)
    script = _repo_root() / "scripts" / "install-tunarr-ram-heal-launchagent.sh"
    result = _run_script(script)
    result["cache_dir"] = str(cache)
    return result


def install_runtime(*, workdir: Optional[str] = None, mode: str = "app_support") -> dict[str, Any]:
    """Install core LaunchAgents for a brand-new universal production-like host."""
    if mode == "app_support":
        wd = Path(workdir) if workdir else default_app_support_workdir()
        wd.mkdir(parents=True, exist_ok=True)
        validation = validate_workdir(wd, mode="app_support")
        # App Support may not have streamtv/ tree until DependencySetup copies it —
        # still require venv when installing LaunchAgent.
        if not validation.has_venv:
            return {
                "ok": False,
                "validation": validation.to_dict(),
                "detail": validation.detail,
            }
    else:
        if not workdir:
            return {"ok": False, "detail": "advanced mode requires workdir"}
        validation = validate_workdir(workdir, mode="repo")
        if not validation.ok:
            return {
                "ok": False,
                "validation": validation.to_dict(),
                "detail": validation.detail,
            }
        wd = Path(validation.workdir)

    steps: dict[str, Any] = {"validation": validation.to_dict()}
    steps["com_streamtv"] = install_com_streamtv(workdir=wd)
    steps["ytdlp_upgrade"] = install_ytdlp_upgrade_agent()
    steps["tunarr_ram_heal"] = install_tunarr_ram_heal_if_present()
    ok = bool(steps["com_streamtv"].get("ok")) and bool(steps["ytdlp_upgrade"].get("ok"))
    return {"ok": ok, "workdir": str(wd), "mode": mode, "steps": steps}


def detect_ffmpeg_paths() -> dict[str, Optional[str]]:
    candidates = [
        "/opt/homebrew/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
        shutil.which("ffmpeg"),
    ]
    ffprobe_candidates = [
        "/opt/homebrew/bin/ffprobe",
        "/usr/local/bin/ffprobe",
        shutil.which("ffprobe"),
    ]
    ffmpeg = next((c for c in candidates if c and Path(c).is_file()), None)
    ffprobe = next((c for c in ffprobe_candidates if c and Path(c).is_file()), None)
    return {"ffmpeg_path": ffmpeg, "ffprobe_path": ffprobe}
