#!/usr/bin/env zsh
# Archive.org Collection Parser with swiftDialog UI
# Interactive parser for creating StreamTV channels from Archive.org collections

# =============================================================================
# Configuration
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DIALOG_BIN="/usr/local/bin/dialog"
PYTHON_PARSER="$SCRIPT_DIR/archive_collection_parser.py"
DATA_DIR="$PROJECT_DIR/data"
SCHEDULES_DIR="$PROJECT_DIR/schedules"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =============================================================================
# Functions
# =============================================================================

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

check_dependencies() {
    log_info "Checking dependencies..."
    
    # Check for swiftDialog
    if [ ! -f "$DIALOG_BIN" ]; then
        log_error "swiftDialog not found!"
        log_info "Installing swiftDialog..."
        
        # Download and install swiftDialog
        DIALOG_URL="https://github.com/swiftDialog/swiftDialog/releases/latest/download/dialog.pkg"
        TEMP_PKG="/tmp/dialog.pkg"
        
        if curl -L "$DIALOG_URL" -o "$TEMP_PKG"; then
            sudo installer -pkg "$TEMP_PKG" -target /
            rm "$TEMP_PKG"
            log_success "swiftDialog installed"
        else
            log_error "Failed to download swiftDialog"
            log_info "Please install manually from: https://github.com/swiftDialog/swiftDialog/releases"
            exit 1
        fi
    fi
    
    # Check for Python 3
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 not found!"
        exit 1
    fi
    
    # Check for requests module
    if ! python3 -c "import requests" 2>/dev/null; then
        log_warning "Python 'requests' module not found. Installing..."
        pip3 install requests
    fi
    
    log_success "All dependencies satisfied"
}

show_welcome() {
    "$DIALOG_BIN" \
        --title "Archive.org Collection Parser" \
        --message "## Welcome to StreamTV Archive.org Collection Parser\n\nThis tool will help you create a complete StreamTV channel from any Archive.org collection.\n\n**What it does:**\n- Fetches all videos from an Archive.org collection\n- Parses episode information\n- Generates complete channel and schedule YAML files\n- Enforces 2-5 minute breaks between episodes\n\n**Requirements:**\n- Archive.org collection URL (e.g., https://archive.org/details/JHiggens)\n- Internet connection\n- Write access to StreamTV directories" \
        --icon "SF=film.stack" \
        --button1text "Continue" \
        --button2text "Cancel" \
        --width 700 \
        --height 400
    
    if [ $? -ne 0 ]; then
        log_info "Cancelled by user"
        exit 0
    fi
}

prompt_for_url() {
    # Create dialog for URL input
    DIALOG_OUTPUT=$("$DIALOG_BIN" \
        --title "Archive.org Collection URL" \
        --message "## Enter Collection Information\n\nProvide the Archive.org collection URL or identifier.\n\n**Examples:**\n- https://archive.org/details/JHiggens\n- JHiggens (identifier only)" \
        --icon "SF=link" \
        --textfield "Collection URL or ID",required,prompt="https://archive.org/details/" \
        --textfield "Channel Number",required,prompt="80" \
        --textfield "Channel Name",required,prompt="My TV Channel" \
        --selecttitle "Minimum Break (minutes)",required \
        --selectvalues "1,2,3,4,5" \
        --selectdefault "2" \
        --selecttitle "Maximum Break (minutes)",required \
        --selectvalues "2,3,4,5,6,7,8,9,10" \
        --selectdefault "5" \
        --button1text "Parse Collection" \
        --button2text "Cancel" \
        --width 700 \
        --height 550 \
        --json)
    
    DIALOG_EXIT=$?
    
    if [ $DIALOG_EXIT -ne 0 ]; then
        log_info "Cancelled by user"
        exit 0
    fi
    
    # Parse JSON output
    COLLECTION_URL=$(echo "$DIALOG_OUTPUT" | python3 -c "import sys, json; print(json.load(sys.stdin)['Collection URL or ID'])" 2>/dev/null)
    CHANNEL_NUMBER=$(echo "$DIALOG_OUTPUT" | python3 -c "import sys, json; print(json.load(sys.stdin)['Channel Number'])" 2>/dev/null)
    CHANNEL_NAME=$(echo "$DIALOG_OUTPUT" | python3 -c "import sys, json; print(json.load(sys.stdin)['Channel Name'])" 2>/dev/null)
    MIN_BREAK=$(echo "$DIALOG_OUTPUT" | python3 -c "import sys, json; print(json.load(sys.stdin)['Minimum Break (minutes)']['selectedValue'])" 2>/dev/null)
    MAX_BREAK=$(echo "$DIALOG_OUTPUT" | python3 -c "import sys, json; print(json.load(sys.stdin)['Maximum Break (minutes)']['selectedValue'])" 2>/dev/null)
    
    # Validate inputs
    if [ -z "$COLLECTION_URL" ] || [ -z "$CHANNEL_NUMBER" ] || [ -z "$CHANNEL_NAME" ]; then
        log_error "Missing required fields"
        exit 1
    fi
    
    log_info "Collection URL: $COLLECTION_URL"
    log_info "Channel Number: $CHANNEL_NUMBER"
    log_info "Channel Name: $CHANNEL_NAME"
    log_info "Break duration: $MIN_BREAK-$MAX_BREAK minutes"
}

