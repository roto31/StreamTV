# Archive.org Collection Parser Tools

Two powerful tools for creating StreamTV channels from Archive.org collections.

---

## 🛠️ Tools Included

### 1. Python Parser (`archive_collection_parser.py`)

**Command-line tool** for automated YAML generation.

#### Usage

```bash
python3 scripts/archive_collection_parser.py <COLLECTION_URL> [OPTIONS]
```

#### Options

| Option | Description | Default |
|--------|-------------|---------|
| `collection_url` | Archive.org URL or identifier | **(required)** |
| `--channel-number` `-n` | Channel number | `80` |
| `--channel-name` `-c` | Channel name | Collection title |
| `--min-break` | Minimum break (minutes) | `2` |
| `--max-break` | Maximum break (minutes) | `5` |
| `--output-dir` `-o` | Output directory | Current directory |

#### Example

```bash
python3 scripts/archive_collection_parser.py \
    "https://archive.org/details/JHiggens" \
    --channel-number 80 \
    --channel-name "Magnum P.I. Complete Series" \
    --min-break 2 \
    --max-break 5 \
    --output-dir ~/Desktop
```

---

### 2. swiftDialog Script (`archive_collection_parser_dialog.sh`)

**Interactive GUI tool** with beautiful macOS-native interface.

#### Usage

```bash
./scripts/archive_collection_parser_dialog.sh
```

#### Features

✅ **User-Friendly**: Beautiful swiftDialog interface  
✅ **Auto-Install**: Automatically installs dependencies  
✅ **Progress Tracking**: Real-time progress indicators  
✅ **Validation**: Validates all inputs  
✅ **File Management**: Automatically saves to correct locations  
✅ **Preview**: Open generated files in Finder  

#### Workflow

1. **Welcome Screen**
   - Introduction and requirements

2. **Input Collection**
   - Enter Archive.org URL
   - Set channel number and name
   - Choose break durations

3. **Processing**
   - Fetches metadata
   - Parses episodes
   - Generates YAML files
   - Shows progress

4. **Results**
   - Displays episode counts
   - Shows season breakdown
   - Confirms file locations

5. **Save**
   - Saves to `data/` and `schedules/`
   - Opens files in Finder
   - Shows next steps

---

## 📋 Requirements

### System Requirements

- **macOS**: 12.0 or later (for swiftDialog)
- **Python**: 3.8 or later
- **Network**: Internet connection

### Python Dependencies

```bash
pip3 install requests
```

### swiftDialog

The interactive script will auto-install swiftDialog if not present, or install manually:

```bash
# Download latest release
curl -L "https://github.com/swiftDialog/swiftDialog/releases/latest/download/dialog.pkg" -o /tmp/dialog.pkg

# Install
sudo installer -pkg /tmp/dialog.pkg -target /
```

---

## 🎯 Supported Collections

These tools work with **any** Archive.org video collection:

### TV Shows
- Classic series (Magnum P.I., The Rockford Files, etc.)
- Modern series
- Documentary series
- Animated series

### Movies
- Feature films
- Short films
- Classic cinema
- Educational films

### Educational Content
- Lectures
- How-to videos
- Historical footage
- Training videos

---

## 📊 Output Files

### Channel YAML (`magnum-pi-channel.yaml`)

Contains complete episode metadata:

```yaml
channels:
  - number: "80"
    name: "Magnum P.I. Complete Series"
    streams:
      - id: magnum_s01e01
        collection: "Magnum P.I. - Season 1"
        url: https://archive.org/download/...
        runtime: PT48M
```

### Schedule YAML (`magnum-pi-schedule.yml`)

Defines playback order with breaks:

```yaml
sequence:
  - key: magnum-marathon
    items:
      - all: season1
        custom_title: "Season 1 Episode 1"
      # 3 minute break
      - all: break_short
        duration: PT3M
```

---

## 🔧 Advanced Usage

