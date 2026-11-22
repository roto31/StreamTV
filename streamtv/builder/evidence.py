"""Evidence classification for Channel Creator (CURSOR_PROMPT §5.3)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml

_STATIONS_PATH = Path(__file__).resolve().parent / "data" / "stations.yaml"

_MONTHS = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}

_HOME_VIDEO = re.compile(
    r"\b(VHSRip|DVDRip|retail|cassette bought|official\s+(VHS|DVD)|Blu-?ray)\b",
    re.I,
)
_OFF_AIR = re.compile(r"\b(recorded off|off-air|aired on|as broadcast)\b", re.I)

_COMM_NO = [
    re.compile(
        r"commercials?\s+(have been|were)?\s*(cut|removed|edited out)", re.I
    ),
    re.compile(r"\bno commercials\b", re.I),
    re.compile(r"\bcommercial[- ]free\b", re.I),
    re.compile(r"\bwithout commercials\b", re.I),
]
_COMM_YES = [
    re.compile(r"\bwith (?:original |all |the )?commercials\b", re.I),
    re.compile(r"\boriginal commercials\b", re.I),
    re.compile(r"\bw/\s*commercials\b", re.I),
    re.compile(r"\bincludes?\s+commercials\b", re.I),
    re.compile(r"\bcommercials included\b", re.I),
    re.compile(r"\breplete with commercials\b", re.I),
    re.compile(r"\bcomplete broadcast\b", re.I),
    re.compile(r"\bas broadcast,?\s+with commercials\b", re.I),
    re.compile(
        r"\bfull (?:movie|special|broadcast) with (?:original )?commercials\b",
        re.I,
    ),
]
_COMM_PARTIAL = [
    re.compile(r"\ba bit of commercials\b", re.I),
    re.compile(r"\bsome commercials\b", re.I),
    re.compile(r"\bmost commercials\b", re.I),
    re.compile(r"\bcommercials mostly\b", re.I),
    re.compile(r"\bsome ad breaks are included\b", re.I),
]
_WOC = re.compile(r"\bWOC\b")
_AI = re.compile(r"\bAI[- ]?(?:enhanced|upscaled?)\b|\bupscal", re.I)
_RECORDED_YEAR = re.compile(
    r"recorded (?:on|in)\b.*?\b(20[1-9]\d)\b", re.I | re.S
)

_NETWORK = re.compile(r"\b(CBS|ABC|NBC|FOX|PBS|WB|UPN)\b")
_CALL = re.compile(r"\b([KW][A-Z]{2,3})(?:-TV)?\b")

_SLOT_RANGES = (
    (28 * 60, 32 * 60),
    (56 * 60, 62 * 60),
    (84 * 60, 92 * 60),
    (112 * 60, 122 * 60),
    (168 * 60, 182 * 60),
)


@dataclass
class EvidenceResult:
    commercials: str = "unverified"
    commercials_evidence: Optional[str] = None
    partial: bool = False
    exclusion_reason: Optional[str] = None
    network: Optional[str] = None
    station: Optional[str] = None
    air_date: Optional[str] = None
    air_date_quality: str = "unknown"
    air_date_uncertain: bool = False
    tier: Optional[int] = None
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "commercials": self.commercials,
            "commercials_evidence": self.commercials_evidence,
            "partial": self.partial,
            "exclusion_reason": self.exclusion_reason,
            "network": self.network,
            "station": self.station,
            "air_date": self.air_date,
            "air_date_quality": self.air_date_quality,
            "air_date_uncertain": self.air_date_uncertain,
            "tier": self.tier,
            "notes": list(self.notes),
        }


@lru_cache(maxsize=1)
def _load_stations() -> dict[str, Any]:
    if not _STATIONS_PATH.exists():
        return {"stations": {}, "call_sign_deny": ["WOC"]}
    data = yaml.safe_load(_STATIONS_PATH.read_text(encoding="utf-8")) or {}
    return data


def _clip_evidence(match: re.Match[str], text: str, max_words: int = 15) -> str:
    start = max(0, match.start() - 40)
    end = min(len(text), match.end() + 40)
    phrase = " ".join(text[start:end].split())
    words = phrase.split()
    if len(words) > max_words:
        # Prefer the matched span centered
        mid = " ".join(match.group(0).split())
        return mid if len(mid.split()) <= max_words else " ".join(mid.split()[:max_words])
    return phrase


def _normalize_year(y: int) -> int:
    if y < 100:
        return 1900 + y if y >= 50 else 2000 + y
    return y


def extract_air_date(text: str) -> tuple[Optional[str], str]:
    """Return (ISO date or None, quality)."""
    if not text:
        return None, "unknown"

    # M/D/Y or M-D-Y
    m = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b", text)
    if m:
        mo, day, yr = int(m.group(1)), int(m.group(2)), _normalize_year(int(m.group(3)))
        if 1 <= mo <= 12 and 1 <= day <= 31:
            return f"{yr:04d}-{mo:02d}-{day:02d}", "exact"

    # YYYY-MM-DD or YYYY.MM.DD
    m = re.search(r"\b(19[5-9]\d|20[0-2]\d)[-.](\d{2})[-.](\d{2})\b", text)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}", "exact"

    month_names = "|".join(_MONTHS.keys())
    # Month day, year
    m = re.search(
        rf"\b({month_names})\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})\b",
        text,
        re.I,
    )
    if m:
        mo = _MONTHS[m.group(1).lower()]
        day = int(m.group(2))
        yr = int(m.group(3))
        return f"{yr:04d}-{mo:02d}-{day:02d}", "exact"

    # day Month year
    m = re.search(
        rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({month_names})\s+(\d{{4}})\b",
        text,
        re.I,
    )
    if m:
        day = int(m.group(1))
        mo = _MONTHS[m.group(2).lower()]
        yr = int(m.group(3))
        return f"{yr:04d}-{mo:02d}-{day:02d}", "exact"

    # Month year
    m = re.search(rf"\b({month_names})\s+(\d{{4}})\b", text, re.I)
    if m:
        mo = _MONTHS[m.group(1).lower()]
        yr = int(m.group(2))
        return f"{yr:04d}-{mo:02d}-15", "month"

    # Year only
    m = re.search(r"\b(19[5-9]\d|20[0-2]\d)\b", text)
    if m:
        yr = int(m.group(1))
        return f"{yr:04d}-12-15", "year"

    return None, "unknown"


def extract_network_station(text: str) -> tuple[Optional[str], Optional[str], bool]:
    """Return (network, station, uncertain_affiliation)."""
    data = _load_stations()
    deny = {str(x).upper() for x in (data.get("call_sign_deny") or [])}
    stations = data.get("stations") or {}

    network: Optional[str] = None
    station: Optional[str] = None
    uncertain = False

    # Prefer CALL (NET) or NET/CALL patterns
    m = re.search(r"\b([KW][A-Z]{2,3})\s*\((CBS|ABC|NBC|FOX|PBS)\)", text, re.I)
    if m:
        station = m.group(1).upper()
        network = m.group(2).upper()
    else:
        m = re.search(r"\b(CBS|ABC|NBC|FOX|PBS)\s*/\s*([KW][A-Z]{2,3})\b", text, re.I)
        if m:
            network = m.group(1).upper()
            station = m.group(2).upper()

    if not network:
        nm = _NETWORK.search(text)
        if nm:
            network = nm.group(1).upper()

    if not station:
        for cm in _CALL.finditer(text):
            call = cm.group(1).upper()
            if call in deny:
                continue
            station = call
            break

    if station and station in stations and not network:
        network = stations[station].get("network")

    return network, station, uncertain


def classify_commercials(
    title: str,
    description: str = "",
    *,
    runtime_s: Optional[int] = None,
) -> tuple[str, Optional[str], bool, Optional[str]]:
    """Return (label, evidence, partial, exclusion_reason)."""
    blob = f"{title}\n{description or ''}"
    title_only = title or ""

    if _AI.search(blob):
        return "unverified", None, False, "AI-altered picture"

    if _HOME_VIDEO.search(blob) and not _OFF_AIR.search(blob):
        m = _HOME_VIDEO.search(blob)
        ev = _clip_evidence(m, blob) if m else None
        return "no", ev, False, "home video, not a broadcast"

    for rx in _COMM_NO:
        m = rx.search(blob)
        if m:
            return "no", _clip_evidence(m, blob), False, None

    for rx in _COMM_YES:
        m = rx.search(blob)
        if m:
            return "yes", _clip_evidence(m, blob), False, None

    for rx in _COMM_PARTIAL:
        m = rx.search(blob)
        if m:
            return "yes", "partial", True, None

    if _WOC.search(title_only):
        return "label-only", "WOC", False, None

    if runtime_s is not None:
        for lo, hi in _SLOT_RANGES:
            if lo <= runtime_s <= hi:
                return "inferred", f"runtime {runtime_s}s fits broadcast slot", False, None

    return "unverified", None, False, None


def classify_item(
    title: str,
    description: str = "",
    *,
    runtime_s: Optional[int] = None,
    era_to: Optional[int] = None,
    requirements: Optional[dict[str, Any]] = None,
) -> EvidenceResult:
    """Full evidence pass for one candidate."""
    result = EvidenceResult()
    blob = f"{title}\n{description or ''}"

    # Modern re-recording exclusion (before commercials labeling for report)
    if era_to is not None:
        rm = _RECORDED_YEAR.search(blob)
        if rm and int(rm.group(1)) > era_to + 5:
            result.exclusion_reason = "modern re-recording"
            result.commercials = "unverified"
            return result

    label, evidence, partial, exclusion = classify_commercials(
        title, description, runtime_s=runtime_s
    )
    result.commercials = label
    result.commercials_evidence = evidence
    result.partial = partial
    if exclusion:
        result.exclusion_reason = exclusion

    network, station, uncertain = extract_network_station(blob)
    result.network = network
    result.station = station
    result.air_date_uncertain = uncertain

    air, quality = extract_air_date(blob)
    if air:
        result.air_date = air
        if quality == "month":
            result.air_date_quality = "month"
            result.notes.append("placeholder")
        elif quality == "year":
            result.air_date_quality = "year"
            result.notes.append("placeholder")
        else:
            result.air_date_quality = "exact"
    else:
        result.air_date_quality = "unknown"

    # Station affiliation window
    data = _load_stations()
    stations = data.get("stations") or {}
    if station and station in stations and air:
        year = int(air[:4])
        entry = stations[station]
        vf = entry.get("valid_from")
        vt = entry.get("valid_to")
        if vf is not None and year < int(vf):
            result.air_date_uncertain = True
            result.notes.append("UNCERTAIN station affiliation")
        if vt is not None and year > int(vt):
            result.air_date_uncertain = True
            result.notes.append("UNCERTAIN station affiliation")

    # Tier (basic; full requirements optional)
    req = requirements or {}
    nets = {str(n).upper() for n in (req.get("networks") or [])}
    era = req.get("era") or {}
    era_from = era.get("from")
    era_end = era.get("to")
    complete = not re.search(
        r"\b(partial|excerpts|incomplete|missing)\b", blob, re.I
    )
    in_net = (not nets) or (network is not None and network in nets)
    in_era = True
    if air and (era_from is not None or era_end is not None):
        y = int(air[:4])
        if era_from is not None and y < int(era_from):
            in_era = False
        if era_end is not None and y > int(era_end):
            in_era = False
    if (
        result.exclusion_reason is None
        and label == "yes"
        and not partial
        and in_net
        and in_era
        and complete
        and result.air_date_quality == "exact"
    ):
        result.tier = 1
    elif result.exclusion_reason is None:
        result.tier = 2

    return result