show_progress() {
    local message="$1"
    
    "$DIALOG_BIN" \
        --title "Processing Collection" \
        --message "$message" \
        --icon "SF=arrow.down.circle" \
        --progress \
        --button1text "Processing..." \
        --button1disabled \
        --width 600 \
        --height 300 &
    
    DIALOG_PID=$!
}

parse_collection() {
    log_info "Parsing collection..."
    
    # Create temporary output directory
    TEMP_OUTPUT_DIR="/tmp/streamtv_parser_$$"
    mkdir -p "$TEMP_OUTPUT_DIR"
    
    # Show progress dialog
    show_progress "## Parsing Archive.org Collection\n\nFetching metadata and generating YAML files...\n\nThis may take a few moments depending on collection size."
    
    # Run Python parser
    PARSER_OUTPUT=$(python3 "$PYTHON_PARSER" \
        "$COLLECTION_URL" \
        --channel-number "$CHANNEL_NUMBER" \
        --channel-name "$CHANNEL_NAME" \
        --min-break "$MIN_BREAK" \
        --max-break "$MAX_BREAK" \
        --output-dir "$TEMP_OUTPUT_DIR" 2>&1)
    
    PARSER_EXIT=$?
    
    # Close progress dialog
    if [ -n "$DIALOG_PID" ]; then
        kill $DIALOG_PID 2>/dev/null
        wait $DIALOG_PID 2>/dev/null
    fi
    
    if [ $PARSER_EXIT -ne 0 ]; then
        log_error "Parser failed"
        show_error "## Parser Error\n\nFailed to parse collection:\n\n\`\`\`\n$PARSER_OUTPUT\n\`\`\`"
        rm -rf "$TEMP_OUTPUT_DIR"
        exit 1
    fi
    
    log_success "Collection parsed successfully"
    
    # Extract episode count from parser output
    EPISODE_COUNT=$(echo "$PARSER_OUTPUT" | grep "Total Episodes:" | head -1 | awk '{print $NF}')
    
    # Get generated file paths
    CHANNEL_YAML="$TEMP_OUTPUT_DIR/magnum-pi-channel.yaml"
    SCHEDULE_YAML="$TEMP_OUTPUT_DIR/magnum-pi-schedule.yml"
    
    if [ ! -f "$CHANNEL_YAML" ] || [ ! -f "$SCHEDULE_YAML" ]; then
        log_error "Generated files not found"
        show_error "## Generation Error\n\nYAML files were not created properly."
        rm -rf "$TEMP_OUTPUT_DIR"
        exit 1
    fi
}

show_error() {
    "$DIALOG_BIN" \
        --title "Error" \
        --message "$1" \
        --icon "SF=xmark.circle" \
        --button1text "OK" \
        --width 700 \
        --height 400
}

