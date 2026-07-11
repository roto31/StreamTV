# StreamTV Logging System

StreamTV includes a comprehensive logging system that captures all application events, errors, and information to help with debugging and monitoring.

## Log Location

All logs are stored in: `~/Library/Logs/StreamTV/`

This is the standard macOS location for application logs, making them easy to find and manage.

## Log Files

Logs are organized by date with automatic rotation:

- **Format**: `streamtv-YYYY-MM-DD.log` (e.g., `streamtv-2025-12-04.log`)
- **Rotation**: Log files are automatically rotated when they reach 10 MB
- **Retention**: Up to 10 backup files are kept per day
- **Encoding**: UTF-8 for proper character support

## Log Levels

The logging system supports multiple log levels (from most to least verbose):

1. **DEBUG** - Detailed information for diagnosing problems
2. **INFO** - General informational messages (default)
3. **WARNING** - Warning messages for potential issues
4. **ERROR** - Error messages for serious problems
5. **CRITICAL** - Critical messages for severe failures

### Changing Log Level

Edit your `config.yaml` file:

```yaml
logging:
  level: INFO  # Change to DEBUG, WARNING, ERROR, or CRITICAL
```

## Log Format

Each log entry includes:

```
YYYY-MM-DD HH:MM:SS - module.name - LEVEL - Message
```

Example:
```
2025-12-04 14:30:45 - streamtv.main - INFO - StreamTV started on 0.0.0.0:8410
2025-12-04 14:30:46 - streamtv.streaming.channel_manager - INFO - Started channel: ABC 1980
```

## Viewing Logs

### Method 1: Using the Log Viewer Script (Recommended)

We provide a convenient script for viewing logs:

```bash
# Make it executable (first time only)
chmod +x scripts/view-logs.sh

# Tail the latest log (live view)
./scripts/view-logs.sh

# List all log files
./scripts/view-logs.sh list

# View today's log
./scripts/view-logs.sh today

# Search logs for errors
./scripts/view-logs.sh search ERROR

# Open log directory in Finder
./scripts/view-logs.sh open

# Show help
./scripts/view-logs.sh help
```

### Method 2: Using Terminal Commands

```bash
# View the latest log file (live tail)
tail -f ~/Library/Logs/StreamTV/streamtv-$(date +%Y-%m-%d).log

# View all of today's log
cat ~/Library/Logs/StreamTV/streamtv-$(date +%Y-%m-%d).log

# Search for errors in today's log
grep ERROR ~/Library/Logs/StreamTV/streamtv-$(date +%Y-%m-%d).log

# Search all logs for a specific term
grep -r "channel" ~/Library/Logs/StreamTV/

# View last 100 lines of latest log
tail -n 100 ~/Library/Logs/StreamTV/streamtv-$(date +%Y-%m-%d).log

# View logs with paging
less ~/Library/Logs/StreamTV/streamtv-$(date +%Y-%m-%d).log
```

### Method 3: Using Console.app

macOS includes a built-in log viewer:

1. Open **Console.app** (in `/Applications/Utilities/`)
2. In the left sidebar, expand **User Reports**
3. Navigate to `~/Library/Logs/StreamTV/`
4. Select the log file you want to view

### Method 4: Using Finder

Simply open the log directory:

```bash
open ~/Library/Logs/StreamTV/
```

Or use the quick script:

```bash
./scripts/view-logs.sh open
```

## What Gets Logged

StreamTV logs all important events including:

### Application Lifecycle
- Server startup and shutdown
- Configuration loading
- Database initialization
- SSDP server status (HDHomeRun discovery)

### Channel Management
- Channel creation, updates, and deletion
- Channel streaming start/stop
- Stream health and status

### Authentication
- Login attempts (success/failure)
- Token generation and validation
- OAuth flow steps
- Archive.org and YouTube authentication

### Streaming
- Stream requests and responses
- FFmpeg process status
- Transcoding events
- Buffer and quality changes
- Error conditions and retries

### API Requests
- HTTP requests and responses
- Rate limiting events
- CORS policy enforcement
- API key validation

### Database Operations
- Query execution (at DEBUG level)
- Transaction commits/rollbacks
- Database errors

### System Information
- Python version and platform details
- Working directory
- Environment configuration

## Troubleshooting with Logs

### Common Issues and Log Patterns

#### Stream Won't Start
Look for:
```bash
grep -i "stream" ~/Library/Logs/StreamTV/*.log | grep -i error
```

#### Authentication Issues
Look for:
```bash
grep -i "auth" ~/Library/Logs/StreamTV/*.log | grep -i error
```

#### FFmpeg Problems
Look for:
```bash
grep -i "ffmpeg" ~/Library/Logs/StreamTV/*.log
```

#### Database Errors
Look for:
```bash
grep -i "database\|sqlite" ~/Library/Logs/StreamTV/*.log | grep -i error
```

#### HDHomeRun Discovery Issues
Look for:
```bash
grep -i "ssdp\|hdhomerun" ~/Library/Logs/StreamTV/*.log
```

## Log Management

### Disk Space

Log files are automatically managed with rotation:
- Maximum file size: 10 MB
- Maximum backup files: 10 per day
- Total maximum per day: ~110 MB (11 files × 10 MB)

### Manual Cleanup

To clean up old logs:

```bash
# Remove logs older than 30 days
find ~/Library/Logs/StreamTV/ -name "*.log*" -mtime +30 -delete

# Remove all logs (careful!)
rm -rf ~/Library/Logs/StreamTV/*.log*
```

### Archiving Logs

To archive logs for later analysis:

```bash
# Archive logs to a zip file
cd ~/Library/Logs/
zip -r StreamTV-logs-$(date +%Y-%m-%d).zip StreamTV/

# Archive and compress with tar
tar -czf StreamTV-logs-$(date +%Y-%m-%d).tar.gz StreamTV/
```

## Development and Debugging

### Enable Debug Logging

For detailed debugging information, set log level to DEBUG:

```yaml
# config.yaml
logging:
  level: DEBUG
```

This will show:
- Detailed HTTP request/response data
- FFmpeg command arguments
- Database query details
- Streaming buffer information
- Authentication token details (redacted for security)

**Note**: DEBUG logging can be very verbose and may impact performance slightly.

### Programmatic Access

To add logging to your custom scripts or modules:

```python
from streamtv.utils.logging_setup import get_logger

logger = get_logger(__name__)

logger.debug("Detailed debug information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error message")
logger.critical("Critical failure")

# Log exceptions with traceback
try:
    # Your code here
    pass
except Exception as e:
    logger.error(f"Operation failed: {e}", exc_info=True)
```

## Performance Considerations

- **Console Output**: Logs are written to both console and file simultaneously
- **Async I/O**: File writes are buffered and non-blocking
- **Rotation**: Automatic rotation prevents disk space issues
- **Format**: Simple text format for easy parsing and searching

## Privacy and Security

StreamTV logging includes privacy considerations:

- **No Passwords**: Passwords are never logged in plain text
- **Redacted Tokens**: Authentication tokens are partially redacted
- **IP Addresses**: Client IPs are logged (can be disabled if needed)
- **User Actions**: User actions are logged for security audit trails

If you need to share logs for support, review them first to ensure no sensitive information is included.

## Support

If you encounter issues:

1. Check the logs for error messages
2. Search for specific error patterns
3. Include relevant log excerpts when reporting issues (redact any sensitive info)

For more information, see:
- [Troubleshooting Guide](TROUBLESHOOTING.md)
- [API Documentation](API.md)
- [Configuration Guide](README.md)

