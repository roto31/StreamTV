# Plex Integration Troubleshooting Guide

Common issues when integrating StreamTV with Plex Media Server.

## Plex Can't Find Tuner

### Symptoms
- Plex shows "No tuners found"
- Discovery URL doesn't work
- HDHomeRun device not appearing in Plex

### Solutions

1. **Verify StreamTV is running:**
   ```bash
   curl http://localhost:8410/hdhomerun/discover.json
   ```
   Should return JSON with device information.

2. **Check discovery URL:**
   - Use your server's IP address, not `localhost`
   - Format: `http://YOUR_IP:8410/hdhomerun/discover.json`
   - Example: `http://192.168.1.100:8410/hdhomerun/discover.json`

3. **Verify SSDP is enabled:**
   ```yaml
   hdhomerun:
     enabled: true
     enable_ssdp: true  # Must be true for auto-discovery
   ```

4. **Check firewall:**
   - Port 8410 must be accessible
   - Port 1900 (SSDP) must be open if using auto-discovery
   - Test: `telnet YOUR_IP 8410`

5. **Manual tuner addition:**
   - Plex → Settings → Live TV & DVR
   - Add Tuner → Manual
   - Enter: `http://YOUR_IP:8410/hdhomerun/discover.json`

## Channels Not Appearing in Plex

### Symptoms
- Tuner found but no channels listed
- Channel scan shows 0 channels
- Channels exist in StreamTV but not in Plex

### Solutions

1. **Verify channels exist:**
   ```bash
   curl http://localhost:8410/api/channels
   ```
   Should return list of channels.

2. **Check channel lineup:**
   ```bash
   curl http://localhost:8410/hdhomerun/lineup.json
   ```
   Should return channel lineup.

3. **Rescan channels in Plex:**
   - Plex → Settings → Live TV & DVR
   - Click "Refresh Guide" or "Scan for Channels"
   - Wait for scan to complete

4. **Verify channel numbers:**
   - Channels must have valid numbers (e.g., "1", "2", "80")
   - Check in StreamTV web interface: http://localhost:8410/channels

5. **Check channel enablement:**
   - Ensure channels are enabled in StreamTV
   - Disabled channels won't appear in Plex

## "Error Tuning Channel" in Plex

### Symptoms
- Plex shows "Error tuning channel" for all channels
- Channels appear but won't play
- Stream connection fails

### Solutions

1. **Check stream URL:**
   ```bash
   curl http://localhost:8410/hdhomerun/auto/v1
   ```
   Should return MPEG-TS stream data.

2. **Verify FFmpeg is working:**
   - Check FFmpeg installation: `ffmpeg -version`
   - View streaming logs for FFmpeg errors
   - Run diagnostic: `check_ffmpeg` script

3. **Check network connectivity:**
   - Ensure Plex can reach StreamTV server
   - Test from Plex server: `curl http://STREAMTV_IP:8410/health`
   - Check firewall rules

4. **Verify channel has content:**
   - Channel must have media items or schedule
   - Check in StreamTV: http://localhost:8410/channels/{channel_id}

5. **Check streaming mode:**
   - Verify channel is configured correctly
   - Test stream directly in browser or VLC

6. **View Plex logs:**
   - Access Plex logs via StreamTV: http://localhost:8410/plex-logs
   - Look for specific error messages
   - Check for timeout or connection errors

## Guide (EPG) Not Loading

### Symptoms
- Channels appear but no guide data
- "No guide data available"
- EPG shows "No information"

### Solutions

1. **Verify XMLTV URL:**
   - Format: `http://YOUR_IP:8410/iptv/xmltv.xml`
   - Test in browser: Should download XML file
   - Check XML is valid: Open in text editor

2. **Add guide in Plex:**
   - Plex → Settings → Live TV & DVR
   - Add Guide → XMLTV
   - Enter: `http://YOUR_IP:8410/iptv/xmltv.xml`

3. **Check XMLTV generation:**
   ```bash
   curl http://localhost:8410/iptv/xmltv.xml | head -20
   ```
   Should show valid XML with channel and program data.

4. **Verify channels have schedules:**
   - Channels need schedule files or media items for EPG
   - Check schedule files in `schedules/` directory
   - Verify channel has associated schedule

5. **Refresh guide in Plex:**
   - Plex → Settings → Live TV & DVR
   - Click "Refresh Guide"
   - Wait several minutes for guide to populate

