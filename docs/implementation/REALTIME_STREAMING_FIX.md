# Real-Time Streaming Fix (`-re` Flag Implementation)

**Date:** January 13, 2026  
**Status:** Implemented  
**Files Modified:** `streamtv/streaming/mpegts_streamer.py`

## Problem Statement

Videos were "skipping ahead" or experiencing buffer underruns during playback. Analysis of debug logs revealed:

1. FFmpeg was transcoding pre-recorded content at 15-26x real-time speed
2. A 30-minute video would transcode in ~2 minutes
3. All video data sent to client in burst
4. Server would then "sleep" for ~28 minutes before starting next item
5. Client would play through buffer, run dry, and experience stuttering/skipping

### Example from Logs

```
Channel 1984, Item 829:
- item_duration: 32 seconds (scheduled)
- actual_stream_duration: 8.7 seconds (FFmpeg finished)
- wait_time: 23.3 seconds (server waits before next item)
```

This burst-then-wait pattern caused poor user experience.

## Solution

Added FFmpeg's `-re` (read input at native frame rate) flag for all pre-recorded content streams. This flag tells FFmpeg to read input at 1x speed, matching the video's natural playback rate.

### Technical Implementation

**Location:** `_build_ffmpeg_command()` in `streamtv/streaming/mpegts_streamer.py`

**Logic:**
```python
# For standard streams (lines 5632-5642)
is_prerecorded = src_archive or src_youtube or ("archive.org" in input_url.lower())

# For MPEG-4/AVI files (lines 5556-5559)
is_prerecorded_mpeg4 = src_archive or src_youtube or True  # All MPEG-4 files are pre-recorded
```

**FFmpeg Flag:**
```python
if is_prerecorded:
    cmd.extend(["-re"])  # Read input at native frame rate (real-time)
```

## Affected Channels

### Archive.org Channels (Always Apply `-re`)
- Channel 80: Magnum P.I. Complete Series
- Channel 143: Mister Rogers' Neighborhood
- Channel 1929: Silly Symphonies
- Channel 1980: 1980 Olympics
- Channel 1985: Computer Chronicles
- Channel 1991: 1991 Winter Olympics
- Channel 1992: 1992 Winter Olympics
- Channel 1994: 1994 Winter Olympics
- Other Archive.org-based channels

### YouTube VOD Channels (Now Apply `-re`)
- All YouTube-sourced commercials and bumpers
- Historical footage compilations
- Music videos and performances
- Any non-live YouTube content

### MPEG-4/AVI Files (Always Apply `-re`)
- Any legacy video files in MPEG-4 or AVI format

## Before vs After

### Before (Burst-then-Wait Pattern)
```
Timeline: |---Transcode (2min)---|---Wait (28min)---|---Next Video---|
Client:   |---Buffer fills------|---Playing--------|---Buffer empty!---|
Result:   Buffering, stuttering, perceived "skipping"
```

### After (Real-Time Streaming)
```
Timeline: |--------Transcode at 1x speed (30min)--------|---Next Video---|
Client:   |--------Continuous data flow-----------------|---Smooth-------|
Result:   Smooth, continuous playback
```

## Behavior Notes

1. **First chunk delay:** May increase slightly as FFmpeg reads input at real-time speed
2. **Server waiting:** Still occurs as fallback if video is shorter than scheduled duration
3. **Live streams:** Not affected (already real-time paced by source)
4. **Plex streams:** Not affected (direct streaming from Plex server)

## Verification

After server restart, check debug logs for:
```json
{
  "is_prerecorded": true,
  "using_realtime_input": true
}
```

FFmpeg stderr should show `speed=1.0x` or close to it, instead of `speed=15-26x`.

## Related Files

- `streamtv/streaming/mpegts_streamer.py` - Main fix location
- `streamtv/streaming/channel_manager.py` - Contains waiting logic (now fallback only)
- `.cursor/debug.log` - Debug instrumentation logs

## Rollback

To revert to burst mode (not recommended), change:
```python
is_prerecorded = src_archive or src_youtube or ("archive.org" in input_url.lower())
```
To:
```python
is_prerecorded = False  # Disable real-time input
```
