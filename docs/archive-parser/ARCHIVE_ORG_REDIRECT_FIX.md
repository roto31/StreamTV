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
