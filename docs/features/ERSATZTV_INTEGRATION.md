# ErsatzTV Integration - Enhanced Scheduling Features

This document describes the ErsatzTV-compatible features that have been integrated into the StreamTV platform.

## Overview

The platform now supports advanced scheduling features inspired by [ErsatzTV](https://github.com/ErsatzTV/ErsatzTV), allowing for more sophisticated channel programming while maintaining compatibility with direct streaming from YouTube and Archive.org.

## New Features

### 1. YAML Import Support

Schedule files can now import other YAML files to share common content definitions and sequences:

```yaml
import:
  - common-commercials.yml
  - shared-sequences.yml

content:
  - key: my_content
    collection: My Collection
    order: chronological
```

**How it works:**
- Imported files are processed first
- Content and sequences are merged (existing keys take precedence)
- Supports relative and absolute paths
- Imports are processed recursively

### 2. Advanced Scheduling Directives

#### `padToNext` - Pad to Next Time Boundary

Pads the schedule to the next hour or half-hour boundary:

```yaml
sequence:
  - key: my-sequence
    items:
      - padToNext: 30  # Pad to next 30-minute boundary
        content: filler_collection
        fallback: backup_filler
        filler_kind: Commercial
```

**Parameters:**
- `padToNext`: Minutes to pad to (e.g., 30 for half-hour, 60 for hour)
- `content`: Primary content collection to use for padding
- `fallback`: Fallback collection if primary is insufficient
- `filler_kind`: Type of filler (Commercial, Filler, etc.)
- `trim`: Whether to trim items to fit exactly
- `discard_attempts`: Number of items to skip if too long

#### `padUntil` - Pad Until Specific Time

Pads the schedule until a specific time:

```yaml
sequence:
  - key: my-sequence
    items:
      - padUntil: "14:00:00"  # Pad until 2:00 PM
        content: filler_collection
        filler_kind: Commercial
```

**Parameters:**
- `padUntil`: Target time in HH:MM or HH:MM:SS format
- `content`: Content collection to use for padding
- `fallback`: Fallback collection
- Other parameters same as `padToNext`

#### `waitUntil` - Wait Until Specific Time

Waits until a specific time before continuing:

```yaml
sequence:
  - key: my-sequence
    items:
      - waitUntil: "08:00:00"  # Wait until 8:00 AM
        tomorrow: false  # If time passed, wait until tomorrow
        rewindOnReset: true  # On reset, rewind to today's time
```

**Parameters:**
- `waitUntil`: Target time in HH:MM or HH:MM:SS format
- `tomorrow`: If true and time has passed, wait until tomorrow
- `rewindOnReset`: If true, on reset use today's time instead of tomorrow

#### `skipItems` - Skip Items from Collection

Skips a specified number of items from a collection:

```yaml
sequence:
  - key: my-sequence
    items:
      - skipItems: 5  # Skip 5 items
        content: my_collection
      - skipItems: "count/2"  # Skip half the items
        content: my_collection
      - skipItems: "random"  # Skip random number
        content: my_collection
```

**Parameters:**
- `skipItems`: Number or expression ("count/2", "random")
- `content`: Collection to skip items from

**Expressions:**
- Integer: Skip exact number
- `"count/2"`: Skip half the items
- `"random"`: Skip random number of items

#### `shuffleSequence` - Shuffle a Sequence

Shuffles the items in a sequence:

```yaml
sequence:
  - key: my-sequence
    items:
      - shuffleSequence: commercial-break-sequence
```

**Parameters:**
- `shuffleSequence`: Key of the sequence to shuffle

### 3. Enhanced EPG Generation

The Electronic Program Guide (EPG) now includes:

- **Categories**: Automatically categorizes programs (Sports, Commercial, Filler, etc.)
- **Episode Information**: Includes episode metadata when available
- **Better Time Management**: More accurate start/end times based on actual content duration
- **Custom Titles**: Supports custom titles from schedule definitions

### 4. Improved Time Management

The scheduling engine now:

- Tracks time more accurately through the schedule
- Handles time boundaries (hour/half-hour) precisely
- Supports time-based directives (waitUntil, padUntil)
- Maintains continuous playback with proper time tracking

## Usage Examples

### Example 1: Hour-Based Programming with Padding

```yaml
name: Hourly News Channel
description: News channel that starts on the hour

content:
  - key: news_content
    collection: News Programs
    order: chronological
  - key: commercial_filler
    collection: Commercial Breaks
    order: shuffle

sequence:
  - key: hourly-news
    items:
      - padToNext: 60  # Pad to next hour
        content: commercial_filler
        filler_kind: Commercial
      - all: news_content
        custom_title: "Hourly News Update"

playout:
  - sequence: hourly-news
  - repeat: true
```

### Example 2: Time-Based Scheduling

```yaml
name: Morning Show Channel
description: Starts at 6 AM daily

content:
  - key: morning_show
    collection: Morning Shows
    order: chronological

sequence:
  - key: daily-morning
    items:
      - waitUntil: "06:00:00"  # Wait until 6 AM
      - all: morning_show

playout:
  - sequence: daily-morning
  - repeat: true
```

### Example 3: Importing Shared Content

**common-commercials.yml:**
```yaml
content:
  - key: national_ads
    collection: National Commercials
    order: shuffle
  - key: local_ads
    collection: Local Commercials
    order: shuffle
```

**channel.yml:**
```yaml
import:
  - common-commercials.yml

content:
  - key: main_content
    collection: Main Programs
    order: chronological

sequence:
  - key: main-sequence
    items:
      - duration: "00:02:00"
        content: national_ads  # From imported file
        filler_kind: Commercial
      - all: main_content
```

## Compatibility

All existing YAML schedule files remain compatible. New features are optional and can be added incrementally.

## References

- [ErsatzTV GitHub](https://github.com/ErsatzTV/ErsatzTV)
- [ErsatzTV Documentation](https://ersatztv.org/docs/)
- [ErsatzTV YAML Scheduling](https://github.com/ErsatzTV/ErsatzTV/tree/main/ErsatzTV.Core/Scheduling/YamlScheduling)

## Implementation Notes

- The platform uses Python instead of C#/.NET, so some ErsatzTV features that require .NET-specific libraries are adapted for Python
- Direct streaming from YouTube/Archive.org is maintained (no local file requirements)
- All ErsatzTV scheduling patterns are supported while keeping the lightweight Python architecture

