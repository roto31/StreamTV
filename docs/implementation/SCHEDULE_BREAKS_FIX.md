# Schedule Breaks Collection Fix

## Issue

Warning in logs:
```
WARNING - Collection/Playlist not found: Inter-Episode Breaks
```

## Root Cause

The generated schedule file referenced a collection "Inter-Episode Breaks" for the 2-5 minute breaks between episodes, but this collection was never created in the database.

The schedule had entries like:
```yaml
- all: break_short
  custom_title: "Inter-Episode Break"
  duration: PT3M
```

But `break_short` pointed to a non-existent collection.

---

## Fix Applied

### Option 1: Remove Breaks (Applied) ✅

Removed all break entries from the schedule file. Episodes now play back-to-back without breaks.

**Before**: 1,845 lines (with 296 breaks)
**After**: 663 lines (episodes only)

**Result**: Clean continuous playback

### Option 2: Create Filler Collection (Alternative)

If you want breaks, you would need to:

1. Create actual filler content (black screen video, station IDs, etc.)
2. Import as a collection called "Inter-Episode Breaks"
3. Keep the break entries in the schedule

---

## Current Schedule Structure

```yaml
name: Magnum P.I. Marathon
description: 24/7 marathon of Magnum P.I. episodes

content:
  - key: season1
    collection: Magnum P.I. - Season 1
    order: chronological
  # ... seasons 2-8 ...

sequence:
  - key: magnum-marathon
    items:
      - all: season1
        custom_title: "Season 1 Episode 1"
      - all: season1
        custom_title: "Season 1 Episode 2"
      # ... continues ...

playout:
  - sequence: magnum-marathon
  - repeat: true
```

**Result**: Episodes play continuously without breaks

---

## Adding Breaks in the Future

If you want to add breaks later, you have two options:

### Option 1: Create Filler Media

1. **Create filler videos** (2-5 minutes each):
   - Black screen with logo
   - Station IDs
   - "We'll be right back" cards
   - Vintage commercials

2. **Import as collection**:
   ```yaml
   # In channels.yaml
   streams:
     - id: filler_01
       collection: "Inter-Episode Breaks"
       type: filler
       url: "path/to/filler1.mp4"
       runtime: PT2M
     - id: filler_02
       collection: "Inter-Episode Breaks"
       type: filler
       url: "path/to/filler2.mp4"
       runtime: PT3M
   ```

3. **Update schedule** to reference the collection

### Option 2: Use Existing Content

Reuse content from other collections as breaks:

```yaml
content:
  - key: station_ids
    collection: WCCO Station IDs  # Use existing content
    order: random

sequence:
  - all: season1
  - all: station_ids  # Use as break
    count: 1
  - all: season1
```

---

## Comparison with Olympic Channels

### Olympic Channels
- No breaks in schedules
- Continuous playback
- Events flow directly into each other

### Magnum P.I. (Current)
- No breaks (like Olympics)
- Continuous episode playback
- Episodes flow directly into each other

### Magnum P.I. (With Breaks - Future)
- Would need filler collection
- 2-5 minute breaks between episodes
- More like traditional TV

---

## Performance Impact

### Without Breaks (Current)
- ✅ Simpler schedule (663 lines vs 1,845)
- ✅ Faster parsing
- ✅ No collection lookup overhead
- ✅ Continuous playback

### With Breaks (If Added)
- More complex schedule
- Requires filler media collection
- More realistic TV experience
- Slightly more processing

---

## Recommendation

**For now**: Keep it simple without breaks
- Episodes play continuously
- No warnings in logs
- Simpler to maintain

**Later**: Add breaks if desired
- Create filler content
- Import as collection
- Update schedule to reference it

---

## Verification

### Check Schedule Parses
```bash
python3 -c "
from pathlib import Path
from streamtv.scheduling.parser import ScheduleParser
schedule = ScheduleParser.parse_file(Path('schedules/80.yml'))
print(f'Schedule: {schedule.name}')
print(f'Items: {len(schedule.content_map)}')
"
```

### Check No Warnings
```bash
./scripts/view-logs.sh search "Inter-Episode Breaks"
```

Should show no new warnings after restart.

---

## Summary

**Issue**: Referenced non-existent "Inter-Episode Breaks" collection
**Fix**: Removed break entries from schedule  
**Result**: Clean continuous playback
**Status**: ✅ Fixed

**Action**: Restart server to apply changes

---

**Date**: December 3, 2025
**Issue**: Missing breaks collection
**Solution**: Removed breaks for continuous playback
