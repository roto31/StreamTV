# StreamTV Project Structure

```
streamtv/
├── streamtv/                    # Main application package
│   ├── __init__.py             # Package initialization
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Configuration management
│   │
│   ├── api/                    # API endpoints
│   │   ├── __init__.py        # API router setup
│   │   ├── channels.py        # Channel management endpoints
│   │   ├── media.py           # Media item endpoints
│   │   ├── collections.py     # Collection endpoints
│   │   ├── playlists.py       # Playlist endpoints
│   │   ├── schedules.py       # Schedule endpoints
│   │   ├── iptv.py            # IPTV streaming endpoints
│   │   └── schemas.py         # Pydantic schemas
│   │
│   ├── database/              # Database layer
│   │   ├── __init__.py       # Database exports
│   │   ├── session.py        # Database session management
│   │   └── models.py         # SQLAlchemy models
│   │
│   └── streaming/             # Streaming adapters
│       ├── __init__.py       # Streaming exports
│       ├── youtube_adapter.py      # YouTube streaming
│       ├── archive_org_adapter.py  # Archive.org streaming
│       └── stream_manager.py       # Stream management
│
├── docs/                      # Documentation
│   ├── API.md                # API documentation
│   ├── INSTALLATION.md        # Installation guide
│   ├── QUICKSTART.md          # Quick start guide
│   └── COMPARISON.md         # ErsatzTV comparison
│
├── config.example.yaml        # Example configuration
├── requirements.txt           # Python dependencies
├── setup.py                  # Setup script
├── README.md                 # Main README
└── PROJECT_STRUCTURE.md      # This file
```

## Key Components

### API Layer (`streamtv/api/`)
- RESTful API endpoints following ErsatzTV patterns
- Pydantic schemas for request/response validation
- IPTV endpoints for streaming

### Database Layer (`streamtv/database/`)
- SQLAlchemy models for data persistence
- Session management
- Models: Channel, MediaItem, Collection, Playlist, Schedule

### Streaming Layer (`streamtv/streaming/`)
- YouTube adapter for direct streaming
- Archive.org adapter for direct streaming
- Stream manager for unified streaming interface

### Configuration (`streamtv/config.py`)
- YAML-based configuration
- Environment variable support
- Default values for all settings

## Data Flow

1. **Media Addition**: User adds URL → API validates → Stream adapter fetches metadata → Database stores
2. **Playlist Creation**: User creates playlist → Adds media items → Database stores relationships
3. **Channel Setup**: User creates channel → Assigns playlist → Database stores
4. **Streaming**: Client requests stream → IPTV endpoint → Stream manager → Direct stream from source

## Extension Points

### Adding New Streaming Sources

1. Create new adapter in `streamtv/streaming/`
2. Implement `get_stream_url()` and `get_media_info()` methods
3. Add to `StreamManager.detect_source()`
4. Update `StreamSource` enum in models

### Adding New API Endpoints

1. Create new router in `streamtv/api/`
2. Define schemas in `streamtv/api/schemas.py`
3. Add router to `streamtv/api/__init__.py`
4. Include in main app

### Database Changes

1. Update models in `streamtv/database/models.py`
2. Create migration (if using Alembic)
3. Update schemas in `streamtv/api/schemas.py`

## Testing

To test the application:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python -m streamtv.main

# Test endpoints
curl http://localhost:8410/
curl http://localhost:8410/api/channels
```

## Deployment

The application can be deployed using:
- Systemd service
- Cloud platforms (Heroku, AWS, etc.)

## License

See LICENSE file for details.
