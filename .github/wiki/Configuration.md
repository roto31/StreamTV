# Configuration

Complete reference for StreamTV configuration options.

## Configuration File

StreamTV uses a YAML configuration file (`config.yaml`) for all settings.

## Location

- Default: `config.yaml` in the project root
- Custom: Specify with `--config` command line option

## Configuration Sections

### Server Configuration

```yaml
server:
  host: "0.0.0.0"              # Server host (0.0.0.0 = all interfaces)
  port: 8410                    # Server port
  base_url: "http://localhost:8410"  # Base URL for IPTV streams
  workers: 1                    # Number of worker processes
  reload: false                 # Auto-reload on code changes (development)
```

### Database Configuration

```yaml
database:
  url: "sqlite:///./streamtv.db"  # Database connection URL
  echo: false                    # SQLAlchemy echo (SQL logging)
  pool_size: 5                   # Connection pool size
  max_overflow: 10                # Max overflow connections
```

**Supported Databases:**
- SQLite: `sqlite:///./streamtv.db`
- PostgreSQL: `postgresql://user:password@localhost/streamtv`
- MySQL: `mysql://user:password@localhost/streamtv`

### YouTube Configuration

```yaml
youtube:
  enabled: true                  # Enable YouTube streaming
  quality: "best"                 # Video quality preference
  extract_audio: false           # Extract audio only
  cookies_file: "data/cookies/youtube_cookies.txt"  # Cookies file path
  timeout: 30                    # Request timeout (seconds)
  max_retries: 3                 # Maximum retry attempts
```

**Quality Options:**
- `"best"` - Best available quality
- `"worst"` - Lowest quality
- `"bestvideo"` - Best video quality
- `"bestaudio"` - Best audio quality
- Specific format ID (e.g., `"137"`)

### Archive.org Configuration

```yaml
archive_org:
  enabled: true                  # Enable Archive.org streaming
  preferred_format: "h264"        # Preferred video format
  timeout: 30                     # Request timeout (seconds)
  max_retries: 3                  # Maximum retry attempts
```

**Format Options:**
- `"h264"` - H.264 encoded video
- `"vp9"` - VP9 encoded video
- `"webm"` - WebM format
- `"mp4"` - MP4 format

### HDHomeRun Configuration

```yaml
hdhomerun:
  enabled: false                 # Enable HDHomeRun emulation
  device_id: "FFFFFFFF"           # Unique device ID (hex)
  friendly_name: "StreamTV HDHomeRun"  # Device friendly name
  tuner_count: 2                  # Number of virtual tuners
  model: "HDTC-2US"               # Device model
```

### Security Configuration

```yaml
security:
  api_key_required: false         # Require API key for access
  access_token: ""                # Access token (if required)
  cors_enabled: true              # Enable CORS
  cors_origins:                   # Allowed CORS origins
    - "*"                         # Allow all (development)
    # - "http://localhost:3000"   # Specific origin
```

### Streaming Configuration

```yaml
streaming:
  buffer_size: 8192               # Buffer size (bytes)
  chunk_size: 1024                # Chunk size (bytes)
  timeout: 30                     # Request timeout (seconds)
  max_retries: 3                  # Maximum retry attempts
  range_requests: true            # Support HTTP range requests
```

### Scheduling Configuration

```yaml
scheduling:
  schedules_dir: "schedules"      # Directory for schedule YAML files
  default_repeat: true            # Default repeat setting
  timezone: "UTC"                 # Default timezone
```

### Logging Configuration

```yaml
logging:
  level: "INFO"                   # Log level (DEBUG, INFO, WARNING, ERROR)
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: ""                        # Log file path (empty = console only)
```

## Environment Variables

All configuration options can be overridden with environment variables:

```bash
# Server
export STREAMTV_SERVER_HOST="0.0.0.0"
export STREAMTV_SERVER_PORT="8410"

# Database
export STREAMTV_DATABASE_URL="sqlite:///./streamtv.db"

# YouTube
export STREAMTV_YOUTUBE_ENABLED="true"
export STREAMTV_YOUTUBE_QUALITY="best"

# Security
export STREAMTV_SECURITY_API_KEY_REQUIRED="false"
export STREAMTV_SECURITY_ACCESS_TOKEN="your-token"
```

## Command Line Options

```bash
python -m streamtv.main \
  --config config.yaml \          # Config file path
  --host 0.0.0.0 \                # Override server host
  --port 8410 \                   # Override server port
  --reload                        # Enable auto-reload (development)
```

## Configuration Validation

StreamTV validates configuration on startup. Invalid settings will cause startup to fail with clear error messages.

## Example Configuration

See `config.example.yaml` for a complete example with all options documented.

## Reloading Configuration

Configuration is loaded at startup. To apply changes:
1. Stop the server
2. Update `config.yaml`
3. Restart the server

For development, use `--reload` flag for automatic reloading.

## Next Steps

- Learn about [Channels](Channels)
- Read [API Reference](API-Reference)
- Check [Troubleshooting](Troubleshooting) for configuration issues

