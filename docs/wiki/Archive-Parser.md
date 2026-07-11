# Archive.org Channel Parser

Create channels from Archive.org collections automatically.

## Quick Reference

# 🎯 Archive.org Collection Parser - Quick Reference

## ⚡ Quick Start

### GUI Method (Recommended)
```bash
./scripts/archive_collection_parser_dialog.sh
```

### Command-Line Method
```bash
python3 scripts/archive_collection_parser.py "https://archive.org/details/JHiggens"
```

---

## 📁 What Was Created

| File | Location | Size | Purpose |
|------|----------|------|---------|
| **Channel YAML** | `data/magnum-pi-channel.yaml` | 129 KB | 298 episodes |
| **Schedule YAML** | `schedules/magnum-pi-schedule.yml` | 54 KB | Playback + breaks |
| **Python Parser** | `scripts/archive_collection_parser.py` | 485 lines | CLI tool |
| **GUI Script** | `scripts/archive_collection_parser_dialog.sh` | 333 lines | Interactive UI |

---

## 🎬 Magnum P.I. Channel Stats

- **Channel Number**: 80
- **Total Episodes**: 298
- **Seasons**: 8 + 3 specials
- **Breaks**: 296 (2-5 minutes each)
- **Runtime**: ~250-263 hours
- **Source**: https://archive.org/details/JHiggens

---

## 🚀 Import & Run

```bash
# 1. Import channel
python3 scripts/import_channels.py data/magnum-pi-channel.yaml

# 2. Start server
./start_server.sh

# 3. Tune to channel 80!
```

---

## 🛠️ Command-Line Options

```bash
python3 scripts/archive_collection_parser.py \
    "URL" \
    --channel-number 80 \
    --channel-name "My Channel" \
    --min-break 2 \
    --max-break 5 \
    --output-dir ~/Desktop
```

---

## 📊 Verify Generation

```bash
# Count episodes
grep -c "^      - id: magnum_" data/magnum-pi-channel.yaml
# Result: 298

# Count breaks
grep -c "# .* minute break" schedules/magnum-pi-schedule.yml
# Result: 296

# View sample
head -50 data/magnum-pi-channel.yaml
```

---

## 📚 Documentation

- **Complete Guide**: `MAGNUM_PI_CHANNEL_COMPLETE.md`
- **Tool README**: `scripts/ARCHIVE_PARSER_README.md`
- **Implementation**: `ARCHIVE_PARSER_IMPLEMENTATION_SUMMARY.md`

---

## 🎨 Customize

### Change Breaks
```bash
# 1-2 minute breaks
python3 scripts/archive_collection_parser.py URL --min-break 1 --max-break 2

# 5-10 minute breaks
python3 scripts/archive_collection_parser.py URL --min-break 5 --max-break 10
```

### Multiple Channels
```bash
# Channel 80
python3 scripts/archive_collection_parser.py "URL1" --channel-number 80

# Channel 81
python3 scripts/archive_collection_parser.py "URL2" --channel-number 81
```

---

## ✅ Success Checklist

- [x] 298 episodes generated
- [x] 296 breaks enforced (2-5 min each)
- [x] Python CLI tool created
- [x] swiftDialog GUI created
- [x] Complete documentation
- [x] Files in correct locations
- [x] Ready to import and stream

---

## 🆘 Common Issues

**Problem**: "requests module not found"  
**Solution**: `pip3 install requests`

**Problem**: "swiftDialog not found"  
**Solution**: Script auto-installs, or get from https://github.com/swiftDialog/swiftDialog

**Problem**: "Collection not found"  
**Solution**: Verify URL at archive.org

---

## 🎉 You're Ready!

Your complete Magnum P.I. channel with **298 episodes** and **296 enforced breaks** (2-5 minutes each) is ready to stream!

**Happy Streaming! 📺**


## ARCHIVE ORG REDIRECT FIX

# Archive.org 302 Redirect Fix

## Issue

