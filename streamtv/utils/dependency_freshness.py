"""Core dependency freshness checks (yt-dlp, player clients, FFmpeg).

Used at startup (log-only) and by ``scripts/check_core_dependency_freshness.py``.
Does not modify bedrock playback; network lookups are optional and best-effort.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Clients that historically returned googlevideo 403 without a PO-token plugin.
BANNED_YOUTUBE_PLAYER_CLIENTS = frozenset(
    {
        "android_vr",  # Issue 73 / yt-dlp #17456 — GVS 403; removed from yt-dlp defaults
        "web",  # SABR / GVS PO Token required
        "android",
        "ios",
        "mweb",
    }
)

# Preferred primary client after yt-dlp 2026.08 (#17184 visionos).
PREFERRED_PRIMARY_CLIENT = "visionos"


@dataclass
class FreshnessFinding:
    component: str
    status: str  # ok | warn | fail
    detail: str


@dataclass
class FreshnessReport:
    findings: list[FreshnessFinding] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(f.status == "fail" for f in self.findings)

    @property
    def has_warnings(self) -> bool:
        return any(f.status == "warn" for f in self.findings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "has_warnings": self.has_warnings,
            "findings": [
                {"component": f.component, "status": f.status, "detail": f.detail}
                for f in self.findings
            ],
        }


def _calver_tuple(version: str) -> tuple[int, ...]:
    """Parse yt-dlp CalVer ``YYYY.M.D`` / ``YYYY.MM.DD`` for ordering."""
    parts: list[int] = []
    for chunk in version.strip().split("."):
        digits = "".join(c for c in chunk if c.isdigit())
        if digits:
            parts.append(int(digits))
    return tuple(parts) if parts else (0,)


def _version_older(installed: str, minimum: str) -> bool:
    return _calver_tuple(installed) < _calver_tuple(minimum)


def fetch_pypi_yt_dlp_version(timeout_sec: float = 8.0) -> Optional[str]:
    """Return latest yt-dlp version on PyPI, or None if unreachable."""
    url = "https://pypi.org/pypi/yt-dlp/json"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        return str(payload["info"]["version"])
    except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError, OSError):
        return None


def check_yt_dlp_floor() -> FreshnessFinding:
    from streamtv.ffmpeg.constants import YTDLP_MIN_VERSION

    try:
        import yt_dlp

        installed = yt_dlp.version.__version__
    except Exception as exc:  # noqa: BLE001 — report as fail
        return FreshnessFinding(
            "yt-dlp",
            "fail",
            f"not importable: {exc}",
        )

    if _version_older(installed, YTDLP_MIN_VERSION):
        return FreshnessFinding(
            "yt-dlp",
            "fail",
            f"installed {installed} < floor {YTDLP_MIN_VERSION} "
            "(stale wheel is the #1 YouTube fleet failure — Issue 73)",
        )
    return FreshnessFinding(
        "yt-dlp",
        "ok",
        f"installed {installed} meets floor {YTDLP_MIN_VERSION}",
    )


def check_yt_dlp_vs_pypi(*, check_pypi: bool = True) -> FreshnessFinding:
    try:
        import yt_dlp

        installed = yt_dlp.version.__version__
    except Exception as exc:  # noqa: BLE001
        return FreshnessFinding("yt-dlp-pypi", "fail", f"not importable: {exc}")

    if not check_pypi:
        return FreshnessFinding(
            "yt-dlp-pypi",
            "ok",
            "PyPI check skipped",
        )

    latest = fetch_pypi_yt_dlp_version()
    if latest is None:
        return FreshnessFinding(
            "yt-dlp-pypi",
            "warn",
            "could not reach PyPI (offline / blocked) — floor check still applies",
        )
    if _version_older(installed, latest):
        return FreshnessFinding(
            "yt-dlp-pypi",
            "warn",
            f"installed {installed} behind PyPI {latest} — "
            "run scripts/upgrade-yt-dlp-production.sh (or pip install -U yt-dlp)",
        )
    return FreshnessFinding(
        "yt-dlp-pypi",
        "ok",
        f"installed {installed} matches or exceeds PyPI {latest}",
    )


def check_youtube_player_clients() -> FreshnessFinding:
    from streamtv.ffmpeg.constants import YOUTUBE_PLAYER_CLIENTS

    clients = list(YOUTUBE_PLAYER_CLIENTS)
    banned_hit = [c for c in clients if c in BANNED_YOUTUBE_PLAYER_CLIENTS]
    if banned_hit:
        return FreshnessFinding(
            "youtube-player-clients",
            "fail",
            f"banned client(s) in YOUTUBE_PLAYER_CLIENTS: {banned_hit} "
            f"(current={clients}) — Issue 73; needs APPROVED: constants.py change",
        )
    if not clients:
        return FreshnessFinding(
            "youtube-player-clients",
            "fail",
            "YOUTUBE_PLAYER_CLIENTS is empty",
        )
    if clients[0] != PREFERRED_PRIMARY_CLIENT:
        return FreshnessFinding(
            "youtube-player-clients",
            "warn",
            f"primary client is {clients[0]!r}, preferred {PREFERRED_PRIMARY_CLIENT!r} "
            f"(full list={clients})",
        )
    return FreshnessFinding(
        "youtube-player-clients",
        "ok",
        f"clients={clients}",
    )


def check_ffmpeg_present() -> FreshnessFinding:
    path = shutil.which("ffmpeg")
    if not path:
        try:
            from streamtv.config import config

            configured = getattr(config.ffmpeg, "ffmpeg_path", None) or ""
            if configured and shutil.which(configured):
                path = configured
            elif configured:
                path = configured
        except Exception:  # noqa: BLE001
            path = None

    if not path:
        return FreshnessFinding(
            "ffmpeg",
            "warn",
            "ffmpeg not found on PATH / config — playout will fail",
        )

    try:
        proc = subprocess.run(
            [path, "-version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        first = (proc.stdout or proc.stderr or "").splitlines()[:1]
        detail = first[0] if first else path
        return FreshnessFinding("ffmpeg", "ok", detail)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return FreshnessFinding("ffmpeg", "warn", f"{path}: {exc}")


def run_freshness_checks(*, check_pypi: bool = True) -> FreshnessReport:
    report = FreshnessReport()
    report.findings.append(check_yt_dlp_floor())
    report.findings.append(check_yt_dlp_vs_pypi(check_pypi=check_pypi))
    report.findings.append(check_youtube_player_clients())
    report.findings.append(check_ffmpeg_present())
    return report


def log_freshness_at_startup(*, check_pypi: bool = False) -> None:
    """Non-fatal startup probe. PyPI skipped by default (offline-friendly)."""
    try:
        report = run_freshness_checks(check_pypi=check_pypi)
        for finding in report.findings:
            msg = f"dependency freshness [{finding.component}]: {finding.detail}"
            if finding.status == "fail":
                logger.warning(msg)
            elif finding.status == "warn":
                logger.warning(msg)
            else:
                logger.info(msg)
    except Exception as exc:  # noqa: BLE001 — never block startup
        logger.warning("dependency freshness check failed: %s", exc)


def ensure_yt_dlp_current(*, check_pypi: bool = True, upgrade: bool = True) -> dict[str, Any]:
    """First-run helper: verify floor (and optional PyPI), pip -U when needed.

    yt-dlp is venv-only (not DMG-bundled). Compares installed wheel to
    ``YTDLP_MIN_VERSION`` / PyPI tip on the active interpreter.
    """
    from streamtv.ffmpeg.constants import YTDLP_MIN_VERSION

    before_report = run_freshness_checks(check_pypi=check_pypi)
    floor = next((f for f in before_report.findings if f.component == "yt-dlp"), None)
    pypi = next((f for f in before_report.findings if f.component == "yt-dlp-pypi"), None)

    needs_upgrade = bool(floor and floor.status == "fail")
    if check_pypi and pypi and pypi.status == "warn" and "behind PyPI" in pypi.detail:
        needs_upgrade = True

    upgraded = False
    pip_detail = "skipped"
    if upgrade and needs_upgrade:
        try:
            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "-U",
                    f"yt-dlp>={YTDLP_MIN_VERSION}",
                ],
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )
            pip_detail = (proc.stdout or proc.stderr or "").strip()[-500:]
            upgraded = proc.returncode == 0
        except (OSError, subprocess.TimeoutExpired) as exc:
            pip_detail = str(exc)
            upgraded = False

    after_report = run_freshness_checks(check_pypi=False)
    floor_after = next((f for f in after_report.findings if f.component == "yt-dlp"), None)
    ok = bool(floor_after and floor_after.status == "ok")
    return {
        "ok": ok,
        "upgraded": upgraded,
        "needs_upgrade": needs_upgrade,
        "floor": YTDLP_MIN_VERSION,
        "detail": floor_after.detail if floor_after else "yt-dlp check missing",
        "pip_detail": pip_detail,
        "before": before_report.to_dict(),
        "after": after_report.to_dict(),
    }
