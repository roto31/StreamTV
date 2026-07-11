# Network & Connectivity Troubleshooting Guide

Common network and connectivity issues in StreamTV.

## DNS Resolution Errors

### Symptoms
- `[Errno 8] nodename nor servname provided, or not known`
- `Unable to resolve hostname`
- YouTube/Archive.org URLs fail to resolve

### Solutions

1. **Run connectivity diagnostic:**
   - Use web interface: Run `test_connectivity` script
   - Automatically detects DNS issues
   - Provides auto-fix options

2. **Flush DNS cache:**
   
   **macOS:**
   ```bash
   sudo dscacheutil -flushcache
   sudo killall -HUP mDNSResponder
   ```
   
   **Linux:**
   ```bash
   sudo systemd-resolve --flush-caches  # systemd
   # OR
   sudo service network-manager restart  # NetworkManager
   ```
   
   **Windows:**
   ```powershell
   ipconfig /flushdns
   ```

3. **Check DNS servers:**
   - Verify DNS server settings
   - Try using Google DNS (8.8.8.8, 8.8.4.4)
   - Test DNS resolution: `nslookup youtube.com`

4. **Test connectivity:**
   ```bash
   ping youtube.com
   ping archive.org
   curl https://www.google.com
   ```

5. **Auto-fix via web interface:**
   - Run `test_connectivity` script
   - If DNS issues detected, auto-fix option appears
   - Click to apply DNS cache flush (requires password)

## YouTube Streaming Issues

### Symptoms
- `yt-dlp not installed` errors
- `Unable to download API page`
- YouTube videos won't play
- Connection timeouts

### Solutions

1. **Install/update yt-dlp:**
   ```bash
   pip install yt-dlp
   # OR update
   pip install --upgrade yt-dlp
   ```
   Auto-fix available via web interface if detected.

2. **Check YouTube accessibility:**
   - Test in browser: https://www.youtube.com
   - Verify YouTube is accessible
   - Check for regional restrictions

3. **Test connectivity:**
   - Run `test_connectivity` script
   - Checks YouTube DNS resolution
   - Tests port 443 accessibility

4. **Check firewall:**
   - Ensure outbound HTTPS (443) is allowed
   - Check for proxy settings
   - Verify no blocking of YouTube domains

5. **Update yt-dlp:**
   - YouTube changes frequently
   - Keep yt-dlp updated
   - Auto-update option in web interface

6. **Check authentication:**
   - YouTube may require authentication
   - Configure in StreamTV settings
   - Add cookies file if needed

## Archive.org Streaming Issues

### Symptoms
- Archive.org videos won't load
- Timeout errors
- "Item not found" errors

### Solutions

1. **Test connectivity:**
   ```bash
   curl https://archive.org
   ping archive.org
   ```

2. **Verify item identifier:**
   - Check Archive.org URL is correct
   - Ensure item exists and is accessible
   - Test URL in browser

3. **Check authentication:**
   - Some items require authentication
   - Configure Archive.org credentials in settings
   - Use web interface to set up authentication

4. **Check item format:**
   - Verify item has video files
   - Check preferred format in config
   - Some items may not have compatible formats

5. **Network connectivity:**
   - Run `test_connectivity` script
   - Check Archive.org DNS resolution
   - Verify HTTPS connectivity

## Network Timeout Issues

### Symptoms
- Connection timeouts
- "Request timed out" errors
- Slow response times

### Solutions

1. **Increase timeout settings:**
   ```yaml
   streaming:
     timeout: 60  # Increase from default 30
   ```

2. **Check network latency:**
   ```bash
   ping -c 10 youtube.com
   ping -c 10 archive.org
   ```
   High latency may cause timeouts.

3. **Test source response time:**
   ```bash
   time curl -I SOURCE_URL
   ```
   Slow sources may need longer timeouts.

4. **Check for network congestion:**
   - Monitor network usage
   - Check for bandwidth limits
   - Test at different times

