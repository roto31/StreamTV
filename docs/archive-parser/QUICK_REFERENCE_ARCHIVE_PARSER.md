# 🎯 Archive.org Collection Parser - Quick Reference

## ⚡ Quick Start

### GUI Method (Recommended)
```bash
./scripts/archive_collection_parser_dialog.sh
```

### Command-Line Method
```bash
python3 scripts/archive_collection_parser.py "https://archive.org/details/JHiggens"
```

---

## 📁 What Was Created

| File | Location | Size | Purpose |
|------|----------|------|---------|
| **Channel YAML** | `data/magnum-pi-channel.yaml` | 129 KB | 298 episodes |
| **Schedule YAML** | `schedules/magnum-pi-schedule.yml` | 54 KB | Playback + breaks |
| **Python Parser** | `scripts/archive_collection_parser.py` | 485 lines | CLI tool |
| **GUI Script** | `scripts/archive_collection_parser_dialog.sh` | 333 lines | Interactive UI |

---

## 🎬 Magnum P.I. Channel Stats

- **Channel Number**: 80
- **Total Episodes**: 298
- **Seasons**: 8 + 3 specials
- **Breaks**: 296 (2-5 minutes each)
- **Runtime**: ~250-263 hours
- **Source**: https://archive.org/details/JHiggens

---

## 🚀 Import & Run

```bash
# 1. Import channel
python3 scripts/import_channels.py data/magnum-pi-channel.yaml

# 2. Start server
./start_server.sh

# 3. Tune to channel 80!
```

---

## 🛠️ Command-Line Options

```bash
python3 scripts/archive_collection_parser.py \
    "URL" \
    --channel-number 80 \
    --channel-name "My Channel" \
    --min-break 2 \
    --max-break 5 \
    --output-dir ~/Desktop
```

---

## 📊 Verify Generation

```bash
# Count episodes
grep -c "^      - id: magnum_" data/magnum-pi-channel.yaml
# Result: 298

# Count breaks
grep -c "# .* minute break" schedules/magnum-pi-schedule.yml
# Result: 296

# View sample
head -50 data/magnum-pi-channel.yaml
```

---

## 📚 Documentation

- **Complete Guide**: `MAGNUM_PI_CHANNEL_COMPLETE.md`
- **Tool README**: `scripts/ARCHIVE_PARSER_README.md`
- **Implementation**: `ARCHIVE_PARSER_IMPLEMENTATION_SUMMARY.md`

---

## 🎨 Customize

### Change Breaks
```bash
# 1-2 minute breaks
python3 scripts/archive_collection_parser.py URL --min-break 1 --max-break 2

# 5-10 minute breaks
python3 scripts/archive_collection_parser.py URL --min-break 5 --max-break 10
```

### Multiple Channels
```bash
# Channel 80
python3 scripts/archive_collection_parser.py "URL1" --channel-number 80

# Channel 81
python3 scripts/archive_collection_parser.py "URL2" --channel-number 81
```

---

## ✅ Success Checklist

- [x] 298 episodes generated
- [x] 296 breaks enforced (2-5 min each)
- [x] Python CLI tool created
- [x] swiftDialog GUI created
- [x] Complete documentation
- [x] Files in correct locations
- [x] Ready to import and stream

---

## 🆘 Common Issues

**Problem**: "requests module not found"  
**Solution**: `pip3 install requests`

**Problem**: "swiftDialog not found"  
**Solution**: Script auto-installs, or get from https://github.com/swiftDialog/swiftDialog

**Problem**: "Collection not found"  
**Solution**: Verify URL at archive.org

---

## 🎉 You're Ready!

Your complete Magnum P.I. channel with **298 episodes** and **296 enforced breaks** (2-5 minutes each) is ready to stream!

**Happy Streaming! 📺**

