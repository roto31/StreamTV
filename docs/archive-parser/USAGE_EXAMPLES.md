# Archive.org Collection Parser - Usage Examples

## 🎬 Example 1: Magnum P.I. (Already Done!)

### Using the GUI
```bash
./scripts/archive_collection_parser_dialog.sh
```

**Inputs**:
- URL: `https://archive.org/details/JHiggens`
- Channel Number: `80`
- Channel Name: `Magnum P.I. Complete Series`
- Min Break: `2` minutes
- Max Break: `5` minutes

**Result**: 298 episodes with 296 enforced breaks

---

## 📺 Example 2: Another TV Show

### Command-Line
```bash
python3 scripts/archive_collection_parser.py \
    "https://archive.org/details/TheRockfordFiles" \
    --channel-number 81 \
    --channel-name "The Rockford Files" \
    --min-break 2 \
    --max-break 5 \
    --output-dir data/
```

Then move and import:
```bash
mv data/magnum-pi-schedule.yml schedules/rockford-files-schedule.yml
python3 scripts/import_channels.py data/magnum-pi-channel.yaml
```

---

## 🎥 Example 3: Movie Collection

### Shorter Breaks for Movies
```bash
python3 scripts/archive_collection_parser.py \
    "https://archive.org/details/feature_films" \
    --channel-number 82 \
    --channel-name "Classic Cinema" \
    --min-break 1 \
    --max-break 3 \
    --output-dir ~/Desktop/movies_channel
```

Movies are longer, so use shorter breaks (1-3 minutes) between films.

---

## 📚 Example 4: Documentary Series

### Longer Breaks for Educational Content
```bash
./scripts/archive_collection_parser_dialog.sh
```

**Inputs**:
- URL: `https://archive.org/details/documentary_series`
- Channel Number: `83`
- Channel Name: `Documentary Marathon`
- Min Break: `5` minutes
- Max Break: `10` minutes

Longer breaks give viewers time to process information.

---

## 🎭 Example 5: Multiple Channels at Once

### Batch Processing
```bash
#!/bin/bash
# Create multiple channels

collections=(
    "JHiggens:80:Magnum P.I."
    "RockfordFiles:81:The Rockford Files"
    "MurderSheWrote:82:Murder She Wrote"
)

for item in "${collections[@]}"; do
    IFS=':' read -r collection channel_num name <<< "$item"

    python3 scripts/archive_collection_parser.py \
        "https://archive.org/details/$collection" \
        --channel-number "$channel_num" \
        --channel-name "$name" \
        --min-break 2 \
        --max-break 5 \
        --output-dir "data/batch_$collection"

    echo "✅ Generated channel $channel_num: $name"
done
```

---

## 🔍 Example 6: Test with Small Collection

### Quick Test
```bash
# Test with a small collection first
python3 scripts/archive_collection_parser.py \
    "SmallTestCollection" \
    --channel-number 99 \
    --output-dir /tmp/test_channel

# Review output
ls -lh /tmp/test_channel/
cat /tmp/test_channel/magnum-pi-channel.yaml | head -50
```

---

## 🎨 Example 7: Custom Break Durations

### No Breaks (Back-to-Back)
```bash
# Set min and max both to 0
python3 scripts/archive_collection_parser.py \
    "URL" \
    --min-break 0 \
    --max-break 0
```

### Very Short Breaks (30 seconds)
```bash
# Note: Convert to minutes (0.5 = 30 seconds)
# Currently only supports whole minutes, so use 1 minute minimum
python3 scripts/archive_collection_parser.py \
    "URL" \
    --min-break 1 \
    --max-break 1
```

### Commercial-Length Breaks
```bash
# Traditional TV commercial breaks (2-3 minutes)
python3 scripts/archive_collection_parser.py \
    "URL" \
    --min-break 2 \
    --max-break 3
```

### Extended Breaks
```bash
# Longer breaks for bathroom/snack runs (5-10 minutes)
python3 scripts/archive_collection_parser.py \
    "URL" \
    --min-break 5 \
    --max-break 10
```

---

## 🛠️ Example 8: Troubleshooting Mode

### Debug Output
```bash
# Run with verbose Python
python3 -v scripts/archive_collection_parser.py "URL" 2>&1 | tee debug.log

# Check what was parsed
grep "Found.*video files" debug.log
grep "Total Episodes" debug.log
```

---

## 📊 Example 9: Verify Generated Files

