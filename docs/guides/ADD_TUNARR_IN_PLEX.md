# Add Tunarr in Plex (via StreamTV proxy)

StreamTV hosts an HDHomeRun-shaped proxy so Plex’s **Live TV & DVR → Add device** GUI accepts Tunarr. Tunarr’s own `DeviceID` is the string `"Tunarr"` (not 8 hex), which Plex filters as incompatible. The proxy rewrites DeviceID and BaseURL; **video still streams from Tunarr** (`:8000`).

## Prerequisites

- StreamTV running with `tuner_manager.enabled: true` (default in `config.example.yaml`)
- Tunarr reachable at the URL in `tuner_manager.tuners[].url` (e.g. `http://192.0.2.1:8000`)
- Restart StreamTV after enabling or changing `tuner_manager`

## URLs to paste

| Purpose | URL |
|---------|-----|
| **Plex Add device** | `http://192.0.2.1:8410/tuners/proxy/tunarr` |
| **Guide (merged StreamTV + Tunarr)** | `http://192.0.2.1:8410/tuners/guide.xml` |

Replace the LAN IP/port with your StreamTV `server.base_url` if different.

Confirm live values:

```bash
curl -s http://127.0.0.1:8410/tuners | python3 -m json.tool
```

Use `plex_add_url` and `plex_guide_url` from that JSON.

## Plex steps

1. Open **Plex** → **Settings** → **Live TV & DVR**.
2. Choose **Set Up Plex DVR** or **Add device**.
3. Paste the **plex_add_url** (proxy root above). Do **not** paste Tunarr’s raw `:8000` URL if Plex previously rejected it.
4. When Plex asks for a guide source, paste **plex_guide_url** (`/tuners/guide.xml`) so both StreamTV and Tunarr channels share one XMLTV.
5. Complete channel mapping / lineup selection.
6. Tune a Tunarr channel (e.g. Disney Afternoon) and confirm playback.

## What the proxy fixes

| Field | Tunarr raw | Via StreamTV proxy |
|-------|------------|--------------------|
| `DeviceID` | `"Tunarr"` (rejected) | Stable 8-hex in `data/tuner_device_ids/tunarr` |
| `BaseURL` / `LineupURL` | Often `http://127.0.0.1:8000` | Proxy LAN URL under `/tuners/proxy/tunarr` |
| Lineup stream `URL` | Loopback host | Rewritten to Tunarr LAN host from config |
| Video path | — | Still Tunarr `:8000` (not proxied through StreamTV) |

## Operator page

Browse `http://192.0.2.1:8410/tuners` in a browser for copy-paste instructions.

## Related

- [Tuner visibility resolution](../TUNER_VISIBILITY_RESOLUTION.md)
- Config: `tuner_manager` in `config.example.yaml`
