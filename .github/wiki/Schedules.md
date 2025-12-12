# Schedules

Complete guide to creating and managing schedule files for StreamTV channels.

## Overview

Schedule files define how content is organized and played on a channel. They use YAML format and support advanced features like pre-roll commercials, mid-roll breaks, and custom sequencing.

## Schedule File Location

Schedule files are stored in the `schedules/` directory. The filename should match your channel number or name:

- Channel "1980" → `schedules/mn-olympics-1980.yml`
- Channel "1992" → `schedules/mn-olympics-1992.yml`

## Basic Structure

```yaml
name: My Channel
description: Channel description

content:
  - key: content_key
    collection: Collection Name
    order: chronological

sequence:
  - key: main_sequence
    items:
      - all: content_key

playout:
  - sequence: main_sequence
  - repeat: true
```

## Content Definitions

Content definitions map keys to collections:

```yaml
content:
  - key: day01
    collection: 1980 Winter Olympics - Day 01
    order: chronological
  - key: pre_roll
    collection: Pre-Roll IDs
    order: shuffle
```

**Options:**
- `key` - Unique identifier for this content
- `collection` - Name of the collection in the database
- `order` - Playback order: `chronological` or `shuffle`

## Sequences

Sequences define reusable playback patterns:

```yaml
sequence:
  - key: pre-roll-sequence
    items:
      - duration: "00:03:00"
        content: pre_roll
        filler_kind: Commercial
        trim: true
        discard_attempts: 3
  - key: main-sequence
    items:
      - all: day01
        custom_title: "Day 01 Coverage"
```

## Sequence Items

### Duration-Based Filler

Fill a specific duration with content:

```yaml
- duration: "00:03:00"
  content: pre_roll
  filler_kind: Commercial
  trim: true
  discard_attempts: 3
```

**Options:**
- `duration` - Target duration (HH:MM:SS format)
- `content` - Content key to use
- `filler_kind` - Type: `Commercial`, `Program`, `Other`
- `trim` - Trim items to fit duration
- `discard_attempts` - Max attempts to find fitting items

### Content Block

Play all items from a collection:

```yaml
- all: day01
  custom_title: "Day 01 – Opening Ceremony"
```

**Options:**
- `all` - Content key to play
- `custom_title` - Override title in EPG (optional)

### Sequence Reference

Reference another sequence:

```yaml
- sequence: pre-roll-sequence
```

### Pre-Roll/Mid-Roll/Post-Roll

Control commercial insertion:

```yaml
- pre_roll: true
  sequence: pre-roll-sequence
- all: main_content
- pre_roll: false
```

**Mid-Roll with Expression:**

```yaml
- mid_roll: true
  sequence: mid-roll-sequence
  expression: "true"
```

## Playout Instructions

Define the main playback sequence:

```yaml
playout:
  - sequence: main-sequence
  - repeat: true
```

**Options:**
- `sequence` - Main sequence key to play
- `repeat` - Loop indefinitely (`true` or `false`)

## Advanced Features

### Custom Titles

Override media titles in EPG:

```yaml
- all: day01
  custom_title: "Day 01 – Preview and Opening Ceremony"
```

### Commercial Breaks

Insert commercial breaks between content:

```yaml
sequence:
  - key: commercial-break-2min
    items:
      - duration: "00:02:00"
        content: ads_collection
        filler_kind: Commercial
        trim: true
        discard_attempts: 3

  - key: main-sequence
    items:
      - all: day01
      - sequence: commercial-break-2min
      - all: day02
```

### Pre-Roll/Mid-Roll/Post-Roll Control

Enable and disable commercial insertion:

```yaml
- pre_roll: true
  sequence: pre-roll-sequence
- all: main_content
- mid_roll: true
  sequence: mid-roll-sequence
  expression: "true"
- all: more_content
- post_roll: true
  sequence: post-roll-sequence
- pre_roll: false
- mid_roll: false
- post_roll: false
```

## Complete Example

```yaml
name: MN 1980 Winter Olympics (WCCO)
description: >-
  Sequential channel that mirrors ABC's Lake Placid coverage but wraps every
  national feed with WCCO-TV IDs, commercials, and Minneapolis/St. Paul
  newscasts sourced from TC Media Now.

content:
  - key: day01
    collection: 1980 Winter Olympics - Day 01 - Preview and Opening Ceremony
    order: chronological
  - key: pre_roll
    collection: MN 1980 Pre-Roll IDs (TC Media Now)
    order: shuffle
  - key: ads_collection
    collection: Retro Ads - 1980 Pod A
    order: shuffle

sequence:
  - key: pre-roll-sequence
    items:
      - duration: "00:03:00"
        content: pre_roll
        filler_kind: Commercial
        trim: true
        discard_attempts: 3

  - key: commercial-break-2min
    items:
      - duration: "00:02:00"
        content: ads_collection
        filler_kind: Commercial
        trim: true
        discard_attempts: 3

  - key: main-channel
    items:
      # Day 01 - Starts with content
      - all: day01
        custom_title: "Day 01 – Preview and Opening Ceremony"
      
      # Enable pre-roll, mid-roll, post-roll for subsequent content
      - pre_roll: true
        sequence: pre-roll-sequence
      - mid_roll: true
        sequence: mid-roll-sequence
        expression: "true"
      - post_roll: true
        sequence: post-roll-sequence

      # Day 02 with commercial break
      - sequence: commercial-break-2min
      - all: day02
        custom_title: "Day 02 – ABC Coverage"

playout:
  - sequence: main-channel
  - repeat: true
```

## Creating Schedules

### Using the Interactive Creator

```bash
./scripts/create_schedule.sh
```

This launches a SwiftDialog-based interactive tool that guides you through creating a schedule file.

### Manual Creation

1. Create a new YAML file in `schedules/`
2. Define content mappings
3. Create sequences
4. Define playout instructions
5. Save and restart StreamTV

## Validation

Schedule files are validated on load. Common errors:

- **Invalid YAML syntax** - Check indentation and formatting
- **Missing content key** - Ensure all referenced keys exist in `content:`
- **Invalid sequence reference** - Check sequence keys exist
- **Invalid duration format** - Use HH:MM:SS format

## Best Practices

1. **Use descriptive keys** - `day01` is better than `d1`
2. **Organize by purpose** - Group related content together
3. **Test incrementally** - Start simple, add complexity gradually
4. **Document with comments** - Add comments for complex sequences
5. **Reuse sequences** - Create reusable commercial break sequences

## Troubleshooting

### Schedule Not Loading

- Check file is in `schedules/` directory
- Verify YAML syntax is valid
- Check logs for error messages

### Content Not Playing

- Verify collection names match database
- Check content keys are correctly referenced
- Ensure collections have media items

### Commercials Not Inserting

- Verify pre-roll/mid-roll/post-roll sequences exist
- Check sequence keys are correct
- Ensure commercial collections have content

## Next Steps

- Learn about [Schedule Creator](Schedule-Creator) tool
- Read [YAML Validation](YAML-Validation) guide
- Check [Example Schedules](Example-Schedules)