StreamTV was encountering errors when trying to stream Magnum P.I. episodes:

```
httpx.HTTPStatusError: Redirect response '302 Found' for url 'https://archive.org/download/JHiggens/...'
Redirect location: 'https://dn720208.ca.archive.org/0/items/JHiggens/...'
```

## Root Cause

Archive.org returns **302 redirects** to direct file servers (e.g., `dn720208.ca.archive.org`), but the HTTP client wasn't configured to follow these redirects automatically.

## Fix Applied

Updated `streamtv/streaming/stream_manager.py` to enable redirect following:

### Before
```python
async with httpx.AsyncClient(timeout=config.streaming.timeout) as client:
    async with client.stream('GET', stream_url, headers=headers) as response:
```

### After
```python
async with httpx.AsyncClient(timeout=config.streaming.timeout, follow_redirects=True) as client:
    async with client.stream('GET', stream_url, headers=headers, follow_redirects=True) as response:
```

## Changes Made

1. **Line 138**: Added `follow_redirects=True` to `AsyncClient` initialization
2. **Line 129**: Added `follow_redirects=True` to authenticated Archive.org streaming

## How to Apply

1. **Restart StreamTV server**:
   ```bash
   # Stop current server (Ctrl+C)
   # Then restart:
   ./start_server.sh
   ```

2. **Test Magnum P.I. channel**: Try streaming from Channel 80

## Verification

After restart, the logs should show:
- ✅ No more "302 Found" errors
- ✅ Successful streaming from Archive.org
- ✅ Content plays without authentication (for public videos)

## Notes

- Archive.org uses multiple CDN servers
- The 302 redirect points to the optimal server for your location
- This is normal Archive.org behavior
- Following redirects is required for all Archive.org content

---

**Status**: ✅ Fixed  
**Date**: December 3, 2025  
**Affected**: All Archive.org streaming (including Magnum P.I. channel)


---

## ARCHIVE PARSER IMPLEMENTATION SUMMARY

# 🎉 Archive.org Collection Parser - Implementation Complete! ✅

## Executive Summary

Successfully created a **complete automated system** for generating StreamTV channels from Archive.org collections, with **strict enforcement** of 2-5 minute breaks between episodes. Includes both command-line and beautiful GUI tools.

---

## 📊 What Was Delivered

### 1. Complete Magnum P.I. Channel ⭐

**298 Episodes** parsed and configured from https://archive.org/details/JHiggens

| Metric | Value |
|--------|-------|
| **Total Episodes** | 298 |
| **Seasons** | 8 + Specials |
| **Channel Number** | 80 |
| **Inter-Episode Breaks** | 296 (strictly enforced) |
| **Break Duration** | 2-5 minutes (randomized) |
| **Total Runtime** | ~250-263 hours |
| **Generated YAML Lines** | 5,433 lines |

#### Season Breakdown
- Season 1: 36 episodes
- Season 2: 42 episodes  
- Season 3: 44 episodes
- Season 4: 42 episodes
- Season 5: 44 episodes
- Season 6: 40 episodes
- Season 7: 21 episodes
- Season 8: 26 episodes
- Specials: 3 episodes

---

### 2. Python Parser Tool 🐍

**File**: `scripts/archive_collection_parser.py` (485 lines)

#### Features
✅ **Automatic Metadata Fetching** from Archive.org API  
✅ **Smart Episode Parsing** (extracts season/episode from filenames)  
✅ **Title Cleaning** (removes technical jargon)  
✅ **Complete YAML Generation** (channels + schedules)  
✅ **Strict Break Enforcement** (2-5 minutes between episodes)  
✅ **Multiple Format Support** (.mp4, .avi, .mkv, .mov, etc.)  
✅ **Configurable Settings** (channel number, name, break duration)  
✅ **Error Handling** (graceful failures, detailed messages)

