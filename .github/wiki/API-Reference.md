# API Reference

Complete API documentation for StreamTV.

## Base URL

```
http://localhost:8410/api
```

## Authentication

If `api_key_required` is enabled in configuration, include the access token:

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8410/api/channels
```

Or as query parameter:

```bash
curl "http://localhost:8410/api/channels?access_token=YOUR_TOKEN"
```

## Endpoints

### Channels

#### List Channels
```http
GET /api/channels
```

**Response:**
```json
[
  {
    "id": 1,
    "number": "1",
    "name": "My Channel",
    "group": "Entertainment",
    "enabled": true
  }
]
```

#### Get Channel
```http
GET /api/channels/{id}
```

#### Create Channel
```http
POST /api/channels
Content-Type: application/json

{
  "number": "1",
  "name": "My Channel",
  "group": "Entertainment",
  "description": "Channel description"
}
```

#### Update Channel
```http
PUT /api/channels/{id}
Content-Type: application/json

{
  "name": "Updated Name"
}
```

#### Delete Channel
```http
DELETE /api/channels/{id}
```

### Media Items

#### List Media
```http
GET /api/media
```

**Query Parameters:**
- `source` - Filter by source (youtube, archive_org)
- `collection_id` - Filter by collection
- `limit` - Limit results
- `offset` - Offset for pagination

#### Get Media Item
```http
GET /api/media/{id}
```

#### Add Media Item
```http
POST /api/media
Content-Type: application/json

{
  "source": "youtube",
  "url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "title": "Optional Title",
  "description": "Optional Description"
}
```

#### Update Media Item
```http
PUT /api/media/{id}
Content-Type: application/json

{
  "title": "Updated Title"
}
```

#### Delete Media Item
```http
DELETE /api/media/{id}
```

### Collections

#### List Collections
```http
GET /api/collections
```

#### Get Collection
```http
GET /api/collections/{id}
```

#### Create Collection
```http
POST /api/collections
Content-Type: application/json

{
  "name": "My Collection"
}
```

#### Update Collection
```http
PUT /api/collections/{id}
Content-Type: application/json

{
  "name": "Updated Name"
}
```

#### Delete Collection
```http
DELETE /api/collections/{id}
```

#### Add Media to Collection
```http
POST /api/collections/{collection_id}/items/{media_id}
```

#### Remove Media from Collection
```http
DELETE /api/collections/{collection_id}/items/{media_id}
```

### Playlists

#### List Playlists
```http
GET /api/playlists
```

#### Get Playlist
```http
GET /api/playlists/{id}
```

#### Create Playlist
```http
POST /api/playlists
Content-Type: application/json

{
  "name": "My Playlist",
  "channel_id": 1
}
```

#### Update Playlist
```http
PUT /api/playlists/{id}
Content-Type: application/json

{
  "name": "Updated Name"
}
```

#### Delete Playlist
```http
DELETE /api/playlists/{id}
```

#### Add Media to Playlist
```http
POST /api/playlists/{playlist_id}/items/{media_id}
```

#### Remove Media from Playlist
```http
DELETE /api/playlists/{playlist_id}/items/{media_id}
```

### Schedules

#### List Schedules
```http
GET /api/schedules
```

#### Get Schedule
```http
GET /api/schedules/{id}
```

#### Create Schedule
```http
POST /api/schedules
Content-Type: application/json

{
  "channel_id": 1,
  "playlist_id": 1,
  "start_time": "2024-01-01T00:00:00",
  "repeat": true
}
```

#### Update Schedule
```http
PUT /api/schedules/{id}
Content-Type: application/json

{
  "repeat": false
}
```

#### Delete Schedule
```http
DELETE /api/schedules/{id}
```

### IPTV Endpoints

#### M3U Playlist
```http
GET /iptv/channels.m3u
```

**Query Parameters:**
- `access_token` - Access token (if required)

#### XMLTV EPG
```http
GET /iptv/xmltv.xml
```

**Query Parameters:**
- `access_token` - Access token (if required)
- `days` - Number of days (default: 7)

#### HLS Stream
```http
GET /iptv/channel/{channel_number}.m3u8
```

**Query Parameters:**
- `access_token` - Access token (if required)

#### Direct Stream
```http
GET /iptv/stream/{media_id}
HEAD /iptv/stream/{media_id}
```

**Headers:**
- `Range` - HTTP range request (for seeking)

**Query Parameters:**
- `access_token` - Access token (if required)

### HDHomeRun Endpoints

#### Discover
```http
GET /hdhomerun/discover.json
```

#### Lineup
```http
GET /hdhomerun/lineup.json
```

#### Lineup Status
```http
GET /hdhomerun/lineup_status.json
```

#### Device Status
```http
GET /hdhomerun/status.json
```

#### Stream Channel
```http
GET /hdhomerun/auto/v{channel_number}
```

#### Tuner Stream
```http
GET /hdhomerun/tuner{n}/stream?channel=auto:v{channel_number}
```

## Response Formats

### Success Response
```json
{
  "id": 1,
  "name": "Example"
}
```

### Error Response
```json
{
  "detail": "Error message"
}
```

### List Response
```json
[
  {
    "id": 1,
    "name": "Item 1"
  },
  {
    "id": 2,
    "name": "Item 2"
  }
]
```

## Status Codes

- `200 OK` - Success
- `201 Created` - Resource created
- `204 No Content` - Success, no content
- `400 Bad Request` - Invalid request
- `401 Unauthorized` - Authentication required
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

## Interactive Documentation

- **Swagger UI**: http://localhost:8410/docs
- **ReDoc**: http://localhost:8410/redoc

## Examples

### Complete Workflow

```bash
# 1. Create channel
CHANNEL_ID=$(curl -X POST http://localhost:8410/api/channels \
  -H "Content-Type: application/json" \
  -d '{"number": "1", "name": "My Channel"}' \
  | jq -r '.id')

# 2. Add media
MEDIA_ID=$(curl -X POST http://localhost:8410/api/media \
  -H "Content-Type: application/json" \
  -d '{"source": "youtube", "url": "https://www.youtube.com/watch?v=VIDEO_ID"}' \
  | jq -r '.id')

# 3. Create collection
COLLECTION_ID=$(curl -X POST http://localhost:8410/api/collections \
  -H "Content-Type: application/json" \
  -d '{"name": "My Collection"}' \
  | jq -r '.id')

# 4. Add media to collection
curl -X POST "http://localhost:8410/api/collections/$COLLECTION_ID/items/$MEDIA_ID"

# 5. Access IPTV stream
curl "http://localhost:8410/iptv/channel/1.m3u8"
```

## Rate Limiting

Currently, StreamTV does not implement rate limiting. Consider implementing rate limiting at the reverse proxy level for production deployments.

## Next Steps

- Explore [Channels](Channels) management
- Learn about [Schedules](Schedules)
- Check [HDHomeRun Integration](HDHomeRun-Integration)