show_results() {
    local season_breakdown=$(echo "$PARSER_OUTPUT" | sed -n '/Episodes by Season:/,/=====/p' | grep -v "=====" | sed 's/^/- /')
    
    "$DIALOG_BIN" \
        --title "Parsing Complete" \
        --message "## ✅ Collection Parsed Successfully!\n\n**Channel:** $CHANNEL_NAME (Channel $CHANNEL_NUMBER)\n**Total Episodes:** $EPISODE_COUNT\n**Break Duration:** $MIN_BREAK-$MAX_BREAK minutes between episodes\n\n**Episode Breakdown:**\n$season_breakdown\n\n**Generated Files:**\n- Channel configuration YAML\n- Schedule configuration YAML\n\nWould you like to save these files to your StreamTV project?" \
        --icon "SF=checkmark.circle" \
        --button1text "Save Files" \
        --button2text "Cancel" \
        --width 700 \
        --height 600
    
    if [ $? -ne 0 ]; then
        log_info "User chose not to save files"
        rm -rf "$TEMP_OUTPUT_DIR"
        exit 0
    fi
}

save_files() {
    log_info "Saving files..."
    
    # Create target directories if they don't exist
    mkdir -p "$DATA_DIR"
    mkdir -p "$SCHEDULES_DIR"
    
    # Generate safe filenames
    SAFE_NAME=$(echo "$CHANNEL_NAME" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd '[:alnum:]-')
    CHANNEL_TARGET="$DATA_DIR/channel-${SAFE_NAME}.yaml"
    SCHEDULE_TARGET="$SCHEDULES_DIR/schedule-${SAFE_NAME}.yml"
    
    # Check if files already exist
    if [ -f "$CHANNEL_TARGET" ] || [ -f "$SCHEDULE_TARGET" ]; then
        "$DIALOG_BIN" \
            --title "File Exists" \
            --message "## Overwrite Existing Files?\n\nOne or more target files already exist:\n\n- ${CHANNEL_TARGET}\n- ${SCHEDULE_TARGET}\n\nDo you want to overwrite them?" \
            --icon "SF=exclamationmark.triangle" \
            --button1text "Overwrite" \
            --button2text "Cancel" \
            --width 700 \
            --height 400
        
        if [ $? -ne 0 ]; then
            log_info "User cancelled overwrite"
            rm -rf "$TEMP_OUTPUT_DIR"
            exit 0
        fi
    fi
    
    # Copy files
    cp "$CHANNEL_YAML" "$CHANNEL_TARGET"
    cp "$SCHEDULE_YAML" "$SCHEDULE_TARGET"
    
    log_success "Files saved"
    log_info "  Channel: $CHANNEL_TARGET"
    log_info "  Schedule: $SCHEDULE_TARGET"
}

show_completion() {
    "$DIALOG_BIN" \
        --title "Setup Complete" \
        --message "## 🎉 Channel Created Successfully!\n\n**Files Saved:**\n- 📄 \`${CHANNEL_TARGET}\`\n- 📄 \`${SCHEDULE_TARGET}\`\n\n**Next Steps:**\n\n1. **Review the YAML files** to ensure everything looks correct\n\n2. **Import the channel** by running:\n   \`\`\`\n   python3 scripts/import_channels.py \"${CHANNEL_TARGET}\"\n   \`\`\`\n\n3. **Start your StreamTV server** and tune to channel ${CHANNEL_NUMBER}\n\n4. **Enjoy your content!** 📺\n\n---\n\n*Files have been saved to your StreamTV project directories.*" \
        --icon "SF=sparkles" \
        --button1text "Open Files in Finder" \
        --button2text "Done" \
        --width 800 \
        --height 700
    
    if [ $? -eq 0 ]; then
        # Open files in Finder
        open -R "$CHANNEL_TARGET"
    fi
    
    # Cleanup
    rm -rf "$TEMP_OUTPUT_DIR"
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    log_info "Archive.org Collection Parser for StreamTV"
    log_info "==========================================="
    echo
    
    # Check dependencies
    check_dependencies
    
    # Show welcome screen
    show_welcome
    
    # Prompt for collection URL and settings
    prompt_for_url
    
    # Parse the collection
    parse_collection
    
    # Show results
    show_results
    
    # Save files
    save_files
    
    # Show completion
    show_completion
    
    log_success "All done! 🎉"
}

# Run main function
main

