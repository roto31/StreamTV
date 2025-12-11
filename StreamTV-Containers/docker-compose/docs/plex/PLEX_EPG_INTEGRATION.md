# Plex EPG Integration Guide

## Overview

StreamTV now integrates with the [Plex Media Server API](https://developer.plex.tv/pms/#tag/EPG) to enhance EPG (Electronic Program Guide) generation and ensure full compatibility with Plex DVR functionality.

## Benefits

1. **Plex-Compatible XMLTV Format** - Ensures EPG data works seamlessly with Plex
2. **Enhanced Metadata** - Uses Plex API for channel mapping and validation
3. **Better Channel Information** - Leverages Plex's EPG data when available
4. **DVR Integration** - Compatible with Plex DVR functionality

## Configuration

### Step 1: Get Plex Authentication Token

1. Open Plex Media Server web interface
2. Go to Settings → Network
3. Enable "Show Advanced" if needed
4. Find your Plex token in the URL or use the API:
   ```bash
   # Get token from Plex server
   curl -X GET "http://YOUR_PLEX_SERVER:32400/api/v2/resources?includeHttps=1&X-Plex-Token=YOUR_TOKEN"
   ```

Alternatively, you can find your token in:
- Browser developer tools (Network tab) when accessing Plex
- Plex server logs
- Using Plex authentication flow

### Step 2: Configure StreamTV

Add Plex configuration to `config.yaml`:

```yaml
plex:
  enabled: true
  base_url: "http://192.168.1.100:32400"  # Your Plex server URL
  token: "your-plex-token-here"  # Your Plex authentication token
  use_for_epg: true  # Enable EPG enhancement via Plex API
```

### Step 3: Restart StreamTV

Restart the server for changes to take effect.

## How It Works

### With Plex Integration Enabled

1. **Channel Validation**: Plex API validates channel mappings
2. **Metadata Enhancement**: Uses Plex EPG data when available
3. **Format Compliance**: Ensures XMLTV output is fully Plex-compatible
4. **Channel Mapping**: Maps StreamTV channels to Plex EPG channels

### Without Plex Integration

StreamTV generates standard XMLTV format that is compatible with Plex, but without Plex-specific enhancements.

## XMLTV Format Enhancements

The EPG generation now includes Plex-specific improvements:

### Channel Definitions
- **Consistent Channel IDs**: Uses numeric channel numbers as IDs (Plex requirement)
- **Multiple Display Names**: Includes channel name, group, and number
- **Absolute Logo URLs**: Ensures logos are accessible from Plex

### Programme Entries
- **Language Attributes**: All text fields include `lang="en"` attribute
- **Required Fields**: Always includes title, desc, and category (Plex requirements)
- **Absolute Thumbnail URLs**: Ensures thumbnails are accessible
- **Standard XMLTV Fields**: Only uses standard XMLTV fields (no custom fields)

### Format Compliance
- **Proper XML Structure**: Valid XMLTV format
- **Time Format**: Uses `YYYYMMDDHHMMSS +0000` format (Plex compatible)
- **Character Encoding**: UTF-8 encoding
- **XML Escaping**: Proper escaping of special characters

## Plex API Endpoints Used

Based on the [Plex API documentation](https://developer.plex.tv/pms/#tag/EPG):

- **Get DVRs**: `/livetv/dvrs` - List available DVRs
- **Get Channels**: `/livetv/dvrs/epg/channels` - Get channels for a lineup
- **Get Lineups**: `/livetv/dvrs/epg/lineups` - Get available lineups
- **Channel Mapping**: `/livetv/dvrs/epg/channelMap` - Compute best channel map
- **Get Countries**: `/livetv/dvrs/epg/countries` - List available countries

## Troubleshooting

### EPG Not Loading in Plex

**Symptoms**: Plex shows "No guide data available"

**Solutions**:
1. Verify Plex configuration in `config.yaml`
2. Check Plex server is accessible from StreamTV
3. Verify authentication token is correct
4. Check XMLTV format is valid:
   ```bash
   curl http://localhost:8410/iptv/xmltv.xml | xmllint --format -
   ```

### Channel Mapping Issues

**Symptoms**: Channels don't match between StreamTV and Plex

**Solutions**:
1. Ensure channel numbers are consistent
2. Use Plex API channel mapping feature
3. Verify channel IDs in XMLTV match channel numbers

### Missing Programme Data

**Symptoms**: Some channels have no programme listings

**Solutions**:
1. Check schedule files are configured
2. Verify media items have duration information
3. Ensure schedules are within EPG time range

## API Reference

### Plex API Client

The `PlexAPIClient` class provides methods for:

```python
from streamtv.streaming.plex_api_client import PlexAPIClient

# Initialize client
async with PlexAPIClient(base_url="http://plex:32400", token="token") as client:
    # Get server info
    info = await client.get_server_info()
    
    # Get DVRs
    dvrs = await client.get_dvrs()
    
    # Get channels for lineup
    channels = await client.get_channels_for_lineup("lineup_id")
    
    # Compute channel map
    channel_map = await client.compute_best_channel_map(
        channel_numbers=["1", "2", "3"],
        lineup_id="lineup_id"
    )
```

## Best Practices

1. **Use Plex Token**: Always provide authentication token for better access
2. **Validate XMLTV**: Test EPG in Plex before production use
3. **Monitor Logs**: Check logs for Plex API errors
4. **Cache EPG**: EPG is cached for 5 minutes to reduce load
5. **Channel Consistency**: Keep channel numbers consistent between StreamTV and Plex

## Configuration Examples

### Basic Configuration (No Plex)

```yaml
plex:
  enabled: false
```

### Full Plex Integration

```yaml
plex:
  enabled: true
  base_url: "http://192.168.1.100:32400"
  token: "abc123def456ghi789"
  use_for_epg: true
```

### Plex Available but EPG Enhancement Disabled

```yaml
plex:
  enabled: true
  base_url: "http://192.168.1.100:32400"
  token: "abc123def456ghi789"
  use_for_epg: false  # Plex available but not used for EPG
```

## Testing

### Test EPG Generation

```bash
# Get EPG XML
curl http://localhost:8410/iptv/xmltv.xml > epg.xml

# Validate XML format
xmllint --noout epg.xml

# Check for Plex compatibility
grep -c "<channel" epg.xml  # Should match number of channels
grep -c "<programme" epg.xml  # Should have programme entries
```

### Test Plex API Connection

```python
from streamtv.streaming.plex_api_client import PlexAPIClient
import asyncio

async def test():
    async with PlexAPIClient("http://plex:32400", "token") as client:
        info = await client.get_server_info()
        print(f"Plex Server: {info}")

asyncio.run(test())
```

## References

- [Plex Media Server API Documentation](https://developer.plex.tv/pms/)
- [Plex EPG API Endpoints](https://developer.plex.tv/pms/#tag/EPG)
- [XMLTV Format Specification](https://github.com/XMLTV/xmltv)

## Migration Notes

### Existing Installations

- **No breaking changes** - Works without Plex configuration
- **Optional enhancement** - Add Plex config for better EPG
- **Backward compatible** - All existing EPG generation continues to work

### Upgrading

1. Add `plex` section to `config.yaml` (optional)
2. Configure Plex server URL and token if desired
3. Set `use_for_epg: true` to enable enhancements
4. Restart StreamTV

---

**Note**: Plex integration is optional. StreamTV generates Plex-compatible XMLTV format even without Plex API integration.

