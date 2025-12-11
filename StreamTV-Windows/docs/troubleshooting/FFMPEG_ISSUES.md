# FFmpeg Troubleshooting Guide

Common FFmpeg-related issues and their solutions.

## FFmpeg Not Found

### Symptoms
- `ffmpeg: command not found`
- FFmpeg errors in logs
- Streaming fails immediately

### Solutions

1. **Verify FFmpeg installation:**
   ```bash
   which ffmpeg
   ffmpeg -version
   ```

2. **Install FFmpeg:**
   - See [Installation Issues](INSTALLATION_ISSUES.md) for platform-specific instructions
   - Run diagnostic: `check_ffmpeg` script

3. **Configure FFmpeg path:**
   ```yaml
   ffmpeg:
     ffmpeg_path: "/usr/local/bin/ffmpeg"  # Custom path if needed
   ```

## FFmpeg Codec Errors

### Symptoms
- "Codec not found" errors
- "Unsupported codec" messages
- Format not supported errors

### Solutions

1. **Check codec support:**
   ```bash
   ffmpeg -codecs | grep h264
   ffmpeg -codecs | grep aac
   ffmpeg -codecs | grep mp2
   ```

2. **Update FFmpeg:**
   - Newer versions have better codec support
   - Install latest version for your platform

3. **Verify required codecs:**
   - H.264 (video) - Required
   - AAC or MP2 (audio) - Required
   - MPEG-2 (for HDHomeRun output) - Required

4. **Check build configuration:**
   ```bash
   ffmpeg -buildconf
   ```
   Look for required codecs in configuration.

## FFmpeg Format Errors

### Symptoms
- "Error opening input" for specific formats
- "Invalid data found" errors
- Format not recognized

### Solutions

1. **Check format support:**
   ```bash
   ffmpeg -formats | grep mp4
   ffmpeg -formats | grep avi
   ```

2. **Test source file:**
   ```bash
   ffmpeg -i source_url -t 1 -f null -
   ```
   This tests if FFmpeg can read the source.

3. **Update FFmpeg:**
   - Format support improves with updates
   - Install latest version

4. **Use different source:**
   - If format not supported, use alternative
   - Convert source to supported format
   - Filter unsupported formats in channel config

## FFmpeg Demuxing Errors

### Symptoms
- "Error during demuxing: Input/output error"
- AVI files fail to demux
- Demuxing timeout errors

### Solutions

1. **Common with AVI files:**
   - AVI format can be problematic
   - Use channel filtering to skip AVI files
   - Example: Filter to MP4-only for specific channels

2. **Increase timeout:**
   - Some files need more time to start
   - Already optimized in code (15 seconds)
   - Check if source is slow to respond

3. **Check source integrity:**
   - Verify source file is not corrupted
   - Test source in other players
   - Try different source if available

4. **Update FFmpeg:**
   - Newer versions handle demuxing better
   - May resolve some AVI issues

## FFmpeg Hardware Acceleration

### Symptoms
- High CPU usage during streaming
- Slow transcoding
- Performance issues

### Solutions

1. **Check hardware acceleration support:**
   ```bash
   ffmpeg -hwaccels
   ```

2. **Enable hardware acceleration:**
   - Configure in `config.yaml` if supported
   - Check FFmpeg build includes hardware acceleration
   - Platform-specific (VideoToolbox on macOS, VAAPI on Linux)

3. **Verify acceleration works:**
   - Monitor CPU usage
   - Check FFmpeg logs for acceleration messages
   - May fall back to software if hardware fails

4. **Common acceleration options:**
   - **macOS**: `-hwaccel videotoolbox`
   - **Linux**: `-hwaccel vaapi` or `-hwaccel vdpau`
   - **Windows**: `-hwaccel d3d11va` or `-hwaccel dxva2`

## FFmpeg Process Management

### Symptoms
- FFmpeg processes not terminating
- Multiple FFmpeg processes running
- Process leaks

### Solutions

1. **Check running processes:**
   ```bash
   ps aux | grep ffmpeg
   ```

2. **Kill stuck processes:**
   ```bash
   pkill -f ffmpeg
   # OR
   killall ffmpeg
   ```

3. **Restart server:**
   - Proper shutdown should clean up processes
   - Restart if processes are stuck
   - Check shutdown handling in logs

4. **Monitor process lifecycle:**
   - Check logs for process creation/termination
   - Verify cleanup on channel stop
   - Check for process leaks

## FFmpeg Performance Issues

### Symptoms
- Slow transcoding
- High CPU usage
- Buffering during streaming

### Solutions

1. **Optimize FFmpeg settings:**
   - Adjust quality settings
   - Use hardware acceleration if available
   - Reduce output quality if needed

2. **Check system resources:**
   - Monitor CPU usage
   - Check RAM availability
   - Verify disk I/O not bottleneck

3. **Reduce concurrent streams:**
   - Limit number of simultaneous streams
   - Each stream uses resources
   - Balance quality vs. quantity

4. **Optimize source quality:**
   - Use lower quality sources if needed
   - Reduce transcoding workload
   - Match source to output quality

## FFmpeg Error Messages

### Common Error Patterns

**"Error opening input: Input/output error"**
- Source URL not accessible
- Network issue
- Source server down
- **Solution**: Check source URL, network connectivity

**"Error during demuxing: Input/output error"**
- File format issue (common with AVI)
- Corrupted source
- Unsupported format
- **Solution**: Filter format, use different source

**"Codec not found"**
- Missing codec support
- FFmpeg build issue
- **Solution**: Update FFmpeg, check codec support

**"Invalid data found"**
- Corrupted source
- Format issue
- **Solution**: Test source, try different source

**"Permission denied"**
- File permission issue
- **Solution**: Check file permissions, access rights

## Debugging FFmpeg Issues

### Enable Verbose Logging

FFmpeg errors are logged in streaming logs. Access via:
- Web interface: http://localhost:8410/logs
- Look for FFmpeg error messages
- Check error context

### Test FFmpeg Directly

1. **Test basic functionality:**
   ```bash
   ffmpeg -version
   ```

2. **Test codec support:**
   ```bash
   ffmpeg -codecs
   ```

3. **Test format support:**
   ```bash
   ffmpeg -formats
   ```

4. **Test source access:**
   ```bash
   ffmpeg -i SOURCE_URL -t 1 -f null -
   ```

### Monitor FFmpeg Processes

```bash
# Watch FFmpeg processes
watch -n 1 'ps aux | grep ffmpeg'

# Check FFmpeg resource usage
top -p $(pgrep ffmpeg)
```

## Getting Help

If FFmpeg issues persist:

1. **Collect information:**
   - FFmpeg version: `ffmpeg -version`
   - Error messages from logs
   - Source URLs causing issues
   - System information

2. **Test FFmpeg:**
   - Verify basic functionality
   - Test with known-good sources
   - Check codec/format support

3. **Check documentation:**
   - [Main Troubleshooting Guide](../TROUBLESHOOTING.md)
   - [Streaming Issues](STREAMING_ISSUES.md)
   - [Installation Issues](INSTALLATION_ISSUES.md)

See also:
- [Troubleshooting Scripts](TROUBLESHOOTING_SCRIPTS.md)
- FFmpeg official documentation: https://ffmpeg.org/documentation.html
