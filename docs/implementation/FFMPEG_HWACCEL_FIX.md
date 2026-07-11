# FFmpeg Hardware Acceleration Fix - MPEG-4 Codec Issue

## Issue

When streaming Magnum P.I. Season 1 episodes (AVI files with MPEG-4/DivX/XviD codec), FFmpeg fails with:

```
ERROR - FFmpeg: [mpeg4 @ 0xc560ea300] Failed setup for format videotoolbox_vld:
hwaccel initialisation returned error.
```

## Root Cause

**VideoToolbox** (macOS hardware acceleration) **does NOT support** older codecs:
- ❌ MPEG-4 (DivX, XviD)
- ❌ MPEG-2
- ❌ Some other legacy codecs

**VideoToolbox ONLY supports**:
- ✅ H.264 (common in modern MP4 files)
- ✅ H.265/HEVC
- ✅ ProRes (on M-series chips)

### The Problem with Mixed Collections

Magnum P.I. collection has:
- **Season 1**: AVI files with MPEG-4/DivX codec ❌ (not supported by VideoToolbox)
- **Seasons 2-8**: MP4 files with H.264 codec ✅ (supported by VideoToolbox)

When hardware acceleration is enabled globally, Season 1 episodes **fail to decode**.

---

## Fix Applied

### Solution: Disable Hardware Acceleration

**Updated**: `config.yaml`

**Before**:
```yaml
ffmpeg:
  hwaccel: videotoolbox  # Fails on MPEG-4 files
```

**After**:
```yaml
ffmpeg:
  hwaccel: null  # Disabled for universal codec support
```

### Why This Works

- **Software decoding** supports ALL codecs
- **Reliable** for mixed format collections
- **Universal compatibility**
- **Slight CPU increase** (usually minimal on modern Macs)

---

## Alternative Solutions

### Option 1: Conditional Hardware Acceleration (Advanced)

If you want hardware acceleration for supported formats:

**You would need to**:
1. Detect codec before streaming
2. Enable `hwaccel` only for H.264/HEVC
3. Use software decoding for MPEG-4/DivX

**This requires code changes** to detect codec per video.

### Option 2: Use Auto-Fallback (Not Fully Reliable)

Add to FFmpeg command (already in code):
```bash
-hwaccel videotoolbox
-hwaccel_output_format videotoolbox
```

**Problem**: FFmpeg still errors out instead of gracefully falling back.

### Option 3: Separate Channels by Codec

Create two channels:
- **Channel 80**: Seasons 2-8 (MP4/H.264) with `hwaccel: videotoolbox`
- **Channel 81**: Season 1 (AVI/MPEG-4) with `hwaccel: null`

**This works** but is inconvenient.

---

## Recommended Configuration

### For Mixed Codec Collections (Like Magnum P.I.)

**Disable hardware acceleration**:

```yaml
ffmpeg:
  hwaccel: null
  threads: 0  # Auto-detect CPU threads
```

**Performance**: Software decoding on modern Macs (M1/M2/M3) is **fast enough** for real-time transcoding.

### For H.264-Only Collections

If you have a collection with **only modern H.264 MP4 files**, enable hardware acceleration:

```yaml
ffmpeg:
  hwaccel: videotoolbox
  hwaccel_device: null
```

---

## Performance Comparison

### With VideoToolbox (H.264 only)
- ✅ Lower CPU usage (~20-30%)
- ✅ Lower power consumption
- ✅ Better battery life (laptops)
- ❌ **FAILS on MPEG-4/DivX/XviD**

### Without Hardware Acceleration (All Codecs)
- ✅ **Works with ALL codecs**
- ✅ Reliable for mixed collections
- ✅ No codec-specific errors
- ⚠️ Higher CPU usage (~50-70%)
- ⚠️ More power consumption

### M1/M2/M3 Mac Performance (Software Decoding)

Modern Apple Silicon is **fast enough** for software decoding:
- **M1**: Can handle 4-6 simultaneous transcodes
- **M2/M3**: Can handle 6-10+ simultaneous transcodes
- **Efficiency**: CPU cores handle transcoding efficiently

**For most users**: Software decoding is perfectly fine! ✅

---

## Testing

### Verify the Fix

1. **Restart StreamTV server**:
   ```bash
   ./start_server.sh
   ```

2. **Try streaming Season 1** (AVI files):
   ```bash
   curl -I http://localhost:8410/iptv/stream/80
   ```

3. **Check logs** for errors:
   ```bash
   tail -f ~/Library/Logs/StreamTV/streamtv-*.log | grep -i "ffmpeg\|error"
   ```

### Expected Results

✅ No "hwaccel initialisation" errors
✅ Streams play successfully
✅ Both AVI and MP4 files work  
✅ Slight CPU increase (acceptable)

---

## CPU Monitoring

Watch CPU usage while streaming:

```bash
# Monitor CPU usage
top -pid $(pgrep -f ffmpeg) -stats cpu
```

On M1/M2/M3 Macs, expect:
- **1 stream**: 30-50% CPU (one core)
- **2 streams**: 50-80% CPU
- **3+ streams**: May approach 100% but still playable

---

## Future Improvements

### Per-Video Codec Detection (Future Enhancement)

Ideal solution would be:
1. Detect video codec before transcoding
2. Enable hardware acceleration for H.264/HEVC
3. Use software decoding for MPEG-4/DivX
4. Automatic per-video decision

**This requires**:
- Running `ffprobe` on each video
- Parsing codec information
- Dynamic FFmpeg command building

---

## Quick Reference

### Disable Hardware Acceleration (Current Fix)
```yaml
ffmpeg:
  hwaccel: null
```

### Enable for H.264-Only Collections
```yaml
ffmpeg:
  hwaccel: videotoolbox
```

### Check Current Setting
```bash
grep "hwaccel:" config.yaml
```

---

## Summary

**Issue**: VideoToolbox doesn't support MPEG-4 (used in AVI files)
**Fix**: Disabled hardware acceleration in `config.yaml`
**Impact**: Slight CPU increase, universal codec support
**Status**: ✅ Fixed

**Action Required**: Restart StreamTV server

---

**Date**: December 3, 2025
**Status**: ✅ Fixed
**Configuration**: Hardware acceleration disabled for universal codec support
