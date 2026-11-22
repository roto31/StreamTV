"""File-backed storage for builder drafts and filler collections."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .models import BuilderDraft, FillerCollection
from .paths import data_dir

ROOT = Path(__file__).resolve().parents[2]


def _drafts_dir() -> Path:
    return data_dir() / "builder_drafts"


def _filler_dir() -> Path:
    return data_dir() / "filler_collections"


DRAFTS_DIR = ROOT / "data" / "builder_drafts"  # fallback for static imports
FILLER_DIR = ROOT / "data" / "filler_collections"


def _ensure_dirs() -> None:
    _drafts_dir().mkdir(parents=True, exist_ok=True)
    _filler_dir().mkdir(parents=True, exist_ok=True)


class DraftStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._base_dir_override = base_dir

    @property
    def base_dir(self) -> Path:
        path = self._base_dir_override or _drafts_dir()
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _path(self, draft_id: str) -> Path:
        return self.base_dir / f"{draft_id}.json"

    def list_ids(self) -> list[str]:
        return sorted(p.stem for p in self.base_dir.glob("*.json"))

    def get(self, draft_id: str) -> Optional[BuilderDraft]:
        path = self._path(draft_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return BuilderDraft.model_validate(data)

    def save(self, draft: BuilderDraft) -> BuilderDraft:
        from datetime import datetime, timezone

        draft.updated_at = datetime.now(timezone.utc).isoformat()
        self._path(draft.id).write_text(
            draft.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return draft

    def delete(self, draft_id: str) -> bool:
        path = self._path(draft_id)
        if path.exists():
            path.unlink()
            return True
        return False


class FillerStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._base_dir_override = base_dir

    @property
    def base_dir(self) -> Path:
        path = self._base_dir_override or _filler_dir()
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _path(self, filler_id: str) -> Path:
        return self.base_dir / f"{filler_id}.json"

    def list_all(self) -> list[FillerCollection]:
        items: list[FillerCollection] = []
        for path in sorted(self.base_dir.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            items.append(FillerCollection.model_validate(data))
        return items

    def get(self, filler_id: str) -> Optional[FillerCollection]:
        path = self._path(filler_id)
        if not path.exists():
            return None
        return FillerCollection.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def save(self, filler: FillerCollection) -> FillerCollection:
        from datetime import datetime, timezone

        filler.updated_at = datetime.now(timezone.utc).isoformat()
        self._path(filler.id).write_text(
            filler.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return filler

    def delete(self, filler_id: str) -> bool:
        path = self._path(filler_id)
        if path.exists():
            path.unlink()
            return True
        return False
