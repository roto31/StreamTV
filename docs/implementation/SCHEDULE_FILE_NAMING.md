# Schedule File Naming Convention

## Issue

Channel 80 (Magnum P.I.) showed "No schedule" in the Playout page.

## Root Cause

The schedule parser looks for **specific filename patterns** based on channel number:

```python
# From streamtv/scheduling/parser.py
possible_names = [
    f"mn-olympics-{channel_number}.yml",   # e.g., mn-olympics-80.yml
    f"mn-olympics-{channel_number}.yaml",  # e.g., mn-olympics-80.yaml
    f"{channel_number}.yml",               # e.g., 80.yml ✅
    f"{channel_number}.yaml"               # e.g., 80.yaml
]
```

**Problem**: We named the file `magnum-pi-schedule.yml`  
**Solution**: Must be named `80.yml` to match the channel number

---

## Fix Applied

**Renamed schedule file**:

```bash
# Created proper name
cp schedules/magnum-pi-schedule.yml schedules/80.yml
```

**Result**: ✅ Schedule now found and parsed!

```
✅ Schedule file found: schedules/80.yml
✅ Schedule parsed: Magnum P.I. Marathon
   Content items: 10
   Sequences: 1
   Playout instructions: 2
```

---

## Naming Rules for Schedule Files

### Channel Number-Based (Required)

For the parser to automatically find schedule files, use:

```
schedules/{channel_number}.yml
```

**Examples**:
- Channel 1980 → `schedules/1980.yml` or `schedules/mn-olympics-1980.yml`
- Channel 1984 → `schedules/1984.yml` or `schedules/mn-olympics-1984.yml`
- Channel 80 → `schedules/80.yml` ✅
- Channel 100 → `schedules/100.yml`

### Legacy Pattern (Also Supported)

For Olympic channels, the legacy pattern works:

```
schedules/mn-olympics-{channel_number}.yml
```

**Examples**:
- `schedules/mn-olympics-1980.yml`
- `schedules/mn-olympics-1984.yml`

---

## Current Schedule Files

```
schedules/
├── mn-olympics-1980.yml    ✅ Found (Channel 1980)
├── mn-olympics-1984.yml    ✅ Found (Channel 1984)
├── mn-olympics-1988.yml    ✅ Found (Channel 1988)
├── mn-olympics-1992.yml    ✅ Found (Channel 1992)
├── mn-olympics-1994.yml    ✅ Found (Channel 1994)
├── 80.yml                  ✅ Found (Channel 80) ⭐
└── magnum-pi-schedule.yml  ⚠️ Not auto-discovered (wrong name)
```

---

## Best Practices

### For New Channels

**Always name schedule files by channel number**:

```bash
# Good - auto-discovered
schedules/80.yml
schedules/100.yml
schedules/200.yml

# Bad - not auto-discovered
schedules/magnum-pi-schedule.yml
schedules/my-channel.yml
schedules/awesome-content.yml
```

### For Descriptive Names

If you want descriptive filenames, create a symbolic link:

```bash
# Create the required numeric name
cp my-schedule.yml 80.yml

# Keep descriptive name too (optional)
ln -s 80.yml magnum-pi-schedule.yml
```

---

## How Schedule Discovery Works

### 1. Channel Management

When displaying channels in the UI, the system calls:

```python
schedule_file = ScheduleParser.find_schedule_file(channel.number)
```

### 2. File Search

The parser searches for files in this order:

1. `mn-olympics-{channel_number}.yml`
2. `mn-olympics-{channel_number}.yaml`
3. `{channel_number}.yml` ✅ (Most common)
4. `{channel_number}.yaml`

### 3. Result

- **If found**: Schedule is loaded and used for playout
- **If not found**: Shows "No schedule" in UI

---

## After Fix

### Restart Server Required

For the schedule to show in the Playout page:

```bash
# Restart StreamTV
./start_server.sh
```

### Expected Result

In the Playout page for Channel 80:
- ✅ Schedule name: "Magnum P.I. Marathon"
- ✅ Green indicator instead of grey
- ✅ Shows schedule details
- ✅ Can view/edit playout

---

## Verification

### Check Schedule is Found

```bash
python3 -c "
from streamtv.scheduling.parser import ScheduleParser
schedule = ScheduleParser.find_schedule_file('80')
print(f'Schedule for Channel 80: {schedule}')
"
```

**Expected**: `schedules/80.yml`

### Test Schedule Parsing

```bash
python3 -c "
from pathlib import Path
from streamtv.scheduling.parser import ScheduleParser

file = Path('schedules/80.yml')
schedule = ScheduleParser.parse_file(file)
print(f'Name: {schedule.name}')
print(f'Content items: {len(schedule.content_map)}')
print(f'Sequences: {len(schedule.sequences)}')
"
```

**Expected**: Should parse without errors

---

## Future Improvement

To allow custom filenames, the parser could be enhanced to:

1. Check database for schedule_file field
2. Allow channel configuration to specify schedule path
3. Support multiple schedule files per channel

**Current**: Must follow naming convention  
**Future**: Could be more flexible

---

## Summary

**Issue**: Schedule file not found due to wrong filename  
**Cause**: Parser expects `{channel_number}.yml` format  
**Fix**: Renamed to `80.yml`  
**Status**: ✅ Fixed - restart server to apply  

**Action Required**: Restart StreamTV server

---

**Date**: December 3, 2025  
**Issue**: Schedule file naming  
**Solution**: Use channel number as filename (80.yml)

