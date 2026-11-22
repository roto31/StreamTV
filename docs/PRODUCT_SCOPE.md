# StreamTV product scope

**Platform:** macOS only (signed DMG).  
**Tip version:** see root [`VERSION`](../VERSION).

## In scope (core)

| Area | What it is |
|------|------------|
| Sources (Builder) | **Archive.org** and **YouTube** only |
| Schedules | On-disk `schedules/{n}.yml` (playout + XMLTV authority). Web create/edit retired |
| Delivery | HDHomeRun emulation + IPTV M3U (`/iptv/channels.m3u`) + XMLTV |
| Clients | Plex / Emby / Jellyfin Live TV; VLC / Kodi via M3U |
| Remux | Source resolution passthrough; clients scale for display |
| Auth | YouTube (cookies/OAuth/passkey) and Archive.org |
| Channel creation | Web Channel Builder and optional **Channel Creator MCP** |
| Ops | Soft deploy, script healers (stalled FFmpeg, TunarrRAM), backup/restore |

## Out of scope (retired / unsupported)

- In-app AI recovery / AutoHealer / Foundation Models / Ollama heal
- Collections UI (Manual / Smart / Multi)
- Linux product or installer
- PBS or Plex as **Channel Builder** first-party sources (DRM / parked)
- PBS authentication UI (DRM)
- Watermarks UI
- Resolutions UI (no forced resize; remux keeps source resolution)
- Schedule-items web editor (YAML is authority)

Parked sources live under `parked/` in the private tree and are **not** loaded.

## Optional peers

- **Tunarr hybrid** (`/tuners`) when `tuner_manager` is enabled — merged EPG / proxy only
- **Plex API settings** — EPG guide reload credentials, not a library browser
- **Channel Creator MCP** — optional AI-host tooling; not required for core operation
