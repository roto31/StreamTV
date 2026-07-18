"""Probe PBS VOD pages for FFmpeg-playable (non-DRM) HLS manifests at build time."""

from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

from streamtv.streaming.pbs_adapter import PBSAdapter

logger = logging.getLogger(__name__)

StreamVerdict = Literal["clear", "drm_only", "unusable", "none"]

M3U8_RE = re.compile(r"https?://[^\s\"'<>]+\.m3u8[^\s\"'<>]*", re.IGNORECASE)


def classify_pbs_m3u8_urls(urls: list[str]) -> StreamVerdict:
    """Classify captured manifest URLs for StreamTV/FFmpeg playability."""
    unique = list(dict.fromkeys(u for u in urls if u and ".m3u8" in u.lower()))
    if not unique:
        return "none"

    good = [u for u in unique if not PBSAdapter._is_bad_pbs_stream_url(u)]
    non_drm = [u for u in good if not PBSAdapter._is_drm_pbs_stream_url(u)]
    if any("/pbs-cs/" in u.lower() for u in non_drm):
        return "clear"
    if any("ga.pbs-video.pbs.org" in u.lower() for u in non_drm):
        return "clear"
    if good and not non_drm:
        return "drm_only"
    return "unusable"


def _cookies_path(cookies_path: str | None) -> str | None:
    if cookies_path:
        return cookies_path
    try:
        from streamtv.config import config

        return getattr(config.pbs, "cookies_file", None)
    except Exception:
        return None


async def probe_pbs_video_stream_verdict(
    video_url: str,
    *,
    cookies_path: str | None = None,
    browser_context: Any | None = None,
) -> StreamVerdict:
    """Load a PBS /video/ page and classify discovered HLS manifests."""
    if not video_url.startswith("http") or "/video/" not in video_url.lower():
        return "unusable"

    owns_browser = browser_context is None
    playwright = None
    browser = None
    context = browser_context

    try:
        if context is None:
            from playwright.async_api import async_playwright
            from http.cookiejar import MozillaCookieJar

            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context()
            cookie_file = _cookies_path(cookies_path)
            if cookie_file and Path(cookie_file).exists():
                jar = MozillaCookieJar(cookie_file)
                jar.load(ignore_discard=True, ignore_expires=True)
                pw_cookies = []
                for cookie in jar:
                    pw_cookies.append(
                        {
                            "name": cookie.name,
                            "value": cookie.value,
                            "domain": cookie.domain,
                            "path": cookie.path,
                            "expires": cookie.expires,
                            "secure": bool(cookie.secure),
                        }
                    )
                if pw_cookies:
                    await context.add_cookies(pw_cookies)

        page = await context.new_page()
        captured: list[str] = []

        def _on_response(response: Any) -> None:
            try:
                url = response.url
                if ".m3u8" in url.lower():
                    captured.append(url)
            except Exception:
                return

        page.on("response", _on_response)
        await page.goto(video_url, wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(3)
        content = await page.content()
        for match in M3U8_RE.finditer(content):
            url = match.group(0).rstrip("\\")
            if url not in captured:
                captured.append(url)
        await page.close()
        return classify_pbs_m3u8_urls(captured)
    except Exception as exc:
        logger.warning("PBS stream probe failed for %s: %s", video_url[:80], exc)
        return "unusable"
    finally:
        if owns_browser:
            if browser is not None:
                await browser.close()
            if playwright is not None:
                await playwright.stop()


async def filter_playable_pbs_episodes_async(
    items: list[dict[str, Any]],
    *,
    cookies_path: str | None = None,
    show_short_circuit: bool = True,
) -> list[dict[str, Any]]:
    """Keep PBS harvest rows that expose clear (non-DRM) HLS for FFmpeg."""
    if not items:
        return []

    from playwright.async_api import async_playwright
    from http.cookiejar import MozillaCookieJar

    groups: dict[str, list[dict[str, Any]]] = {}
    singles: list[dict[str, Any]] = []
    for item in items:
        src = (item.get("expanded_from") or "").strip()
        if src:
            groups.setdefault(src, []).append(item)
        else:
            singles.append(item)

    kept: list[dict[str, Any]] = []
    cookie_file = _cookies_path(cookies_path)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()
        if cookie_file and Path(cookie_file).exists():
            jar = MozillaCookieJar(cookie_file)
            jar.load(ignore_discard=True, ignore_expires=True)
            pw_cookies = []
            for cookie in jar:
                pw_cookies.append(
                    {
                        "name": cookie.name,
                        "value": cookie.value,
                        "domain": cookie.domain,
                        "path": cookie.path,
                        "expires": cookie.expires,
                        "secure": bool(cookie.secure),
                    }
                )
            if pw_cookies:
                await context.add_cookies(pw_cookies)

        async def keep_item(item: dict[str, Any]) -> bool:
            url = (item.get("url") or "").strip()
            verdict = await probe_pbs_video_stream_verdict(
                url, cookies_path=cookie_file, browser_context=context
            )
            item["pbs_stream_verdict"] = verdict
            return verdict == "clear"

        for item in singles:
            if await keep_item(item):
                kept.append(item)

        for source_url, group in groups.items():
            if show_short_circuit and group:
                sample = group[0]
                verdict = await probe_pbs_video_stream_verdict(
                    (sample.get("url") or "").strip(),
                    cookies_path=cookie_file,
                    browser_context=context,
                )
                if verdict == "clear":
                    for entry in group:
                        entry["pbs_stream_verdict"] = "clear"
                    kept.extend(group)
                    logger.info(
                        "PBS show %s: sample playable — keeping %d episodes",
                        urlparse(source_url).path,
                        len(group),
                    )
                    continue
                if verdict == "drm_only":
                    logger.warning(
                        "PBS show %s: Passport/DRM-only streams — excluding %d episodes",
                        urlparse(source_url).path,
                        len(group),
                    )
                    continue

            for entry in group:
                if await keep_item(entry):
                    kept.append(entry)

        await browser.close()

    return kept


def filter_playable_pbs_episodes(
    items: list[dict[str, Any]],
    *,
    cookies_path: str | None = None,
    show_short_circuit: bool = True,
) -> list[dict[str, Any]]:
    return asyncio.run(
        filter_playable_pbs_episodes_async(
            items,
            cookies_path=cookies_path,
            show_short_circuit=show_short_circuit,
        )
    )
