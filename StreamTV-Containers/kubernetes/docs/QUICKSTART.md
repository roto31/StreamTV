# StreamTV Quick Start Guide

## Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure:**
   ```bash
   cp config.example.yaml config.yaml
   # Edit config.yaml if needed
   ```

3. **Run:**
   ```bash
   python -m streamtv.main
   ```

## Basic Usage

### 1. Create a Channel

```bash
curl -X POST http://localhost:8410/api/channels \
  -H "Content-Type: application/json" \
  -d '{
    "number": "1",
    "name": "My YouTube Channel",
    "group": "Entertainment"
  }'
```

### 2. Add a YouTube Video

```bash
curl -X POST http://localhost:8410/api/media \
  -H "Content-Type: application/json" \
  -d '{
    "source": "youtube",
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
  }'
```

### 3. Create a Playlist

```bash
curl -X POST http://localhost:8410/api/playlists \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Playlist",
    "channel_id": 1
  }'
```

### 4. Add Video to Playlist

```bash
curl -X POST http://localhost:8410/api/playlists/1/items/1
```

### 5. Access IPTV Streams

- **M3U Playlist:** http://localhost:8410/iptv/channels.m3u
- **EPG:** http://localhost:8410/iptv/xmltv.xml
- **Channel Stream:** http://localhost:8410/iptv/channel/1.m3u8

## Using with IPTV Clients

### VLC Media Player

1. Open VLC
2. Go to Media → Open Network Stream
3. Enter: `http://localhost:8410/iptv/channels.m3u`
4. Click Play

### Kodi

1. Install IPTV Simple Client addon
2. Configure:
   - M3U Playlist URL: `http://localhost:8410/iptv/channels.m3u`
   - EPG URL: `http://localhost:8410/iptv/xmltv.xml`

### Plex

1. Install xTeVe or similar IPTV proxy
2. Configure with StreamTV endpoints

## Adding Archive.org Content

```bash
curl -X POST http://localhost:8410/api/media \
  -H "Content-Type: application/json" \
  -d '{
    "source": "archive_org",
    "url": "https://archive.org/details/identifier"
  }'
```

## Scheduling

Create a schedule for a channel:

```bash
curl -X POST http://localhost:8410/api/schedules \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": 1,
    "playlist_id": 1,
    "start_time": "2024-01-01T00:00:00",
    "repeat": true
  }'
```

## API Documentation

Interactive API documentation is available at:
- Swagger UI: http://localhost:8410/docs
- ReDoc: http://localhost:8410/redoc

## Troubleshooting

### Port Already in Use

Change the port in `config.yaml`:
```yaml
server:
  port: 8500
```

### YouTube Videos Not Loading

- Check your internet connection
- Verify the YouTube URL is valid
- Check YouTube's terms of service

### Archive.org Content Not Loading

- Verify the identifier is correct
- Check Archive.org's API status
- Ensure the item has video files

## Next Steps

- Read the full [API Documentation](API.md)
- Check [Installation Guide](INSTALLATION.md)
- Explore the codebase structure