#### Usage Example
```bash
python3 scripts/archive_collection_parser.py \
    "https://archive.org/details/JHiggens" \
    --channel-number 80 \
    --channel-name "Magnum P.I. Complete Series" \
    --min-break 2 \
    --max-break 5 \
    --output-dir ~/Desktop
```

#### Output
- Channel YAML (3,587 lines)
- Schedule YAML (1,846 lines)
- Detailed summary
- Episode statistics

---

### 3. swiftDialog Interactive Script 🖥️

**File**: `scripts/archive_collection_parser_dialog.sh` (333 lines)

#### Features
✅ **Beautiful macOS GUI** using swiftDialog  
✅ **User-Friendly Workflow** (guided step-by-step)  
✅ **Auto-Install Dependencies** (swiftDialog, Python modules)  
✅ **Input Validation** (URL verification, required fields)  
✅ **Progress Indicators** (real-time processing status)  
✅ **Results Preview** (episode counts, season breakdown)  
✅ **Automatic File Management** (saves to correct directories)  
✅ **Finder Integration** (opens generated files)

#### Workflow

1. **Welcome Screen**
   ```
   ┌─────────────────────────────────────┐
   │ Archive.org Collection Parser       │
   │                                     │
   │ Welcome to StreamTV Parser!         │
   │ Create channels from Archive.org    │
   │                                     │
   │ [ Continue ]  [ Cancel ]            │
   └─────────────────────────────────────┘
   ```

2. **Input Form**
   ```
   Enter Collection Information:
   ┌─────────────────────────────────────┐
   │ Collection URL: [________________] │
   │ Channel Number: [80____________]   │
   │ Channel Name:   [________________] │
   │ Min Break (min): ▼2                │
   │ Max Break (min): ▼5                │
   │                                     │
   │ [ Parse Collection ]  [ Cancel ]    │
   └─────────────────────────────────────┘
   ```

3. **Processing**
   ```
   ┌─────────────────────────────────────┐
   │ Processing Collection               │
   │                                     │
   │ Fetching metadata and generating    │
   │ YAML files...                       │
   │                                     │
   │ [████████████░░░░░░░░░] 65%         │
   └─────────────────────────────────────┘
   ```

4. **Results**
   ```
   ┌─────────────────────────────────────┐
   │ ✅ Collection Parsed Successfully!  │
   │                                     │
   │ Channel: Magnum P.I. (Channel 80)   │
   │ Total Episodes: 298                 │
   │ Break Duration: 2-5 minutes         │
   │                                     │
   │ Episode Breakdown:                  │
   │   Season 1: 36 episodes             │
   │   Season 2: 42 episodes             │
   │   ...                               │
   │                                     │
   │ [ Save Files ]  [ Cancel ]          │
   └─────────────────────────────────────┘
   ```

5. **Completion**
   ```
   ┌─────────────────────────────────────┐
   │ 🎉 Channel Created Successfully!    │
   │                                     │
   │ Files Saved:                        │
   │ • channel-magnum-pi.yaml            │
   │ • schedule-magnum-pi.yml            │
   │                                     │
   │ Next Steps:                         │
   │ 1. Review the YAML files            │
   │ 2. Import: python3 scripts/...     │
   │ 3. Start StreamTV server            │
   │                                     │
   │ [ Open in Finder ]  [ Done ]        │
   └─────────────────────────────────────┘
   ```

---

## 📁 Generated Files

### Channel Configuration
**Location**: `data/magnum-pi-channel.yaml`  
**Size**: 129 KB  
**Lines**: 3,587  
**Contains**: All 298 episodes with:
- Unique IDs
- Collection groupings (by season)
- Episode types (episode/special)
- Years and broadcast dates
- Network information
- Runtime estimates
- Source URLs (properly encoded)
- Descriptive notes

**Sample Entry**:
```yaml
- id: magnum_s01e01
  collection: "Magnum P.I. - Season 1"
  type: episode
  year: 1981
  slot: "S01E01 - Please Don't Eat The Snow In Hawaii (1)"
  broadcast_date: 1981-09-08
  network: CBS
  runtime: PT48M
  source: archive
  url: https://archive.org/download/JHiggens/...
  notes: "Season 1 Episode 1"
```

