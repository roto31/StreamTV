# StreamTV Logging - Quick Start

## Where Are My Logs?

All logs are in: **`~/Library/Logs/StreamTV/`**

## Quick Commands

```bash
# View latest logs (live)
./scripts/view-logs.sh

# OR directly with tail
tail -f ~/Library/Logs/StreamTV/streamtv-$(date +%Y-%m-%d).log

# Open log folder in Finder
open ~/Library/Logs/StreamTV/

# Search for errors
./scripts/view-logs.sh search ERROR

# List all log files
./scripts/view-logs.sh list
```

## What's Logged?

✅ Server startup/shutdown
✅ All API requests and responses
✅ Channel streaming events
✅ Authentication attempts
✅ FFmpeg operations
✅ Database operations
✅ Error messages with full tracebacks
✅ System information

## Log Format

Every log line shows:
- Timestamp (YYYY-MM-DD HH:MM:SS)
- Module name
- Log level (INFO, WARNING, ERROR, etc.)
- Message

Example:
```
2025-12-04 14:30:45 - streamtv.main - INFO - StreamTV started on 0.0.0.0:8410
```

## Change Log Level

Edit `config.yaml`:

```yaml
logging:
  level: DEBUG  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

- **DEBUG**: Very detailed (use for troubleshooting)
- **INFO**: Standard level (recommended)
- **WARNING**: Only warnings and errors
- **ERROR**: Only errors and critical issues

## Troubleshooting

### Can't find logs?

Make sure the application has been started at least once. The log directory is created automatically when StreamTV starts.

### Logs too verbose?

Change log level to `WARNING` or `ERROR` in `config.yaml`.

### Need to share logs?

```bash
# Create a zip archive of all logs
cd ~/Library/Logs/
zip -r StreamTV-logs.zip StreamTV/
```

**⚠️ Important**: Review logs before sharing to remove any sensitive information!

## Full Documentation

For complete logging documentation, see: [docs/LOGGING.md](docs/LOGGING.md)

## Common Issues

### Stream won't start
```bash
grep -i "stream" ~/Library/Logs/StreamTV/*.log | grep -i error
```

### Authentication problems
```bash
grep -i "auth" ~/Library/Logs/StreamTV/*.log | grep -i error
```

### FFmpeg issues
```bash
grep -i "ffmpeg" ~/Library/Logs/StreamTV/*.log
```

---

**💡 Tip**: Keep a terminal window open with `./scripts/view-logs.sh` running while developing to see real-time logs!
