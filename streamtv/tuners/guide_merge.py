"""Merge StreamTV + Tunarr XMLTV into one guide for Plex DVR."""

from __future__ import annotations

import logging
import re
from typing import Optional
from xml.etree import ElementTree as ET

import httpx

logger = logging.getLogger(__name__)

_CHANNEL_ID_ATTR = "id"
_CHANNEL_REF_ATTR = "channel"


def _local(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


async def fetch_xmltv(url: str, timeout: float = 30.0) -> Optional[ET.Element]:
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return ET.fromstring(resp.content)
    except Exception as exc:
        logger.warning("XMLTV fetch failed for %s: %s", url, exc)
        return None


def _collect_channel_ids(root: ET.Element) -> set[str]:
    ids: set[str] = set()
    for el in root.iter():
        if _local(el.tag) == "channel":
            cid = el.get(_CHANNEL_ID_ATTR)
            if cid:
                ids.add(cid)
    return ids


def _prefix_channel_tree(root: ET.Element, prefix: str, collide: set[str]) -> None:
    """Prefix channel ids that collide with an existing set."""
    remap: dict[str, str] = {}
    for el in list(root.iter()):
        local = _local(el.tag)
        if local == "channel":
            cid = el.get(_CHANNEL_ID_ATTR)
            if cid and cid in collide:
                new_id = f"{prefix}{cid}"
                remap[cid] = new_id
                el.set(_CHANNEL_ID_ATTR, new_id)
        elif local == "programme":
            cref = el.get(_CHANNEL_REF_ATTR)
            if cref and cref in collide:
                el.set(_CHANNEL_REF_ATTR, f"{prefix}{cref}")
            elif cref and cref in remap:
                el.set(_CHANNEL_REF_ATTR, remap[cref])


def merge_xmltv_roots(
    primary: ET.Element,
    secondary: ET.Element,
    *,
    secondary_prefix: str = "tunarr.",
) -> ET.Element:
    """Merge secondary channels/programmes into a copy of primary."""
    out = ET.Element("tv")
    for key, val in primary.attrib.items():
        out.set(key, val)
    if "generator-info-name" not in out.attrib:
        out.set("generator-info-name", "StreamTV tuner_manager")

    primary_ids = _collect_channel_ids(primary)
    secondary_ids = _collect_channel_ids(secondary)
    collide = primary_ids & secondary_ids

    # Copy primary as-is
    for child in list(primary):
        if _local(child.tag) in ("channel", "programme"):
            out.append(child)

    # Mutate secondary in place for collisions, then append
    if collide:
        _prefix_channel_tree(secondary, secondary_prefix, collide)
        logger.info(
            "XMLTV merge: prefixed %d colliding channel id(s) with %r",
            len(collide),
            secondary_prefix,
        )

    for child in list(secondary):
        if _local(child.tag) in ("channel", "programme"):
            out.append(child)

    return out


async def merge_xmltv(
    streamtv_xmltv_url: str,
    tunarr_xmltv_url: str,
    *,
    secondary_prefix: str = "tunarr.",
    extra_urls: Optional[list[tuple[str, str]]] = None,
) -> tuple[bytes, list[str]]:
    """Fetch guides and return merged XMLTV bytes plus source labels."""
    labels = ["streamtv", "tunarr"]
    primary = await fetch_xmltv(streamtv_xmltv_url)
    secondary = await fetch_xmltv(tunarr_xmltv_url)

    if primary is None and secondary is None:
        raise RuntimeError("Both XMLTV sources failed")
    if primary is None:
        assert secondary is not None
        merged_root = secondary
    elif secondary is None:
        merged_root = primary
    else:
        merged_root = merge_xmltv_roots(primary, secondary, secondary_prefix=secondary_prefix)

    for url, prefix in extra_urls or []:
        extra = await fetch_xmltv(url)
        if extra is None:
            continue
        merged_root = merge_xmltv_roots(merged_root, extra, secondary_prefix=prefix)
        labels.append(prefix.rstrip("."))

    xml_bytes = ET.tostring(merged_root, encoding="utf-8", xml_declaration=True)
    return xml_bytes, labels
