# First channel in 15 minutes

Goal: one live channel on a fresh macOS install using the public demo pack.

## Prerequisites

- StreamTV.app from the [latest release](https://github.com/roto31/StreamTV/releases) (or `com.streamtv` from source)
- FFmpeg (`brew install ffmpeg`)
- Browser at `http://127.0.0.1:8410`

## Steps

1. **Confirm health**  
   `curl -s http://127.0.0.1:8410/api/health` → `"status":"healthy"`

2. **Import the demo channel**  
   - UI: **Import** → upload [`data/public_demo/channel_101.example.yaml`](../../data/public_demo/channel_101.example.yaml)  
   - Or API:  
     `curl -s -X POST http://127.0.0.1:8410/api/import/channels/yaml -F "file=@data/public_demo/channel_101.example.yaml"`

3. **Install the demo schedule**  
   Copy [`schedules/101.example.yml`](../../schedules/101.example.yml) to `schedules/101.yml` next to your `config.yaml` (Application Support for the app, or repo root for LaunchAgent). Soft-restart channel 101 if the server was already running.

4. **Check lineup**  
   - `curl -s http://127.0.0.1:8410/lineup.json | head`  
   - `curl -s http://127.0.0.1:8410/iptv/channels.m3u | head`  
   - `curl -s http://127.0.0.1:8410/iptv/xmltv.xml | head`

5. **Preview**  
   Open `/player` and tune **101**, or add StreamTV as an HDHomeRun tuner in Plex.

6. **Optional — MCP**  
   See [Channel Creator MCP](CHANNEL_CREATOR_MCP.md) and `scripts/setup_channel_creator_mcp.sh` for agent-driven builds (Archive.org + YouTube only).

## Notes

- Demo uses public-domain **Big Buck Bunny** (Archive.org). No cookies required.
- Schedules are YAML-only; the Schedules page is a read-only inventory.
- Remux keeps source resolution; Plex scales for the TV.
