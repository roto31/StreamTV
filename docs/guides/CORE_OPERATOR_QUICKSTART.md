# Core operator quickstart

1. **Dashboard** (`/`) — verify YouTube and Archive.org auth tiles are green (Plex EPG settings remain under Settings when used).
2. **Build** — [Channel Builder](/builder) for Archive.org / YouTube URL-first channels, or [Import](/import) for YAML migration.
3. **Channels** (`/channels`) — enable channel; playout reset if needed.
4. **Schedules** (`/schedules`) — read-only inventory of `schedules/{n}.yml` (edit YAML on disk; no web create).
5. **Tune** — Browser [Player preview](PLAYER_PREVIEW.md) (`/player` → `/player/live/{n}.ts`) or HDHomeRun (`/discover.json`, `/auto/v{n}`).
6. **Guide** — `/iptv/xmltv.xml` (native StreamTV XMLTV).

Retired from the live UI: Collections (`/collections` → `/media`), AI Recovery / Foundation Models / Ollama. Ops healing = scripts only.

Docs: [Import vs Builder](IMPORT_VS_BUILDER.md) · [Schedules](../SCHEDULES.md) · [Player preview](PLAYER_PREVIEW.md) · [Soft deploy](SOFT_DEPLOY.md) · [HDHomeRun](../HDHOMERUN.md)
