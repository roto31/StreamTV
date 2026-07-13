"""HTTP routes for tuner manager — Plex GUI-compatible Tunarr proxy."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response

from ..config import config
from ..hdhomerun.urls import resolve_hdhomerun_base_url
from ..tuners.guide_merge import merge_xmltv
from ..tuners.proxy import TunerProxy

logger = logging.getLogger(__name__)

tuner_router = APIRouter(tags=["tuner-manager"])


def _proxies() -> dict[str, TunerProxy]:
    out: dict[str, TunerProxy] = {}
    for t in config.tuner_manager.tuners or []:
        name = getattr(t, "name", None) or (t.get("name") if isinstance(t, dict) else None)
        url = getattr(t, "url", None) or (t.get("url") if isinstance(t, dict) else None)
        if not name or not url:
            continue
        out[name] = TunerProxy(
            name=name,
            upstream_url=url,
            force_device_id=getattr(t, "force_device_id", None)
            if not isinstance(t, dict)
            else t.get("force_device_id"),
            force_base_url=getattr(t, "force_base_url", None)
            if not isinstance(t, dict)
            else t.get("force_base_url"),
            xmltv_url=getattr(t, "xmltv_url", None)
            if not isinstance(t, dict)
            else t.get("xmltv_url"),
        )
    return out


def _get_proxy(name: str) -> TunerProxy:
    proxies = _proxies()
    if name not in proxies:
        raise HTTPException(status_code=404, detail=f"Unknown tuner proxy: {name}")
    return proxies[name]


def _streamtv_base(request: Request) -> str:
    return resolve_hdhomerun_base_url(request)


@tuner_router.get("/tuners")
async def tuners_inventory(request: Request) -> Response:
    """Operator inventory with exact Plex paste URLs."""
    base = _streamtv_base(request)
    guide_url = f"{base}/tuners/guide.xml"
    items: list[dict[str, Any]] = []
    for name, proxy in _proxies().items():
        reachable, issues = await proxy.reachable()
        items.append(
            {
                "name": name,
                "upstream": proxy.upstream_url,
                "device_id": proxy.device_id,
                "plex_add_url": proxy.proxy_root(base),
                "plex_guide_url": guide_url,
                "reachable": reachable,
                "issues": issues,
            }
        )
    accept = (request.headers.get("accept") or "").lower()
    if "text/html" in accept and "application/json" not in accept:
        return HTMLResponse(_inventory_html(items, guide_url))
    return JSONResponse(
        {
            "enabled": config.tuner_manager.enabled,
            "merged_guide": config.tuner_manager.merged_guide,
            "plex_guide_url": guide_url,
            "tuners": items,
        }
    )


def _inventory_html(items: list[dict[str, Any]], guide_url: str) -> str:
    rows = []
    for t in items:
        rows.append(
            f"<tr><td><code>{t['name']}</code></td>"
            f"<td><code>{t['device_id']}</code></td>"
            f"<td>{'yes' if t['reachable'] else 'no'}</td>"
            f"<td><code>{t['plex_add_url']}</code></td></tr>"
        )
    body = "\n".join(rows) or "<tr><td colspan='4'>No tuners configured</td></tr>"
    return f"""<!DOCTYPE html>
