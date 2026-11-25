"""Optional first-run starter channel packs (Movies / Music / Kids / Sports)."""

from __future__ import annotations

import logging
import os
import re
import shutil
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)

STARTER_NUMBERS = ("9101", "9102", "9103", "9104")

# channel.schema.json stream.type enum — aliases map common authoring mistakes.
_SCHEMA_STREAM_TYPES = frozenset(
    {"event", "bumper", "commercial", "news", "filler", "movie", "episode"}
)
_TYPE_ALIASES = {
    "music_video": "episode",
    "music-video": "episode",
    "musicvideo": "episode",
    "trailer": "commercial",
    "preview": "commercial",
    "ad": "commercial",
    "advertisement": "commercial",
    "promo": "bumper",
    "clip": "filler",
    "short": "filler",
}

CATALOG: list[dict[str, Any]] = [
    {
        "number": "9101",
        "id": "movies",
        "name": "Movies (All Eras)",
        "blurb": "Top-of-genre features across decades from Archive.org, with trailer breaks.",
    },
    {
        "number": "9102",
        "id": "music",
        "name": "Music Videos (Top of Genre)",
        "blurb": "Best-of-genre music videos across eras (Archive-first; YouTube when needed).",
    },
    {
        "number": "9103",
        "id": "kids",
        "name": "Saturday Morning Kids",
        "blurb": "Vintage Saturday-morning cartoon blocks (CBS/ABC style) with commercial breaks.",
    },
    {
        "number": "9104",
        "id": "sports",
        "name": "Greatest Sports",
        "blurb": "Championship games and highlight specials (not Olympic day-part clones).",
    },
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _pack_complete(root: Path) -> bool:
    return all((root / f"channel_{n}.yaml").is_file() for n in STARTER_NUMBERS)


def _candidate_pack_roots() -> list[Path]:
    """Search order for starter pack YAMLs (setup greys out when none found)."""
    roots: list[Path] = []
    env = (os.environ.get("STREAMTV_STARTER_PACKS_DIR") or "").strip()
    if env:
        roots.append(Path(env).expanduser())
    roots.append(Path.cwd() / "data" / "starter_packs")
    roots.append(_repo_root() / "data" / "starter_packs")
    app_support = Path.home() / "Library" / "Application Support" / "StreamTV" / "data" / "starter_packs"
    roots.append(app_support)
    roots.append(Path("/Applications/StreamTV.app/Contents/Resources/data/starter_packs"))
    # Dedupe while preserving order
    seen: set[str] = set()
    out: list[Path] = []
    for root in roots:
        key = str(root)
        if key in seen:
            continue
        seen.add(key)
        out.append(root)
    return out


def find_starter_packs_root() -> Optional[Path]:
    for root in _candidate_pack_roots():
        try:
            if _pack_complete(root):
                return root
        except OSError:
            continue
    return None


def starter_packs_root() -> Path:
    """Preferred pack directory (complete tree if found, else package-relative default)."""
    found = find_starter_packs_root()
    if found is not None:
        return found
    return _repo_root() / "data" / "starter_packs"


def ensure_starter_packs_in_workdir(workdir: Optional[Path] = None) -> Optional[Path]:
    """Copy a complete pack tree into workdir/data/starter_packs when missing.

    LaunchAgent / App Support installs often run with cwd that lacks packs even when
    the app bundle or another tree has them. Seeding un-greys the setup picker.
    """
    wd = Path(workdir) if workdir is not None else Path.cwd()
    dest = wd / "data" / "starter_packs"
    if _pack_complete(dest):
        return dest
    src = find_starter_packs_root()
    if src is None or src.resolve() == dest.resolve():
        return dest if _pack_complete(dest) else None
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)
        logger.info("Seeded starter packs into %s from %s", dest, src)
        return dest
    except OSError as exc:
        logger.warning("Could not seed starter packs into %s: %s", dest, exc)
        return src if _pack_complete(src) else None


@dataclass
class StarterInstallResult:
    ok: bool
    installed: list[str]
    detail: str
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def list_catalog(*, base_url: str = "http://127.0.0.1:8410") -> list[dict[str, Any]]:
    ensure_starter_packs_in_workdir()
    root = starter_packs_root()
    items: list[dict[str, Any]] = []
    for row in CATALOG:
        number = row["number"]
        yaml_path = root / f"channel_{number}.yaml"
        icon_pack = root / "icons" / f"channel_{number}.png"
        available = yaml_path.is_file()
        items.append(
            {
                **row,
                "available": available,
                "unavailable_reason": (
                    None
                    if available
                    else "Starter pack files are missing on this install"
                ),
                "icon_url": (
                    f"{base_url.rstrip('/')}/static/channel_icons/channel_{number}.png"
                    if icon_pack.is_file()
                    or (_repo_root() / "data" / "channel_icons" / f"channel_{number}.png").is_file()
                    or (Path.cwd() / "data" / "channel_icons" / f"channel_{number}.png").is_file()
                    else None
                ),
                "has_pack_icon": icon_pack.is_file(),
            }
        )
    return items