5. **Verify firewall rules:**
   - Ensure outbound connections allowed
   - Check for rate limiting
   - Verify no proxy interference

## Port Access Issues

### Symptoms
- Can't access web interface
- Port 8410 not accessible
- Connection refused errors

### Solutions

1. **Check server is running:**
   ```bash
   ps aux | grep streamtv
   curl http://localhost:8410/health
   ```

2. **Verify port is listening:**
   ```bash
   # macOS/Linux
   lsof -i :8410
   netstat -an | grep 8410
   
   # Windows
   netstat -ano | findstr :8410
   ```

3. **Check firewall:**
   - Ensure port 8410 is open
   - Check inbound firewall rules
   - Test from different network

4. **Test local access:**
   ```bash
   curl http://localhost:8410/health
   ```
   If this works, issue is network/firewall.

5. **Check config:**
   ```yaml
   server:
     host: "0.0.0.0"  # Should be 0.0.0.0 for network access
     port: 8410
   ```

## SSDP/Discovery Issues

### Symptoms
- Plex can't discover tuner
- SSDP not working
- Auto-discovery fails

### Solutions

1. **Verify SSDP is enabled:**
   ```yaml
   hdhomerun:
     enable_ssdp: true
   ```

2. **Check port 1900:**
   - SSDP uses UDP port 1900
   - Ensure port is not blocked
   - Check firewall allows UDP 1900

3. **Test discovery manually:**
   ```bash
   curl http://localhost:8410/hdhomerun/discover.json
   ```
   Should return device information.

4. **Network requirements:**
   - SSDP requires multicast
   - Some networks block multicast
   - May need to use manual discovery URL

5. **Use manual discovery:**
   - If SSDP doesn't work, use manual URL
   - Format: `http://YOUR_IP:8410/hdhomerun/discover.json`
   - Works without SSDP

## Proxy/VPN Issues

### Symptoms
- Connections fail through proxy
- VPN causes issues
- Network routing problems

### Solutions

1. **Check proxy settings:**
   - Verify proxy configuration if used
   - Test direct connection without proxy
   - Check proxy allows required domains

2. **VPN considerations:**
   - VPN may route traffic differently
   - Check VPN allows local network access
   - Verify routing for StreamTV server

3. **Test without proxy/VPN:**
   - Temporarily disable to test
   - If works without, configure proxy properly
   - Check proxy authentication if needed

## Network Performance

### Symptoms
- Slow streaming
- High latency
- Bandwidth issues

### Solutions

1. **Test bandwidth:**
   ```bash
   # Install speedtest-cli
   pip install speedtest-cli
   speedtest-cli
   ```

2. **Monitor network usage:**
   ```bash
   # macOS
   netstat -i
   
   # Linux
   iftop
   ```

3. **Optimize stream quality:**
   - Reduce quality settings
   - Lower bitrate
   - Adjust buffer sizes

4. **Check for network congestion:**
   - Monitor at different times
   - Check for bandwidth limits
   - Verify no other heavy usage

## Getting Help

If network issues persist:

1. **Collect information:**
   - DNS server settings
   - Network configuration
   - Firewall rules
   - Error messages

2. **Run diagnostics:**
   - Use `test_connectivity` script
   - Check all connectivity tests
   - Review diagnostic output

3. **Test components:**
   - Test DNS resolution
   - Test HTTP/HTTPS connectivity
   - Test specific source URLs

4. **Check documentation:**
   - [Main Troubleshooting Guide](../TROUBLESHOOTING.md)
   - [Troubleshooting Scripts](TROUBLESHOOTING_SCRIPTS.md)
   - [Installation Issues](INSTALLATION_ISSUES.md)

See also:
- [Streaming Issues](STREAMING_ISSUES.md)
- [Plex Integration Issues](PLEX_INTEGRATION_ISSUES.md)
