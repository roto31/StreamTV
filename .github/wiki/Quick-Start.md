# Quick Start Guide

Get StreamTV up and running in 5 minutes!

## Prerequisites

- Python 3.8+ installed
- Internet connection
- 5 minutes of time

## Step 1: Install StreamTV

### macOS (Automated)
```bash
./install_macos.sh
```

### Manual Installation
```bash
# Clone repository
git clone https://github.com/yourusername/streamtv.git
cd streamtv

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure
cp config.example.yaml config.yaml
```

## Step 2: Start the Server

```bash
python -m streamtv.main
```

You should see:
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8410
```

## Step 3: Verify It's Working

Open your browser and visit:
- **Web Interface**: http://localhost:8410
- **API Docs**: http://localhost:8410/docs
- **IPTV Playlist**: http://localhost:8410/iptv/channels.m3u

## Step 4: Create Your First Channel

### Using the API

```bash
curl -X POST http://localhost:8410/api/channels \
  -H "Content-Type: application/json" \
  -d '{
    "number": "1",
    "name": "My First Channel",
    "group": "Entertainment"
  }'
```

### Using the Web Interface

1. Navigate to http://localhost:8410
2. Click "Create Channel"
3. Fill in the form
4. Click "Create"

## Step 5: Add Media

### Add a YouTube Video

```bash
curl -X POST http://localhost:8410/api/media \
  -H "Content-Type: application/json" \
  -d '{
    "source": "youtube",
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
  }'
```

### Add Archive.org Content

```bash
curl -X POST http://localhost:8410/api/media \
  -H "Content-Type: application/json" \
  -d '{
    "source": "archive_org",
    "url": "https://archive.org/details/identifier"
  }'
```

## Step 6: Create a Collection

```bash
curl -X POST http://localhost:8410/api/collections \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Collection"
  }'
```

## Step 7: Add Media to Collection

```bash
curl -X POST http://localhost:8410/api/collections/1/items/1
```

## Step 8: Create a Schedule

### Using the Interactive Creator

```bash
./scripts/create_schedule.sh
```

### Manual YAML Creation

Create `schedules/my-channel.yml`:

```yaml
name: My First Channel
description: A simple channel with YouTube content

content:
  - key: my_content
    collection: My Collection
    order: chronological

sequence:
  - key: main_sequence
    items:
      - all: my_content

playout:
  - sequence: main_sequence
  - repeat: true
```

## Step 9: Access Your Channel

### M3U Playlist
```
http://localhost:8410/iptv/channels.m3u
```

### EPG (Electronic Program Guide)
```
http://localhost:8410/iptv/xmltv.xml
```

### HLS Stream
```
http://localhost:8410/iptv/channel/1.m3u8
```

## Step 10: Watch in Your IPTV Client

### VLC Media Player

1. Open VLC
2. Media → Open Network Stream
3. Enter: `http://localhost:8410/iptv/channels.m3u`
4. Click Play

### Kodi

1. Install "IPTV Simple Client" addon
2. Configure:
   - M3U Playlist URL: `http://localhost:8410/iptv/channels.m3u`
   - EPG URL: `http://localhost:8410/iptv/xmltv.xml`

### Plex

1. Install xTeVe or similar IPTV proxy
2. Configure with StreamTV endpoints
3. Add to Plex as Live TV source

## Common Commands

### List Channels
```bash
curl http://localhost:8410/api/channels
```

### List Media
```bash
curl http://localhost:8410/api/media
```

### Get Channel Details
```bash
curl http://localhost:8410/api/channels/1
```

### Update Channel
```bash
curl -X PUT http://localhost:8410/api/channels/1 \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated Name"}'
```

### Delete Channel
```bash
curl -X DELETE http://localhost:8410/api/channels/1
```

## Next Steps

- Read the [Beginner Guide](Beginner-Guide) for more detailed instructions
- Explore [Configuration](Configuration) options
- Learn about [Schedules](Schedules) for advanced channel programming
- Check out [API Reference](API-Reference) for complete API documentation

## Troubleshooting

### Server Won't Start

**Port in use:**
```yaml
# config.yaml
server:
  port: 8500  # Change from 8410
```

**Python not found:**
```bash
# Check Python version
python3 --version  # Should be 3.8+

# If not found, install Python
# macOS: brew install python3
# Linux: sudo apt install python3
```

### Media Won't Load

**Check URL:**
- Ensure YouTube URL is valid
- Verify Archive.org identifier exists

**Check logs:**
```bash
# Look for error messages in terminal
```

### Can't Access from Other Devices

**Update base_url in config.yaml:**
```yaml
server:
  base_url: "http://YOUR_IP:8410"  # Replace YOUR_IP
```

**Firewall:**
- Ensure port 8410 is open
- Check firewall settings

## Getting Help

- Check the [Troubleshooting](Troubleshooting) page
- Review [Common Issues](Common-Issues)
- Open an issue on GitHub
- Check the [FAQ](FAQ)

---

**Congratulations!** You've successfully set up StreamTV. Now explore the [Documentation](Home) to learn more advanced features.

