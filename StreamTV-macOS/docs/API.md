# StreamTV API Documentation

This document describes the RESTful API for StreamTV, modeled after ErsatzTV's API structure.

## Base URL

All API endpoints are prefixed with `/api` unless otherwise noted.

## Authentication

If `api_key_required` is enabled in configuration, include the access token as a query parameter:
```
?access_token=YOUR_TOKEN
```

## Endpoints

### Channels

#### Get All Channels
```
GET /api/channels
```

Returns a list of all channels.

**Response:**
```json
[
  {
    "id": 1,
    "number": "1",
    "name": "My Channel",
    "group": "Entertainment",
    "enabled": true,
    "logo_path": null,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
]
```

#### Get Channel by ID
```
GET /api/channels/{channel_id}
```

#### Get Channel by Number
```
GET /api/channels/number/{channel_number}
```

#### Create Channel
```
POST /api/channels
Content-Type: application/json

{
  "number": "1",
  "name": "My Channel",
  "group": "Entertainment",
  "enabled": true,
  "logo_path": null
}
```

#### Update Channel
```
PUT /api/channels/{channel_id}
Content-Type: application/json

{
  "name": "Updated Channel Name"
}
```

#### Delete Channel
```
DELETE /api/channels/{channel_id}
```

### Media Items

#### Get All Media Items
```
GET /api/media?source=youtube&skip=0&limit=100
```

Query parameters:
- `source`: Filter by source (youtube, archive_org)
- `skip`: Number of items to skip (pagination)
- `limit`: Maximum number of items to return

#### Get Media Item by ID
```
GET /api/media/{media_id}
```

#### Add Media Item
```
POST /api/media
Content-Type: application/json

{
  "source": "youtube",
  "url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "title": "Video Title",
  "description": "Video description",
  "duration": 3600,
  "thumbnail": "https://..."
}
```

The system will automatically detect the source and fetch metadata if the URL is valid.

#### Delete Media Item
```
DELETE /api/media/{media_id}
```

### Collections

#### Get All Collections
```
GET /api/collections
```

#### Get Collection by ID
```
GET /api/collections/{collection_id}
```

#### Create Collection
```
POST /api/collections
Content-Type: application/json

{
  "name": "My Collection",
  "description": "Collection description"
}
```

#### Add Item to Collection
```
POST /api/collections/{collection_id}/items/{media_id}
```

#### Remove Item from Collection
```
DELETE /api/collections/{collection_id}/items/{media_id}
```

#### Delete Collection
```
DELETE /api/collections/{collection_id}
```

### Playlists

#### Get All Playlists
```
GET /api/playlists
```

#### Get Playlist by ID
```
GET /api/playlists/{playlist_id}
```

#### Create Playlist
```
POST /api/playlists
Content-Type: application/json

{
  "name": "My Playlist",
  "description": "Playlist description",
  "channel_id": 1
}
```

#### Add Item to Playlist
```
POST /api/playlists/{playlist_id}/items/{media_id}
```

#### Remove Item from Playlist
```
DELETE /api/playlists/{playlist_id}/items/{item_id}
```

#### Delete Playlist
```
DELETE /api/playlists/{playlist_id}
```

### Schedules

#### Get All Schedules
```
GET /api/schedules?channel_id=1
```

Query parameters:
- `channel_id`: Filter by channel ID

#### Get Schedule by ID
```
GET /api/schedules/{schedule_id}
```

#### Create Schedule
```
POST /api/schedules
Content-Type: application/json

{
  "channel_id": 1,
  "playlist_id": 1,
  "start_time": "2024-01-01T00:00:00",
  "end_time": "2024-01-01T23:59:59",
  "repeat": false
}
```

#### Delete Schedule
```
DELETE /api/schedules/{schedule_id}
```

## IPTV Endpoints

### Channel Playlist (M3U)
```
GET /iptv/channels.m3u?mode=mixed&access_token=TOKEN
```

Returns an M3U playlist of all enabled channels.

Query parameters:
- `mode`: Stream mode (hls, ts, mixed)
- `access_token`: Access token if required

Notes:
- **Default (`mode=mixed`)**: Entries point to HLS (`.m3u8`) URLs for browser/HLS players.
- **TS mode (`mode=ts`)**: Entries point to continuous MPEG-TS (`.ts`) URLs that use the same
  continuous playout method as the HDHomeRun endpoint. This is recommended for Plex IPTV if you
  want true live join-in-progress behavior.

### Electronic Program Guide (XMLTV)
```
GET /iptv/xmltv.xml?access_token=TOKEN
```

Returns XMLTV format EPG data for all channels.

### HLS Stream
```
GET /iptv/channel/{channel_number}.m3u8?access_token=TOKEN
```

Returns HLS playlist for a specific channel.

### Transport Stream
```
GET /iptv/channel/{channel_number}.ts?access_token=TOKEN
```

Returns a **continuous MPEG-TS transport stream** for a channel, using the same
ErsatzTV-style continuous playout method as the HDHomeRun `/hdhomerun/auto/v{channel_number}` endpoint:

- Uses `ChannelManager` to join the live timeline in progress.
- Falls back to an on-demand MPEG-TS streamer if `ChannelManager` is not available.

This endpoint is ideal for IPTV clients (e.g., Plex IPTV) that expect a TS stream and
should be used together with `mode=ts` in the channels M3U.

### Direct Media Stream
```
GET /iptv/stream/{media_id}?access_token=TOKEN
```

Streams a media item directly.

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message"
}
```

HTTP Status Codes:
- `200`: Success
- `201`: Created
- `400`: Bad Request
- `401`: Unauthorized
- `404`: Not Found
- `500`: Internal Server Error
- `501`: Not Implemented

## Examples

### Complete Workflow

1. Create a channel:
```bash
curl -X POST http://localhost:8410/api/channels \
  -H "Content-Type: application/json" \
  -d '{"number": "1", "name": "My Channel"}'
```

2. Add a YouTube video:
```bash
curl -X POST http://localhost:8410/api/media \
  -H "Content-Type: application/json" \
  -d '{"source": "youtube", "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```

3. Create a playlist:
```bash
curl -X POST http://localhost:8410/api/playlists \
  -H "Content-Type: application/json" \
  -d '{"name": "My Playlist", "channel_id": 1}'
```

4. Add video to playlist:
```bash
curl -X POST http://localhost:8410/api/playlists/1/items/1
```

5. Get IPTV playlist:
```bash
curl http://localhost:8410/iptv/channels.m3u
```
