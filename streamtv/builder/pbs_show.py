"""PBS show page expansion for Channel Builder."""

from __future__ import annotations

import re
from typing import Any, Callable, Optional
from urllib.parse import urljoin, urlparse

import requests

from streamtv.builder.cookie_io import load_pbs_session

PBS_VIDEO_HREF_RE = re.compile(r'href="(/video/[a-z0-9-]+/)"', re.IGNORECASE)
PBS_VIDEO_PATH_RE = re.compile(r"/video/([a-z0-9-]+)/?", re.IGNORECASE)
PBS_RSC_META_RE = re.compile(
    r'\\"slug\\":\\"([a-z0-9-]+)\\",\\"title\\":\\"([^\\]+)\\"[^}]{0,240}?\\"duration\\":(\d+)',
    re.IGNORECASE,
)
SEASON_OPTION_RE = re.compile(
    r'<option value="([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"',
    re.IGNORECASE,
)
from streamtv.builder.pbs_episode_filter import (
    filter_full_pbs_episodes,
    pbs_show_max_videos,
)

# Back-compat for scripts that patch this module attribute.
MAX_VIDEOS = pbs_show_max_videos()


def _slugify(text: str, max_len: int = 48) -> str:
    slug = re.sub(r"[^\w]+", "_", text.lower()).strip("_")
    return slug[:max_len] or "item"


def pbs_video_stream_id(url: str) -> str:
    """Stable per-episode id from PBS /video/{slug}/ path (avoids URL-prefix collisions)."""
    match = PBS_VIDEO_PATH_RE.search(url)
    if match:
        return _slugify(match.group(1), max_len=80)
    return _slugify(url, max_len=80)


def parse_show_slug(url: str) -> str:
    path = urlparse(url).path.strip("/")
    parts = path.split("/")
    if len(parts) >= 2 and parts[0] == "show":
        return parts[1]
    raise ValueError(f"Not a PBS show URL: {url}")


def _canonical_video_url(slug: str) -> str:
    return f"https://www.pbs.org/video/{slug}/"


def harvest_from_html(html: str, expanded_from: str) -> dict[str, dict[str, Any]]:
    items: dict[str, dict[str, Any]] = {}
    for match in PBS_VIDEO_HREF_RE.finditer(html):
        slug = match.group(1).strip("/").split("/")[-1]
        url = _canonical_video_url(slug)
        items[url] = {
            "url": url,
            "title": slug.replace("-", " ").title(),
            "source": "pbs",
            "stream_id": pbs_video_stream_id(url),
            "duration": None,
            "upload_date": None,
            "expanded_from": expanded_from,
        }
    for slug, title, duration in PBS_RSC_META_RE.findall(html):
        url = _canonical_video_url(slug)
        entry = items.get(url, {"url": url, "source": "pbs", "expanded_from": expanded_from})
        entry["title"] = title.replace("\\'", "'")
        entry["stream_id"] = pbs_video_stream_id(url)
        entry["duration"] = int(duration)
        items[url] = entry
    return items


def extract_season_ids(html: str) -> list[str]:
    seen: set[str] = set()
    ids: list[str] = []
    for season_id in SEASON_OPTION_RE.findall(html):
        if season_id not in seen:
            seen.add(season_id)
            ids.append(season_id)
    return ids