### Schedule Configuration
**Location**: `schedules/magnum-pi-schedule.yml`  
**Size**: 54 KB  
**Lines**: 1,846  
**Contains**:
- Content definitions (8 seasons + specials)
- Break collection definition

---

## MAGNUM PI CHANNEL COMPLETE

# 🎉 Magnum P.I. Channel - Complete! ✅

## Summary

A complete **Magnum P.I.** channel has been successfully generated for StreamTV with **298 episodes** from the Archive.org collection, including **296 enforced breaks** (2-5 minutes) between episodes!

---

## 📊 Channel Statistics

### Content Overview

| Metric | Value |
|--------|-------|
| **Total Episodes** | 298 |
| **Seasons** | 8 (plus 3 specials) |
| **Channel Number** | 80 |
| **Inter-Episode Breaks** | 296 |
| **Break Duration** | 2-5 minutes (randomized) |
| **Source** | Archive.org (JHiggens collection) |

### Season Breakdown

- **Specials**: 3 episodes (Murder She Wrote crossover + Rockford Files bonus)
- **Season 1**: 36 episodes
- **Season 2**: 42 episodes
- **Season 3**: 44 episodes
- **Season 4**: 42 episodes
- **Season 5**: 44 episodes
- **Season 6**: 40 episodes
- **Season 7**: 21 episodes
- **Season 8**: 26 episodes (series finale)

### Total Runtime

- **Episodes**: ~238 hours (298 episodes × 48 min average)
- **Breaks**: ~12-25 hours (296 breaks × 2-5 min)
- **Total Content**: ~250-263 hours of continuous programming

---

## 📁 Generated Files

### 1. Channel Configuration
**Location**: `data/magnum-pi-channel.yaml`  
**Size**: 129 KB  
**Contains**: All 298 episodes with complete metadata

### 2. Schedule Configuration
**Location**: `schedules/magnum-pi-schedule.yml`  
**Size**: 54 KB  
**Contains**: Sequential playback schedule with enforced breaks

---

## 🎬 Channel Features

### Content Structure

```
Channel 80: Magnum P.I. Complete Series
├── Season 1 (36 episodes)
│   ├── Episode 1: "Please Don't Eat The Snow In Hawaii (1)"
│   ├── [2-5 min break]
│   ├── Episode 2: "Please Don't Eat The Snow In Hawaii (2)"
│   ├── [2-5 min break]
│   └── ... (continues)
├── Season 2 (42 episodes)
├── Season 3 (44 episodes)
├── Season 4 (42 episodes)
├── Season 5 (44 episodes)
├── Season 6 (40 episodes)
├── Season 7 (21 episodes)
├── Season 8 (26 episodes)
└── Specials (3 episodes)
    ├── Murder She Wrote: Magnum on Ice
    └── The Rockford Files bonus episodes
```

### Break System

**Strictly Enforced**: Every episode is followed by a break (except the last)
- **Duration**: Randomly selected between 2-5 minutes
- **Implementation**: ISO 8601 duration format (PT2M, PT3M, PT4M, PT5M)
- **Total Breaks**: 296 breaks throughout the schedule
- **Purpose**: Mimics traditional TV commercial breaks

---

## 🛠️ Tools Created

### 1. Python Parser (`scripts/archive_collection_parser.py`)

**Features**:
- Fetches metadata from Archive.org API
- Parses 298 video files automatically
- Extracts season/episode information
- Generates complete YAML configurations
- Enforces 2-5 minute breaks between episodes
- Handles multiple video formats (.mp4, .avi, .mkv, etc.)

**Usage**:
```bash
python3 scripts/archive_collection_parser.py \
    "https://archive.org/details/JHiggens" \
    --channel-number 80 \
    --channel-name "Magnum P.I. Complete Series" \
    --min-break 2 \
    --max-break 5 \
    --output-dir /path/to/output
```

