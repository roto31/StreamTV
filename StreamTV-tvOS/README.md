## StreamTV-tvOS client blueprint

This is a Swift Package scaffold for a tvOS client that consumes the StreamTV backend (M3U/XMLTV/HLS) and provides a UI for browsing channels, viewing an EPG, and playing streams. The package also outlines how to call a backend endpoint to create new channels from user-provided URLs (Archive.org, YouTube, or generic HTTP sources).

### FastAPI endpoint contract (server-side)

- `POST /api/channels`
  - Auth: bearer token or API key (match your backend security).
  - Body (JSON):
    ```json
    {
      "url": "https://archive.org/details/example",
      "source": "archive",           // "archive" | "youtube" | "http"
      "name": "Optional display name",
      "number": "Optional channel number/string"
    }
    ```
  - Behavior: validate URL, probe metadata (HEAD/yt-dlp/archive.org), assign channel number if absent, persist channel + schedule, regenerate EPG.
  - Responses:
    - 201: `{ "channel_number": "123", "name": "Foo", "status": "created|updated" }`
    - 400: validation error (bad URL/source)
    - 401/403: auth failure
    - 500: internal error (probe/import failed)

Consider also:
- `DELETE /api/channels/{number}` to remove a channel.
- Optional `GET /api/channels` (JSON) to avoid parsing M3U on the client.

### Client modules
- `M3UService` / `XMLTVService`: fetch and parse playlist and guide.
- `ChannelAdminService`: call `POST /api/channels` to create channels from URLs.
- `AppState`: holds channels, programmes, and settings (base URL, token).
- `Views`: channel list, EPG grid, player, add-channel form.
- `Caching`: in-memory + URLCache; optional disk cache for XMLTV/M3U blobs.
- `Retry`: simple exponential backoff on fetch failures.

### SwiftUI EPG grid recipe (concept)
- Use `UICollectionViewCompositionalLayout` (UIKit in SwiftUI via `UIViewControllerRepresentable`) or a SwiftUI `ScrollView` with horizontal time axis and vertical channels.
- Model: `Channel` + `[Programme]` keyed by channelId.
- Layout: rows per channel; columns for time slices; position programmes using `GeometryReader` relative to timeline start; use `LazyHStack` inside a `ScrollView`.
- “Now” indicator: vertical line at current time.

### Project layout
- `Package.swift` — tvOS 15 library target.
- `Sources/StreamTVClient/Models.swift`
- `Sources/StreamTVClient/Services.swift`
- `Sources/StreamTVClient/EPGView.swift`
- Add your own app target in Xcode that depends on `StreamTVClient`.

### Usage (local dev)
1) Open in Xcode > Add Package (local path).
2) Create a tvOS app target; add `StreamTVClient` as a dependency.
3) In `AppState`, set `baseURL` to your StreamTV server (e.g., `http://100.70.119.112:8410`) and optional token.
4) Fetch channels/EPG, render the EPG grid, and play HLS via `AVPlayer`.

### Notes
- Ensure ATS allows your server host/port (or use HTTPS).
- For LAN discovery, add `NSLocalNetworkUsageDescription` and, if you use Bonjour/SSDP, the service types in `NSBonjourServices`.
- Keep channel creation endpoint protected; do not expose without auth.
