"""HDHomeRun URL helpers — stable public base URL for Plex/Jellyfin clients."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import Request

from ..config import config

logger = logging.getLogger(__name__)

_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def resolve_hdhomerun_base_url(request: Optional[Request] = None) -> str:
    """Return the base URL advertised in discover/lineup stream URLs.

    Plex often fetches discover.json via 127.0.0.1 when colocated with StreamTV.
    Stream URLs must use the configured LAN base_url so remote transcoders can reach
    the tuner (see runtime: discover on 127.0.0.1 returned 127.0.0.1/auto/v* URLs).
    """
    configured = (config.server.base_url or "http://localhost:8410").rstrip("/")
    if request is None:
        return configured

    host = (request.url.hostname or "").lower()
    if host in _LOOPBACK_HOSTS:
        logger.debug(
            "HDHomeRun base URL: loopback request from %s → %s", host, configured
        )
        return configured

    scheme = request.url.scheme
    port = request.url.port
    if port:
        resolved = f"{scheme}://{host}:{port}"
    else:
        resolved = f"{scheme}://{host}"

    return resolved
