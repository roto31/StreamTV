# YouTube Data API v3 Integration Guide

## Overview

StreamTV now integrates with the [YouTube Data API v3](https://developers.google.com/youtube) to improve reliability and resolve streaming issues. The API is used for:

- **Video validation** - Check if videos exist and are available before attempting to stream
- **Metadata retrieval** - Get accurate video information (title, description, thumbnails, etc.)
- **Error prevention** - Detect unavailable videos early to avoid unnecessary yt-dlp calls
- **Better error messages** - Provide clear feedback when videos are private, deleted, or unavailable

## Benefits

1. **Reduced Rate Limiting** - API validation prevents unnecessary yt-dlp requests
2. **Better Error Handling** - Know immediately if a video is unavailable
3. **Improved Reliability** - Validate videos before attempting to stream
4. **Enhanced Metadata** - Get accurate information from YouTube's official API

## Setup Instructions

### Step 1: Get a YouTube Data API v3 Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the YouTube Data API v3:
   - Navigate to "APIs & Services" > "Library"
   - Search for "YouTube Data API v3"
   - Click "Enable"
4. Create credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "API Key"
   - Copy your API key
   - (Optional) Restrict the API key to YouTube Data API v3 for security

### Step 2: Configure StreamTV

Add your API key to `config.yaml`:

```yaml
youtube:
  enabled: true
  quality: "best"
  extract_audio: false
  cookies_file: null
  use_authentication: false
  api_key: "YOUR_API_KEY_HERE"  # Add your API key
  oauth_client_id: null
  oauth_client_secret: null
  oauth_refresh_token: null
```

### Step 3: Restart StreamTV

Restart the StreamTV server for changes to take effect.

## How It Works

### With API Key (Recommended)

1. **Video Validation**: When a YouTube URL is requested, StreamTV first validates it using the YouTube Data API
2. **Availability Check**: The API checks if the video is public and available
3. **Metadata Retrieval**: If available, metadata is retrieved from the API (faster and more reliable)
4. **Stream URL Extraction**: yt-dlp is still used to get the actual streaming URL (API doesn't provide this)
5. **Error Prevention**: Unavailable videos are detected early, preventing unnecessary processing

### Without API Key (Fallback)

If no API key is configured, StreamTV falls back to the previous behavior:
- Uses yt-dlp for all operations
- No pre-validation
- May encounter more rate limiting issues

## API Quota

The YouTube Data API v3 has a default quota of **10,000 units per day**. Each API call consumes units:

- `videos.list` (get video info): **1 unit**
- `search.list` (search videos): **100 units**

For most use cases, the default quota is sufficient. If you need more:
1. Go to Google Cloud Console
2. Navigate to "APIs & Services" > "Quotas"
3. Request a quota increase

## Troubleshooting

### API Key Invalid

**Error**: `YouTube API quota exceeded or API key invalid`

**Solutions**:
1. Verify your API key is correct in `config.yaml`
2. Ensure YouTube Data API v3 is enabled in Google Cloud Console
3. Check API key restrictions (if any) allow YouTube Data API v3

### Quota Exceeded

**Error**: `YouTube API quota exceeded`

**Solutions**:
1. Wait for quota reset (daily at midnight Pacific Time)
2. Request quota increase in Google Cloud Console
3. StreamTV will fall back to yt-dlp-only mode

### Video Not Found

**Error**: `YouTube video not found via API`

**Possible Causes**:
- Video ID is invalid
- Video has been deleted
- Video is private/unlisted (if not authenticated)

**Solutions**:
- Verify the YouTube URL is correct
- Check if video is still available on YouTube
- For private videos, use cookies authentication

## Features

### Video Validation

The API validates videos before attempting to stream:

```python
# Example validation result
{
    'valid': True,
    'video_id': 'dQw4w9WgXcQ',
    'available': True,
    'info': {
        'title': 'Video Title',
        'duration': 212,
        'thumbnail': 'https://...',
        ...
    },
    'error': None
}
```

### Enhanced Error Messages

With API integration, you get clearer error messages:

- **Before**: "Error getting YouTube video info"
- **After**: "YouTube video unavailable: Video is private"

### Metadata Quality

API-provided metadata is more accurate:
- Exact duration
- Official thumbnails
- Accurate view counts
- Proper upload dates

## Best Practices

1. **Always use an API key** - Significantly improves reliability
2. **Monitor quota usage** - Check Google Cloud Console regularly
3. **Restrict API key** - Limit to YouTube Data API v3 only
4. **Use cookies for private videos** - API key alone won't access private content
5. **Combine with cookies** - Use both API key and cookies for best results

## References

- [YouTube Data API v3 Documentation](https://developers.google.com/youtube/v3)
- [Google Cloud Console](https://console.cloud.google.com/)
- [API Quota Information](https://developers.google.com/youtube/v3/getting-started#quota)

## Migration Notes

### Existing Installations

If you're upgrading from a previous version:

1. **No breaking changes** - Works without API key (fallback mode)
2. **Optional enhancement** - Add API key for better reliability
3. **Backward compatible** - All existing configurations work

### Configuration Migration

Your existing `config.yaml` will continue to work. Simply add the `api_key` field:

```yaml
youtube:
  # ... existing settings ...
  api_key: "YOUR_API_KEY_HERE"  # Add this line
```

---

**Note**: The YouTube Data API v3 is free to use within quota limits. No payment required for basic usage.

