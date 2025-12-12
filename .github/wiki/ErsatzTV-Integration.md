# ErsatzTV Integration

Guide to integrating StreamTV with ErsatzTV and migrating from ErsatzTV.

## Overview

StreamTV is designed to be compatible with ErsatzTV's API structure and features, making it easy to migrate or use alongside ErsatzTV.

## Compatibility

### API Compatibility

StreamTV implements many ErsatzTV API endpoints:

- `/api/channels` - Channel management
- `/api/media` - Media items
- `/api/collections` - Collections
- `/api/playlists` - Playlists
- `/iptv/channels.m3u` - M3U playlist
- `/iptv/xmltv.xml` - XMLTV EPG

### Feature Comparison

See [ErsatzTV Comparison](../docs/COMPARISON.md) for detailed feature comparison.

## Migration from ErsatzTV

### Step 1: Export Data

Export your ErsatzTV data:
- Channels
- Media items
- Collections
- Playlists

### Step 2: Import to StreamTV

Use import scripts:
```bash
python3 scripts/import_channels.py channels.yaml
python3 scripts/import_collections.py collections.yaml
```

### Step 3: Update Configuration

Update IPTV client configurations to point to StreamTV instead of ErsatzTV.

### Step 4: Test

Verify all channels and streams work correctly.

## Using Alongside ErsatzTV

StreamTV can run alongside ErsatzTV:

1. **Different Ports**
   - ErsatzTV: Default port
   - StreamTV: Port 8410 (configurable)

2. **Different Use Cases**
   - ErsatzTV: Local media library
   - StreamTV: Online streaming sources

3. **Combined Setup**
   - Use both for different channels
   - Combine in IPTV client

## Schedule Compatibility

StreamTV supports ErsatzTV-compatible schedule YAML files:

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

## API Differences

### Media Sources

- **ErsatzTV**: Local files only
- **StreamTV**: YouTube and Archive.org URLs

### Storage

- **ErsatzTV**: Requires media library storage
- **StreamTV**: Minimal storage (metadata only)

### Setup

- **ErsatzTV**: Media library scanning required
- **StreamTV**: Just add URLs

## Integration Status

See [ErsatzTV Integration Status](../ERSATZTV_INTEGRATION_STATUS.md) for current compatibility status.

## Complete Integration Guide

For detailed integration instructions, see [ErsatzTV Complete Integration](../docs/ERSATZTV_COMPLETE_INTEGRATION.md).

## Related Documentation

- [ErsatzTV Comparison](../docs/COMPARISON.md) - Feature comparison
- [ErsatzTV Complete Integration](../docs/ERSATZTV_COMPLETE_INTEGRATION.md) - Full integration guide
- [ErsatzTV Integration Status](../ERSATZTV_INTEGRATION_STATUS.md) - Current status
- [ErsatzTV Integration Summary](../ERSATZTV_INTEGRATION_SUMMARY.md) - Integration summary

