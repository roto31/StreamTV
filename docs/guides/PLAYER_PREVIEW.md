# Browser `/player` preview

StreamTV serves an in-browser channel preview at **`GET /player`**. It is for
operators and local debugging. **Plex / Emby / Jellyfin HDHomeRun tuning is
unchanged** (`/discover.json`, `/lineup.json`, `/hdhomerun/auto/v{n}`, `/auto/v{n}`).

## How it works

1. Open `http://<host>:8410/player` (optional `?channel=` / channel picker).
2. The page uses **mpegts.js** against **`GET /player/live/{channel_number}.ts`**.
3. That endpoint copy-remuxes the continuous IPTV join (regenerated PTS + SPS/PPS)
   and waits for a mid-join keyframe before sending playable video.
4. CSP allows `worker-src 'self' blob:` for the mpegts worker.
5. Optional **VLC handoff**: `vlc://open?url=…`, channel M3U, or raw `.ts`.

## Related endpoints

| Path | Role |
|------|------|
| `GET /player` | HTML preview UI |
| `GET /player/live/{n}.ts` | Remuxed MPEG-TS for mpegts.js |
| `GET /iptv/channel/{n}.ts` | Continuous MPEG-TS (same playout as HDHomeRun) |
| `GET /iptv/channel/{n}.m3u8` | HLS playlist (separate path; not the primary `/player` feed) |
| `POST /api/channels/by-number/{n}/stream-restart` | Soft-restart one channel stream |
| `POST /api/channels/stream-restart-all` | Soft-restart all channel streams |

## Soft deploy vs kickstart

Refreshing a channel stream after YAML import uses soft deploy
(`scripts/deploy_soft.sh` / stream-restart APIs). That does **not** reload Python
modules. After `streamtv/` code changes, use
`launchctl kickstart -k gui/$(id -u)/com.streamtv`. See [Soft deploy](SOFT_DEPLOY.md).

## Verify

```bash
curl -sf -o /dev/null -w '%{http_code}\n' 'http://127.0.0.1:8410/player'
curl -s -m 12 -o /tmp/player_live.ts -w 'HTTP %{http_code} size=%{size_download}\n' \
  'http://127.0.0.1:8410/player/live/80.ts'
ffprobe -v error -show_entries stream=codec_type,codec_name -of default=nw=1 /tmp/player_live.ts
```

**Pass:** `/player` returns 200; live TS size ≫ 8192 with `h264` + `aac` (after keyframe wait).

## Related

- [Core operator quickstart](CORE_OPERATOR_QUICKSTART.md)
- [Soft deploy](SOFT_DEPLOY.md)
- [Plex video hold](PLEX_VIDEO_HOLD.md) — Plex path only; `/player` is separate
- Architecture Mermaid: [ARCHITECTURE.md](../../ARCHITECTURE.md)
