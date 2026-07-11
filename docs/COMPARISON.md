# StreamTV vs ErsatzTV Comparison

This document compares StreamTV with ErsatzTV to highlight the differences and similarities.

## Key Differences

### Media Source
- **ErsatzTV**: Streams from local media library (requires downloading/storing media)
- **StreamTV**: Streams directly from YouTube and Archive.org (no local storage required)

### Architecture
- **ErsatzTV**: .NET/C# application
- **StreamTV**: Python/FastAPI application

### Storage Requirements
- **ErsatzTV**: Requires significant disk space for media library
- **StreamTV**: Minimal storage (only metadata and configuration)

### Setup Complexity
- **ErsatzTV**: Requires media library setup, scanning, and organization
- **StreamTV**: Just add URLs and start streaming

## Similarities

### API Structure
Both platforms follow similar RESTful API patterns:
- Channels management
- Media items
- Collections
- Playlists
- Schedules

### IPTV Support
Both provide:
- M3U playlist format
- XMLTV EPG format
- HLS streaming
- Transport stream support (planned)

### Features
- Channel creation and management
- Playlist scheduling
- EPG generation
- IPTV client compatibility

## API Endpoint Comparison

| Feature | ErsatzTV | StreamTV |
|---------|----------|----------|
| Get Channels | `GET /api/channels` | `GET /api/channels` |
| Create Channel | `POST /api/channels` | `POST /api/channels` |
| Get Media | `GET /api/media` | `GET /api/media` |
| Add Media | Via library scan | `POST /api/media` (with URL) |
| IPTV Playlist | `GET /iptv/channels.m3u` | `GET /iptv/channels.m3u` |
| EPG | `GET /iptv/xmltv.xml` | `GET /iptv/xmltv.xml` |
| HLS Stream | `GET /iptv/channel/{number}.m3u8` | `GET /iptv/channel/{number}.m3u8` |

## Use Cases

### Use ErsatzTV When:
- You have a large local media library
- You want full control over media quality
- You need offline access
- You want to avoid streaming dependencies

### Use StreamTV When:
- You want to stream from online sources
- You have limited storage space
- You want quick setup without media management
- You want to leverage YouTube/Archive.org content

## Migration Path

If you're using ErsatzTV and want to try StreamTV:

1. Export your channel configuration from ErsatzTV
2. Create corresponding channels in StreamTV
3. Add media items using URLs instead of local files
4. Recreate playlists and schedules
5. Update IPTV client configuration

## Future Enhancements

StreamTV could add:
- Support for more streaming sources (Vimeo, Dailymotion, etc.)
- Local media library support (hybrid mode)
- Advanced transcoding options
- Better caching mechanisms
- Multi-user support

## Performance Considerations

### ErsatzTV
- Fast local streaming
- No internet dependency
- Higher storage costs

### StreamTV
- Depends on internet connection
- No storage costs
- Potential for streaming delays
- Bandwidth dependent

## Conclusion

StreamTV is designed as a complementary solution to ErsatzTV, focusing on online streaming sources rather than local media. Both serve different use cases and can coexist in different scenarios.
