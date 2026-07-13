# StreamTV + Tunarr hybrid operator guide

StreamTV and [Tunarr](https://github.com/chrisbenincasa/tunarr) complement each other. Use this guide to choose the right tool for each workflow.

## When to use StreamTV Builder

- YouTube, Archive.org, PBS, and custom HTTP sources
- YAML-first channel inventory (`data/unified/*.channel.yaml`)
- Continuous playout from `schedules/{number}.yml`
- Channel Builder at `/builder`

## When to use Tunarr

- Plex / Jellyfin / Emby library browsing and slot scheduling
- Custom Shows synced from Plex playlists
- Smart Collections and filler lists
- Tunarr web UI at `http://<tunarr-host>:8000/web`

## When to use both (recommended for Plex households)

1. Configure `tuner_manager` in `config.yaml` (see [ADD_TUNARR_IN_PLEX.md](ADD_TUNARR_IN_PLEX.md)).
2. Add Tunarr in Plex using the StreamTV proxy URL from `/tuners`.
3. Point Plex DVR guide at merged EPG: `http://<streamtv>:8410/tuners/guide.xml`.
4. Browse Plex libraries in StreamTV Collections via `/api/integrations/tunarr/*` when Tunarr is reachable; native `/api/plex/*` is the fallback.

## API surfaces

| Need | StreamTV endpoint |
|------|-------------------|
| Tunarr health | `GET /api/integrations/tunarr/status` |
| Media sources | `GET /api/integrations/tunarr/media-sources` |
| Search | `GET /api/integrations/tunarr/search?q=...` |
| Custom shows | `GET /api/integrations/tunarr/custom-shows` |
| Smart collections | `GET /api/integrations/tunarr/smart-collections` |
| Native Plex libraries | `GET /api/plex/libraries` |
| Merged EPG | `GET /tuners/guide.xml` |

## EPG note

`config.plex.use_for_epg` is honored at the **merge layer** (`X-Merged-Sources` response header). StreamTV bedrock `iptv.py` is unchanged. Prefer `/tuners/guide.xml` in Plex DVR for a single guide covering StreamTV YAML channels and Tunarr channels.

## References

- [Tunarr channels](https://tunarr.com/configure/channels/)
- [Tunarr scheduling](https://tunarr.com/configure/scheduling/)
- [Tunarr custom shows](https://tunarr.com/configure/library/custom-shows/)
