"""Shared yt-dlp option builder for all YouTube extract/download paths.

Merges PO-token-free player_client policy (constants) with optional EJS/Deno
challenge solving from config. Does not alter format selectors or stream URLs.
"""

from __future__ import annotations

import shutil
from typing import Any

from streamtv.ffmpeg.constants import YOUTUBE_EXTRACTOR_ARGS


def _resolve_js_runtimes(js_runtime: str | None) -> dict[str, dict[str, str]] | None:
    """Parse config youtube.js_runtime into yt-dlp js_runtimes dict."""
    if not js_runtime:
        return None
    raw = js_runtime.strip()
    if not raw:
        return None
    if ":" in raw:
        name, path = raw.split(":", 1)
        name = name.strip().lower()
        path = path.strip()
    else:
        name = raw.lower()
        path = shutil.which(name) or ""
    if not path:
        return None
    return {name: {"path": path}}


def _resolve_remote_components(value: str | None) -> list[str] | None:
    if not value:
        return None
    parts = [p.strip() for p in value.replace(",", " ").split() if p.strip()]
    return parts or None


def youtube_ydl_opts(**overrides: Any) -> dict[str, Any]:
    """Base yt-dlp options for YouTube — always includes YOUTUBE_EXTRACTOR_ARGS."""
    from streamtv.config import config

    opts: dict[str, Any] = {
        "extractor_args": YOUTUBE_EXTRACTOR_ARGS,
    }
    remote = _resolve_remote_components(getattr(config.youtube, "remote_components", None))
    if remote:
        opts["remote_components"] = remote
    js_runtimes = _resolve_js_runtimes(getattr(config.youtube, "js_runtime", None))
    if js_runtimes:
        opts["js_runtimes"] = js_runtimes
    opts.update(overrides)
    return opts
