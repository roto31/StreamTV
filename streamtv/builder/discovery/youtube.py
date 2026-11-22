"""YouTube discovery via yt-dlp (CURSOR_PROMPT §5.2)."""

from __future__ import annotations

from typing import Any

import yt_dlp


def build_youtube_queries(requirements: dict[str, Any]) -> list[str]:
    from streamtv.builder.discovery.audience import (
        apply_audience_to_requirements,
        audience_query_extra,
    )

    requirements = apply_audience_to_requirements(requirements)
    theme = (requirements.get("theme") or "Christmas").strip()
    networks = requirements.get("networks") or ["CBS", "ABC"]
    stations = requirements.get("stations_for_breaks") or ["WCCO", "KSTP"]
    titles = requirements.get("known_titles") or []
    audience_terms = audience_query_extra(requirements)
    aud = str(requirements.get("audience") or "")
    queries: list[str] = []
    for title in titles[:15]:
        for net in networks:
            queries.append(f"{title} {net} commercials")
    for net in networks:
        queries.append(f"{net} {theme} special 1980s complete broadcast commercials")
        if aud in ("adults", "teens", "general", ""):
            queries.append(f"{net} {theme} movie full airing with commercials 1990s")
        if aud == "kids":
            queries.append(f"{net} {theme} kids cartoon special commercials")
            queries.append(f"{theme} animated special {net} with commercials")
        queries.append(f"{theme} full special with original commercials {net}")
        queries.append(f"Complete {net}-TV Special {theme}")
    for term in audience_terms[:4]:
        queries.append(f"{theme} {term} with original commercials")
    for station in stations:
        queries.append(f"{station} {theme} commercials 1980s")
        queries.append(f"{station} commercials December")
        queries.append(f"taped off {station} with commercials")
    seen: set[str] = set()
    out: list[str] = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            out.append(q)
    return out


def _ydl_opts(*, flat: bool = False) -> dict[str, Any]:
    from streamtv.youtube.ydl_opts import youtube_ydl_opts

    opts = youtube_ydl_opts(quiet=True, no_warnings=True, skip_download=True)
    if flat:
        opts["extract_flat"] = "in_playlist"
    return opts


def search_youtube(query: str, *, n: int = 10) -> list[dict[str, Any]]:
    n = max(1, min(int(n), 50))
    with yt_dlp.YoutubeDL(_ydl_opts(flat=True)) as ydl:
        info = ydl.extract_info(f"ytsearch{n}:{query}", download=False)
    entries = (info or {}).get("entries") or []
    out: list[dict[str, Any]] = []
    for ent in entries:
        if not isinstance(ent, dict):
            continue
        video_id = ent.get("id")
        if not video_id:
            continue
        duration = ent.get("duration")
        try:
            duration_i = int(duration) if duration is not None else None
        except (TypeError, ValueError):
            duration_i = None
        out.append(
            {
                "video_id": video_id,
                "title": ent.get("title") or video_id,
                "duration": duration_i,
                "channel": ent.get("channel") or ent.get("uploader"),
                "channel_id": ent.get("channel_id") or ent.get("uploader_id"),
                "url": ent.get("url")
                or ent.get("webpage_url")
                or f"https://www.youtube.com/watch?v={video_id}",
            }
        )
    return out


def inspect_youtube_video(video_id: str) -> dict[str, Any]:
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        with yt_dlp.YoutubeDL(_ydl_opts(flat=False)) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:  # noqa: BLE001
        return {
            "video_id": video_id,
            "url": url,
            "playable": False,
            "playable_reason": str(exc),
        }
    if not info:
        return {
            "video_id": video_id,
            "url": url,
            "playable": False,
            "playable_reason": "empty extract_info",
        }
    availability = info.get("availability")
    playable = availability in (None, "public", "unlisted")
    duration = info.get("duration")
    try:
        duration_f = float(duration) if duration is not None else None
    except (TypeError, ValueError):
        duration_f = None
    if duration_f is None and info.get("duration_string"):
        from streamtv.builder.source_meta import parse_archive_length

        duration_f = parse_archive_length(info.get("duration_string"))
    desc = str(info.get("description") or "")[:1000]
    return {
        "video_id": info.get("id") or video_id,
        "url": info.get("webpage_url") or url,
        "title": info.get("title"),
        "description": desc,
        "channel": info.get("channel") or info.get("uploader"),
        "channel_id": info.get("channel_id"),
        "uploader_id": info.get("uploader_id"),
        "upload_date": info.get("upload_date"),
        "duration": int(round(duration_f)) if duration_f is not None else None,
        "duration_exact": duration_f,
        "availability": availability,
        "tags": info.get("tags") or [],
        "categories": info.get("categories") or [],
        "thumbnail_source": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
        "playable": playable and duration_f is not None,
        "playable_reason": None
        if playable and duration_f is not None
        else (
            f"availability={availability}"
            if not playable
            else "missing duration"
        ),
    }
