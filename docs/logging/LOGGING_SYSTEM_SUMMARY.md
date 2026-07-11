# StreamTV Logging System - Implementation Summary

## ✅ Completed

A comprehensive logging system has been implemented for StreamTV that captures all application events and writes them to both the console and log files in `~/Library/Logs/StreamTV/`.

## What Was Created

### 1. Core Logging Module
**File**: `streamtv/utils/logging_setup.py`

Features:
- Dual output to console and file
- Automatic log directory creation in `~/Library/Logs/StreamTV/`
- Log rotation (10 MB max per file, 10 backups)
- Configurable log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- System information logging
- Exception logging with full tracebacks
- UTF-8 encoding support

### 2. Updated Main Application
**File**: `streamtv/main.py`

Changes:
- Replaced basic `logging.basicConfig()` with comprehensive `setup_logging()`
- Added system information logging at startup
- Configured uvicorn to use custom logging

### 3. Log Viewer Script
**File**: `scripts/view-logs.sh`

A convenient shell script for viewing logs with multiple modes:
```bash
./scripts/view-logs.sh           # Live tail of latest log
./scripts/view-logs.sh list      # List all log files
./scripts/view-logs.sh today     # View today's log
./scripts/view-logs.sh search    # Search logs
./scripts/view-logs.sh open      # Open in Finder
```

### 4. Test Script
**File**: `scripts/test_logging.py`

A Python test script to verify the logging system is working correctly.

### 5. Documentation

Created three documentation files:

1. **`docs/LOGGING.md`** - Complete logging documentation
2. **`LOGGING_QUICKSTART.md`** - Quick reference guide
3. **`LOGGING_SYSTEM_SUMMARY.md`** - This file

## Log File Location

**Primary Location**: `~/Library/Logs/StreamTV/`

This is the standard macOS location for application logs, making them easily accessible through:
- Console.app (built-in macOS log viewer)
- Terminal commands
- Finder
- The provided view-logs.sh script

## Log File Format

**Filename Pattern**: `streamtv-YYYY-MM-DD.log`

**Log Entry Format**:
```
YYYY-MM-DD HH:MM:SS - module.name - LEVEL - Message
```

**Example**:
```
2025-12-03 18:05:36 - streamtv.main - INFO - StreamTV started on 0.0.0.0:8410
2025-12-03 18:05:36 - streamtv.streaming.channel_manager - INFO - Started continuous stream for channel 1980
```

## What Gets Logged

The system now logs:

✅ **Application Lifecycle**
- Server startup/shutdown
- Configuration loading
- Database initialization
- SSDP server status

✅ **Channel Operations**
- Channel creation/updates
- Stream start/stop events
- Playout initialization
- Timeline generation

✅ **Streaming Events**
- FFmpeg operations
- Transcoding status
- Stream health
- Client connections

✅ **API Activity**
- HTTP requests/responses
- Authentication attempts
- Rate limiting
- CORS enforcement

✅ **Database Operations**
- Query execution (DEBUG level)
- Transaction status
- Database errors

✅ **System Information**
- Python version
- Platform details
- Working directory
- Environment configuration

✅ **Errors and Exceptions**
- Full stack traces
- Error context
- Warning conditions

## Log Management

### Automatic Features
- **Rotation**: Files rotate at 10 MB
- **Retention**: Keep 10 backup files per day
- **Encoding**: UTF-8 for proper character support
- **Buffering**: Non-blocking async I/O

### Manual Cleanup
```bash
# Remove logs older than 30 days
find ~/Library/Logs/StreamTV/ -name "*.log*" -mtime +30 -delete
```

## Usage Examples

### View Live Logs
```bash
# Using the script (recommended)
./scripts/view-logs.sh

# OR directly
tail -f ~/Library/Logs/StreamTV/streamtv-$(date +%Y-%m-%d).log
```

### Search for Errors
```bash
./scripts/view-logs.sh search ERROR

# OR directly
grep ERROR ~/Library/Logs/StreamTV/*.log
```

### Open in Finder
```bash
open ~/Library/Logs/StreamTV/
```

### View in Console.app
1. Open Console.app
2. Navigate to `~/Library/Logs/StreamTV/`
3. Select the log file

## Configuration

Log level can be changed in `config.yaml`:

```yaml
logging:
  level: INFO  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## Testing

Verify the logging system:

```bash
./scripts/test_logging.py
```

This will:
1. Initialize the logging system
2. Log test messages at all levels
3. Test exception logging
4. Display log file location
5. List current log files

## Integration with Existing Code

All existing logging statements throughout the codebase automatically use this new system:

```python
import logging
logger = logging.getLogger(__name__)

logger.info("This message goes to both console and file")
logger.error("Errors are captured with full context")
```

No changes needed to existing code - it all works automatically!

## Performance

- Minimal overhead (buffered I/O)
- Non-blocking file writes
- Automatic rotation prevents disk space issues
- Console and file output are independent

## Privacy and Security

- Passwords are never logged
- Auth tokens are partially redacted
- Sensitive data is protected
- Review logs before sharing

## Benefits

1. **Easy Troubleshooting**: All events in one place
2. **Persistent Logs**: Events survive server restarts
3. **Standard Location**: macOS ~/Library/Logs convention
4. **Searchable**: Plain text for easy grep/search
5. **Rotating**: Automatic cleanup prevents disk fill
6. **Detailed**: Full context for debugging
7. **Convenient**: Multiple viewing options

## Next Steps

The logging system is fully operational and requires no additional setup. Simply:

1. **Start your application** - logs begin automatically
2. **View logs** using `./scripts/view-logs.sh`
3. **Change log level** in `config.yaml` if needed
4. **Archive old logs** periodically if desired

## Quick Reference

| Action | Command |
|--------|---------|
| Live view | `./scripts/view-logs.sh` |
| List logs | `./scripts/view-logs.sh list` |
| Search | `./scripts/view-logs.sh search ERROR` |
| Open folder | `open ~/Library/Logs/StreamTV/` |
| View today | `./scripts/view-logs.sh today` |
| Change level | Edit `config.yaml` → `logging.level` |

## Documentation

- **Full Guide**: [docs/LOGGING.md](docs/LOGGING.md)
- **Quick Start**: [LOGGING_QUICKSTART.md](LOGGING_QUICKSTART.md)
- **This Summary**: [LOGGING_SYSTEM_SUMMARY.md](LOGGING_SYSTEM_SUMMARY.md)

---

**Status**: ✅ Complete and operational

**Location**: `~/Library/Logs/StreamTV/`

**Test**: `./scripts/test_logging.py`

**View**: `./scripts/view-logs.sh`
