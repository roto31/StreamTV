"""Audience → programming filters and query bias for Channel Creator discovery."""

from __future__ import annotations

import re
from typing import Any

AUDIENCE_DENY: dict[str, re.Pattern[str]] = {
    "kids": re.compile(
        r"\bR[\s-]?rated\b|erotica|softcore|porn|slasher|"
        r"nude|striptease|adult film|XXX|"
        r"late[\s-]?night talk|\bSNL\b|Saturday Night Live",
        re.I,
    ),
    "family": re.compile(
        r"\bR[\s-]?rated\b|erotica|softcore|porn|XXX|nude|striptease",
        re.I,
    ),
}

AUDIENCE_QUERY_TERMS: dict[str, list[str]] = {
    "kids": [
        "kids",
        "children",
        "cartoon",
        "animated special",
        "Saturday morning",
    ],
    "family": [
        "family special",
        "holiday special",
        "variety special",
        "parade",
    ],
    "teens": [
        "teen",
        "after school special",
        "young adult",
    ],
    "adults": [
        "prime time",
        "made for TV movie",
        "Sunday Night Movie",
        "drama special",
    ],
    "general": [],
}

AUDIENCE_TO_TEMPLATE: dict[str, str] = {
    "kids": "kids_specials",
    "family": "holiday_family",
    "teens": "prime_time_station_ids",
    "adults": "prime_time_station_ids",
    "general": "custom",
}

AUDIENCE_CHOICES_PLAIN = (
    "kids (cartoons / children's specials), "
    "family (all-ages holiday and variety), "
    "teens, "
    "adults (prime-time movies and dramas), "
    "or general / mixed"
)

AUDIENCE_QUESTION = (
    "Who is this channel for? "
    "Kids, family (all ages), teens, adults (prime time), or general / mixed?"
)


def normalize_audience(raw: str) -> str:
    text = (raw or "").strip().lower()
    aliases = {
        "children": "kids",
        "child": "kids",
        "kid": "kids",
        "preschool": "kids",
        "all ages": "family",
        "all-ages": "family",
        "adult": "adults",
        "prime time": "adults",
        "primetime": "adults",
        "teen": "teens",
        "teenager": "teens",
        "mixed": "general",
        "anyone": "general",
        "everybody": "general",
    }
    if text in AUDIENCE_QUERY_TERMS:
        return text
    return aliases.get(text, text if text in AUDIENCE_TO_TEMPLATE else "")


def audience_query_extra(requirements: dict[str, Any]) -> list[str]:
    aud = normalize_audience(str(requirements.get("audience") or ""))
    terms = list(AUDIENCE_QUERY_TERMS.get(aud) or [])
    notes = str(requirements.get("audience_notes") or "").strip()
    if notes:
        terms.append(notes)
    return terms


def passes_audience_filter(
    title: str,
    description: str = "",
    *,
    audience: str,
) -> bool:
    aud = normalize_audience(audience)
    if not aud or aud == "general":
        return True
    blob = f"{title}\n{description or ''}"
    deny = AUDIENCE_DENY.get(aud)
    if deny and deny.search(blob):
        return False
    return True


def apply_audience_to_requirements(requirements: dict[str, Any]) -> dict[str, Any]:
    out = dict(requirements)
    aud = normalize_audience(str(out.get("audience") or ""))
    if aud:
        out["audience"] = aud
    tmpl = str(out.get("template") or "custom")
    if aud and tmpl in ("", "custom"):
        out["template"] = AUDIENCE_TO_TEMPLATE.get(aud, "custom")
    if aud == "adults" and out.get("daypart") in (None, "", "any"):
        out["daypart"] = "evening"
    return out