async def harvest_seasons_playwright(
    show_url: str,
    season_ids: list[str],
    cookies_path: Optional[str] = None,
) -> list[dict[str, Any]]:
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise ValueError(
            "Playwright is required to harvest full PBS season catalogs. "
            "pip install playwright && playwright install chromium"
        ) from exc

    from pathlib import Path
    from http.cookiejar import MozillaCookieJar

    results: dict[str, dict[str, Any]] = {}
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()
        if cookies_path and Path(cookies_path).exists():
            jar = MozillaCookieJar(cookies_path)
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
        await page.goto(show_url, wait_until="networkidle", timeout=90000)
        picker_count = await page.locator('select[name="season-picker"]').count()
        if picker_count == 0:
            await browser.close()
            return []

        live_ids: list[str] = await page.eval_on_selector(
            'select[name="season-picker"]',
            """el => [...new Set(Array.from(el.options).map(o => o.value).filter(v => v && v.length > 8))]""",
        )
        target_ids = live_ids or list(season_ids)
        for season_id in target_ids:
            selected = False
            for idx in range(picker_count):
                picker = page.locator('select[name="season-picker"]').nth(idx)
                try:
                    ok = await picker.evaluate(
                        "(el, value) => {"
                        "if (![...el.options].some(o => o.value === value)) return false;"
                        "el.value = value;"
                        "el.dispatchEvent(new Event('input', { bubbles: true }));"
                        "el.dispatchEvent(new Event('change', { bubbles: true }));"
                        "return true;"
                        "}",
                        season_id,
                    )
                    if ok:
                        selected = True
                        break
                except Exception:
                    continue
            if not selected:
                continue
            await page.wait_for_timeout(3000)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(500)
            links = await page.eval_on_selector_all(
                'a[href*="/video/"]',
                "els => els.map(e => ({href: e.getAttribute('href'), title: (e.textContent || '').trim()}))",
            )
            for entry in links or []:
                href = entry.get("href") if isinstance(entry, dict) else entry
                title = entry.get("title") if isinstance(entry, dict) else ""
                if not href or "/video/" not in href:
                    continue
                slug_match = PBS_VIDEO_PATH_RE.search(href)
                if not slug_match:
                    continue
                url = _canonical_video_url(slug_match.group(1))
                display = title or slug_match.group(1).replace("-", " ").title()
                results[url] = {
                    "url": url,
                    "title": display,
                    "source": "pbs",
                    "stream_id": pbs_video_stream_id(url),
                    "duration": None,
                    "upload_date": None,
                    "expanded_from": show_url,
                }
        await browser.close()
    return list(results.values())


def expand_pbs_show(
    url: str,
    *,
    season_harvester: Optional[Callable[..., list[dict[str, Any]]]] = None,
    filter_full_episodes: bool = False,
    min_episode_seconds: int = 300,
    exclude_passport_drm: bool = False,
    max_videos: Optional[int] = None,
) -> list[dict[str, Any]]:
    slug = parse_show_slug(url)
    canonical = f"https://www.pbs.org/show/{slug}/"
    session = load_pbs_session()
    response = session.get(canonical, timeout=60)
    response.raise_for_status()
    html = response.text
    items = harvest_from_html(html, canonical)
    season_ids = extract_season_ids(html)
    if season_ids:
        import asyncio
        from streamtv.config import config as app_config

        harvester = season_harvester or harvest_seasons_playwright
        cookies_file = getattr(app_config.pbs, "cookies_file", None) or str(
            __import__("pathlib").Path("data/cookies/pbs_cookies.txt")
        )
        if asyncio.iscoroutinefunction(harvester):
            season_items = asyncio.run(harvester(canonical, season_ids, cookies_file))
        else:
            season_items = harvester(canonical, season_ids, cookies_file)
        for entry in season_items:
            items[entry["url"]] = {**items.get(entry["url"], {}), **entry}
    ordered = list(items.values())
    if filter_full_episodes:
        ordered = filter_full_pbs_episodes(ordered, min_seconds=min_episode_seconds)
    if exclude_passport_drm:
        from streamtv.builder.pbs_stream_probe import filter_playable_pbs_episodes

        ordered = filter_playable_pbs_episodes(ordered)
    if not ordered:
        if exclude_passport_drm:
            raise ValueError(
                "No PBS videos with FFmpeg-playable streams found. "
                "Passport-only DRM episodes were excluded — choose a public PBS show "
                "or disable 'Exclude Passport DRM' in Channel Builder."
            )
        raise ValueError(
            "No PBS videos found on this show page. Configure PBS sign-in for Passport content."
        )
    cap = pbs_show_max_videos(max_videos)
    if len(ordered) > cap:
        raise ValueError(f"PBS show has more than {cap} videos; narrow the selection.")
    return ordered
