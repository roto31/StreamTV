"""Parse and merge MediaItem.meta_data for archive scrape + provider enrichment."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

_PROVIDER_SOURCES = frozenset({"tvdb", "tvmaze", "tmdb", "historical", "archive"})


def parse_meta_data(raw: Optional[str]) -> Dict[str, Any]:
    """Parse meta_data JSON into a dict; empty on missing/invalid."""
    if not raw or not str(raw).strip():
        return {}
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def get_enrichment(meta: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Return provider enrichment dict if present.

    Supports nested ``meta['enrichment']`` and legacy flat enricher payloads
    where ``source`` is tvdb|tvmaze|tmdb|historical|archive at the top level.
    """
    if not meta:
        return None
    nested = meta.get("enrichment")
    if isinstance(nested, dict) and nested:
        return nested
    src = str(meta.get("source") or "").lower()
    if src in _PROVIDER_SOURCES:
        return meta
    return None


def get_archive(meta: Dict[str, Any]) -> Dict[str, Any]:
    """Return archive scrape payload, migrating legacy flat scrape if needed."""
    if not meta:
        return {}
    archive = meta.get("archive")
    if isinstance(archive, dict):
        return dict(archive)

    # Nested form without archive key
    if "enrichment" in meta:
        return {}

    # Legacy flat provider-only payload
    src = str(meta.get("source") or "").lower()
    if src in _PROVIDER_SOURCES:
        return {}

    # Legacy flat Archive.org (or other) scrape
    return dict(meta)


def merge_enrichment(existing_raw: Optional[str], enrichment: Dict[str, Any]) -> str:
    """
    Merge provider enrichment into meta_data without wiping archive scrape.

    Returns a JSON string with ``{"archive": {...}, "enrichment": {...}}``.
    """
    meta = parse_meta_data(existing_raw)
    archive = get_archive(meta)
    payload = {
        "archive": archive,
        "enrichment": dict(enrichment) if enrichment else {},
    }
    return json.dumps(payload, default=str)


def has_enrichment(raw: Optional[str]) -> bool:
    """True when meta_data already carries provider enrichment."""
    return get_enrichment(parse_meta_data(raw)) is not None


def _jaccard(a: str, b: str) -> float:
    ta = {t for t in (a or "").lower().split() if t}
    tb = {t for t in (b or "").lower().split() if t}
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def descriptions_conflict(a: str, b: str, *, min_len: int = 40) -> bool:
    """True when both plots are substantial and differ enough to flag."""
    da = (a or "").strip()
    db = (b or "").strip()
    if len(da) < min_len or len(db) < min_len:
        return False
    if da == db:
        return False
    # Prefer length ratio + token overlap
    shorter, longer = (da, db) if len(da) <= len(db) else (db, da)
    if len(longer) > len(shorter) * 1.5 and shorter.lower() in longer.lower():
        return False  # longer is a superset — not a conflict
    return _jaccard(da, db) < 0.55


def prefer_longest_description(
    primary: Dict[str, Any],
    secondary: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Merge two provider payloads: keep longest description; flag conflicts.

    ``primary`` is the preferred source for non-description fields when equal.
    """
    out = dict(primary or {})
    consulted: List[str] = []
    for src in (out.get("source"), (secondary or {}).get("source")):
        if src and src not in consulted:
            consulted.append(str(src))
    out["sources_consulted"] = consulted

    desc_a = str(out.get("description") or "").strip()
    desc_b = str((secondary or {}).get("description") or "").strip() if secondary else ""
    conflicts: List[Dict[str, Any]] = list(out.get("conflicts") or [])

    if secondary:
        # Fill missing fields from secondary
        for key, val in secondary.items():
            if key in ("description", "source", "conflicts", "sources_consulted"):
                continue
            if out.get(key) in (None, "", [], {}):
                out[key] = val
        # Genres: union
        ga = list(out.get("genres") or [])
        gb = list(secondary.get("genres") or [])
        if gb:
            merged = list(ga)
            for g in gb:
                if g and g not in merged:
                    merged.append(g)
            out["genres"] = merged

    if desc_a and desc_b:
        if descriptions_conflict(desc_a, desc_b):
            out["unverified"] = True
            conflicts.append(
                {
                    "field": "description",
                    "a": desc_a[:500],
                    "b": desc_b[:500],
                    "note": (
                        f"sources {(primary or {}).get('source')} vs "
                        f"{(secondary or {}).get('source')}; kept longest"
                    ),
                }
            )
        # Longest description wins for display
        if len(desc_b) > len(desc_a):
            out["description"] = desc_b
            if secondary and secondary.get("source"):
                out["description_source"] = secondary.get("source")
        else:
            out["description"] = desc_a
            out["description_source"] = (primary or {}).get("source")
    elif desc_b and not desc_a:
        out["description"] = desc_b
        out["description_source"] = (secondary or {}).get("source")
    elif desc_a:
        out["description_source"] = (primary or {}).get("source")

    desc_final = str(out.get("description") or "")
    out["description_completeness"] = len(desc_final)
    if conflicts:
        out["conflicts"] = conflicts
        out["unverified"] = True
    else:
        out.setdefault("unverified", False)
    return out


def append_conflict_log(
    row: Dict[str, Any],
    *,
    conflicts_dir: Optional[Path] = None,
) -> Path:
    """Append one conflict/unverified row to dated JSONL under data/enrichment/conflicts."""
    root = Path(__file__).resolve().parents[2]
    out_dir = conflicts_dir or (root / "data" / "enrichment" / "conflicts")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{date.today().isoformat()}.jsonl"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, default=str) + "\n")
    return path


def normalize_cast(credits: Any) -> List[Dict[str, str]]:
    """Normalize TMDB-style credits into ``[{name, role}, ...]``."""
    out: List[Dict[str, str]] = []
    if not isinstance(credits, dict):
        return out
    for person in (credits.get("cast") or [])[:15]:
        name = (person or {}).get("name")
        if name:
            out.append({"name": str(name), "role": "actor"})
    for person in (credits.get("crew") or []):
        job = str((person or {}).get("job") or "").lower()
        name = (person or {}).get("name")
        if name and job in ("director", "writer"):
            out.append({"name": str(name), "role": job})
    return out
