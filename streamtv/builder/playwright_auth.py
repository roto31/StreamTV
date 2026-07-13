"""Playwright-based sign-in cookie capture for Channel Builder."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Optional

from streamtv.builder.cookie_io import cookies_path_for_scope, write_netscape_cookies

logger = logging.getLogger(__name__)

PLAYWRIGHT_INSTALL_HINT = (
    "Playwright is required for automated sign-in. "
    "Install with: pip install playwright && playwright install chromium"
)


class PlaywrightAuthError(RuntimeError):
    pass


def _playwright_cookies_to_netscape(cookies: list[dict]) -> list[dict]:
    out: list[dict] = []
    for cookie in cookies:
        out.append(
            {
                "domain": cookie.get("domain", ""),
                "path": cookie.get("path", "/"),
                "secure": cookie.get("secure", False),
                "expires": cookie.get("expires", -1),
                "name": cookie.get("name", ""),
                "value": cookie.get("value", ""),
            }
        )
    return out


async def _run_login(
    login_fn: Callable,
    email: str,
    password: str,
    domain_filter: Optional[str],
) -> list[dict]:
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise PlaywrightAuthError(PLAYWRIGHT_INSTALL_HINT) from exc

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            context = await browser.new_context()
            page = await context.new_page()
            await login_fn(page, email, password)
            cookies = await context.cookies()
            if domain_filter:
                cookies = [c for c in cookies if domain_filter in (c.get("domain") or "")]
            if not cookies:
                raise PlaywrightAuthError(
                    "Sign-in completed but no session cookies were captured. "
                    "If 2FA or CAPTCHA was shown, use cookie upload instead."
                )
            return _playwright_cookies_to_netscape(cookies)
        finally:
            await browser.close()


async def _login_youtube(page, email: str, password: str) -> None:
    await page.goto("https://accounts.google.com/signin/v2/identifier?service=youtube", wait_until="domcontentloaded")
    await page.fill('input[type="email"]', email, timeout=15000)
    await page.click("#identifierNext", timeout=10000)
    await page.wait_for_timeout(1500)
    await page.fill('input[type="password"]', password, timeout=15000)
    await page.click("#passwordNext", timeout=10000)
    await page.wait_for_timeout(3000)
    await page.goto("https://www.youtube.com/", wait_until="domcontentloaded", timeout=30000)


async def _login_pbs(page, email: str, password: str) -> None:
    await page.goto("https://account.pbs.org/accounts/login/", wait_until="domcontentloaded")
    await page.fill('input[name="username"], input[type="email"]', email, timeout=15000)
    await page.fill('input[name="password"], input[type="password"]', password, timeout=15000)
    await page.click('button[type="submit"], input[type="submit"]', timeout=10000)
    await page.wait_for_timeout(3000)
    await page.goto("https://www.pbs.org/", wait_until="domcontentloaded", timeout=30000)


async def _login_generic(page, login_url: str, email: str, password: str) -> None:
    await page.goto(login_url, wait_until="domcontentloaded")
    await page.fill('input[type="email"], input[name="username"], input[name="email"]', email, timeout=15000)
    await page.fill('input[type="password"], input[name="password"]', password, timeout=15000)
    await page.click('button[type="submit"], input[type="submit"]', timeout=10000)
    await page.wait_for_timeout(3000)


async def capture_cookies_youtube(email: str, password: str) -> Path:
    cookies = await _run_login(_login_youtube, email, password, "youtube")
    path = cookies_path_for_scope("youtube")
    return write_netscape_cookies(path, cookies)


async def capture_cookies_pbs(email: str, password: str) -> Path:
    cookies = await _run_login(_login_pbs, email, password, "pbs.org")
    path = cookies_path_for_scope("pbs")
    return write_netscape_cookies(path, cookies)


async def capture_cookies_generic(
    login_url: str,
    email: str,
    password: str,
    cookies_domain: str,
    output_scope: str,
) -> Path:
    async def _fn(page, user: str, pwd: str) -> None:
        await _login_generic(page, login_url, user, pwd)

    cookies = await _run_login(_fn, email, password, cookies_domain)
    path = cookies_path_for_scope(output_scope)
    return write_netscape_cookies(path, cookies)
