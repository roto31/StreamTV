# Plex Channel Scan Not Showing New Channels - Fix

## Issue

After adding a new channel (e.g., Channel 80 - Magnum P.I.), rescanning with Plex tuner doesn't show the new channel.

## Root Cause

**Plex caches the HDHomeRun channel lineup** and doesn't always refresh it properly during a rescan.

---

## ✅ Verified Working

Channel 80 **IS** in the HDHomeRun lineup:

```json
{
    "GuideNumber": "80",
    "GuideName": "Magnum P.I. Complete Series",
    "URL": "http://localhost:8410/hdhomerun/auto/v80",
    "HD": 0
}
```

The channel is properly configured and exposed. Plex just needs to refresh its cache.

---

## Solution: Force Plex to Refresh

### Method 1: Remove and Re-add the DVR Source (Recommended)

This forces Plex to completely refresh the lineup:

1. **Open Plex Web Interface** (http://100.70.119.112:32400/web)

2. **Go to Settings** → **Live TV & DVR**

3. **Find your StreamTV HDHomeRun device**

4. **Click the "..." menu** → **Remove Device**

5. **Wait 10 seconds**

6. **Click "Add DVR Source"** → **Select Network Device**

7. **Plex should auto-discover**: `StreamTV HDHomeRun (FFFFFFFF)`

8. **Click Continue** and follow the setup

9. **All 6 channels should now appear** (1980, 1984, 1988, 1992, 1994, **80**)

### Method 2: Restart Plex Media Server

Sometimes Plex needs a restart to refresh the lineup:

```bash
# On your Plex server machine
sudo systemctl restart plexmediaserver

# OR if using macOS
# Quit Plex from menu bar, then restart
```

### Method 3: Clear Plex Cache (Advanced)

If the above don't work, clear Plex's DVR cache:

1. **Stop Plex Media Server**

2. **Navigate to Plex data directory**:
   - **macOS**: `~/Library/Application Support/Plex Media Server/`
   - **Linux**: `/var/lib/plexmediaserver/Library/Application Support/Plex Media Server/`
   - **Windows**: `%LOCALAPPDATA%\Plex Media Server\`

3. **Delete DVR cache**:
   ```bash
   # macOS example
   rm -rf "~/Library/Application Support/Plex Media Server/Cache/DVR"
   ```

4. **Restart Plex**

5. **Re-add the DVR source**

### Method 4: Manual Refresh Endpoint (If Available)

Some Plex versions support forcing a lineup refresh:

```bash
# Replace YOUR_PLEX_TOKEN with your actual token
curl -X POST "http://100.70.119.112:32400/livetv/dvrs/refresh?X-Plex-Token=YOUR_TOKEN"
```

---

## Verification Steps

### 1. Verify StreamTV is Exposing the Channel

```bash
# Check lineup
curl http://localhost:8410/lineup.json | python3 -m json.tool | grep -A 3 "\"80\""

# Should show:
# "GuideNumber": "80",
# "GuideName": "Magnum P.I. Complete Series",
```

### 2. Verify Plex Can Reach StreamTV

```bash
# From your Plex server, test connectivity
curl http://localhost:8410/discover.json

# Should return HDHomeRun device info
```

### 3. Check Plex Sees the Device

In Plex Settings → Live TV & DVR:
- Device should show: **StreamTV HDHomeRun**
- Tuner Count: **4**
- Status: **Active**

---

## Common Issues

### Issue: "No channels found"

**Cause**: Plex can't reach StreamTV  
**Fix**: 
- Ensure StreamTV server is running: `./start_server.sh`
- Check firewall isn't blocking port 8410
- Verify Plex and StreamTV are on same network

### Issue: "Only old channels showing"

**Cause**: Plex cached lineup  
**Fix**: Remove and re-add DVR source (Method 1 above)

### Issue: "Channel shows but won't play"

**Cause**: Stream URL not working  
**Fix**: 
- Test stream directly: `curl -I http://localhost:8410/iptv/stream/80`
- Check logs: `./scripts/view-logs.sh search "channel 80"`
- Verify FFmpeg is working (should be fixed now with hwaccel disabled)

---

## Why This Happens

### Plex DVR Caching

Plex caches the HDHomeRun lineup for performance:
- **Initial scan**: Gets full lineup
- **Rescan**: Only checks for channel changes
- **Cache duration**: Can persist for hours/days

### When to Re-add Source

Re-add the DVR source when:
- ✅ Adding new channels
- ✅ Removing channels
- ✅ Changing channel numbers
- ✅ After major StreamTV updates

### When Rescan Works

Normal rescan works for:
- Channel metadata changes (name, description)
- EPG updates
- Stream URL changes

---

## Step-by-Step: Complete Refresh

1. **Verify channel in lineup**:
   ```bash
   curl http://localhost:8410/lineup.json | grep "\"80\""
   ```
   ✅ Should show Channel 80

2. **Open Plex** → Settings → Live TV & DVR

3. **Remove StreamTV device**

4. **Wait 10 seconds** (important!)

5. **Click "Setup Plex DVR"**

6. **Select "Network Device"**

7. **Plex discovers**: StreamTV HDHomeRun (FFFFFFFF)

8. **Continue through setup**

9. **Channel selection**: All 6 channels should appear
   - Select Channel 80: Magnum P.I. Complete Series ✅
   - Select other channels as desired

10. **Complete setup**

11. **Go to Live TV** → Channel 80 should be there! 🎉

---

## Verification

After re-adding the DVR source:

### Check in Plex Web
```
Settings → Live TV & DVR → Guide
```

Should show:
- Channel 1980
- Channel 1984
- Channel 1988
- Channel 1992
- Channel 1994
- **Channel 80** ⭐ (NEW!)

### Check in Plex Apps
- Open Plex app
- Navigate to Live TV
- Channel 80 should appear in the guide

### Test Streaming
- Click on Channel 80
- Should start playing Magnum P.I. episodes
- With 2-5 minute breaks between episodes

---

## Alternative: XMLTV EPG Method

If HDHomeRun method doesn't work, use direct M3U/XMLTV:

### 1. In Plex Settings
- Settings → Live TV & DVR
- Add a new source
- Select "Use M3U playlist"

### 2. Enter URLs
- **M3U Playlist**: `http://localhost:8410/iptv/channels.m3u`
- **XMLTV Guide**: `http://localhost:8410/iptv/xmltv.xml`

### 3. Configure
- Refresh Guide Data: Every 4 hours
- Match channels automatically

This bypasses HDHomeRun emulation entirely.

---

## Expected Behavior After Fix

✅ Channel 80 appears in Plex channel list  
✅ EPG shows "Magnum P.I. Complete Series"  
✅ Clicking channel starts streaming  
✅ Episodes play with breaks  
✅ Guide shows episode information

---

## Still Not Working?

### Check StreamTV Logs
```bash
./scripts/view-logs.sh search "lineup\|channel 80"
```

### Check Plex Logs
Look for HDHomeRun device scan logs in Plex.

### Verify Channel Stream
```bash
# Test stream directly
curl -I http://localhost:8410/iptv/stream/80
vlc http://localhost:8410/iptv/stream/80
```

### Check Network
```bash
# From Plex server, verify it can reach StreamTV
curl http://localhost:8410/discover.json
```

---

## Summary

**Problem**: Plex not showing new Channel 80  
**Cause**: Plex cached old lineup  
**Fix**: Remove and re-add DVR source in Plex  
**Status**: Channel 80 is properly configured and exposed  

**Action**: Re-add the DVR source in Plex to see Channel 80!

---

**Date**: December 3, 2025  
**Issue**: Plex lineup cache  
**Solution**: Remove and re-add StreamTV HDHomeRun device

