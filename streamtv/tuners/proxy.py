"""Rewrite upstream HDHomeRun discover/lineup for Plex GUI compatibility."""

from __future__ import annotations

import logging
import re
from typing import Any, Optional
from urllib.parse import urlparse, urlunparse

import httpx

from .device_ids import ensure_tuner_device_id

logger = logging.getLogger(__name__)

_LOOPBACK = frozenset({"127.0.0.1", "localhost", "::1", "0.0.0.0"})
_HEX_DEVICE_ID = re.compile(r"^[0-9A-Fa-f]{8}$")


class TunerProxy:
    """Normalize one upstream HDHomeRun-compatible tuner for Plex."""

    def __init__(
        self,
        name: str,
        upstream_url: str,
        *,
        force_device_id: Optional[str] = None,
        force_base_url: Optional[str] = None,
        xmltv_url: Optional[str] = None,
        timeout: float = 10.0,
    ) -> None:
        self.name = name
        self.upstream_url = upstream_url.rstrip("/")
        self.force_base_url = (force_base_url or "").rstrip("/") or None
        self.xmltv_url = xmltv_url
        self.timeout = timeout
        self.device_id = ensure_tuner_device_id(name, force_device_id)
        parsed = urlparse(self.upstream_url)
        self.upstream_host = parsed.hostname or "127.0.0.1"
        self.upstream_port = parsed.port
        self.upstream_scheme = parsed.scheme or "http"

    def proxy_root(self, streamtv_base: str) -> str:
        """Public proxy root Plex should use as BaseURL."""
        if self.force_base_url:
            return self.force_base_url.rstrip("/")
        return f"{streamtv_base.rstrip('/')}/tuners/proxy/{self.name}"

    async def fetch_json(self, path: str) -> Any:
        url = f"{self.upstream_url}{path}"
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()

    async def reachable(self) -> tuple[bool, list[str]]:
        issues: list[str] = []
        try:
            data = await self.fetch_json("/discover.json")
            raw_id = str(data.get("DeviceID", ""))
            if not _HEX_DEVICE_ID.match(raw_id):
                issues.append(f"upstream DeviceID is non-hex ({raw_id!r}) — proxy rewrites it")
            base = str(data.get("BaseURL", ""))
            host = (urlparse(base).hostname or "").lower()
            if host in _LOOPBACK:
                issues.append(f"upstream BaseURL is loopback ({base}) — proxy rewrites it")
            return True, issues
        except Exception as exc:
            return False, [f"unreachable: {exc}"]

    async def discover(self, streamtv_base: str) -> dict[str, Any]:
        try:
            data = await self.fetch_json("/discover.json")
            if not isinstance(data, dict):
                data = {}
        except Exception as exc:
            logger.warning("Tunarr discover fetch failed for %s: %s", self.name, exc)
            data = {
                "FriendlyName": self.name.title(),
                "Manufacturer": "Silicondust",
                "ModelNumber": "HDTC-2US",
                "FirmwareName": "hdhomeruntc_atsc",
                "TunerCount": 4,
                "FirmwareVersion": "20170930",
                "DeviceAuth": "",
            }

        root = self.proxy_root(streamtv_base)
        data["DeviceID"] = self.device_id
        data["BaseURL"] = root
        data["LineupURL"] = f"{root}/lineup.json"
        # Prefer merged guide when clients honor EPGURL; Plex often uses wizard paste instead
        data["EPGURL"] = f"{streamtv_base.rstrip('/')}/tuners/guide.xml"
        if "FriendlyName" not in data or not data["FriendlyName"]:
            data["FriendlyName"] = self.name.title()
        return data

    async def lineup(self) -> list[dict[str, Any]]:
        try:
            data = await self.fetch_json("/lineup.json")
        except Exception as exc:
            logger.warning("Tunarr lineup fetch failed for %s: %s", self.name, exc)
            return []
        if not isinstance(data, list):
            return []
        return [self._rewrite_lineup_item(item) for item in data if isinstance(item, dict)]

    async def lineup_status(self) -> dict[str, Any]:
        try:
            data = await self.fetch_json("/lineup_status.json")
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return {
            "ScanInProgress": 0,
            "ScanPossible": 1,
            "Source": "Cable",
            "SourceList": ["Cable"],
        }

    def device_xml(self, streamtv_base: str) -> str:
        root = self.proxy_root(streamtv_base)
        return f"""<?xml version="1.0" encoding="utf-8"?>
<root xmlns="urn:schemas-upnp-org:device-1-0">
  <specVersion><major>1</major><minor>0</minor></specVersion>
  <URLBase>{root}/</URLBase>
  <device>
    <deviceType>urn:schemas-upnp-org:device:MediaServer:1</deviceType>
    <friendlyName>{self.name.title()} (StreamTV proxy)</friendlyName>
    <manufacturer>Silicondust</manufacturer>
    <modelName>HDHomeRun</modelName>
    <modelNumber>HDTC-2US</modelNumber>
    <serialNumber>{self.device_id}</serialNumber>
    <UDN>uuid:streamtv-tuner-{self.name}-{self.device_id}</UDN>
  </device>
</root>
"""

    def _rewrite_lineup_item(self, item: dict[str, Any]) -> dict[str, Any]:
        out = dict(item)
        url = out.get("URL")
        if isinstance(url, str) and url:
            out["URL"] = self._rewrite_stream_url(url)
        return out

    def _rewrite_stream_url(self, url: str) -> str:
        """Point stream URLs at Tunarr LAN host; do not proxy video through StreamTV."""
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if host not in _LOOPBACK and host:
            return url
        netloc = self.upstream_host
        if self.upstream_port:
            netloc = f"{self.upstream_host}:{self.upstream_port}"
        return urlunparse(
            (
                self.upstream_scheme,
                netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment,
            )
        )
