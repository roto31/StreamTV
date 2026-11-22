# StreamTV WebUI design system

Server-rendered Jinja templates (`streamtv/templates/`) + a shared design system (`streamtv/static/ui/`), mounted at `/static/ui`.
The Channel Builder (`frontend/builder`, React/Vite) consumes the same tokens.

## Files

| File | Purpose |
|---|---|
| `static/ui/streamtv-ui.css` | Tokens (light / dark / increased-contrast / forced-colors), base, shell, every shared component class |
| `static/ui/core.js` | Loaded in `<head>`. Theme, `authenticatedFetch`, `registerActions`, `[data-action]` dispatch, `whenDomReady` |
| `static/ui/icons.js` | Converts `<span class="material-icons">name</span>` to inline SVG (Lucide, ISC). Keeps `window.iconMap` / `convertMaterialIcons()` |
| `static/ui/shell.js` | Sidebar drawer, live status, ARIA combobox search (`/` or Cmd/Ctrl+K), docs disclosure |
| `static/ui/fonts/` | Inter variable + JetBrains Mono (SIL OFL). System font (SF Pro) is preferred on Apple devices |
| `templates/base.html` | Landmarks, skip link, sidebar. Blocks unchanged: `title`, `extra_styles`, `content`, `extra_scripts` |

## Contract that page templates rely on (do not break)

- Globals: `authenticatedFetch`, `getApiKey`, `setApiKey`, `getCsrfToken`, `registerActions`, `StreamTVActions`, `openWindow`, `whenDomReady`, `bindActionHandlers`, `toggleTheme`, `convertMaterialIcons`, `iconMap`.
- `[data-action]` attributes: `data-args`, `data-action-event`, `data-self-only`, `data-prevent-default`, `data-stop-propagation`, `data-pass-event`.
- localStorage keys: `theme` (`dark`|`light`; absent = follow OS), `streamtv_api_key`, `streamtv_drawer`.
- Shell element IDs: `drawer`, `drawerOverlay`, `drawerToggleButton`, `themeToggleButton`, `themeIcon`, `statusIndicator`, `statusText`, `globalSearchInput`.
- Legacy CSS variables remain as aliases (`--primary`, `--surface`, `--divider`, `--text-primary`, `--apple-*` ...). New code should use the semantic tokens (`--accent`, `--accent-fill`, `--label`, `--label-2`, `--separator`, `--control-border`, `--success|error|warning[-solid]`).
- CSP: scripts and styles are served from `'self'`; no inline script is needed. Page scripts in `extra_scripts` still use `nonce="{{ request.state.csp_nonce }}"`.

## Rules for new UI

1. Text on a solid fill uses `--accent-fill` / `--*-solid` (white text >= 4.5:1). `--accent` is for text/links on surfaces.
2. Never convey state by colour alone (status dot is solid vs. ring; badges carry text).
3. Icons: `<span class="material-icons" aria-hidden="true">name</span>`; add the name to `icons.js` map if new. Icon-only buttons need `aria-label`.
4. Every page has exactly one level-1 heading (`<h1>` or `role="heading" aria-level="1"`); every form control has a label or `aria-label`.
5. Interactive targets >= 40px (44px on coarse pointers); keep `:focus-visible` rings.
6. Respect `prefers-reduced-motion`, `prefers-contrast`, `forced-colors`.

## 2026 web platform extras

- `site.webmanifest` + apple-touch / favicon links for installable / home-screen use
- Dual `theme-color` metas (light + dark) kept in sync by `core.js`
- `@view-transition { navigation: auto }` (progressive)
- `100dvh`, `safe-area-inset-*`, sticky table headers, `content-visibility` on cards
- Global search indexes nav pages as well as channels/media; `aria-live` announces result counts
- Search field uses `type="search"` + `enterkeyhint="search"`

## Verifying

Run the server, then audit every page with axe-core (WCAG 2.0-2.2 A/AA + best practices) in both themes. Expected result: 0 violations.
