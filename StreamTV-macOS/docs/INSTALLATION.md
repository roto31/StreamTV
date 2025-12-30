# StreamTV Installation Guide

## Requirements

- Python 3.10 or higher
- pip (Python package manager)
- FFmpeg (optional, for advanced streaming features)

## Installation Steps

### 1. Clone or Download

If you have the source code:
```bash
cd streamtv
```

### 2. Create Virtual Environment (Recommended)

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure

Copy the example configuration:
```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml` with your settings:
```yaml
server:
  host: "0.0.0.0"
  port: 8410
  base_url: "http://localhost:8410"

database:
  url: "sqlite:///./streamtv.db"

youtube:
  enabled: true
  quality: "best"

archive_org:
  enabled: true
  preferred_format: "h264"
```

### 5. Initialize Database

The database will be automatically initialized on first run.

### 6. Run the Server

```bash
python -m streamtv.main
```

Or using uvicorn directly:
```bash
uvicorn streamtv.main:app --host 0.0.0.0 --port 8410
```

### 7. Access the Application

- Web Interface: http://localhost:8410
- API Documentation: http://localhost:8410/docs
- IPTV Playlist: http://localhost:8410/iptv/channels.m3u
- EPG: http://localhost:8410/iptv/xmltv.xml

## Docker Installation (Optional)

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-m", "streamtv.main"]
```

Build and run:
```bash
docker build -t streamtv .
docker run -p 8410:8410 -v $(pwd)/config.yaml:/app/config.yaml streamtv
```

## Browser Compatibility

StreamTV uses HLS (HTTP Live Streaming) for browser playback, ensuring compatibility with modern browsers:

- **Chrome/Edge**: Full HLS support via HLS.js library
- **Safari**: Native HLS support (no additional libraries needed)
- **Firefox**: Full HLS support via HLS.js library

The web player automatically detects browser capabilities and uses the best available method. For best results:
- Use a modern browser with JavaScript enabled
- Ensure your browser is up to date
- If playback fails, try using VLC Media Player with the M3U playlist

### Troubleshooting Browser Playback

If channels don't play in the browser:
1. Check browser console for errors (F12 → Console)
2. Verify HLS endpoint is accessible: `curl http://localhost:8410/iptv/channel/{number}.m3u8`
3. Try a different browser
4. Use VLC Media Player with the M3U playlist: `http://localhost:8410/iptv/channels.m3u`

## Configuration Options

### Server Configuration

- `host`: Server host (default: "0.0.0.0")
- `port`: Server port (default: 8410)
- `base_url`: Base URL for IPTV streams

### Database Configuration

- `url`: Database connection URL
  - SQLite: `sqlite:///./streamtv.db`
  - PostgreSQL: `postgresql://user:password@localhost/streamtv`

### Streaming Configuration

- `buffer_size`: Buffer size for streaming (default: 8192)
- `chunk_size`: Chunk size for streaming (default: 1024)
- `timeout`: Request timeout in seconds (default: 30)
- `max_retries`: Maximum retry attempts (default: 3)

### YouTube Configuration

- `enabled`: Enable YouTube streaming (default: true)
- `quality`: Video quality preference (default: "best")
- `extract_audio`: Extract audio only (default: false)

### Archive.org Configuration

- `enabled`: Enable Archive.org streaming (default: true)
- `preferred_format`: Preferred video format (default: "h264")

### Security Configuration

- `api_key_required`: Require API key for access (default: false)
- `access_token`: Access token if required

## Troubleshooting

### Port Already in Use

If port 8410 is already in use, change it in `config.yaml`:
```yaml
server:
  port: 8500
```

### Database Errors

If you encounter database errors, delete the database file and restart:
```bash
rm streamtv.db
python -m streamtv.main
```

### YouTube Streaming Issues

YouTube may rate limit requests. If you encounter issues:
1. Reduce the number of concurrent requests
2. Use a VPN or proxy
3. Check YouTube's terms of service

### Archive.org Streaming Issues

Archive.org may have rate limits. If you encounter issues:
1. Reduce request frequency
2. Check Archive.org's API status
3. Verify the item identifier is correct

## Upgrading

To upgrade StreamTV:

1. Pull the latest code
2. Update dependencies:
   ```bash
   pip install -r requirements.txt --upgrade
   ```
3. Restart the server

## Uninstallation

To uninstall StreamTV:

1. Stop the server
2. Remove the virtual environment:
   ```bash
   deactivate
   rm -rf venv
   ```
3. Optionally remove the database:
   ```bash
   rm streamtv.db
   ```
