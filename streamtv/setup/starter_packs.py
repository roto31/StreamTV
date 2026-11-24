"""Optional first-run starter channel packs (private product; not public sync)."""

from __future__ import annotations

import logging
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

STARTER_NUMBERS = ("9101", "9102", "9103", "9104")

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
        "blurb": "Vintage Saturday-morning style cartoons with short commercial breaks.",
    },
    {
        "number": "9104",
        "id": "sports",
        "name": "Greatest Sports",
        "blurb": "Historic sporting events and films still available on Archive.org.",
    },
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def starter_packs_root() -> Path:
    return _repo_root() / "data" / "starter_packs"


@dataclass
class StarterInstallResult:
    ok: bool
    installed: list[str]
    detail: str
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def list_catalog(*, base_url: str = "http://127.0.0.1:8410") -> list[dict[str, Any]]:
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
                "icon_url": (
                    f"{base_url.rstrip('/')}/static/channel_icons/channel_{number}.png"
                    if icon_pack.is_file()
                    or (_repo_root() / "data" / "channel_icons" / f"channel_{number}.png").is_file()
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


async def install_starter_channels(
    numbers: list[str],
    *,
    workdir: Optional[Path] = None,
    db_session: Any = None,
) -> StarterInstallResult:
    """Import selected starter packs into the active StreamTV workdir."""
    root = starter_packs_root()
    wd = workdir or Path.cwd()
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
        try:
            _copy_icon(number, wd)
            _install_schedule(number, wd)
            await import_channels_from_yaml(yaml_path, validate=True, db_session=db_session)
            try:
                from streamtv.streaming.channel_manager import channel_manager

                await channel_manager.restart_channel(number)
            except Exception as restart_exc:  # noqa: BLE001
                logger.info("soft-restart deferred for %s: %s", number, restart_exc)
            installed.append(number)
        except Exception as exc:  # noqa: BLE001
            logger.exception("starter install failed for %s", number)
            errors.append(f"{number}: {exc}")

    if installed:
        _set_build_days(3)

    detail = f"installed={installed}" if installed else "nothing installed"
    if errors:
        detail += f"; errors={errors}"
    ok = bool(installed) and not errors
    if installed and errors:
        ok = False
    return StarterInstallResult(
        ok=ok if errors else bool(installed) or wanted == [],
        installed=installed,
        detail=detail,
        errors=errors,
    )
