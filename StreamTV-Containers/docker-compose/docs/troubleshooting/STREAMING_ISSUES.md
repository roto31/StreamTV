# Streaming Issues Troubleshooting Guide

Common issues with video streaming and playback in StreamTV.

## Channels Won't Play

### Symptoms
- Channel exists but shows "No stream available"
- Timeout errors when trying to play
- "Stream not found" message

### Solutions

1. **Verify channel is enabled:**
   - Check in web interface: http://localhost:8410/channels
   - Ensure channel has `enabled: true`
   - Disabled channels won't stream

2. **Check channel has content:**
   - Channel must have media items or schedule
   - Verify in web interface
   - Check schedule file exists if using schedules

3. **Verify schedule configuration:**
   - Check schedule file in `schedules/` directory
   - Ensure schedule is linked to channel
   - Validate schedule YAML syntax

4. **Test stream URL directly:**
   ```bash
   curl http://localhost:8410/api/channels/{channel_id}/stream
   ```
   Or use channel number:
   ```bash
   curl http://localhost:8410/hdhomerun/auto/v{channel_number}
   ```

5. **Check streaming logs:**
   - Access: http://localhost:8410/logs
   - Look for errors when accessing channel
   - Check FFmpeg errors

6. **Verify streaming mode:**
   - CONTINUOUS: Requires schedule file
   - ON_DEMAND: Can work with just media items
   - Check channel configuration

## Video Buffering or Stuttering

### Symptoms
- Video plays but buffers frequently
- Stuttering or choppy playback
- Long delays before playback starts

### Solutions

1. **Check network bandwidth:**
   - Test connection speed
   - Ensure sufficient bandwidth for streaming
   - Check for network congestion

2. **Reduce stream quality:**
   ```yaml
   youtube:
     quality: "medium"  # Instead of "best"
   ```
   Or in channel settings via web interface.

3. **Check FFmpeg performance:**
   - Monitor CPU usage during streaming
   - Check FFmpeg processes: `ps aux | grep ffmpeg`
   - Consider hardware acceleration if available

4. **Adjust buffer settings:**
   ```yaml
   streaming:
     buffer_size: 16384  # Increase buffer
     chunk_size: 2048    # Increase chunk size
   ```

5. **Check source video quality:**
   - Lower quality sources may buffer less
   - Check if source itself is slow
   - Try different media sources

6. **Monitor system resources:**
   - Check CPU usage
   - Check RAM usage
   - Check disk I/O
   - Close other resource-intensive applications

## FFmpeg Errors

### Symptoms
- FFmpeg crashes during streaming
- Format errors or codec issues
- "Error opening input" messages

### Solutions

1. **Update FFmpeg:**
   ```bash
   # macOS
   brew upgrade ffmpeg
   
   # Linux
   sudo apt-get update && sudo apt-get upgrade ffmpeg
   ```

2. **Check FFmpeg codec support:**
   ```bash
   ffmpeg -codecs | grep h264
   ffmpeg -codecs | grep aac
   ```

3. **Check FFmpeg logs:**
   - View streaming logs in web interface
   - Look for specific FFmpeg error messages
   - Check for codec or format errors

4. **Verify source format:**
   - Some formats may not be supported
   - Check source video codec
   - Try different source if available

5. **FFmpeg hardware acceleration:**
   - Enable if supported by your system
   - Check config for hardware acceleration options
   - May improve performance and compatibility

6. **Common FFmpeg errors:**
   - **"Error opening input"**: Source URL not accessible
   - **"Codec not found"**: Missing codec support
   - **"Invalid data"**: Corrupted source or format issue
   - **"Permission denied"**: File permission issue

## Stream Stops Unexpectedly

### Symptoms
- Stream plays then stops
- "Stream ended" message
- Connection drops

### Solutions

1. **Check for errors in logs:**
   - View streaming logs
   - Look for FFmpeg errors
   - Check for network errors

2. **Verify continuous streaming:**
   - Channel should stream continuously
   - Check schedule has enough content
   - Ensure no gaps in schedule

3. **Check FFmpeg process:**
   ```bash
   ps aux | grep ffmpeg
   ```
   Process should remain running during stream.

4. **Network stability:**
   - Check network connection
   - Test for packet loss
   - Verify firewall isn't blocking

