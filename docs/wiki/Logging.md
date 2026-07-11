# Logging System

Comprehensive logging system for StreamTV.

## Quick Start

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

For complete logging documentation, see: [LOGGING.md](LOGGING.md)

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

## LOGGING COMPLETE SUMMARY

# 🎉 StreamTV Comprehensive Logging System - COMPLETE! ✅

## 📋 Implementation Summary

A complete logging system has been successfully implemented for StreamTV that captures **all Terminal log output** and writes it to **`~/Library/Logs/StreamTV/`**.

---

## ✅ What Was Accomplished

### 1. Core Logging System ✅
- **Created**: `streamtv/utils/logging_setup.py` (comprehensive logging module)
- **Updated**: `streamtv/main.py` (integrated logging system)
- **Features**:
  - ✅ Dual output (console + file)
  - ✅ Automatic directory creation
  - ✅ Log rotation (10 MB max, 10 backups)
  - ✅ UTF-8 encoding
  - ✅ Configurable log levels
  - ✅ System information capture
  - ✅ Exception tracking with full stack traces

### 2. Log Viewer Tools ✅
- **Created**: `scripts/view-logs.sh` (interactive log viewer)
- **Created**: `scripts/test_logging.py` (logging system test)
- **Features**:
  - ✅ Live log tailing
  - ✅ Search functionality
  - ✅ List all logs
  - ✅ Open in Finder
  - ✅ View today's log
  - ✅ Color-coded output

### 3. Documentation ✅
- **Created**: `LOGGING.md` (complete guide)
- **Created**: `LOGGING_QUICKSTART.md` (quick reference)
- **Created**: `LOGGING_SYSTEM_SUMMARY.md` (technical details)
- **Created**: `LOGGING_IMPLEMENTATION_COMPLETE.md` (completion report)
- **Created**: `LOGGING_COMPLETE_SUMMARY.md` (this file)
- **Updated**: `README.md` (added logging section)

---

## 📁 Log Location

```
~/Library/Logs/StreamTV/
└── streamtv-2025-12-03.log (58 KB)
```

**Current Status**: ✅ Operational with 58 KB of logs captured

---

## 🚀 Quick Start Guide

### View Logs Live

```bash
# Option 1: Use the script (recommended)
./scripts/view-logs.sh

# Option 2: Direct tail
tail -f ~/Library/Logs/StreamTV/streamtv-*.log
```

### Search for Errors

```bash
./scripts/view-logs.sh search ERROR
```

### List All Logs

```bash
./scripts/view-logs.sh list
```

### Open in Finder

```bash
open ~/Library/Logs/StreamTV/
```

---

## 📊 What's Being Logged

### ✅ Application Lifecycle
```
2025-12-03 18:05:36 - streamtv.main - INFO - StreamTV started on 0.0.0.0:8410
2025-12-03 18:05:36 - streamtv.main - INFO - Database initialized
```

### ✅ System Information
```
2025-12-03 18:05:36 - streamtv.utils.logging_setup - INFO - Python version: 3.13.3
2025-12-03 18:05:36 - streamtv.utils.logging_setup - INFO - Platform: macOS-26.1-arm64
2025-12-03 18:05:36 - streamtv.utils.logging_setup - INFO - Machine: arm64
```

### ✅ Channel Operations
```
2025-12-03 18:05:36 - streamtv.streaming.channel_manager - INFO - Started continuous stream for channel 1980
2025-12-03 18:05:36 - streamtv.streaming.channel_manager - INFO - Initialized playout timeline for channel 1984
```

### ✅ Streaming Events
```
2025-12-03 18:05:36 - streamtv.streaming.channel_manager - INFO - Streaming playout for channel 1984 with 1000 items
2025-12-03 18:05:36 - streamtv.streaming.channel_manager - INFO - Channel 1984 using ON-DEMAND mode
```

### ✅ HDHomeRun Integration
```
2025-12-03 18:05:36 - streamtv.hdhomerun.ssdp_server - INFO - SSDP server started on port 1900
2025-12-03 18:05:36 - streamtv.main - INFO - HDHomeRun SSDP server started
```