### 2. swiftDialog Interactive Script (`scripts/archive_collection_parser_dialog.sh`)

**Features**:
- Beautiful macOS-native GUI using swiftDialog
- Prompts for collection URL
- Customizable channel settings
- Adjustable break durations
- Progress indicators
- Auto-installation of dependencies
- File management and preview

**Usage**:
```bash
./scripts/archive_collection_parser_dialog.sh
```

**Workflow**:
1. Welcome screen with instructions
2. Prompt for Archive.org URL
3. Configure channel number and name
4. Set break duration (min/max)
5. Parse collection with progress indicator
6. Review results and episode counts
7. Save files to StreamTV directories
8. Open generated files in Finder

---

## 📝 YAML Structure

### Channel YAML Example

```yaml
channels:
  - number: "80"
    name: "Magnum P.I. Complete Series"
    group: "Classic Television"
    description: "Complete Magnum P.I. series (1980-1988)..."
    enabled: true
    streams:
      - id: magnum_s01e01
        collection: "Magnum P.I. - Season 1"
        type: episode
        year: 1981
        slot: "S01E01 - Please Don't Eat The Snow In Hawaii (1)"
        broadcast_date: 1981-09-08
        network: CBS
        runtime: PT48M
        source: archive
        url: https://archive.org/download/JHiggens/...
        notes: "Season 1 Episode 1"
```

### Schedule YAML Example

```yaml
name: Magnum P.I. Marathon
description: >-
  24/7 marathon with 2-5 minute breaks between episodes.
  
content:
  - key: season1
    collection: Magnum P.I. - Season 1
    order: chronological
  - key: break_short
    collection: Inter-Episode Breaks
    order: random

sequence:
  - key: magnum-marathon
    items:
      - all: season1
        custom_title: "Season 1 Episode 1"
      # 3 minute break
      - all: break_short
        custom_title: "Inter-Episode Break"
        duration: PT3M
      - all: season1
        custom_title: "Season 1 Episode 2"
      # 5 minute break
      - all: break_short
        duration: PT5M

playout:
  - sequence: magnum-marathon
  - repeat: true
```


---

## MAGNUM PI RESTART COMPLETE

# ✅ Magnum P.I. Channel Restart - Complete!

## Summary

Successfully **restarted Channel 80 from scratch** - cleaned database, regenerated YAML files, and re-imported.

---

## 🔄 What Was Done

### 1. ✅ Cleaned Old Data
- Deleted Channel 80 from database
- Removed 9 collections (Seasons 1-8 + Specials)
- Removed 1 playlist
- Cleared all associated media items

### 2. ✅ Regenerated YAML Files
- Fetched fresh metadata from Archive.org
- Generated new `magnum-pi-channel.yaml` (128 KB)
- Generated new `magnum-pi-schedule.yml` (54 KB)
- 298 episodes parsed
- 296 breaks enforced (2-5 minutes)

### 3. ✅ Re-imported Channel
- Imported fresh data into database
- Created 9 collections
- Configured all 298 episodes
- Channel enabled and ready

---

## 📊 Current Status

### Channel Information
- **Channel Number**: 80
- **Name**: Magnum P.I. Complete Series
- **Group**: Classic Television
- **Status**: ✅ Enabled
- **Episodes**: 298
- **Collections**: 9

### Collections Breakdown
- Magnum P.I. - Specials: 3 episodes
- Magnum P.I. - Season 1: 36 episodes
- Magnum P.I. - Season 2: 42 episodes
- Magnum P.I. - Season 3: 44 episodes
- Magnum P.I. - Season 4: 42 episodes
- Magnum P.I. - Season 5: 44 episodes
- Magnum P.I. - Season 6: 40 episodes
- Magnum P.I. - Season 7: 21 episodes
- Magnum P.I. - Season 8: 26 episodes

---

## 📺 All Channels

