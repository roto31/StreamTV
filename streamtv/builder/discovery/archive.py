"""Archive.org discovery (CURSOR_PROMPT §5.2)."""

from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
from typing import Any, Optional
from urllib.parse import quote, urlencode

import requests

ADVANCED_SEARCH = "https://archive.org/advancedsearch.php"
METADATA_URL = "https://archive.org/metadata/{identifier}"
DETAILS_URL = "https://archive.org/details/{identifier}"

DEFAULT_THEME_KEEP = re.compile(
    r"christmas|xmas|holiday|santa|noel|december|/12/|12/[0-9]+/", re.I
)
DEFAULT_DENY = re.compile(
    r"ABC Family|ABC Kids|split screen|screen-recording|news\s*:|"
    r"Fox Family|Disney Channel|Nickelodeon|Cartoon Network|\bTNT\b",
    re.I,
)


def build_archive_queries(requirements: dict[str, Any]) -> list[str]:
    from streamtv.builder.discovery.audience import (
        apply_audience_to_requirements,
        audience_query_extra,
    )

    requirements = apply_audience_to_requirements(requirements)
    theme = (requirements.get("theme") or "christmas").strip()
    theme_terms = requirements.get("theme_terms") or [theme.lower()]
    networks = requirements.get("networks") or ["CBS", "ABC"]
    stations = requirements.get("stations_for_breaks") or ["WCCO", "KSTP"]
    era = requirements.get("era") or {}
    known_titles = requirements.get("known_titles") or []
    month = requirements.get("theme_month") or "december"
    audience_terms = audience_query_extra(requirements)
    aud = str(requirements.get("audience") or "")

    queries: list[str] = []
    for net in networks:
        queries.append(
            f"title:{theme} AND (title:{net} OR description:{net}) AND "
            f"(title:commercials OR description:commercials OR title:WOC) AND "
            f"mediatype:movies"
        )
        queries.append(
            f'description:({theme}) AND description:("original commercials" OR '
            f'"with commercials" OR "all commercials") AND description:{net} AND '
            f"mediatype:movies"
        )

    station_or = " OR ".join(stations)
    theme_or = " OR ".join(theme_terms[:6])
    queries.append(
        f"({station_or}) AND ({theme_or} OR {month}) AND mediatype:movies"
    )
    queries.append(
        f'title:("complete broadcast") AND ({theme_or}) AND mediatype:movies'
    )

    for term in audience_terms[:5]:
        queries.append(
            f'title:({theme}) AND (title:"{term}" OR description:"{term}") AND '
            f"mediatype:movies"
        )

    if known_titles:
        title_or = " OR ".join(f'"{t}"' for t in known_titles[:20])
        net_or = " OR ".join(networks)
        queries.append(
            f"({title_or}) AND (commercials OR WOC OR {net_or} OR broadcast OR airing) "
            f"AND mediatype:movies"
        )

    date_from = era.get("from") or 1980
    date_to = era.get("to") or 1999
    queries.append(
        f'({theme}) AND (title:"WOC" OR title:"with commercials" OR '
        f'title:"original commercials" OR title:"w/ commercials") AND '
        f"mediatype:movies AND date:[{date_from}-01-01 TO {date_to}-12-31]"
    )
    if aud in ("adults", "teens", "general", ""):
        queries.append(
            f'title:("CBS Sunday Movie" OR "ABC Sunday Night Movie" OR '
            f'"Hallmark Hall of Fame") AND ({theme_or}) AND mediatype:movies'
        )
    if aud == "kids":
        queries.append(
            f"title:({theme}) AND (title:cartoon OR title:animated OR title:kids OR "
            f"title:children OR title:peanuts OR title:muppet) AND mediatype:movies"
        )

    seen: set[str] = set()
    out: list[str] = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            out.append(q)
    return out


def _strip_html(text: str) -> str:
    no_tags = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", unescape(no_tags)).strip()