def _copy_icon(number: str, workdir: Path) -> Optional[Path]:
    src = starter_packs_root() / "icons" / f"channel_{number}.png"
    if not src.is_file():
        return None
    dest_dirs = [
        workdir / "data" / "channel_icons",
        _repo_root() / "data" / "channel_icons",
    ]
    written: Optional[Path] = None
    for dest_dir in dest_dirs:
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"channel_{number}.png"
        shutil.copy2(src, dest)
        written = dest
    return written


def _install_schedule(number: str, workdir: Path) -> Path:
    src = starter_packs_root() / "schedules" / f"{number}.yml"
    if not src.is_file():
        raise FileNotFoundError(f"missing schedule {src}")
    dest_dir = workdir / "schedules"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{number}.yml"
    shutil.copy2(src, dest)
    return dest


def _set_build_days(days: int = 3) -> None:
    try:
        from streamtv.config import config

        config.playout.build_days = int(days)
        logger.info("playout.build_days set in-memory to %s", days)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not set build_days=%s: %s", days, exc)


def _coerce_year(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if 1800 <= value <= 2100 else None
    s = str(value).strip()
    m = re.match(r"^(\d{4})$", s)
    if m:
        y = int(m.group(1))
        return y if 1800 <= y <= 2100 else None
    m = re.search(r"(19|20)\d{2}", s)
    if m:
        y = int(m.group(0))
        return y if 1800 <= y <= 2100 else None
    return None


def sanitize_stream_dict(stream: dict[str, Any]) -> dict[str, Any]:
    """Coerce stream fields to channel.schema.json (type enum + integer year)."""
    out = dict(stream)
    raw_type = out.get("type")
    if isinstance(raw_type, str):
        key = raw_type.strip().lower().replace(" ", "_")
        mapped = _TYPE_ALIASES.get(key, key)
        out["type"] = mapped if mapped in _SCHEMA_STREAM_TYPES else "event"
    year = _coerce_year(out.get("year"))
    if year is None:
        out.pop("year", None)
    else:
        out["year"] = year
    return out


def sanitize_channel_doc(doc: dict[str, Any]) -> dict[str, Any]:
    """Return a schema-safe copy of a channel YAML document."""
    channels = []
    for ch in doc.get("channels") or []:
        ch_out = dict(ch)
        streams = ch_out.get("streams") or []
        ch_out["streams"] = [sanitize_stream_dict(s) for s in streams if isinstance(s, dict)]
        channels.append(ch_out)
    out = dict(doc)
    out["channels"] = channels
    return out


def write_sanitized_pack_yaml(src: Path) -> Path:
    """Load pack YAML, sanitize streams, write a temp file for import."""
    raw = yaml.safe_load(src.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"invalid channel YAML root in {src}")
    clean = sanitize_channel_doc(raw)
    fd, name = tempfile.mkstemp(prefix=f"{src.stem}_sanitized_", suffix=".yaml")
    path = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            yaml.safe_dump(clean, fh, sort_keys=False, allow_unicode=True)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return path


async def install_starter_channels(
    numbers: list[str],
    *,
    workdir: Optional[Path] = None,
    db_session: Any = None,
) -> StarterInstallResult:
    """Import selected starter packs into the active StreamTV workdir."""
    wd = workdir or Path.cwd()
    ensure_starter_packs_in_workdir(wd)
    root = starter_packs_root()
    installed: list[str] = []
    errors: list[str] = []

    wanted = [n for n in numbers if n in STARTER_NUMBERS]
    if not wanted:
        return StarterInstallResult(ok=True, installed=[], detail="no channels selected", errors=[])

    from streamtv.importers import import_channels_from_yaml

    for number in wanted:
        yaml_path = root / f"channel_{number}.yaml"
        if not yaml_path.is_file():
            errors.append(f"{number}: pack YAML missing")
            continue
        sanitized: Optional[Path] = None
        try:
            _copy_icon(number, wd)
            _install_schedule(number, wd)
            sanitized = write_sanitized_pack_yaml(yaml_path)
            await import_channels_from_yaml(sanitized, validate=True, db_session=db_session)
            try:
                from streamtv.streaming.channel_manager import channel_manager

                await channel_manager.restart_channel(number)
            except Exception as restart_exc:  # noqa: BLE001
                logger.info("soft-restart deferred for %s: %s", number, restart_exc)
            installed.append(number)
        except Exception as exc:  # noqa: BLE001
            logger.exception("starter install failed for %s", number)
            errors.append(f"{number}: {exc}")
        finally:
            if sanitized is not None:
                try:
                    sanitized.unlink(missing_ok=True)
                except OSError:
                    pass

    if installed:
        _set_build_days(3)

    detail = f"installed={installed}" if installed else "nothing installed"
    if errors:
        detail += f"; errors={errors}"
    ok = bool(installed) and not errors
    return StarterInstallResult(
        ok=ok,
        installed=installed,
        detail=detail,
        errors=errors,
    )
