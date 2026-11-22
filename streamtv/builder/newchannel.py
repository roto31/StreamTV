"""New-channel-only write path with number safety and rollback (§5.6)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml
from sqlalchemy.orm import Session

from streamtv.builder.gates import GateReport, evaluate_compiled_package
from streamtv.builder.ids import apply_existing_url_ids
from streamtv.builder.paths import repo_root
from streamtv.builder.planner import build_channel_package, dump_yaml
from streamtv.builder.templates import TEMPLATE_EXAMPLE_NUMBERS

logger = logging.getLogger(__name__)


def _default_root() -> Path:
    return repo_root()


ROOT = Path(__file__).resolve().parents[2]  # package checkout (fallback)
DATA_DIR = ROOT / "data"
SCHEDULES_DIR = ROOT / "schedules"
UNIFIED_DIR = DATA_DIR / "unified"
DRAFTS_DIR = DATA_DIR / "builder_drafts"


@dataclass
class NumberConflict:
    number: str
    reasons: list[str] = field(default_factory=list)

    @property
    def free(self) -> bool:
        return not self.reasons


def suggest_next_free_number(
    *,
    preferred: Optional[str] = None,
    db: Optional[Session] = None,
    start_at: int = 2000,
    root: Optional[Path] = None,
) -> str:
    root = Path(root) if root is not None else _default_root()
    if preferred and check_number_free(preferred, db=db, root=root).free:
        return preferred
    n = start_at
    while n < 99999:
        cand = str(n)
        if check_number_free(cand, db=db, root=root).free:
            return cand
        n += 1
    raise RuntimeError("No free channel number found")


def check_number_free(
    number: str,
    *,
    db: Optional[Session] = None,
    root: Optional[Path] = None,
) -> NumberConflict:
    """G5: number must be free in DB, data/, schedules/, unified/."""
    root = Path(root) if root is not None else _default_root()
    conflict = NumberConflict(number=str(number))
    num = str(number)

    if num in TEMPLATE_EXAMPLE_NUMBERS:
        conflict.reasons.append(
            f"channel {num} is a template example — never rebuild "
            "(see docs/builder/CHANNEL_PROCESS_REFERENCE.md)"
        )

    data_dir = root / "data"
    schedules = root / "schedules"
    unified = data_dir / "unified"

    for path in sorted(data_dir.glob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        for ch in data.get("channels") or []:
            if str(ch.get("number")) == num:
                conflict.reasons.append(f"present in {path.name}")
                break

    for name in (
        f"{num}.yml",
        f"{num}.yaml",
        f"mn-olympics-{num}.yml",
        f"mn-olympics-{num}.yaml",
    ):
        if (schedules / name).exists():
            conflict.reasons.append(f"schedule file {name} exists")

    if (unified / f"{num}.channel.yaml").exists():
        conflict.reasons.append(f"unified/{num}.channel.yaml exists")

    if db is not None:
        try:
            from streamtv.database.models import Channel

            row = db.query(Channel).filter(Channel.number == num).first()
            if row is not None:
                conflict.reasons.append("channel row exists in database")
        except Exception as exc:  # noqa: BLE001
            logger.warning("DB number check skipped: %s", exc)

    return conflict


def refuse_edit_existing(number: str) -> str:
    return (
        f"Editing or adding to existing channel {number} is out of scope for "
        "Channel Creator MCP v2. See docs/builder/CHANNEL_PROCESS_REFERENCE.md §9. "
        "Create a new free channel number instead."
    )


@dataclass
class BuildArtifacts:
    number: str
    paths: list[Path] = field(default_factory=list)
    channel_row_id: Optional[int] = None
    manifest_path: Optional[Path] = None


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_new_channel(
    channel_spec: dict[str, Any],
    candidates: list[dict[str, Any]],
    *,
    db: Optional[Session] = None,
    root: Optional[Path] = None,
    enrich_metadata: bool = False,
    guide_title_style: str = "slot",
    import_channel: bool = True,
    dry_run: bool = False,
    skip_availability: bool = False,
    force_fail_gate: Optional[str] = None,
) -> tuple[GateReport, Optional[BuildArtifacts], dict[str, Any]]:
    """Compile + G5 + write data/schedule/unified; import optional; rollback on failure.

    Returns (gate_report, artifacts_or_None, details).
    """
    root = Path(root) if root is not None else _default_root()
    number = str(channel_spec["number"])
    report = GateReport()
    conflict = check_number_free(number, db=db, root=root)
    if not conflict.free:
        report.add(
            "G5",
            False,
            "number in use: " + "; ".join(conflict.reasons)
            + f" — suggest {suggest_next_free_number(db=db, root=root)}",
        )
        return report, None, {"conflict": conflict.reasons}

    report.add("G5", True, f"number {number} is free")

    data_dir = root / "data"
    remapped, reuse_log = apply_existing_url_ids(list(candidates), data_dir)
    if reuse_log:
        report.add(
            "G2",
            True,
            f"D16 reused {len(reuse_log)} existing URL ids",
            level="INFO",
        )

    channel_doc, schedule = build_channel_package(
        channel_spec,
        remapped,
        enrich_metadata=enrich_metadata,
        guide_title_style=guide_title_style,
    )
    compiled = evaluate_compiled_package(
        channel_doc, schedule, skip_availability=skip_availability
    )
    report.results.extend(compiled.results)
    if compiled.failed:
        return report, None, {"compiled_failed": True, "reuse_log": reuse_log}

    if dry_run:
        report.add("G7", True, "dry_run — nothing written")
        return report, None, {
            "channel_yaml": dump_yaml(channel_doc),
            "schedule_yaml": dump_yaml(schedule),
            "reuse_log": reuse_log,
        }

    schedules = root / "schedules"
    unified = data_dir / "unified"
    drafts = data_dir / "builder_drafts"
    drafts.mkdir(parents=True, exist_ok=True)
    schedules.mkdir(parents=True, exist_ok=True)
    unified.mkdir(parents=True, exist_ok=True)

    artifacts = BuildArtifacts(number=number)
    channel_path = data_dir / f"channels_generated_{number}.yaml"
    schedule_path = schedules / f"{number}.yml"
    unified_path = unified / f"{number}.channel.yaml"
    manifest_path = drafts / f"newchannel_{number}.build.json"

    try:
        _write_text(channel_path, dump_yaml(channel_doc))
        artifacts.paths.append(channel_path)
        _write_text(schedule_path, dump_yaml(schedule))
        artifacts.paths.append(schedule_path)

        unified_doc = {
            "channel": {
                "number": number,
                "name": channel_spec["name"],
                "group": channel_spec.get("group"),
                "description": channel_spec.get("description"),
                "enabled": True,
                "playout_mode": "continuous",
            },
            "streams": channel_doc["channels"][0]["streams"],
            "schedule": schedule,
        }
        _write_text(unified_path, dump_yaml(unified_doc))
        artifacts.paths.append(unified_path)

        manifest = {
            "number": number,
            "paths": [str(p) for p in artifacts.paths],
            "reuse_log": reuse_log,
        }
        _write_text(manifest_path, json.dumps(manifest, indent=2) + "\n")
        artifacts.manifest_path = manifest_path
        artifacts.paths.append(manifest_path)

        if force_fail_gate == "G9":
            raise RuntimeError("forced G9 failure (e2e)")  # caught below for rollback

        if import_channel:
            from streamtv.importers import import_channels_from_yaml
            import asyncio

            async def _imp() -> Any:
                return await import_channels_from_yaml(
                    channel_path, validate=True, db_session=db
                )

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    channels = pool.submit(lambda: asyncio.run(_imp())).result()
            else:
                channels = asyncio.run(_imp())
            if channels:
                artifacts.channel_row_id = getattr(channels[0], "id", None)

        report.add("G7", True, "files written")
        report.add("G8", True, "import ok" if import_channel else "import skipped")
        report.add("G9", True, "no rollback needed")
        return report, artifacts, {
            "paths": [str(p) for p in artifacts.paths],
            "reuse_log": reuse_log,
        }

    except Exception as exc:  # noqa: BLE001
        if force_fail_gate:
            logger.warning("newchannel forced failure %s — rolling back", force_fail_gate)
        else:
            logger.exception("newchannel build failed; rolling back")
        rollback_artifacts(artifacts, db=db)
        if force_fail_gate == "G9":
            report.add("G9", False, f"forced failure: {exc}")
        else:
            report.add("G8", False, f"build failed: {exc}")
        report.add("G9" if force_fail_gate != "G9" else "G8", True, "rollback completed")
        report.rolled_back = [str(p) for p in artifacts.paths]
        return report, None, {"error": str(exc), "reuse_log": reuse_log, "rolled_back": True}


def rollback_artifacts(
    artifacts: BuildArtifacts,
    *,
    db: Optional[Session] = None,
) -> None:
    """Delete only files/rows this build created."""
    for path in artifacts.paths:
        try:
            if path.exists():
                path.unlink()
        except Exception as exc:  # noqa: BLE001
            logger.warning("rollback unlink %s: %s", path, exc)
    if artifacts.channel_row_id is not None and db is not None:
        try:
            from streamtv.database.models import Channel

            row = db.query(Channel).filter(Channel.id == artifacts.channel_row_id).first()
            if row is not None:
                db.delete(row)
                db.commit()
        except Exception as exc:  # noqa: BLE001
            logger.warning("rollback DB: %s", exc)
            db.rollback()
