# macOS app — Web UI sidebar

StreamTV.app sidebar includes **Web UI** (WKWebView of local server) so every WebUI admin action works in-app without Safari.

```mermaid
flowchart LR
  Sidebar --> Channels
  Sidebar --> Guide
  Sidebar --> Manage
  Sidebar --> Admin
  Sidebar --> WebUI["Web UI WKWebView"]
  Sidebar --> Settings
  WebUI --> Local["127.0.0.1 WebUI"]
  Admin --> Local
  Settings --> TroubleNative["Troubleshooting section"]
  TroubleNative --> ScriptsAPI["/api/scripts/*"]
  WebUI --> TroublePage["/settings/troubleshooting"]
  TroublePage --> ScriptsAPI
```

Settings **Switch to Web UI tab** selects that sidebar item; **Open in Browser** remains available. Native **Settings → Troubleshooting** mirrors the WebUI Scripts catalog (hover help + Run).
