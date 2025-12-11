# StreamTV Changelog

## Version 1.0.0 (2025-12-11)

### Features
- HDHomeRun tuner emulation for Plex/Emby/Jellyfin integration
- IPTV support with M3U playlists and XMLTV EPG
- Continuous and on-demand streaming modes
- YouTube, Archive.org, and PBS media source support
- Web-based channel and media management interface
- Automated macOS installation script

### Fixes
- Fixed FFmpeg errors during application shutdown
- Improved error handling for AVI file demuxing
- Channel-specific media filtering support (e.g., MP4-only filtering to avoid AVI demuxing errors)
- Fixed Plex logs page API endpoint paths
- Improved cancellation handling during shutdown
- Enhanced error recovery for problematic media files

### Improvements
- Better error recovery for problematic media files
- Enhanced logging and debugging capabilities
- Improved stream stability and error handling
- Graceful exception handling in streaming generators

### Technical Notes
- Channel-specific filtering: The codebase includes example filtering logic that can be applied to any channel to filter media by file type (e.g., MP4-only) to avoid format-specific issues
- FFmpeg error detection: Automatic detection of fatal demuxing errors with proper error handling
- Shutdown handling: Improved async task cancellation and process cleanup during application shutdown