<html><head><title>StreamTV Tuner Manager</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 2rem; max-width: 900px; }}
code {{ background: #f4f4f4; padding: 0.15em 0.4em; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ccc; padding: 0.5rem; text-align: left; }}
ol {{ line-height: 1.6; }}
</style></head><body>
<h1>StreamTV Tuner Manager</h1>
<p>Add Tunarr in <strong>Plex → Settings → Live TV &amp; DVR → Set Up / Add device</strong>.</p>
<ol>
<li>Paste the <strong>plex_add_url</strong> for the tuner below.</li>
<li>When asked for a guide, paste: <code>{guide_url}</code></li>
</ol>
<table>
<thead><tr><th>Name</th><th>DeviceID</th><th>Reachable</th><th>Plex add URL</th></tr></thead>
<tbody>{body}</tbody>
</table>
</body></html>"""


@tuner_router.get("/tuners/guide.xml")
async def merged_guide(request: Request) -> Response:
    if not config.tuner_manager.merged_guide:
        raise HTTPException(
            status_code=404,
            detail="merged_guide is disabled; enable tuner_manager.merged_guide in config",
        )
    base = _streamtv_base(request)
    streamtv_url = f"{base}/iptv/xmltv.xml"
    # Prefer first proxy with xmltv_url
    tunarr_url: Optional[str] = None
    for proxy in _proxies().values():
        if proxy.xmltv_url:
            tunarr_url = proxy.xmltv_url
            break
    if not tunarr_url:
        # Fallback: first upstream /api/xmltv.xml
        for proxy in _proxies().values():
            tunarr_url = f"{proxy.upstream_url}/api/xmltv.xml"
            break
    if not tunarr_url:
        raise HTTPException(status_code=404, detail="No tuner xmltv_url configured")
    perf_start = time.time()
    try:
        xml_bytes, source_labels = await merge_xmltv(streamtv_url, tunarr_url)
    except Exception as exc:
        logger.exception("Guide merge failed")
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    generation_time = time.time() - perf_start
    now = datetime.now(timezone.utc)
    epg_note = ""
    if config.plex.use_for_epg:
        epg_note = ";plex_epg_flag=merge_layer_only"
    return Response(
        content=xml_bytes,
        media_type="application/xml; charset=utf-8",
        headers={
            "Content-Disposition": "inline; filename=guide.xml",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "X-Generated-At": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "X-Generation-Time": f"{generation_time:.2f}s",
            "X-Merged-Sources": ",".join(source_labels) + epg_note,
        },
    )


@tuner_router.get("/tuners/proxy/{name}/discover.json")
async def proxy_discover(name: str, request: Request) -> JSONResponse:
    proxy = _get_proxy(name)
    data = await proxy.discover(_streamtv_base(request))
    return JSONResponse(data)


@tuner_router.get("/tuners/proxy/{name}/lineup.json")
async def proxy_lineup(name: str) -> JSONResponse:
    proxy = _get_proxy(name)
    return JSONResponse(await proxy.lineup())


@tuner_router.get("/tuners/proxy/{name}/lineup_status.json")
async def proxy_lineup_status(name: str) -> JSONResponse:
    proxy = _get_proxy(name)
    return JSONResponse(await proxy.lineup_status())


@tuner_router.get("/tuners/proxy/{name}/device.xml")
async def proxy_device_xml(name: str, request: Request) -> Response:
    proxy = _get_proxy(name)
    return Response(
        content=proxy.device_xml(_streamtv_base(request)),
        media_type="application/xml",
    )


@tuner_router.get("/tuners/proxy/{name}/xmltv.xml")
async def proxy_xmltv_alias(name: str, request: Request) -> Response:
    """Alias under proxy prefix — prefer merged guide when enabled."""
    if config.tuner_manager.merged_guide:
        return await merged_guide(request)
    proxy = _get_proxy(name)
    url = proxy.xmltv_url or f"{proxy.upstream_url}/api/xmltv.xml"
    import httpx

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        resp = await client.get(url)
        if resp.status_code >= 400:
            raise HTTPException(status_code=502, detail=f"Upstream XMLTV {resp.status_code}")
        return Response(content=resp.content, media_type="application/xml")


@tuner_router.get("/tuners/proxy/{name}/")
@tuner_router.get("/tuners/proxy/{name}")
async def proxy_root(name: str, request: Request) -> Response:
    """Device root — JSON discover for API clients, HTML tip for browsers."""
    proxy = _get_proxy(name)
    accept = (request.headers.get("accept") or "").lower()
    data = await proxy.discover(_streamtv_base(request))
    if "text/html" in accept and "application/json" not in accept:
        add_url = proxy.proxy_root(_streamtv_base(request))
        guide = f"{_streamtv_base(request)}/tuners/guide.xml"
        html = f"""<!DOCTYPE html>
<html><head><title>Add {name} in Plex</title></head><body>
<h1>{name.title()} (StreamTV proxy)</h1>
<p>In Plex → Live TV &amp; DVR → Add device, paste:</p>
<p><code>{add_url}</code></p>
<p>Guide (merged): <code>{guide}</code></p>
<p>DeviceID: <code>{proxy.device_id}</code></p>
</body></html>"""
        return HTMLResponse(html)
    return JSONResponse(data)
