# StreamTV Expert Guide

**For Engineers - Complete Architecture, Code Structure, and Deep Technical Details**

## Table of Contents
1. [System Architecture](#system-architecture)
2. [Code Structure](#code-structure)
3. [Component Interactions](#component-interactions)
4. [Database Schema](#database-schema)
5. [Streaming Architecture](#streaming-architecture)
6. [Scheduling System](#scheduling-system)
7. [HDHomeRun Protocol](#hdhomerun-protocol)
8. [Extension Points](#extension-points)
9. [Performance Optimization](#performance-optimization)
10. [Deep Troubleshooting](#deep-troubleshooting)

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │   Web    │  │   Plex   │  │  Emby    │  │ Jellyfin │      │
│  │ Browser  │  │          │  │          │  │          │      │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘      │
└───────┼─────────────┼─────────────┼─────────────┼─────────────┘
        │             │             │             │
        │ HTTP        │ HDHomeRun   │ HDHomeRun   │ HDHomeRun
        │             │ Protocol    │ Protocol    │ Protocol
┌───────▼─────────────▼─────────────▼─────────────▼─────────────┐
│                    FastAPI Application Layer                   │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                    Main Application                      │ │
│  │  - Lifespan Management                                   │ │
│  │  - Middleware (CORS, Logging)                            │ │
│  │  - Router Registration                                   │ │
│  └──────────────────────────────────────────────────────────┘ │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │  API Router  │  │  IPTV Router │  │ HDHomeRun    │        │
│  │              │  │              │  │ Router       │        │
│  │ - Channels   │  │ - M3U        │  │ - Discover   │        │
│  │ - Media      │  │ - XMLTV      │  │ - Lineup     │        │
│  │ - Collections│  │ - HLS        │  │ - Stream     │        │
│  │ - Playlists  │  │ - Direct     │  │ - SSDP       │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
└───────────────────────────────┬───────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────┐
│                    Business Logic Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │  Scheduling  │  │  Streaming    │  │  Importers   │        │
│  │              │  │              │  │              │        │
│  │ - Parser     │  │ - Manager    │  │ - Channel    │        │
│  │ - Engine     │  │ - Adapters   │  │   Importer   │        │
│  │ - Timeline   │  │ - MPEG-TS    │  │ - Validator  │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
│  ┌──────────────┐  ┌──────────────┐                          │
│  │  Channel     │  │  Validation  │                          │
│  │  Manager     │  │              │                          │
│  │              │  │ - YAML       │                          │
│  │ - Streams    │  │ - Schema     │                          │
│  │ - Timeline   │  │ - Data       │                          │
│  └──────────────┘  └──────────────┘                          │
└───────────────────────────────┬───────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────┐
│                      Data Layer                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │  Database    │  │  File System  │  │  External    │        │
│  │              │  │              │  │              │        │
│  │ - SQLite     │  │ - YAML       │  │ - YouTube    │        │
│  │ - SQLAlchemy │  │ - Logs       │  │ - Archive.org│        │
│  │ - Models     │  │ - Config     │  │ - FFmpeg     │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
└───────────────────────────────────────────────────────────────┘
```

### Request Flow

**Web Request Flow:**
```
Browser → FastAPI → API Router → Business Logic → Database → Response
```

**Streaming Request Flow:**
```
Client → IPTV Router → Channel Manager → Schedule Engine → 
Stream Manager → YouTube/Archive.org → FFmpeg → MPEG-TS → Client
```

**HDHomeRun Request Flow:**
```
Plex → HDHomeRun Router → Channel Manager → MPEG-TS Streamer → 
FFmpeg → Continuous Stream → Plex
```

---

## Code Structure

### Package Organization

```
streamtv/
├── __init__.py                 # Package initialization
├── main.py                     # FastAPI app entry point
├── config.py                   # Configuration management
│
├── api/                        # API endpoints
│   ├── __init__.py            # Router aggregation
│   ├── channels.py            # Channel CRUD
│   ├── media.py               # Media item management
│   ├── collections.py         # Collection management
│   ├── playlists.py           # Playlist management
│   ├── schedules.py           # Schedule management
│   ├── iptv.py                # IPTV streaming endpoints
│   ├── import_api.py          # YAML import endpoints
│   ├── playouts.py            # Playout information
│   ├── settings.py            # Settings management
│   └── schemas.py             # Pydantic schemas
│
├── database/                   # Database layer
│   ├── __init__.py            # Database exports
│   ├── session.py             # Session management
│   └── models.py              # SQLAlchemy models
│
├── streaming/                  # Streaming system
│   ├── __init__.py            # Streaming exports
│   ├── stream_manager.py     # Unified stream interface
│   ├── youtube_adapter.py     # YouTube streaming
│   ├── archive_org_adapter.py # Archive.org streaming
│   ├── mpegts_streamer.py     # MPEG-TS transcoding
│   └── channel_manager.py     # Continuous stream management
│
├── scheduling/                 # Schedule system
│   ├── __init__.py            # Scheduling exports
│   ├── parser.py              # YAML schedule parser
│   └── engine.py              # Schedule execution engine
│
├── hdhomerun/                  # HDHomeRun emulation
│   ├── __init__.py            # HDHomeRun exports
│   ├── api.py                 # HDHomeRun API endpoints
│   └── ssdp_server.py         # SSDP discovery server
│
├── importers/                  # Import system
│   ├── __init__.py            # Importer exports
│   └── channel_importer.py    # Channel YAML importer
│
├── validation/                 # Validation system
│   ├── __init__.py            # Validation exports
│   └── validator.py           # YAML schema validation
│
├── utils/                      # Utilities
│   ├── __init__.py            # Utility exports
│   ├── macos_credentials.py   # macOS Keychain integration
│   └── yaml_to_json.py        # YAML conversion
│
└── templates/                  # Web interface
    ├── base.html              # Base template
    ├── index.html             # Dashboard
    ├── channels.html          # Channel management
    ├── player.html            # Video player
    ├── import.html            # Import interface
    └── ...                    # Other templates
```

### Key Classes and Their Responsibilities

#### `streamtv.main.FastAPI`
- Application entry point
- Lifespan management
- Router registration
- Middleware configuration

#### `streamtv.config.Config`
- Configuration loading from YAML
- Environment variable support
- Section-based configuration
- Runtime configuration updates

#### `streamtv.database.models.*`
- SQLAlchemy ORM models
- Database schema definition
- Relationship definitions
- Type constraints

#### `streamtv.streaming.StreamManager`
- Unified streaming interface
- Source detection (YouTube/Archive.org)
- Adapter routing
- Error handling and retries

#### `streamtv.streaming.ChannelManager`
- Continuous stream management
- Timeline tracking
- Multi-client broadcasting
- Stream lifecycle management

#### `streamtv.scheduling.ScheduleEngine`
- Schedule execution
- Sequence processing
- Content resolution
- Timeline calculation

#### `streamtv.importers.ChannelImporter`
- YAML parsing
- Database population
- Collection/Media/Playlist creation
- Validation

---

## Component Interactions

### Channel Creation Flow

```python
# 1. User uploads YAML
POST /api/channels/yaml
  ↓
# 2. Import API receives file
import_api.import_channel_from_file()
  ↓
# 3. Channel Importer parses YAML
ChannelImporter.import_from_yaml()
  ↓
# 4. Create/Update Channel
ChannelImporter.import_channel_from_config()
  ↓
# 5. Process Streams
for stream in config['streams']:
  - Create/Update Collection
  - Create/Update MediaItem
  - Add to Collection
  ↓
# 6. Create Playlist
ChannelImporter._create_playlist()
  ↓
# 7. Commit to Database
db.commit()
```

### Streaming Flow

```python
# 1. Client requests stream
GET /hdhomerun/auto/v1980
  ↓
# 2. HDHomeRun router
hdhomerun.api.stream_channel()
  ↓
# 3. Get ChannelManager from app state
app.state.channel_manager.get_channel_stream()
  ↓
# 4. ChannelManager calculates position
ChannelStream._get_current_position()
  - Calculate elapsed time from midnight
  - Determine current item index
  ↓
# 5. Start streaming from position
ChannelStream._run_continuous_stream()
  ↓
# 6. For each schedule item
MPEGTSStreamer._stream_single_item()
  ↓
# 7. Get stream URL
StreamManager.get_stream_url()
  - Detect source (YouTube/Archive.org)
  - Route to adapter
  - Get direct stream URL
  ↓
# 8. Transcode to MPEG-TS
MPEGTSStreamer._transcode_to_mpegts()
  - Build FFmpeg command
  - Start FFmpeg process
  - Stream output chunks
  ↓
# 9. Broadcast to clients
ChannelStream broadcasts chunks to all client queues
  ↓
# 10. Client receives stream
Client receives MPEG-TS chunks
```

### Schedule Execution Flow

```python
# 1. Load schedule file
ScheduleParser.parse_file()
  - Parse YAML
  - Build content map
  - Build sequence map
  - Build playout map
  ↓
# 2. Generate playlist
ScheduleEngine.generate_playlist_from_schedule()
  ↓
# 3. Process main sequence
ScheduleEngine._generate_sequence_playlist()
  ↓
# 4. For each sequence item
  - collection: Get media from collection
  - duration: Fill duration with media
  - all: Play all items in collection
  - pre_roll/mid_roll/post_roll: Handle roll sequences
  - padToNext/padUntil/waitUntil: Handle time-based items
  ↓
# 5. Return schedule items
List[Dict[str, Any]] with media_item, custom_title, etc.
```

---

## Database Schema

### Entity Relationship Diagram

```
Channel (1) ────< (N) Playlist
Channel (1) ────< (N) Schedule
Playlist (1) ────< (N) PlaylistItem
PlaylistItem (N) ────> (1) MediaItem
Collection (1) ────< (N) CollectionItem
CollectionItem (N) ────> (1) MediaItem
```

### Table Definitions

#### `channels`
```sql
CREATE TABLE channels (
    id INTEGER PRIMARY KEY,
    number VARCHAR UNIQUE NOT NULL,
    name VARCHAR NOT NULL,
    group VARCHAR,
    enabled BOOLEAN DEFAULT TRUE,
    logo_path VARCHAR,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes:**
- `number` (unique)
- `enabled`

**Relationships:**
- One-to-many with `playlists`
- One-to-many with `schedules`

#### `media_items`
```sql
CREATE TABLE media_items (
    id INTEGER PRIMARY KEY,
    source ENUM('youtube', 'archive_org') NOT NULL,
    source_id VARCHAR NOT NULL,
    url VARCHAR UNIQUE NOT NULL,
    title VARCHAR NOT NULL,
    description TEXT,
    duration INTEGER,
    thumbnail VARCHAR,
    uploader VARCHAR,
    upload_date VARCHAR,
    view_count INTEGER,
    meta_data TEXT,  -- JSON string
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes:**
- `url` (unique)
- `source`
- `source_id`

**Relationships:**
- Many-to-many with `collections` (via `collection_items`)
- Many-to-many with `playlists` (via `playlist_items`)

#### `collections`
```sql
CREATE TABLE collections (
    id INTEGER PRIMARY KEY,
    name VARCHAR UNIQUE NOT NULL,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes:**
- `name` (unique)

#### `collection_items`
```sql
CREATE TABLE collection_items (
    id INTEGER PRIMARY KEY,
    collection_id INTEGER NOT NULL REFERENCES collections(id),
    media_item_id INTEGER NOT NULL REFERENCES media_items(id),
    order INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes:**
- `collection_id`
- `media_item_id`
- Composite: `(collection_id, order)`

#### `playlists`
```sql
CREATE TABLE playlists (
    id INTEGER PRIMARY KEY,
    name VARCHAR NOT NULL,
    description TEXT,
    channel_id INTEGER REFERENCES channels(id),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes:**
- `channel_id`

#### `playlist_items`
```sql
CREATE TABLE playlist_items (
    id INTEGER PRIMARY KEY,
    playlist_id INTEGER NOT NULL REFERENCES playlists(id),
    media_item_id INTEGER NOT NULL REFERENCES media_items(id),
    order INTEGER DEFAULT 0,
    start_time DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes:**
- `playlist_id`
- `media_item_id`
- Composite: `(playlist_id, order)`

---

## Streaming Architecture

### Stream Manager Architecture

```python
StreamManager
├── detect_source(url) → StreamSource
├── get_stream_url(url) → str
└── get_media_info(url) → Dict
    │
    ├── YouTubeAdapter
    │   ├── Uses yt-dlp
    │   ├── Extracts direct stream URL
    │   └── Handles geo-restrictions
    │
    └── ArchiveOrgAdapter
        ├── Uses Archive.org API
        ├── Handles authentication
        └── Selects preferred format
```

### MPEG-TS Streaming

**FFmpeg Command Structure:**
```bash
ffmpeg \
  # Global options
  -loglevel info \
  # Input options (before -i)
  -hwaccel videotoolbox \
  -fflags +genpts+discardcorrupt+fastseek \
  -flags +low_delay \
  -probesize 1000000 \
  -analyzeduration 2000000 \
  -i <input_url> \
  # Output options (after -i)
  -threads 0 \
  -c:v mpeg2video \
  -b:v 4M \
  -c:a mp2 \
  -b:a 192k \
  -f mpegts \
  -flush_packets 1 \
  -
```

**Process Management:**
- Async subprocess execution
- Real-time stderr monitoring
- Graceful cleanup on errors
- Process lifecycle tracking

### Channel Manager Architecture

```python
ChannelManager
├── start_all_channels()
├── stop_all_channels()
├── get_channel_stream(channel_number)
└── _start_channel(channel)
    │
    └── ChannelStream
        ├── start() → Initialize timeline
        ├── stop() → Cleanup
        ├── get_stream() → Client connection
        └── _run_continuous_stream()
            ├── Load schedule items
            ├── Calculate start position
            ├── Stream items sequentially
            └── Broadcast to clients
```

**Timeline System:**
- `_playout_start_time`: Midnight of channel creation day
- `_current_item_index`: Current item in schedule
- `_get_current_position()`: Calculate position from system time
- Continuous timeline (doesn't reset on loops)

---

## Scheduling System

### Schedule Parser

**YAML Structure:**
```yaml
name: "Channel Name"
description: "Description"

content:
  - key: content_key
    collection: "Collection Name"
    order: chronological | shuffle

sequence:
  - name: "Sequence Name"
    items:
      - collection: "Collection"
      - duration: "HH:MM:SS"
        collection: "Filler"
      - all: "Collection"
      - pre_roll: true
        collection: "IDs"

playout:
  - name: "Playout Name"
    sequence: "Sequence Name"
    repeat: true
```

**Parser Process:**
1. Load YAML file
2. Parse content section → `content_map`
3. Parse sequence section → `sequences`
4. Parse playout section → `playouts`
5. Handle imports (if present)
6. Return `ParsedSchedule` object

### Schedule Engine

**Execution Process:**
1. Get playout for channel
2. Get sequence from playout
3. Process sequence items:
   - Resolve collections
   - Handle duration fillers
   - Handle time-based items
   - Handle roll sequences
4. Generate schedule items list
5. Handle repeat logic
6. Return final playlist

**Advanced Features:**
- `padToNext`: Pad to next time boundary
- `padUntil`: Pad until specific time
- `waitUntil`: Wait until specific time
- `skipItems`: Skip items conditionally
- `shuffleSequence`: Shuffle sequence items

---

## HDHomeRun Protocol

### SSDP Discovery

**Multicast Message:**
```
NOTIFY * HTTP/1.1
HOST: 239.255.255.250:1900
CACHE-CONTROL: max-age=1800
LOCATION: http://IP:8410/hdhomerun/device.xml
NT: urn:schemas-upnp-org:device:MediaServer:1
NTS: ssdp:alive
USN: uuid:DEVICE_ID::urn:schemas-upnp-org:device:MediaServer:1
```

### API Endpoints

**Discovery:**
- `GET /hdhomerun/discover.json` → Device information
- `GET /hdhomerun/device.xml` → UPnP device description

**Lineup:**
- `GET /hdhomerun/lineup.json` → Channel lineup
- `GET /hdhomerun/lineup_status.json` → Lineup status

**Streaming:**
- `GET /hdhomerun/auto/v{channel_number}` → MPEG-TS stream
- `GET /hdhomerun/tuner{n}/stream?channel=auto:v{number}` → Tuner stream

### Protocol Implementation

**Device ID Format:**
- 8-character hexadecimal
- Default: "FFFFFFFF"
- Should be unique per instance

**Channel Number Format:**
- String (e.g., "1980", "1992")
- Used in M3U as `tvg-id`
- Used in XMLTV as channel ID

---

## Extension Points

### Adding New Stream Source

1. **Create Adapter:**
```python
# streamtv/streaming/new_source_adapter.py
class NewSourceAdapter:
    async def get_stream_url(self, url: str) -> str:
        # Extract stream URL
        pass
    
    async def get_media_info(self, url: str) -> Dict:
        # Extract metadata
        pass
```

2. **Update StreamSource Enum:**
```python
# streamtv/database/models.py
class StreamSource(str, Enum):
    YOUTUBE = "youtube"
    ARCHIVE_ORG = "archive_org"
    NEW_SOURCE = "new_source"  # Add here
```

3. **Register in StreamManager:**
```python
# streamtv/streaming/stream_manager.py
def detect_source(self, url: str) -> StreamSource:
    if "newsource.com" in url:
        return StreamSource.NEW_SOURCE
    # ...
```

### Adding New API Endpoint

1. **Create Router:**
```python
# streamtv/api/new_feature.py
from fastapi import APIRouter
router = APIRouter(prefix="/api/new-feature")

@router.get("/")
async def get_feature():
    return {"feature": "data"}
```

2. **Register Router:**
```python
# streamtv/api/__init__.py
from .new_feature import router as new_feature_router
api_router.include_router(new_feature_router)
```

### Custom Schedule Handlers

1. **Add Handler Method:**
```python
# streamtv/scheduling/engine.py
def _handle_custom_directive(self, item: Dict, schedule: ParsedSchedule):
    # Custom logic
    pass
```

2. **Register in Sequence Processing:**
```python
if 'custom_directive' in item:
    return self._handle_custom_directive(item, schedule)
```

---

## Performance Optimization

### Database Optimization

**Indexes:**
- All foreign keys indexed
- Unique constraints on critical fields
- Composite indexes for common queries

**Query Optimization:**
- Use `joinedload()` for relationships
- Cache collection media items
- Batch operations where possible

### Streaming Optimization

**FFmpeg Settings:**
- Hardware acceleration when available
- Optimized codec settings
- Reduced probe/analysis time

**Network Optimization:**
- Connection pooling
- Timeout management
- Retry logic with backoff

### Caching Strategy

**Collection Cache:**
- Cache collection media items
- Invalidate on updates
- Per-session caching

**Schedule Cache:**
- Cache parsed schedules
- Cache generated playlists
- Time-based invalidation

---

## Deep Troubleshooting

### Debugging Timeline Issues

**Check Timeline Calculation:**
```python
# In ChannelStream._get_current_position()
now = datetime.utcnow()
elapsed = (now - self._playout_start_time).total_seconds()
# Log elapsed time and calculated position
```

**Verify Midnight Start:**
```python
# Check channel creation date
channel = db.query(Channel).filter(Channel.number == "1980").first()
creation_date = channel.created_at.date()
midnight = datetime.combine(creation_date, time.min)
# Verify _playout_start_time matches midnight
```

### Debugging Stream Issues

**Check FFmpeg Process:**
```bash
# Monitor FFmpeg processes
ps aux | grep ffmpeg

# Check FFmpeg logs
tail -f streamtv.log | grep FFmpeg
```

**Test Stream URL:**
```python
# In StreamManager
stream_url = await adapter.get_stream_url(url)
# Test URL accessibility
async with httpx.AsyncClient() as client:
    response = await client.head(stream_url)
    print(f"Status: {response.status_code}")
```

### Database Debugging

**Inspect Database:**
```python
from streamtv.database import get_db
db = next(get_db())

# Check channels
channels = db.query(Channel).all()
for ch in channels:
    print(f"{ch.number}: {ch.name}")

# Check media items
media = db.query(MediaItem).filter(MediaItem.url.like('%PLACEHOLDER%')).all()
print(f"Placeholder items: {len(media)}")
```

---

## Next Steps

- **Need Troubleshooting Help?** → Use [Troubleshooting Scripts](./TROUBLESHOOTING_SCRIPTS.md)
- **Want API Details?** → Read [API Documentation](./API.md)
- **Configuration Help?** → See [Intermediate Guide](./INTERMEDIATE_GUIDE.md)

---

*Last Updated: 2025-01-28*

