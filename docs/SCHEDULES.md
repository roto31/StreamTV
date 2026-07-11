# Schedule YAML File Support

StreamTV now supports schedule YAML files that define complex playback sequences with pre-roll, mid-roll, post-roll commercials, custom titles, and duration-based fillers.

## Overview

Schedule files are located in the `schedules/` directory and follow a specific YAML format. When a channel has a matching schedule file (e.g., `mn-olympics-1980.yml` for channel "1980"), StreamTV will automatically use it to generate the playback sequence instead of simple playlists.

## Schedule File Format

Schedule files contain three main sections:

### 1. Content Definitions

Maps content keys to collections and their playback order:

```yaml
content:
  - key: 1980_opening
    collection: Retro Olympics - 1980 Opening Ceremony (ABC)
    order: chronological
  - key: mn80_pre_roll
    collection: MN 1980 Pre-Roll IDs (TC Media Now)
    order: shuffle
```

- `key`: Unique identifier for this content
- `collection`: Name of the collection/playlist in the database
- `order`: `chronological` or `shuffle`

### 2. Sequences

Defines reusable sequences of content:

```yaml
sequence:
  - key: mn80-pre-roll
    items:
      - duration: "00:01:00"
        content: mn80_pre_roll
        filler_kind: Commercial
        trim: true
        discard_attempts: 2
  - key: mn80-channel
    items:
      - pre_roll: true
        sequence: mn80-pre-roll
      - all: 1980_opening
        custom_title: "Lake Placid Opening Ceremony (ABC)"
      - pre_roll: false
```

Sequence items can be:
- **Duration-based fillers**: `duration` + `content` key
- **Content blocks**: `all` + content key (plays all items from collection)
- **Sequence references**: `sequence` key (references another sequence)
- **Pre-roll/Mid-roll/Post-roll flags**: Control when commercial sequences are inserted

### 3. Playout Instructions

Defines which sequence to play and whether to repeat:

```yaml
playout:
  - sequence: mn80-channel
  - repeat: true
```

## Setup Steps

### 1. Import Media and Collections

First, import media items and create collections:

```bash
# Import media items from data/retro_olympics_streams.yaml
python3 scripts/import_olympics_data.py

# Import collections (groups media items by collection name)
python3 scripts/import_collections.py
```

### 2. Schedule File Location

Place schedule YAML files in the `schedules/` directory. The file name should match the channel number:

- Channel "1980" → `schedules/mn-olympics-1980.yml`
- Channel "1984" → `schedules/mn-olympics-1984.yml`
- Channel "1988" → `schedules/mn-olympics-1988.yml`

### 3. Automatic Detection

StreamTV automatically detects and loads schedule files when generating HLS streams or EPG data. No additional configuration is needed.

## Features

### Pre-Roll, Mid-Roll, Post-Roll

Schedule files support inserting commercial sequences before, during, and after content:

```yaml
- pre_roll: true
  sequence: mn80-pre-roll
- all: 1980_opening
  custom_title: "Lake Placid Opening Ceremony (ABC)"
- pre_roll: false
```

When `pre_roll: true` is set, items from the referenced sequence are inserted before the next content block. When `pre_roll: false`, pre-roll insertion stops.

### Custom Titles

Override media item titles in EPG and playlists:

```yaml
- all: 1980_opening
  custom_title: "Lake Placid Opening Ceremony (ABC)"
```

### Duration-Based Fillers

Fill a specific duration with items from a collection:

```yaml
- duration: "00:08:00"
  content: ads_1980_wjcl
  filler_kind: Commercial
  trim: true
  discard_attempts: 6
```

The system will select items from the collection to fill approximately 8 minutes, with up to 6 discard attempts if items don't fit.

### Repeat

Enable infinite looping:

```yaml
playout:
  - sequence: mn80-channel
  - repeat: true
```

When `repeat: true`, the sequence will loop indefinitely.

## How It Works

1. **HLS Stream Generation** (`/iptv/channel/{channel_number}.m3u8`):
   - Checks for schedule file matching channel number
   - Parses YAML and generates playlist from sequence
   - Falls back to database playlists if no schedule file found

2. **EPG Generation** (`/iptv/xmltv.xml`):
   - Uses schedule to generate program listings
   - Applies custom titles
   - Calculates start/end times for each program

3. **Collection Mapping**:
   - Schedule files reference collections by name
   - Collections are created from `data/retro_olympics_streams.yaml`
   - Media items are grouped by the `collection` field

## Troubleshooting

### Schedule Not Loading

- Check that the schedule file exists in `schedules/` directory
- Verify the file name matches the channel number pattern
- Check server logs for parsing errors

### Collections Not Found

- Run `python3 scripts/import_collections.py` to create collections
- Verify collection names in schedule file match database collection names
- Check that media items have been imported first

### Empty Playlist

- Ensure collections contain media items
- Verify content keys in schedule file match keys in `content` section
- Check that sequence references are correct

## Example Schedule File

See `schedules/mn-olympics-1980.yml` for a complete example with:
- Multiple content definitions
- Pre-roll, mid-roll, post-roll sequences
- Custom titles
- Duration-based fillers
- Repeat logic