1. ✅ Channel 1980: 1980 Lake Placid Winter Olympics
2. ✅ Channel 1984: 1984 Sarajevo Winter Olympics
3. ✅ Channel 1988: 1988 Calgary Winter Olympics
4. ✅ Channel 1992: 1992 Albertville Winter Olympics
5. ✅ Channel 1994: 1994 Lillehammer Winter Olympics
6. ✅ **Channel 80: Magnum P.I. Complete Series** ⭐

---

## 🚀 Next Steps

### Restart Server
The channel is in the database, but you need to restart for it to appear in the UI:

```bash
# Stop current server (Ctrl+C if running)
# Then restart:
./start_server.sh
```

### Access the Channel
After restarting:
1. **Web UI**: http://localhost:8410/channels
2. **IPTV Playlist**: http://localhost:8410/iptv/channels.m3u
3. **Direct Stream**: http://localhost:8410/iptv/stream/80

### Test Streaming
```bash
# Test the stream URL
curl -I http://localhost:8410/iptv/stream/80

# Or open in VLC
vlc http://localhost:8410/iptv/stream/80
```

---

## 📁 Files

### Generated YAML Files
- `data/magnum-pi-channel.yaml` (128 KB)
- `schedules/magnum-pi-schedule.yml` (54 KB)

### Database
- Channel 80 with all 298 episodes
- 9 collections (by season)
- 1 playlist
- All media items linked

---

## 🔧 Configuration Applied

### Break System
- **Min Break**: 2 minutes
- **Max Break**: 5 minutes
- **Total Breaks**: 296 (between all episodes)
- **Random Duration**: Each break randomly 2-5 minutes

### Episode Format
- **Type**: event (per StreamTV schema)
- **Source**: archive.org
- **Runtime**: PT48M (48 minutes average)
- **Network**: CBS
- **Years**: 1980-1988

---

## ✅ Verification

### Database Check
```bash
# Count channels
SELECT COUNT(*) FROM channels WHERE number = '80';
# Result: 1

# Count collections
SELECT COUNT(*) FROM collections WHERE name LIKE '%Magnum%';
# Result: 9

# Count total episodes
SELECT COUNT(*) FROM collection_items 
WHERE collection_id IN (
    SELECT id FROM collections WHERE name LIKE '%Magnum%'
);
# Result: 298
```

### Files Check
```bash
ls -lh data/magnum-pi-channel.yaml
# Result: 128K

ls -lh schedules/magnum-pi-schedule.yml
# Result: 54K

grep -c "^      - id: magnum_" data/magnum-pi-channel.yaml
# Result: 298

grep -c "# .* minute break" schedules/magnum-pi-schedule.yml
# Result: 296
```

---

## 🎬 Ready to Stream!

Your Magnum P.I. channel has been **completely restarted from scratch** and is ready to stream!

- ✅ Database cleaned
- ✅ Fresh YAML files generated
- ✅ Channel imported successfully
- ✅ All 298 episodes configured
- ✅ 296 breaks enforced
- ✅ Ready for playback

**Just restart the server and tune to Channel 80!** 📺

---

**Date**: December 3, 2025  
**Status**: ✅ Complete  
**Action**: Restart server to see changes


---

## QUICK REFERENCE ARCHIVE PARSER

# 🎯 Archive.org Collection Parser - Quick Reference

## ⚡ Quick Start

### GUI Method (Recommended)
```bash
./scripts/archive_collection_parser_dialog.sh
```

### Command-Line Method
```bash
python3 scripts/archive_collection_parser.py "https://archive.org/details/JHiggens"
```

---

## 📁 What Was Created

| File | Location | Size | Purpose |
|------|----------|------|---------|
| **Channel YAML** | `data/magnum-pi-channel.yaml` | 129 KB | 298 episodes |
| **Schedule YAML** | `schedules/magnum-pi-schedule.yml` | 54 KB | Playback + breaks |
| **Python Parser** | `scripts/archive_collection_parser.py` | 485 lines | CLI tool |
| **GUI Script** | `scripts/archive_collection_parser_dialog.sh` | 333 lines | Interactive UI |

