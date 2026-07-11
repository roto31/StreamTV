# StreamTV Intermediate Guide

**For Technicians - Configuration, Management, and Troubleshooting**

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Configuration System](#configuration-system)
3. [YAML File Structure](#yaml-file-structure)
4. [Channel Management](#channel-management)
5. [Schedule System](#schedule-system)
6. [Streaming System](#streaming-system)
7. [HDHomeRun Integration](#hdhomerun-integration)
8. [Advanced Troubleshooting](#advanced-troubleshooting)
9. [Script Usage](#script-usage)

---

## Architecture Overview

### System Components

StreamTV consists of several key components that work together:

```
┌─────────────────────────────────────────────────────────┐
│                    Web Interface                         │
│              (HTML/JavaScript Frontend)                  │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                  FastAPI Server                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │   API    │  │   IPTV    │  │ HDHomeRun│             │
│  │  Routes  │  │  Routes   │  │  Routes  │             │
│  └──────────┘  └──────────┘  └──────────┘             │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              Business Logic Layer                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  Scheduling  │  │  Streaming   │  │  Importers   │ │
│  │    Engine    │  │   Manager    │  │              │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              Data Layer                                  │
│  ┌──────────────┐  ┌──────────────┐                    │
│  │  Database    │  │  File System │                    │
│  │  (SQLite)    │  │  (YAML/Logs) │                    │
│  └──────────────┘  └──────────────┘                    │
└─────────────────────────────────────────────────────────┘
```

### Component Interactions

1. **Web Interface → API**: User actions trigger API calls
2. **API → Business Logic**: API routes call business logic functions
3. **Business Logic → Data**: Logic reads/writes to database and files
4. **Streaming → External**: Streams video from YouTube/Archive.org
5. **HDHomeRun → Plex**: Emulates HDHomeRun device for Plex integration

### Data Flow

**Channel Creation Flow:**
```
User uploads YAML → Import API → Channel Importer → 
Parse YAML → Create Collections → Create Media Items → 
Create Playlist → Create Channel → Database
```

**Streaming Flow:**
```
Client Request → IPTV Endpoint → Channel Manager → 
Schedule Engine → Stream Manager → YouTube/Archive.org → 
FFmpeg (MPEG-TS) → Client
```

---

## Configuration System

### Configuration File: `config.yaml`

Located in the project root, this file controls all StreamTV settings.

### Configuration Sections

#### Server Configuration
```yaml
server:
  host: "0.0.0.0"        # Listen on all interfaces
  port: 8410             # HTTP port
  base_url: "http://localhost:8410"  # Base URL for links
```

**When to Change:**
- Change `host` if you want to restrict access
- Change `port` if 8410 is already in use
- Change `base_url` if accessing from another computer

#### Database Configuration
```yaml
database:
  url: "sqlite:///./streamtv.db"  # SQLite database file
```

**When to Change:**
- Use a different database file path
- Switch to PostgreSQL/MySQL (requires code changes)

#### Streaming Configuration
```yaml
streaming:
  buffer_size: 8192      # Buffer size in bytes
  chunk_size: 1024       # Chunk size for streaming
  timeout: 30            # Timeout in seconds
  max_retries: 3         # Retry attempts
```

**When to Change:**
- Increase `buffer_size` for slower connections
- Increase `timeout` for slow sources
- Increase `max_retries` for unreliable sources

#### YouTube Configuration
```yaml
youtube:
  enabled: true
  quality: "best"        # best, worst, or specific quality
  extract_audio: false   # Extract audio only
```

**When to Change:**
- Set `quality` to "worst" for slower connections
- Enable `extract_audio` for audio-only channels

#### Archive.org Configuration
```yaml
archive_org:
  enabled: true
  preferred_format: "h264"
  username: null         # Your Archive.org username
  password: null         # Your Archive.org password
  use_authentication: false
```

**When to Change:**
- Add credentials for restricted content
- Set `use_authentication: true` after adding credentials

#### HDHomeRun Configuration
```yaml
hdhomerun:
  enabled: true
  device_id: "FFFFFFFF"  # Unique device ID
  friendly_name: "StreamTV HDHomeRun"
  tuner_count: 2        # Number of tuners
  enable_ssdp: true     # Enable discovery
```

**When to Change:**
- Change `device_id` if you have multiple StreamTV instances
- Increase `tuner_count` for more simultaneous streams
- Set `enable_ssdp: false` if port 1900 is in use

#### FFmpeg Configuration
```yaml
ffmpeg:
  ffmpeg_path: "/usr/local/bin/ffmpeg"
  ffprobe_path: "/usr/local/bin/ffprobe"
  log_level: "info"      # error, warning, info, debug
  threads: 0            # 0 = auto, or specific number
  hwaccel: null         # videotoolbox, vaapi, etc.
  hwaccel_device: null  # Device for hardware acceleration
  extra_flags: null     # Additional FFmpeg flags
```

**When to Change:**
- Set custom paths if FFmpeg is installed elsewhere
- Enable hardware acceleration for better performance
- Add `extra_flags` for advanced FFmpeg options

### Editing Configuration

**Via Web Interface:**
1. Go to Settings → FFmpeg
2. Edit values in the form
3. Click Save

**Via File:**
1. Edit `config.yaml` directly
2. Restart StreamTV for changes to take effect

---

## YAML File Structure

### Channel YAML Files

Channel YAML files define complete channels with all their content.

#### Basic Structure
```yaml
channels:
  - number: "1980"
    name: "1980 Winter Olympics"
    group: "Winter Olympics"
    description: "Channel description"
    enabled: true
    streams:
      - id: unique_id
        collection: "Collection Name"
        type: "event"
        year: 1980
        source: "youtube"  # or "archive"
        url: "https://www.youtube.com/watch?v=VIDEO_ID"
        notes: "Optional notes"
```

#### Required Fields

- **number**: Channel number (string, must be unique)
- **name**: Channel name
- **enabled**: true/false
- **streams**: List of media items

#### Stream Fields

- **id**: Unique identifier for this stream
- **collection**: Collection name (groups related items)
- **source**: "youtube" or "archive"
- **url**: Full URL to the video
- **type**: Content type (event, news, commercial, etc.)
- **year**: Year of content
- **runtime**: Duration in ISO 8601 format (PT3M44S = 3 minutes 44 seconds)
- **notes**: Optional description

#### Example Channel YAML
```yaml
channels:
  - number: "1980"
    name: "1980 Winter Olympics"
    group: "Winter Olympics"
    enabled: true
    streams:
      - id: opening_ceremony
        collection: "1980 Opening Ceremony"
        type: "event"
        year: 1980
        source: "youtube"
        url: "https://www.youtube.com/watch?v=uTW6jH3sk1k"
        runtime: "PT3M44S"
        notes: "Opening ceremony teaser"
```

### Schedule YAML Files

Schedule files define how content plays on a channel (ErsatzTV-style).

#### Basic Structure
```yaml
name: "Channel Name"
description: "Channel description"

content:
  - key: content_key
    collection: "Collection Name"
    order: chronological  # or shuffle

sequence:
  - name: "Main Sequence"
    items:
      - collection: "Collection Name"
      - duration: "00:30:00"  # Fill 30 minutes
        collection: "Filler Collection"
      - all: "Collection Name"  # Play all items

playout:
  - name: "Main Playout"
    sequence: "Main Sequence"
    repeat: true
```

#### Content Section

Defines available content collections:
```yaml
content:
  - key: main_content
    collection: "Main Show Collection"
    order: chronological
  - key: commercials
    collection: "Commercial Collection"
    order: shuffle  # Randomize order
```

#### Sequence Section

Defines playback sequences:
```yaml
sequence:
  - name: "Prime Time"
    items:
      # Play a collection
      - collection: "main_content"
      
      # Fill duration with filler
      - duration: "00:05:00"
        collection: "commercials"
      
      # Play all items in collection
      - all: "main_content"
      
      # Pre-roll (before main content)
      - pre_roll: true
        collection: "station_ids"
      
      # Mid-roll (during content)
      - mid_roll: true
        collection: "commercials"
      
      # Post-roll (after content)
      - post_roll: true
        collection: "sign_offs"
```

#### Playout Section

Defines how sequences are used:
```yaml
playout:
  - name: "24/7 Stream"
    sequence: "Prime Time"
    repeat: true  # Loop continuously
```

#### Advanced Sequence Options

**Duration-based Filler:**
```yaml
- duration: "00:30:00"  # Fill exactly 30 minutes
  collection: "Filler Collection"
  discard_attempts: 5  # Skip items that don't fit
```

**Time-based Scheduling:**
```yaml
- padToNext: "00:00:00"  # Pad to next hour
  collection: "Filler"
- padUntil: "12:00:00"   # Pad until noon
  collection: "Filler"
- waitUntil: "20:00:00"  # Wait until 8 PM
  collection: "Prime Time"
```

---

## Channel Management

### Creating Channels

#### Method 1: YAML Import (Recommended)

1. Create a channel YAML file (see structure above)
2. Go to Import in web interface
3. Upload or drag the YAML file
4. Click Import

#### Method 2: API

```bash
curl -X POST http://localhost:8410/api/channels \
  -H "Content-Type: application/json" \
  -d '{
    "number": "1980",
    "name": "1980 Winter Olympics",
    "group": "Winter Olympics",
    "enabled": true
  }'
```

#### Method 3: Script

```bash
python3 scripts/create_channel.py --number 1980 --name "1980 Olympics"
```

### Managing Channels

#### Enable/Disable
- **Web Interface**: Toggle switch in Channels page
- **API**: `PUT /api/channels/{channel_id}` with `{"enabled": true/false}`

#### Update Channel
- **Web Interface**: Click Edit on channel
- **API**: `PUT /api/channels/{channel_id}`

#### Delete Channel
- **Web Interface**: Click Delete (with confirmation)
- **API**: `DELETE /api/channels/{channel_id}`

### Channel Status

**Enabled**: Channel is active and streaming
**Disabled**: Channel exists but is not streaming
**No Content**: Channel has no playlists or schedules

---

## Schedule System

### How Schedules Work

1. **Content Definition**: Define what content is available
2. **Sequence Definition**: Define playback order and logic
3. **Playout Definition**: Define how sequences are used
4. **Timeline Calculation**: System calculates current position based on midnight start

### Schedule File Location

Schedule files are in the `schedules/` directory:
- Format: `mn-olympics-{year}.yml`
- Or: `{channel-name}.yml`

### Schedule Engine

The Schedule Engine:
- Parses schedule YAML files
- Generates playlists from sequences
- Handles repeats and loops
- Calculates timeline positions

### Timeline System

**Midnight Start**: All channels start at midnight (00:00:00) of their creation day
**System Time Sync**: Uses server system time to calculate current position
**Continuous Playback**: Streams continuously, clients join at current position

### Schedule Validation

Schedule files are validated against JSON schema:
- Location: `schemas/schedule.schema.json`
- Validates structure and data types
- Web interface shows validation errors

---

## Streaming System

### Stream Sources

#### YouTube
- Direct streaming via `yt-dlp`
- No downloads required
- Supports all YouTube formats
- Handles geo-restrictions

#### Archive.org
- Direct streaming from Archive.org
- Supports authentication for restricted content
- Multiple format support

### Stream Manager

The Stream Manager:
- Detects source type from URL
- Routes to appropriate adapter
- Handles errors and retries
- Manages stream URLs

### MPEG-TS Streaming

For HDHomeRun/Plex compatibility:
- Transcodes to MPEG-TS format
- Uses FFmpeg for transcoding
- Continuous streaming (no gaps)
- Hardware acceleration support

### Channel Manager

Manages continuous streams:
- Starts all channels on server startup
- Maintains timeline for each channel
- Broadcasts to multiple clients
- Handles client connections/disconnections

---

## HDHomeRun Integration

### How It Works

StreamTV emulates an HDHomeRun device:
1. **SSDP Discovery**: Broadcasts on network (port 1900)
2. **Discovery Endpoint**: `/hdhomerun/discover.json`
3. **Lineup Endpoint**: `/hdhomerun/lineup.json`
4. **Stream Endpoint**: `/hdhomerun/auto/v{channel_number}`

### Plex Setup

1. **Add Tuner**:
   - Plex → Settings → Live TV & DVR
   - Add Tuner → HDHomeRun
   - Enter: `http://YOUR_IP:8410/hdhomerun/discover.json`

2. **Add Guide**:
   - Use XMLTV URL: `http://YOUR_IP:8410/iptv/xmltv.xml`

3. **Map Channels**:
   - Plex will detect channels
   - Map to guide data

### Troubleshooting HDHomeRun

**Plex Can't Find Tuner:**
- Check SSDP is enabled
- Check firewall allows port 1900
- Try manual discovery URL

**Channels Not Appearing:**
- Check channels are enabled
- Check XMLTV guide is generating
- Verify channel numbers match

**Stream Won't Play:**
- Check FFmpeg is installed
- Check FFmpeg path in config
- Check logs for FFmpeg errors

---

## Advanced Troubleshooting

### Log Files

**Location**: `streamtv.log` (or configured path)

**Log Levels**:
- ERROR: Critical errors
- WARNING: Potential issues
- INFO: General information
- DEBUG: Detailed debugging

**View Logs**:
```bash
tail -f streamtv.log
```

### Common Issues

#### Issue: Channel Starts from Beginning

**Cause**: Timeline not initialized correctly

**Solution**:
1. Check channel `created_at` in database
2. Verify midnight calculation
3. Check system time is correct
4. Restart StreamTV

#### Issue: Streams Stop After First Video

**Cause**: Schedule not looping

**Solution**:
1. Check schedule has `repeat: true`
2. Verify sequence is complete
3. Check for errors in logs

#### Issue: FFmpeg Errors

**Cause**: FFmpeg configuration or missing codecs

**Solution**:
1. Verify FFmpeg installation: `ffmpeg -version`
2. Check FFmpeg path in config
3. Test FFmpeg command manually
4. Check hardware acceleration settings

#### Issue: Placeholder URLs

**Cause**: YAML has placeholder URLs

**Solution**:
1. Run cleanup script: `python3 scripts/cleanup_placeholders.py --execute`
2. Update YAML files with real URLs
3. Re-import channels

### Database Issues

**Check Database**:
```bash
sqlite3 streamtv.db ".tables"
sqlite3 streamtv.db "SELECT * FROM channels;"
```

**Backup Database**:
```bash
cp streamtv.db streamtv.db.backup
```

**Reset Database** (WARNING: Deletes all data):
```bash
rm streamtv.db
# Restart StreamTV to recreate
```

---

## Script Usage

### Import Channels Script

```bash
python3 scripts/import_channels.py path/to/channel.yml
```

**Options**:
- Validates YAML before import
- Creates collections and media items
- Creates playlists
- Creates or updates channel

### Cleanup Placeholders Script

```bash
python3 scripts/cleanup_placeholders.py [--execute]
```

**Options**:
- `--execute`: Actually delete (default is dry-run)
- Finds all placeholder URLs
- Removes from database

### Create Channel Script

```bash
python3 scripts/create_channel.py \
  --number 1980 \
  --name "1980 Olympics" \
  --group "Winter Olympics"
```

**Options**:
- `--number`: Channel number (required)
- `--name`: Channel name (required)
- `--group`: Channel group (optional)
- `--enabled`: Enable channel (default: true)

---

## Next Steps

- **Ready for Deep Dive?** → Read the [Expert Guide](./EXPERT_GUIDE.md)
- **Need Troubleshooting Help?** → Use [Troubleshooting Scripts](./TROUBLESHOOTING_SCRIPTS.md)
- **Want API Details?** → Read [API Documentation](./API.md)

---

*Last Updated: 2025-01-28*

