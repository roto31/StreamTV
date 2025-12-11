# Schedule YAML Creator

An interactive macOS tool for creating schedule YAML configuration files using SwiftDialog. This tool guides you through the process of creating channel schedule files step-by-step, similar to the SYM-Helper workflow.

## Prerequisites

### SwiftDialog Installation

This tool requires SwiftDialog to be installed on your macOS system. SwiftDialog is a powerful dialog tool for macOS that provides native-looking dialogs.

**Installation:**

1. Download the latest release from [SwiftDialog GitHub](https://github.com/swiftDialog/swiftDialog)
2. Install using one of these methods:
   - **Homebrew**: `brew install --cask swiftdialog`
   - **Manual**: Download the `.pkg` installer and run it
   - **Direct**: Download the binary and place it in `/usr/local/bin/dialog`

**Verify Installation:**

```bash
which dialog
# Should return: /usr/local/bin/dialog
```

### Optional: jq for Better JSON Parsing

The script works without `jq`, but having it installed provides better JSON parsing:

```bash
brew install jq
```

## Usage

### Basic Usage

Run the script from the project root or scripts directory:

```bash
./scripts/create_schedule.sh
```

Or from the scripts directory:

```bash
cd scripts
./create_schedule.sh
```

### Interactive Workflow

The tool guides you through creating a schedule YAML file with the following steps:

#### 1. Basic Information
- **Schedule Name**: Enter a descriptive name for your schedule (e.g., "MN 1980 Winter Olympics (WCCO)")
- **Description**: Enter a multi-line description of the schedule

#### 2. Content Definitions
Define content keys that map to collections in your database:

- **Content Key**: Unique identifier (e.g., `day01`, `pre_roll`, `ads_1980`)
- **Collection Name**: Name of the collection in your database
- **Playback Order**: Choose `chronological` or `shuffle`

You can add multiple content definitions. The tool will prompt you to add more after each one.

#### 3. Sequences
Create playback sequences that define how content is organized:

- **Sequence Key**: Unique identifier for the sequence (e.g., `mn80-channel`, `pre-roll`)
- **Sequence Items**: Add items to the sequence:
  - **Duration Item**: Fill a specific duration with content (e.g., 3-minute commercial break)
  - **All Item**: Play all items from a content collection
  - **Sequence Reference**: Reference another sequence
  - **Pre-Roll/Mid-Roll/Post-Roll**: Control commercial insertion points

#### 4. Playout Instructions
Define the main playback configuration:

- **Main Sequence**: Select which sequence to use as the main channel sequence
- **Repeat**: Enable or disable looping (infinite repeat)

#### 5. Save File
- **Filename**: Enter the filename (will be saved to `schedules/` directory)
- The tool will check if the file exists and ask for confirmation before overwriting

## Features

### Save/Cancel Handling

The tool implements proper save/cancel behavior:

- **At any point**, you can click "Cancel" to exit
- **Before exiting**, you'll be prompted: "Do you want to save your changes?"
  - **Yes**: Saves the file (you'll be prompted for filename if not already provided)
  - **No**: Exits without saving and deletes the temporary file

### Error Handling

- Validates that SwiftDialog is installed before starting
- Checks for required fields
- Validates file paths and prevents accidental overwrites
- Provides clear error messages via dialog boxes

### Preview

Before saving, the tool shows a preview of the first 30 lines of your YAML file so you can verify the structure.

## Example Output

The tool generates YAML files in this format:

```yaml
name: MN 1980 Winter Olympics (WCCO)
description: >-
  Sequential channel that mirrors ABC's Lake Placid coverage but wraps every
  national feed with WCCO-TV IDs, commercials, and Minneapolis/St. Paul
  newscasts sourced from TC Media Now.

content:
  - key: day01
    collection: 1980 Winter Olympics - Day 01 - Preview and Opening Ceremony
    order: chronological
  - key: pre_roll
    collection: MN 1980 Pre-Roll IDs (TC Media Now)
    order: shuffle

sequence:
  - key: mn80-pre-roll
    items:
      - duration: "00:03:00"
        content: pre_roll
        filler_kind: Commercial
        trim: true
        discard_attempts: 3
  - key: mn80-channel
    items:
      - all: day01
        custom_title: "Day 01 – Preview and Opening Ceremony"
      - pre_roll: true
        sequence: mn80-pre-roll

playout:
  - sequence: mn80-channel
  - repeat: true
```

## File Locations

- **Script**: `scripts/create_schedule.sh`
- **Output Directory**: `schedules/`
- **Temporary Files**: Created in `/tmp/` and automatically cleaned up

## Troubleshooting

### SwiftDialog Not Found

If you see "SwiftDialog not found":

1. Verify installation: `which dialog`
2. If not found, install SwiftDialog (see Prerequisites)
3. If installed in a non-standard location, edit the `DIALOG` variable in the script

### JSON Parsing Issues

If you encounter JSON parsing errors:

1. Install `jq` for better parsing: `brew install jq`
2. The script will fall back to basic parsing if `jq` is not available

### Permission Errors

If you get permission errors:

```bash
chmod +x scripts/create_schedule.sh
```

### Dialog Not Appearing

If dialogs don't appear:

1. Check that SwiftDialog is properly installed
2. Try running from Terminal (not just double-clicking)
3. Check Console.app for SwiftDialog errors

## Integration with StreamTV

Once you've created a schedule YAML file:

1. **Import Collections**: Ensure your collections exist in the database
   ```bash
   python3 scripts/import_collections.py
   ```

2. **Use the Schedule**: StreamTV automatically detects schedule files in the `schedules/` directory when generating HLS streams or EPG data

3. **File Naming**: Schedule files should match your channel number pattern (e.g., `mn-olympics-1980.yml` for channel "1980")

## References

- **SwiftDialog**: https://github.com/swiftDialog/swiftDialog
- **SwiftDialog Documentation**: https://github.com/swiftDialog/swiftDialog/wiki
- **SYM-Helper**: https://github.com/setup-your-mac/SYM-Helper (design inspiration)
- **Schedule Documentation**: See `docs/SCHEDULES.md` for detailed schedule file format

## Support

For issues or questions:

1. Check the troubleshooting section above
2. Review SwiftDialog documentation
3. Check StreamTV schedule documentation in `docs/SCHEDULES.md`

