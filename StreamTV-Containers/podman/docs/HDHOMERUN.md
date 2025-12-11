# HDHomeRun Tuner Emulation

StreamTV can emulate an HDHomeRun network tuner, allowing direct integration with Plex, Emby, and Jellyfin without requiring M3U playlists.

## Features

- **SSDP Discovery**: Automatically discoverable by media servers
- **HDHomeRun API**: Full compatibility with HDHomeRun API endpoints
- **Multiple Tuners**: Configurable number of virtual tuners (default: 2)
- **Automatic Channel Mapping**: Channels are automatically exposed to media servers

## Configuration

Add the following to your `config.yaml`:

```yaml
hdhomerun:
  enabled: true
  device_id: "FFFFFFFF"  # Unique device ID (hex)
  friendly_name: "StreamTV HDHomeRun"
  tuner_count: 2  # Number of virtual tuners
```

## API Endpoints

The HDHomeRun emulation exposes the following endpoints:

- `GET /hdhomerun/discover.json` - Device discovery
- `GET /hdhomerun/lineup.json` - Channel lineup
- `GET /hdhomerun/lineup_status.json` - Lineup status
- `GET /hdhomerun/status.json` - Device status
- `GET /hdhomerun/device.xml` - UPnP device description
- `GET /hdhomerun/auto/v{channel_number}` - Stream a channel
- `GET /hdhomerun/tuner{n}/stream?channel=auto:v{channel_number}` - Tuner stream

## Integration with Plex

1. **Start StreamTV** with HDHomeRun emulation enabled
2. **Open Plex** → Settings → Live TV & DVR
3. **Click "Set Up Plex DVR"**
4. Plex should automatically discover the HDHomeRun device
5. If not auto-discovered, manually add: `http://YOUR_SERVER_IP:8410/hdhomerun/discover.json`
6. **Configure channels** - Plex will fetch the lineup automatically
7. **Start watching** - Your StreamTV channels will appear in Plex Live TV

### Manual Discovery (if needed)

If Plex doesn't auto-discover the device:

1. Go to Settings → Live TV & DVR → DVR
2. Click "Add Device"
3. Enter: `http://YOUR_SERVER_IP:8410/hdhomerun/discover.json`
4. Plex will connect and fetch channels

## Integration with Emby

1. **Start StreamTV** with HDHomeRun emulation enabled
2. **Open Emby** → Dashboard → Live TV
3. **Click "Set Up Live TV"**
4. **Select "HDHomeRun"** as the tuner type
5. Emby should auto-discover the device
6. If not, manually enter: `http://YOUR_SERVER_IP:8410/hdhomerun/discover.json`
7. **Configure EPG** - Use the XMLTV endpoint: `http://YOUR_SERVER_IP:8410/iptv/xmltv.xml`
8. **Save** and start watching

### Manual Setup

1. Dashboard → Live TV → Tuners
2. Click "Add Tuner"
3. Select "HDHomeRun"
4. Enter device URL: `http://YOUR_SERVER_IP:8410/hdhomerun/discover.json`
5. Configure EPG source: `http://YOUR_SERVER_IP:8410/iptv/xmltv.xml`

## Integration with Jellyfin

1. **Start StreamTV** with HDHomeRun emulation enabled
2. **Open Jellyfin** → Dashboard → Live TV
3. **Click "Add Tuner"**
4. **Select "HDHomeRun"**
5. Jellyfin should auto-discover the device
6. If not, manually enter: `http://YOUR_SERVER_IP:8410/hdhomerun/discover.json`
7. **Configure EPG** - Add XMLTV source: `http://YOUR_SERVER_IP:8410/iptv/xmltv.xml`
8. **Save** and start watching

### Manual Setup

1. Dashboard → Live TV → Tuners
2. Click "Add Tuner"
3. Select "HDHomeRun"
4. Enter device URL: `http://YOUR_SERVER_IP:8410/hdhomerun/discover.json`
5. Add EPG source: `http://YOUR_SERVER_IP:8410/iptv/xmltv.xml`

## Troubleshooting

### Device Not Discovered

1. **Check SSDP is running**: Look for "HDHomeRun SSDP server started" in logs
2. **Check firewall**: Ensure UDP port 1900 is open for SSDP
3. **Check network**: Media server and StreamTV must be on the same network
4. **Manual entry**: Use the discover.json URL directly

### Channels Not Loading

1. **Verify channels exist**: Check `/api/channels` endpoint
2. **Check channel lineup**: Visit `/hdhomerun/lineup.json` in browser
3. **Verify playlists**: Ensure channels have playlists with media items
4. **Check logs**: Look for errors in StreamTV logs

### Streams Not Playing

1. **Test direct stream**: Try `/iptv/channel/{number}.m3u8` in browser
2. **Check media items**: Ensure playlists have media items
3. **Verify source URLs**: Check that YouTube/Archive.org URLs are valid
4. **Check network**: Ensure media server can reach StreamTV

## Testing

### Test Discovery

```bash
curl http://localhost:8410/hdhomerun/discover.json
```

### Test Lineup

```bash
curl http://localhost:8410/hdhomerun/lineup.json
```

### Test Stream

```bash
curl http://localhost:8410/hdhomerun/auto/v1980
```

## Notes

- **SSDP Discovery**: Requires UDP port 1900 (multicast)
- **Tuner Count**: Each tuner can stream one channel simultaneously
- **Channel Numbers**: Use your channel numbers (e.g., "1980", "1984", "1988")
- **Stream Format**: Streams are delivered as HLS (.m3u8), which Plex/Emby/Jellyfin support
- **EPG**: Use the XMLTV endpoint for program guide data

## Advanced Configuration

### Custom Device ID

Change the device ID in `config.yaml`:

```yaml
hdhomerun:
  device_id: "12345678"  # Your custom hex ID
```

### Multiple Virtual Tuners

Increase the number of tuners:

```yaml
hdhomerun:
  tuner_count: 4  # Support 4 simultaneous streams
```

### Custom Friendly Name

```yaml
hdhomerun:
  friendly_name: "My Custom HDHomeRun"
```

## Security

If you're exposing StreamTV to the internet:

1. **Use authentication**: Enable `api_key_required` in config
2. **Use HTTPS**: Configure reverse proxy with SSL
3. **Firewall**: Only expose necessary ports
4. **VPN**: Consider using VPN for remote access

## Comparison with M3U

| Feature | HDHomeRun Emulation | M3U Playlist |
|---------|---------------------|--------------|
| Auto-discovery | ✅ Yes | ❌ No |
| Plex Integration | ✅ Native | ⚠️ Manual |
| Emby Integration | ✅ Native | ⚠️ Manual |
| Jellyfin Integration | ✅ Native | ⚠️ Manual |
| Setup Complexity | ✅ Easy | ⚠️ Moderate |
| Tuner Management | ✅ Automatic | ❌ N/A |

HDHomeRun emulation provides a more seamless integration experience compared to M3U playlists.

