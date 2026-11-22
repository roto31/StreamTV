"""Exact runtimes and source metadata for Channel Creator (§5.9)."""

from __future__ import annotations

import json
import math
import re
from html import unescape
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field


class SourceMetadata(BaseModel):
    """Verbatim-ish source metadata; all fields optional (§5.9.2)."""

    platform: Optional[str] = None
    identifier: Optional[str] = None
    id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    date: Optional[str] = None
    year: Optional[str] = None
    creator: Optional[str] = None
    uploader: Optional[str] = None
    channel: Optional[str] = None
    channel_id: Optional[str] = None
    uploader_id: Optional[str] = None
    subject: list[str] = Field(default_factory=list)
    collection: list[str] = Field(default_factory=list)
    language: Optional[str] = None
    publicdate: Optional[str] = None
    upload_date: Optional[str] = None
    licenseurl: Optional[str] = None
    page_url: Optional[str] = None
    webpage_url: Optional[str] = None
    name: Optional[str] = None
    format: Optional[str] = None
    size: Optional[Any] = None
    length: Optional[Any] = None
    duration_exact: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    tags: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    chapters: list[dict[str, Any]] = Field(default_factory=list)
    view_count: Optional[int] = None
    availability: Optional[str] = None
    thumbnail_source: Optional[str] = None


def parse_archive_length(raw: Any) -> Optional[float]:
    """Parse archive.org ``files[].length`` (seconds or clock string)."""
    if raw is None or raw == "":
        return None
    if isinstance(raw, (int, float)):
        val = float(raw)
        return val if val > 0 else None
    text = str(raw).strip()
    if not text:
        return None
    try:
        val = float(text)
        return val if val > 0 else None
    except ValueError:
        pass
    # H:MM:SS(.ms) or MM:SS(.ms)
    m = re.match(
        r"^(?:(\d+):)?(\d{1,2}):(\d{1,2}(?:\.\d+)?)$", text
    )
    if not m:
        return None
    hours = int(m.group(1) or 0)
    minutes = int(m.group(2))
    seconds = float(m.group(3))
    total = hours * 3600 + minutes * 60 + seconds
    return total if total > 0 else None


def round_duration_seconds(exact: float) -> int:
    """Half-up round to whole seconds for YAML runtime / MediaItem.duration."""
    return int(math.floor(exact + 0.5))


def iso_runtime_from_exact(exact: float) -> str:
    seconds = max(1, round_duration_seconds(exact)) if exact > 0 else 1
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    parts: list[str] = []
    if h:
        parts.append(f"{h}H")
    if m:
        parts.append(f"{m}M")
    if s or not parts:
        parts.append(f"{s}S")
    return "PT" + "".join(parts)


def clean_html_description(text: str) -> str:
    no_tags = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", unescape(no_tags)).strip()


def compose_guide_description(
    *,
    air_date: Optional[str],
    air_date_quality: str = "unknown",
    network: Optional[str] = None,
    station: Optional[str] = None,
    source_description: str = "",
    commercials_label: str = "unverified",
) -> str:
    """Build YAML ``description`` for Plex sub-title / desc path (§5.9.3)."""
    cleaned = clean_html_description(source_description)[:1500]
    net_bits = " / ".join(x for x in (network, station) if x)
    if air_date and air_date_quality == "exact":
        # Month D, YYYY
        try:
            y, mo, d = air_date.split("-")
            import calendar

            month = calendar.month_name[int(mo)]
            head = f"Original air date: {month} {int(d)}, {y}."
        except Exception:  # noqa: BLE001
            head = f"Original air date: {air_date}."
    elif air_date and air_date_quality in ("month", "year", "placeholder"):
        try:
            y, mo, _d = air_date.split("-")
            import calendar

            month = calendar.month_name[int(mo)]
            head = f"Air date: about {month} {y} (exact day not listed)."
        except Exception:  # noqa: BLE001
            head = f"Air date: about {air_date} (exact day not listed)."
    else:
        head = "Air date: unknown."

    parts = [head]
    if net_bits:
        parts.append(net_bits + ".")
    if cleaned:
        parts.append(cleaned)
    plain = {
        "yes": "yes",
        "no": "no",
        "label-only": "labeled WOC only",
        "inferred": "inferred from runtime",
        "unverified": "unverified",
        "partial": "partial",
    }.get(commercials_label, commercials_label)
    parts.append(f"Commercials: {plain}.")
    return " ".join(parts)


def yaml_source_metadata_compact(meta: SourceMetadata) -> dict[str, Any]:
    """Compact copy for channel YAML — drop description and chapters."""
    data = meta.model_dump(exclude_none=True)
    data.pop("description", None)
    data.pop("chapters", None)
    return data


def write_metadata_sidecar(
    package_dir: Path,
    stream_id: str,
    meta: SourceMetadata | dict[str, Any],
) -> Path:
    meta_dir = package_dir / "metadata"
    meta_dir.mkdir(parents=True, exist_ok=True)
    path = meta_dir / f"{stream_id}.json"
    payload = meta.model_dump() if isinstance(meta, SourceMetadata) else meta
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def cache_thumbnail(
    stream_id: str,
    thumbnail_source: str,
    *,
    thumbnails_dir: Path,
    timeout: float = 30.0,
) -> Optional[str]:
    """Download to data/thumbnails/<id>.jpg; convert non-JPEG with Pillow when available."""
    import requests

    thumbnails_dir.mkdir(parents=True, exist_ok=True)
    dest = thumbnails_dir / f"{stream_id}.jpg"
    if dest.exists() and dest.stat().st_size > 0:
        return f"/static/thumbnails/{stream_id}.jpg"
    try:
        resp = requests.get(thumbnail_source, timeout=timeout)
        resp.raise_for_status()
        content = resp.content
        ctype = (resp.headers.get("content-type") or "").lower()
        if "jpeg" in ctype or "jpg" in ctype or thumbnail_source.lower().endswith(
            (".jpg", ".jpeg")
        ):
            dest.write_bytes(content)
            return f"/static/thumbnails/{stream_id}.jpg"
        try:
            from io import BytesIO

            from PIL import Image

            img = Image.open(BytesIO(content))
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            img.save(dest, format="JPEG", quality=85)
            return f"/static/thumbnails/{stream_id}.jpg"
        except Exception:
            return None
    except Exception:
        return None
