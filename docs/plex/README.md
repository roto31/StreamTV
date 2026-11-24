# Plex Integration Documentation

Complete guides for integrating StreamTV with Plex Media Server.

---

## 🚀 Quick Start

**Start here**: [PLEX_SETUP_COMPLETE.md](PLEX_SETUP_COMPLETE.md)

---

## 📚 Documentation Files

### Setup Guide ⭐
**[PLEX_SETUP_COMPLETE.md](PLEX_SETUP_COMPLETE.md)**
- Initial setup steps
- Configuration
- Connection testing
- Quick start

### Complete Integration
**[PLEX_INTEGRATION_COMPLETE.md](PLEX_INTEGRATION_COMPLETE.md)**
- Full integration guide
- All features
- Advanced configuration

### API + Schedule Integration
**[PLEX_API_SCHEDULE_INTEGRATION_COMPLETE.md](PLEX_API_SCHEDULE_INTEGRATION_COMPLETE.md)**
- API integration
- Schedule synchronization
- Metadata enhancement
- EPG generation

### EPG Integration
**[PLEX_EPG_INTEGRATION.md](PLEX_EPG_INTEGRATION.md)**
- Electronic Program Guide
- Metadata fetching
- Guide data

### Schedule Integration
**[PLEX_SCHEDULE_INTEGRATION.md](PLEX_SCHEDULE_INTEGRATION.md)**
- Schedule synchronization
- Playout coordination

### Troubleshooting
**[PLEX_CONNECTION_FIX.md](PLEX_CONNECTION_FIX.md)**
- Connection issues
- Authentication problems
- Network troubleshooting

**[PLEX_LIVE_TV_RECOVERY.md](PLEX_LIVE_TV_RECOVERY.md)**
- DVR id / `reloadGuide` after StreamTV restart

**[../guides/PLEX_PLAYBACK_ERROR_HOST.md](../guides/PLEX_PLAYBACK_ERROR_HOST.md)** (Issues 71–72)
- Playback Error while StreamTV preview OK
- Missing AAC codec packs (`libaac_decoder.dylib`) — verify/install scripts; first-run SetupDone gate
- Boot disk / TranscoderTempDirectory
- `/identity` 503 startup maintenance
- TunarrRAM / YouTube full-cache checklist

---

## ⚙️ Configuration

Add to `config.yaml`:

```yaml
plex:
  enabled: true
  base_url: "http://YOUR_PLEX_SERVER:32400"
  token: "YOUR_PLEX_TOKEN"
  use_for_epg: true
```

---

## 🔗 Related Documentation

- [Main Documentation Index](../INDEX.md)
- [API Documentation](../API.md)
- [HDHomeRun Guide](../HDHOMERUN.md)

---

**Start Here**: [PLEX_SETUP_COMPLETE.md](PLEX_SETUP_COMPLETE.md)