## Stream Stops or Disconnects

### Symptoms
- Stream plays for a while then stops
- "Stream ended unexpectedly"
- Frequent disconnections

### Solutions

1. **Check streaming logs:**
   - Access: http://localhost:8410/logs
   - Look for FFmpeg errors or timeouts
   - Check for network errors

2. **Verify continuous streaming:**
   - Channel should stream continuously
   - Check channel mode (CONTINUOUS vs ON_DEMAND)
   - Ensure schedule has enough content

3. **Check FFmpeg process:**
   - Monitor FFmpeg processes: `ps aux | grep ffmpeg`
   - Check for crashes or hangs
   - Restart server if needed

4. **Network stability:**
   - Check network connection quality
   - Test bandwidth: `speedtest-cli`
   - Check for packet loss

5. **Increase timeouts:**
   ```yaml
   streaming:
     timeout: 60  # Increase from default 30
   ```

## Channel Mapping Issues

### Symptoms
- Wrong channel numbers in Plex
- Channels don't match between StreamTV and Plex
- Guide data doesn't match channels

### Solutions

1. **Verify channel numbers:**
   - Check StreamTV channel numbers
   - Ensure they match what Plex expects
   - Use consistent numbering scheme

2. **Remap channels in Plex:**
   - Plex → Settings → Live TV & DVR
   - Edit channel mappings
   - Match StreamTV channel numbers

3. **Check XMLTV channel IDs:**
   - XMLTV uses channel numbers as IDs
   - Verify channel numbers in XMLTV match StreamTV
   - Regenerate XMLTV if needed

## Plex Logs Access

### Viewing Plex Logs via StreamTV

1. **Access Plex logs page:**
   - Navigate to: http://localhost:8410/plex-logs
   - Select log file from dropdown
   - View recent entries

2. **Common Plex errors to look for:**
   - "Could not tune channel" → Stream format issue
   - "Problem fetching channel mappings" → XMLTV issue
   - "Tuner not found" → Discovery/SSDP issue
   - "Timeout" → Network or stream speed issue

3. **Filter logs:**
   - Use search to find specific errors
   - Filter by date/time
   - Look for patterns

## Advanced Troubleshooting

### Test HDHomeRun Endpoints

1. **Discovery:**
   ```bash
   curl http://localhost:8410/hdhomerun/discover.json
   ```

2. **Lineup:**
   ```bash
   curl http://localhost:8410/hdhomerun/lineup.json
   ```

3. **Stream:**
   ```bash
   curl http://localhost:8410/hdhomerun/auto/v1
   ```

4. **Device XML:**
   ```bash
   curl http://localhost:8410/hdhomerun/device.xml
   ```

### Verify Network Configuration

1. **Check IP address:**
   ```bash
   # macOS/Linux
   ifconfig | grep "inet "
   
   # Windows
   ipconfig
   ```

2. **Test connectivity from Plex server:**
   ```bash
   curl http://STREAMTV_IP:8410/health
   ```

3. **Check firewall:**
   - Ensure port 8410 is open
   - Test with: `telnet STREAMTV_IP 8410`

### Reset Plex Integration

If all else fails:

1. **Remove tuner from Plex:**
   - Plex → Settings → Live TV & DVR
   - Remove existing tuner

2. **Restart StreamTV:**
   ```bash
   # Stop server
   pkill -f streamtv.main
   
   # Start server
   ./start_server.sh
   ```

3. **Re-add tuner in Plex:**
   - Add tuner with discovery URL
   - Scan for channels
   - Add guide URL

## Getting Help

If Plex integration issues persist:

1. **Collect information:**
   - StreamTV logs (from web interface)
   - Plex logs (from StreamTV Plex logs page)
   - Network configuration
   - Channel configuration

2. **Test components:**
   - Verify StreamTV works standalone
   - Test HDHomeRun endpoints directly
   - Verify network connectivity

3. **Check documentation:**
   - [HDHomeRun Integration Guide](../HDHOMERUN.md)
   - [Plex Setup Guide](../plex/PLEX_SETUP_COMPLETE.md)
   - [Main Troubleshooting Guide](../TROUBLESHOOTING.md)

See also:
- [Troubleshooting Scripts](TROUBLESHOOTING_SCRIPTS.md)
- [Plex Integration Documentation](../plex/)
