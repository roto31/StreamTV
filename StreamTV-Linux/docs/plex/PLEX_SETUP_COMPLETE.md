# Plex API Integration - Setup Complete! ✅

## Current Status

Your Plex API integration has been configured with:

✅ **Enabled**: `true`  
✅ **Base URL**: `http://localhost:32400` (detected automatically)  
✅ **EPG Enhancement**: `true`  
⏳ **Token**: Needs to be configured (see below)

## Next Step: Get Your Plex Token

To complete the setup, you need to add your Plex authentication token.

### Quick Method

Run this helper script:
```bash
python3 scripts/get_plex_token.py
```

This will:
- Open your Plex Web App in a browser
- Show detailed instructions
- Guide you through extracting the token

### Manual Method

1. **Open Plex Web App**:
   - http://localhost:32400/web
   - OR https://app.plex.tv/desktop

2. **Open Browser Developer Tools**:
   - macOS: `Cmd + Option + I`
   - Windows/Linux: `F12`

3. **Go to Network Tab**

4. **Refresh the page**

5. **Find a request** and check:
   - Request Headers
   - Look for `X-Plex-Token` parameter
   - Copy the token value

### Alternative: Browser Console

1. Open Developer Tools → Console tab
2. Type: `window.localStorage.getItem('token')`
3. Press Enter
4. Copy the returned value

## Update Configuration

Once you have your token, update `config.yaml`:

```yaml
plex:
  enabled: true
  base_url: "http://localhost:32400"
  token: "YOUR_TOKEN_HERE"  # Paste your token here
  use_for_epg: true
```

## Restart StreamTV

After adding your token, restart the StreamTV server:

```bash
# Stop current server (Ctrl+C)
# Then restart:
./start_server.sh
```

## Verify Integration

Once configured, you can verify the integration:

```bash
# Check if Plex server is accessible
curl http://localhost:32400/

# Test EPG generation
curl http://localhost:8410/iptv/xmltv.xml | head -20
```

## What You Get

With full Plex API integration enabled:

✅ **Enhanced EPG Generation** - Uses Plex-compatible format  
✅ **Channel Mapping** - Better channel identification  
✅ **Metadata Enrichment** - Enhanced programme information  
✅ **DVR Compatibility** - Full compatibility with Plex DVR  
✅ **Performance Optimized** - Faster EPG generation  

## Current Configuration

Your current `config.yaml` shows:

```yaml
plex:
  enabled: true
  base_url: "http://localhost:32400"
  token: null  # ← Add your token here
  use_for_epg: true
```

## Troubleshooting

### Plex Server Not Found

If your Plex server is on a different IP:
1. Find your Plex server IP address
2. Update `base_url` in `config.yaml`
3. Example: `"http://192.168.1.100:32400"`

### Token Not Working

- Make sure you copied the full token (it's a long string)
- Token should not have spaces
- Check if token has expired (get a new one)

### EPG Not Loading in Plex

- Verify XMLTV is accessible: `http://localhost:8410/iptv/xmltv.xml`
- Check Plex server can reach StreamTV
- Verify channel numbers match

## Need Help?

- Check logs: `tail -f streamtv.log`
- Run diagnostics: `python3 scripts/discover_plex.py`
- See full documentation: `PLEX_EPG_INTEGRATION.md`

---

**Status**: ✅ Configuration complete, token pending  
**Next**: Get your Plex token and add it to `config.yaml`