### Check Episode Count
```bash
# Count episodes in channel YAML
grep -c "^      - id:" data/magnum-pi-channel.yaml

# Count breaks in schedule YAML
grep -c "# .* minute break" schedules/magnum-pi-schedule.yml
```

### View Break Distribution
```bash
# See how breaks are distributed
grep "duration: PT" schedules/magnum-pi-schedule.yml | \
    sed 's/.*PT\([0-9]*\)M/\1/' | \
    sort -n | \
    uniq -c

# Output example:
#   58 2
#   62 3
#   57 4
#  119 5
```

### Sample Episode Metadata
```bash
# View first episode
awk '/- id: magnum_s01e01/,/^$/' data/magnum-pi-channel.yaml | head -15
```

---

## 🔄 Example 10: Update Existing Channel

### Regenerate with Different Settings
```bash
# Original channel with 2-5 minute breaks
python3 scripts/archive_collection_parser.py \
    "https://archive.org/details/JHiggens" \
    --channel-number 80 \
    --min-break 2 \
    --max-break 5 \
    --output-dir data/original

# Updated version with 1-3 minute breaks
python3 scripts/archive_collection_parser.py \
    "https://archive.org/details/JHiggens" \
    --channel-number 80 \
    --min-break 1 \
    --max-break 3 \
    --output-dir data/updated

# Compare
diff data/original/magnum-pi-schedule.yml data/updated/magnum-pi-schedule.yml
```

---

## 💡 Example 11: Custom Post-Processing

### Add Custom Content to Breaks
```bash
# Generate channel
python3 scripts/archive_collection_parser.py "URL"

# Edit schedule YAML to add commercials
# Replace:
#   - all: break_short
#     duration: PT3M
# With:
#   - all: commercials_1980s
#     count: 2  # Show 2 commercials
```

### Filter Episodes
```python
# Python script to filter episodes
import yaml

with open('data/magnum-pi-channel.yaml', 'r') as f:
    data = yaml.safe_load(f)

# Keep only Season 1 episodes
data['channels'][0]['streams'] = [
    s for s in data['channels'][0]['streams']
    if s['id'].startswith('magnum_s01')
]

with open('data/season1-only.yaml', 'w') as f:
    yaml.dump(data, f)
```

---

## 🎯 Example 12: Test Before Full Import

### Generate, Review, Test
```bash
# 1. Generate files
python3 scripts/archive_collection_parser.py \
    "https://archive.org/details/JHiggens" \
    --output-dir /tmp/test_magnum

# 2. Review files
less /tmp/test_magnum/magnum-pi-channel.yaml
less /tmp/test_magnum/magnum-pi-schedule.yml

# 3. Validate YAML syntax
python3 -c "import yaml; yaml.safe_load(open('/tmp/test_magnum/magnum-pi-channel.yaml'))"

# 4. If good, copy to production
cp /tmp/test_magnum/*.yaml* data/
cp /tmp/test_magnum/*.yml schedules/

# 5. Import
python3 scripts/import_channels.py data/magnum-pi-channel.yaml
```

---

## 🎊 Pro Tips

### Tip 1: Start Small
Test with a small collection (10-20 episodes) before processing large collections (100+ episodes).

### Tip 2: Use GUI for Interactive Work
The swiftDialog script is perfect for one-off channel creation with validation and preview.

### Tip 3: Use CLI for Automation
The Python script is ideal for batch processing and scripting.

### Tip 4: Always Review First
Review generated YAML files before importing to catch any issues.

### Tip 5: Keep Backups
```bash
# Backup before regenerating
cp data/magnum-pi-channel.yaml data/magnum-pi-channel.yaml.backup
cp schedules/magnum-pi-schedule.yml schedules/magnum-pi-schedule.yml.backup
```

### Tip 6: Test Stream URLs
```bash
# Test if URLs are accessible
grep "url:" data/magnum-pi-channel.yaml | \
    head -3 | \
    sed 's/.*url: //' | \
    while read url; do
        echo "Testing: $url"
        curl -I "$url" 2>&1 | grep "HTTP"
    done
```

---

## 📞 Need Help?

- **Quick Reference**: `QUICK_REFERENCE_ARCHIVE_PARSER.md`
- **Complete Guide**: `MAGNUM_PI_CHANNEL_COMPLETE.md`
- **Tool Documentation**: `scripts/ARCHIVE_PARSER_README.md`
- **Implementation Details**: `ARCHIVE_PARSER_IMPLEMENTATION_SUMMARY.md`

---

**Happy Channel Creating! 📺🎬**