def search_archive(
    query: str,
    *,
    rows: int = 100,
    page: int = 1,
    timeout: float = 30.0,
    session: Optional[requests.Session] = None,
) -> list[dict[str, Any]]:
    rows = min(int(rows), 400)
    params = [
        ("q", query),
        ("fl[]", "identifier"),
        ("fl[]", "title"),
        ("fl[]", "date"),
        ("fl[]", "description"),
        ("fl[]", "creator"),
        ("rows", str(rows)),
        ("page", str(page)),
        ("output", "json"),
    ]
    url = f"{ADVANCED_SEARCH}?{urlencode(params)}"
    sess = session or requests
    last_err: Optional[Exception] = None
    for attempt in range(3):
        try:
            resp = sess.get(url, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            docs = (data.get("response") or {}).get("docs") or []
            return [d for d in docs if isinstance(d, dict)]
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(0.5 * (attempt + 1))
    if last_err:
        raise last_err
    return []


def post_filter_docs(
    docs: list[dict[str, Any]],
    *,
    theme_keep: Optional[re.Pattern[str]] = None,
    deny: Optional[re.Pattern[str]] = None,
    broadcast_network_only: bool = True,
    audience: str = "",
) -> list[dict[str, Any]]:
    from streamtv.builder.discovery.audience import passes_audience_filter

    keep = theme_keep or DEFAULT_THEME_KEEP
    drop = deny or DEFAULT_DENY
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for doc in docs:
        ident = str(doc.get("identifier") or "")
        if not ident or ident in seen:
            continue
        title = str(doc.get("title") or "")
        desc = str(doc.get("description") or "")
        if not keep.search(title) and not keep.search(desc):
            continue
        if broadcast_network_only and drop.search(title):
            continue
        if not passes_audience_filter(title, desc, audience=audience):
            continue
        seen.add(ident)
        out.append(doc)
    return out


def _parse_length(raw: Any) -> Optional[float]:
    from streamtv.builder.source_meta import parse_archive_length

    return parse_archive_length(raw)


def inspect_archive_item(
    identifier: str,
    *,
    timeout: float = 30.0,
    session: Optional[requests.Session] = None,
    fetch_uploader: bool = True,
) -> dict[str, Any]:
    sess = session or requests
    resp = sess.get(METADATA_URL.format(identifier=identifier), timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    md = data.get("metadata") or {}
    files_raw = data.get("files") or []

    video_files: list[dict[str, Any]] = []
    for f in files_raw:
        if not isinstance(f, dict):
            continue
        name = str(f.get("name") or "")
        if name.lower().endswith(".ia.mp4"):
            continue
        if str(f.get("source") or "").lower() == "derivative":
            continue
        lower = name.lower()
        if not lower.endswith((".mp4", ".mpeg4", ".mpg", ".mpeg", ".mkv", ".avi")):
            continue
        length = _parse_length(f.get("length"))
        video_files.append(
            {
                "name": name,
                "length": int(round(length)) if length is not None else None,
                "length_exact": length,
                "size": f.get("size"),
                "format": f.get("format"),
                "source": f.get("source"),
                "url": (
                    f"https://archive.org/download/{identifier}/"
                    f"{quote(name, safe='/')}"
                ),
            }
        )

    playable = bool(video_files)
    uploader = None
    if fetch_uploader:
        try:
            details = sess.get(
                DETAILS_URL.format(identifier=identifier), timeout=timeout
            )
            if details.ok:
                m = re.search(r'href="/details/@([^"]+)"', details.text)
                if m:
                    uploader = m.group(1)
        except Exception:  # noqa: BLE001
            uploader = None

    return {
        "identifier": identifier,
        "title": md.get("title") or identifier,
        "date": md.get("date"),
        "description": _strip_html(str(md.get("description") or "")),
        "creator": md.get("creator"),
        "uploader": uploader,
        "publicdate": md.get("publicdate"),
        "subject": md.get("subject") or [],
        "collection": md.get("collection") or [],
        "page_url": DETAILS_URL.format(identifier=identifier),
        "thumbnail_source": f"https://archive.org/services/img/{identifier}",
        "files": video_files,
        "playable": playable,
        "playable_reason": None
        if playable
        else "no original playable video file (refusing *.ia.mp4)",
    }


def search_and_inspect(
    requirements: dict[str, Any],
    *,
    max_items: int = 40,
    rows_per_query: int = 100,
) -> list[dict[str, Any]]:
    from streamtv.builder.discovery.audience import apply_audience_to_requirements

    requirements = apply_audience_to_requirements(requirements)
    queries = build_archive_queries(requirements)
    docs: list[dict[str, Any]] = []
    for q in queries:
        docs.extend(search_archive(q, rows=rows_per_query))
    filtered = post_filter_docs(
        docs, audience=str(requirements.get("audience") or "")
    )
    identifiers = [d["identifier"] for d in filtered[:max_items]]
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = {pool.submit(inspect_archive_item, i): i for i in identifiers}
        for fut in as_completed(futs):
            try:
                results.append(fut.result())
            except Exception as exc:  # noqa: BLE001
                results.append(
                    {
                        "identifier": futs[fut],
                        "playable": False,
                        "playable_reason": str(exc),
                    }
                )
    return results