5. **Increase timeouts:**
   ```yaml
   streaming:
     timeout: 60  # Increase timeout
     max_retries: 5  # Increase retries
   ```

6. **Check source availability:**
   - Verify source URLs are still valid
   - Check if source requires authentication
   - Test source URLs directly

## No Audio or Video

### Symptoms
- Video plays but no audio
- Audio but no video
- Black screen or no playback

### Solutions

1. **Check source has audio/video:**
   - Test source in browser or VLC
   - Verify source format is supported
   - Check source codec

2. **FFmpeg codec issues:**
   - Check FFmpeg supports required codecs
   - Update FFmpeg if needed
   - Check FFmpeg logs for codec errors

3. **Stream format:**
   - MPEG-TS format requires specific codecs
   - Verify FFmpeg can encode to MPEG-TS
   - Check streaming configuration

4. **Client compatibility:**
   - Test in different players (VLC, browser, Plex)
   - Some clients may not support format
   - Check client codec support

## Slow Stream Start

### Symptoms
- Long delay before playback starts
- "Loading" for extended time
- Timeout before stream starts

### Solutions

1. **Check source response time:**
   - Test source URL directly
   - Check if source is slow to respond
   - Verify network to source

2. **Reduce first chunk timeout:**
   - Already optimized in code (15 seconds)
   - Check if source needs more time
   - Verify source is accessible

3. **Check FFmpeg startup:**
   - FFmpeg may take time to initialize
   - Check FFmpeg logs for startup delays
   - Verify FFmpeg is working correctly

4. **Network latency:**
   - Check ping to source
   - Verify DNS resolution is fast
   - Check for network issues

## Format-Specific Issues

### AVI File Errors

**Symptoms:**
- "Error during demuxing" for AVI files
- AVI files won't play
- FFmpeg errors with AVI format

**Solutions:**
1. **Filter problematic formats:**
   - Use channel-specific filtering (e.g., MP4-only)
   - Skip AVI files in schedule
   - Use different source format if available

2. **Update FFmpeg:**
   - Newer FFmpeg versions handle AVI better
   - May resolve some demuxing issues

3. **Convert source:**
   - Convert AVI to MP4 if possible
   - Use different source format

### H.264/MP4 Issues

**Symptoms:**
- MP4 files won't play
- Codec errors with H.264
- Format not supported errors

**Solutions:**
1. **Verify codec support:**
   ```bash
   ffmpeg -codecs | grep h264
   ```

2. **Check file integrity:**
   - Verify MP4 file is not corrupted
   - Test file in other players
   - Try different MP4 file

3. **Update FFmpeg:**
   - Ensure latest FFmpeg version
   - H.264 support should be standard

## Debugging Streaming Issues

### Enable Debug Logging

```yaml
logging:
  level: "DEBUG"
  file: "streamtv.log"
```

### Test Stream Directly

1. **Test HDHomeRun endpoint:**
   ```bash
   curl http://localhost:8410/hdhomerun/auto/v1 > test.ts
   ```
   Then play `test.ts` in VLC.

2. **Test API endpoint:**
   ```bash
   curl http://localhost:8410/api/channels/1/stream > test.ts
   ```

3. **Monitor FFmpeg:**
   ```bash
   # Watch FFmpeg processes
   watch -n 1 'ps aux | grep ffmpeg'
   ```

### Check Streaming Logs

1. **Access logs:**
   - Web interface: http://localhost:8410/logs
   - Real-time monitoring available
   - Error detection and highlighting

2. **Look for patterns:**
   - Recurring errors
   - Specific time patterns
   - Source-specific issues

3. **Use self-heal:**
   - Click errors in logs
   - Use "Self-Heal" button
   - Automatic script matching

## Getting Help

If streaming issues persist:

1. **Collect information:**
   - Streaming logs
   - FFmpeg version
   - Source URLs
   - Channel configuration
   - Error messages

2. **Test components:**
   - Test source URLs directly
   - Verify FFmpeg works
   - Check network connectivity

3. **Check documentation:**
   - [Main Troubleshooting Guide](../TROUBLESHOOTING.md)
   - [Troubleshooting Scripts](TROUBLESHOOTING_SCRIPTS.md)
   - [Schedules Guide](../SCHEDULES.md)

See also:
- [FFmpeg Issues](FFMPEG_ISSUES.md)
- [Network Issues](NETWORK_ISSUES.md)