---

## 🎬 Magnum P.I. Channel Stats

- **Channel Number**: 80
- **Total Episodes**: 298
- **Seasons**: 8 + 3 specials
- **Breaks**: 296 (2-5 minutes each)
- **Runtime**: ~250-263 hours
- **Source**: https://archive.org/details/JHiggens

---

## 🚀 Import & Run

```bash
# 1. Import channel
python3 scripts/import_channels.py data/magnum-pi-channel.yaml

# 2. Start server
./start_server.sh

# 3. Tune to channel 80!
```

---

## 🛠️ Command-Line Options

```bash
python3 scripts/archive_collection_parser.py \
    "URL" \
    --channel-number 80 \
    --channel-name "My Channel" \
    --min-break 2 \
    --max-break 5 \
    --output-dir ~/Desktop
```

---

## 📊 Verify Generation

```bash
# Count episodes
grep -c "^      - id: magnum_" data/magnum-pi-channel.yaml
# Result: 298

# Count breaks
grep -c "# .* minute break" schedules/magnum-pi-schedule.yml
# Result: 296

# View sample
head -50 data/magnum-pi-channel.yaml
```

---

## 📚 Documentation

- **Complete Guide**: `MAGNUM_PI_CHANNEL_COMPLETE.md`
- **Tool README**: `scripts/ARCHIVE_PARSER_README.md`
- **Implementation**: `ARCHIVE_PARSER_IMPLEMENTATION_SUMMARY.md`

---

## 🎨 Customize

### Change Breaks
```bash
# 1-2 minute breaks
python3 scripts/archive_collection_parser.py URL --min-break 1 --max-break 2

# 5-10 minute breaks
python3 scripts/archive_collection_parser.py URL --min-break 5 --max-break 10
```

### Multiple Channels
```bash
# Channel 80
python3 scripts/archive_collection_parser.py "URL1" --channel-number 80

# Channel 81
python3 scripts/archive_collection_parser.py "URL2" --channel-number 81
```

---

## ✅ Success Checklist

- [x] 298 episodes generated
- [x] 296 breaks enforced (2-5 min each)
- [x] Python CLI tool created
- [x] swiftDialog GUI created
- [x] Complete documentation
- [x] Files in correct locations
- [x] Ready to import and stream

---

## 🆘 Common Issues

**Problem**: "requests module not found"  
**Solution**: `pip3 install requests`

**Problem**: "swiftDialog not found"  
**Solution**: Script auto-installs, or get from https://github.com/swiftDialog/swiftDialog

**Problem**: "Collection not found"  
**Solution**: Verify URL at archive.org

---

## 🎉 You're Ready!

Your complete Magnum P.I. channel with **298 episodes** and **296 enforced breaks** (2-5 minutes each) is ready to stream!

**Happy Streaming! 📺**


---

## USAGE EXAMPLES

# Archive.org Collection Parser - Usage Examples

## 🎬 Example 1: Magnum P.I. (Already Done!)

### Using the GUI
```bash
./scripts/archive_collection_parser_dialog.sh
```

**Inputs**:
- URL: `https://archive.org/details/JHiggens`
- Channel Number: `80`
- Channel Name: `Magnum P.I. Complete Series`
- Min Break: `2` minutes
- Max Break: `5` minutes

**Result**: 298 episodes with 296 enforced breaks

---

## 📺 Example 2: Another TV Show

### Command-Line
```bash
python3 scripts/archive_collection_parser.py \
    "https://archive.org/details/TheRockfordFiles" \
    --channel-number 81 \
    --channel-name "The Rockford Files" \
    --min-break 2 \
    --max-break 5 \
    --output-dir data/
```

Then move and import:
```bash
mv data/magnum-pi-schedule.yml schedules/rockford-files-schedule.yml
python3 scripts/import_channels.py data/magnum-pi-channel.yaml
```

---

