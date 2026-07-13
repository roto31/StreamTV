# PBS + Playwright

## When Playwright is needed

- **Show expansion** in Channel Builder (`pbs.org/show/...` URLs).
- Optional headless harvest when `pbs.use_headless_browser: true`.

## Install

```bash
pip install playwright
playwright install chromium
```

## Builder workflow

1. Paste PBS show URL on the URLs step.
2. Click **Resolve** — expands to episode URLs.
3. Build only after all PBS show links show status `ok`.

Without expansion, build is blocked in the Builder UI.

## Authentication

Upload PBS cookies via `/api/auth/pbs` for Passport / DRM streams.
