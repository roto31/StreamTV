# Native admin parity

| Phase | Surfaces |
|-------|----------|
| P1 | Dashboard, Channels, Import, Auth, Settings subtree, Logs, Health, Cache, Test stream, Updates |
| P2 | Media, Playlists, Playouts, Schedules, Builder, Documentation |

```mermaid
flowchart LR
  Native["Native Admin hub"] --> WV["WKWebView path"]
  WV --> API["Same FastAPI as WebUI"]
  NativeTab["Native Channels/Guide"] --> API
```

Full WebUI remains on the **Web UI** tab as fallback while individual Swift forms expand.
