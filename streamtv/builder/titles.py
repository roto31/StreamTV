"""Humanize media titles for Channel Builder / guide display.

Archive.org download URLs often embed percent-encoded filenames
(``Winnie%20the%20Pooh...``). Those must never land in XMLTV / Plex guide
cells as raw ``%20`` strings.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

_VIDEO_SUFFIXES = (".mp4", ".avi", ".mkv", ".mov", ".m4v", ".webm")
_MULTI_SPACE = re.compile(r"\s+")
_ENCODED_TOKEN = re.compile(r"%[0-9A-Fa-f]{2}")


def looks_url_encoded(text: str) -> bool:
    return bool(_ENCODED_TOKEN.search(text or ""))


def humanize_media_title(raw: str) -> str:
    """Decode URL encoding and light-normalize filename stems for the guide.

    Examples:
      ``Winnie%20the%20Pooh%20%26%20Christmas%20Too.mp4``
        → ``Winnie the Pooh & Christmas Too``
    """
    title = (raw or "").strip()
    if not title:
        return title

    # Decode once or twice (double-encoded paths)
    for _ in range(2):
        if looks_url_encoded(title):
            title = unquote(title)
        else:
            break

    # Drop trailing media extension if present
    lower = title.lower()
    for ext in _VIDEO_SUFFIXES:
        if lower.endswith(ext):
            title = title[: -len(ext)]
            break

    # Filename separators → spaces
    title = re.sub(r"[._]+", " ", title)
    title = title.replace("+", " ")
    title = _MULTI_SPACE.sub(" ", title).strip(" -_")
    return title


def title_from_media_url(url: str) -> str:
    """Best-effort display title from a direct media URL path basename."""
    try:
        path = unquote(url or "")
        name = Path(path).name
        if not name:
            return ""
        return humanize_media_title(name)
    except Exception:
        return ""