### Custom Break Durations

```bash
# Shorter breaks (1-2 minutes)
python3 scripts/archive_collection_parser.py \
    "URL" --min-break 1 --max-break 2

# Longer breaks (5-10 minutes)
python3 scripts/archive_collection_parser.py \
    "URL" --min-break 5 --max-break 10
```

### Multiple Channels

```bash
# Channel 80: Magnum P.I.
python3 scripts/archive_collection_parser.py \
    "https://archive.org/details/JHiggens" \
    --channel-number 80

# Channel 81: Another Show
python3 scripts/archive_collection_parser.py \
    "https://archive.org/details/AnotherCollection" \
    --channel-number 81
```

### Extract Identifier from URL

The parser automatically extracts the identifier from various URL formats:

```
https://archive.org/details/JHiggens       → JHiggens
https://archive.org/download/JHiggens/...  → JHiggens
JHiggens                                    → JHiggens
```

---

## 🐛 Troubleshooting

### Issue: "Collection not found"

**Cause**: Invalid URL or identifier  
**Solution**: Verify the collection exists at archive.org

### Issue: "No video files found"

**Cause**: Collection contains no supported video formats  
**Solution**: Check if collection has .mp4, .avi, .mkv, etc.

### Issue: "swiftDialog not found"

**Cause**: swiftDialog not installed  
**Solution**: Script will auto-install, or install manually

### Issue: "requests module not found"

**Cause**: Python requests library not installed  
**Solution**: `pip3 install requests`

### Issue: "Permission denied"

**Cause**: Script not executable  
**Solution**: `chmod +x scripts/*.sh`

---

## 📝 Example Collections

Try these Archive.org collections:

### TV Shows

```bash
# Magnum P.I. (298 episodes)
./scripts/archive_collection_parser_dialog.sh
# Enter: https://archive.org/details/JHiggens
```

### Public Domain Movies

```bash
# Classic Films
python3 scripts/archive_collection_parser.py \
    "https://archive.org/details/feature_films"
```

### Educational Content

```bash
# Educational Videos
python3 scripts/archive_collection_parser.py \
    "https://archive.org/details/prelinger"
```

---

## 🎨 Customization

### Modify Episode Titles

Edit generated YAML files to customize titles:

```yaml
- id: magnum_s01e01
  slot: "Custom Title Here"
```

### Add Commercial Content

Replace break collection with actual commercials:

```yaml
content:
  - key: commercials_1980s
    collection: 1980s TV Commercials
    order: random

sequence:
  - all: season1
  - all: commercials_1980s  # Instead of break_short
    duration: PT3M
```

### Change Playback Order

Modify sequence order in schedule YAML:

```yaml
sequence:
  - key: best-episodes
    items:
      - all: season3  # Start with season 3
      - all: season1
      - all: season2
```

---

## 📚 Documentation

- **Full Guide**: `MAGNUM_PI_CHANNEL_COMPLETE.md`
- **StreamTV Docs**: `docs/README.md`
- **Schedule Format**: `docs/SCHEDULES.md`
- **Archive.org API**: https://archive.org/developers/

---

## 🆘 Getting Help

1. Check `MAGNUM_PI_CHANNEL_COMPLETE.md` for detailed info
2. Review generated files for examples
3. Test with small collections first
4. Enable debug output: `python3 -v scripts/...`

---

## ✅ Quick Start Checklist

- [ ] Install Python 3.8+
- [ ] Install requests module
- [ ] Make scripts executable
- [ ] Find Archive.org collection
- [ ] Run swiftDialog script OR Python script
- [ ] Review generated YAML files
- [ ] Import channel: `python3 scripts/import_channels.py data/...`
- [ ] Start StreamTV server
- [ ] Enjoy your channel!

---

## 🎉 Success!

You now have powerful tools to create StreamTV channels from **any** Archive.org collection with enforced breaks between episodes!

**Happy Streaming! 📺**