## 🎥 Example 3: Movie Collection

### Shorter Breaks for Movies
```bash
python3 scripts/archive_collection_parser.py \
    "https://archive.org/details/feature_films" \
    --channel-number 82 \
    --channel-name "Classic Cinema" \
    --min-break 1 \
    --max-break 3 \
    --output-dir ~/Desktop/movies_channel
```

Movies are longer, so use shorter breaks (1-3 minutes) between films.

---

## 📚 Example 4: Documentary Series

### Longer Breaks for Educational Content
```bash
./scripts/archive_collection_parser_dialog.sh
```

**Inputs**:
- URL: `https://archive.org/details/documentary_series`
- Channel Number: `83`
- Channel Name: `Documentary Marathon`
- Min Break: `5` minutes
- Max Break: `10` minutes

Longer breaks give viewers time to process information.

---

## 🎭 Example 5: Multiple Channels at Once

### Batch Processing
```bash
#!/bin/bash
# Create multiple channels

collections=(
    "JHiggens:80:Magnum P.I."
    "RockfordFiles:81:The Rockford Files"
    "MurderSheWrote:82:Murder She Wrote"
)

for item in "${collections[@]}"; do
    IFS=':' read -r collection channel_num name <<< "$item"
    
    python3 scripts/archive_collection_parser.py \
        "https://archive.org/details/$collection" \
        --channel-number "$channel_num" \
        --channel-name "$name" \
        --min-break 2 \
        --max-break 5 \
        --output-dir "data/batch_$collection"
    
    echo "✅ Generated channel $channel_num: $name"
done
```

---

## 🔍 Example 6: Test with Small Collection

### Quick Test
```bash
# Test with a small collection first
python3 scripts/archive_collection_parser.py \
    "SmallTestCollection" \
    --channel-number 99 \
    --output-dir /tmp/test_channel

# Review output
ls -lh /tmp/test_channel/
cat /tmp/test_channel/magnum-pi-channel.yaml | head -50
```

---

## 🎨 Example 7: Custom Break Durations

### No Breaks (Back-to-Back)
```bash
# Set min and max both to 0
python3 scripts/archive_collection_parser.py \
    "URL" \
    --min-break 0 \
    --max-break 0
```

### Very Short Breaks (30 seconds)
```bash
# Note: Convert to minutes (0.5 = 30 seconds)
# Currently only supports whole minutes, so use 1 minute minimum
python3 scripts/archive_collection_parser.py \
    "URL" \
    --min-break 1 \
    --max-break 1
```

### Commercial-Length Breaks
```bash
# Traditional TV commercial breaks (2-3 minutes)
python3 scripts/archive_collection_parser.py \
    "URL" \
    --min-break 2 \
    --max-break 3
```

### Extended Breaks
```bash
# Longer breaks for bathroom/snack runs (5-10 minutes)
python3 scripts/archive_collection_parser.py \
    "URL" \
    --min-break 5 \
    --max-break 10
```

---

## 🛠️ Example 8: Troubleshooting Mode

### Debug Output
```bash
# Run with verbose Python
python3 -v scripts/archive_collection_parser.py "URL" 2>&1 | tee debug.log

# Check what was parsed
grep "Found.*video files" debug.log
grep "Total Episodes" debug.log
```

---

## 📊 Example 9: Verify Generated Files

### Check Episode Count
```bash
# Count episodes in channel YAML
grep -c "^      - id:" data/magnum-pi-channel.yaml

# Count breaks in schedule YAML
grep -c "# .* minute break" schedules/magnum-pi-schedule.yml
```

### View Break Distribution
```bash
# See how breaks are distributed
grep "duration: PT" schedules/magnum-pi-schedule.yml | \
    sed 's/.*PT\([0-9]*\)M/\1/' | \
    sort -n | \
    uniq -c

# Output example:
#   58 2
#   62 3

---

## Related Pages

- [Scripts and Tools](Scripts-and-Tools)
- [Home](Home)