### ✅ Schedule Processing
```
2025-12-03 18:05:36 - streamtv.scheduling.parser - INFO - Parsed schedule: MN 1980 Winter Olympics with 11 content items
2025-12-03 18:05:36 - streamtv.scheduling.engine - INFO - Generated 1000 items from schedule
```

---

## 🎨 Log Format

Every log entry follows this format:

```
YYYY-MM-DD HH:MM:SS - module.name - LEVEL - Message
```

**Example**:
```
2025-12-03 18:05:36 - streamtv.main - INFO - StreamTV started on 0.0.0.0:8410
│                   │               │      │
│                   │               │      └─ Message content
│                   │               └──────── Log level
│                   └───────────────────────── Module name
└─────────────────────────────────────────── Timestamp
```

---

## 🛠️ Available Commands

### Log Viewer Script

---

## LOGGING IMPLEMENTATION COMPLETE

# ✅ StreamTV Logging System - Implementation Complete

## Summary

A comprehensive logging system has been successfully implemented for StreamTV. All application events, errors, and information are now automatically logged to **`~/Library/Logs/StreamTV/`** in addition to console output.

---

## 📁 Files Created

### Core Implementation

1. **`streamtv/utils/logging_setup.py`**
   - Main logging configuration module
   - Handles dual output (console + file)
   - Automatic log rotation
   - System information logging
   - Exception tracking with full tracebacks

2. **`streamtv/main.py`** (Updated)
   - Integrated new logging system
   - System info logging at startup
   - Custom uvicorn log configuration

### Utilities & Scripts

3. **`scripts/view-logs.sh`** ⭐
   - Interactive log viewer with multiple modes
   - Commands: list, tail, search, today, open
   - Color-coded output
   - Made executable

4. **`scripts/test_logging.py`**
   - Test script to verify logging system
   - Tests all log levels
   - Exception logging test
   - Log file detection and reporting
   - Made executable

### Documentation

5. **`LOGGING.md`**
   - Complete logging documentation
   - Usage examples
   - Troubleshooting patterns
   - Privacy and security considerations
   - Configuration options

6. **`LOGGING_QUICKSTART.md`**
   - Quick reference guide
   - Common commands
   - Quick troubleshooting tips
   - One-page reference

7. **`LOGGING_SYSTEM_SUMMARY.md`**
   - Implementation overview
   - Feature list
   - What gets logged
   - Configuration details

8. **`LOGGING_IMPLEMENTATION_COMPLETE.md`** (This file)
   - Final summary of implementation
   - Quick start instructions
   - File listing

9. **`README.md`** (Updated)
   - Added logging system section
   - Quick commands
   - Documentation links

---

## 🎯 Quick Start

### View Logs (Live)

```bash
./scripts/view-logs.sh
```

### List All Log Files

```bash
./scripts/view-logs.sh list
```

### Search for Errors

```bash
./scripts/view-logs.sh search ERROR
```

### Open Log Folder in Finder

```bash
open ~/Library/Logs/StreamTV/
```

OR

```bash
./scripts/view-logs.sh open
```

### View Today's Log

```bash
./scripts/view-logs.sh today
```

### Direct Terminal Access

```bash
# Live tail
tail -f ~/Library/Logs/StreamTV/streamtv-$(date +%Y-%m-%d).log

# View entire log
cat ~/Library/Logs/StreamTV/streamtv-$(date +%Y-%m-%d).log

# Search all logs
grep -r "search term" ~/Library/Logs/StreamTV/
```

---

## 🧪 Testing

The logging system has been tested and verified:

```bash
./scripts/test_logging.py
```

**Test Results**: ✅ All tests passed
- ✅ Log directory created at `~/Library/Logs/StreamTV/`
- ✅ Console output working
- ✅ File output working
- ✅ All log levels functioning (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- ✅ Exception logging with tracebacks working
- ✅ System information logging working
- ✅ Log rotation configured
- ✅ Log file created: `streamtv-2025-12-03.log` (58 KB)

---

## 📊 What Gets Logged

The system captures:

### Application Events

---

## LOGGING SYSTEM SUMMARY

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

1. **`LOGGING.md`** - Complete logging documentation
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

---

## Related Pages

- [Scripts and Tools](Scripts-and-Tools)
- [Home](Home)
