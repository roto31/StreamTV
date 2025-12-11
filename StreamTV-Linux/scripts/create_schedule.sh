#!/bin/bash

###############################################################################
# Schedule YAML Creator
# Interactive tool for creating schedule YAML files using SwiftDialog
# Based on SYM-Helper design pattern
###############################################################################

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SCHEDULES_DIR="$PROJECT_ROOT/schedules"
TEMP_FILE=""

# SwiftDialog binary path (adjust if needed)
DIALOG="/usr/local/bin/dialog"
if [[ ! -f "$DIALOG" ]]; then
    if command -v dialog &> /dev/null; then
        DIALOG=$(command -v dialog)
    else
        echo "Error: SwiftDialog not found. Please install from https://github.com/swiftDialog/swiftDialog"
        exit 1
    fi
fi

# Check for jq (optional, for better JSON parsing)
HAS_JQ=false
if command -v jq &> /dev/null; then
    HAS_JQ=true
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Cleanup function
cleanup() {
    if [[ -n "$TEMP_FILE" && -f "$TEMP_FILE" ]]; then
        rm -f "$TEMP_FILE"
    fi
}
trap cleanup EXIT

# Function to parse JSON response from SwiftDialog
parse_dialog_json() {
    local json_output="$1"
    local field_name="$2"
    
    if [[ "$HAS_JQ" == "true" ]]; then
        echo "$json_output" | jq -r ".$field_name // empty" 2>/dev/null || echo ""
    else
        # Fallback parsing without jq
        echo "$json_output" | grep -o "\"$field_name\"[[:space:]]*:[[:space:]]*\"[^\"]*\"" | sed "s/.*\"$field_name\"[[:space:]]*:[[:space:]]*\"\([^\"]*\)\".*/\1/" || echo ""
    fi
}

# Function to check if button1 was clicked
check_button1() {
    local json_output="$1"
    
    if [[ "$HAS_JQ" == "true" ]]; then
        local button=$(echo "$json_output" | jq -r ".button // empty" 2>/dev/null)
        [[ "$button" == "button1" ]]
    else
        echo "$json_output" | grep -q '"button"[[:space:]]*:[[:space:]]*"button1"'
    fi
}

# Function to show error dialog
show_error() {
    local message="$1"
    "$DIALOG" --title "Error" \
        --message "$message" \
        --icon "caution" \
        --button1text "OK" \
        --overlayicon "caution" \
        --ontop > /dev/null 2>&1
}

# Function to show info dialog
show_info() {
    local message="$1"
    "$DIALOG" --title "Information" \
        --message "$message" \
        --icon "info" \
        --button1text "OK" \
        --overlayicon "info" > /dev/null 2>&1
}

# Function to get text input
get_text_input() {
    local title="$1"
    local message="$2"
    local default_value="${3:-}"
    local field_name="${4:-Value}"
    local result
    local json_output
    
    json_output=$("$DIALOG" --title "$title" \
        --message "$message" \
        --textfield "$field_name",required \
        --textfieldvalue "$default_value" \
        --button1text "Continue" \
        --button2text "Cancel" \
        --icon "info" \
        --overlayicon "info" \
        --json 2>/dev/null)
    
    if ! check_button1 "$json_output"; then
        return 1
    fi
    
    result=$(parse_dialog_json "$json_output" "$field_name")
    
    if [[ -z "$result" ]]; then
        return 1
    fi
    echo "$result"
}

# Function to get multiline text input
get_multiline_input() {
    local title="$1"
    local message="$2"
    local default_value="${3:-}"
    local result
    local json_output
    
    json_output=$("$DIALOG" --title "$title" \
        --message "$message" \
        --textfield "Description",required \
        --textfieldvalue "$default_value" \
        --button1text "Continue" \
        --button2text "Cancel" \
        --icon "info" \
        --overlayicon "info" \
        --json 2>/dev/null)
    
    if ! check_button1 "$json_output"; then
        return 1
    fi
    
    result=$(parse_dialog_json "$json_output" "Description")
    
    if [[ -z "$result" ]]; then
        return 1
    fi
    echo "$result"
}

# Function to get choice from list
get_choice() {
    local title="$1"
    local message="$2"
    local options="$3"
    local result
    local json_output
    local select_values
    
    # Convert comma-separated list to SwiftDialog format
    select_values=$(echo "$options" | tr ',' '\n' | sed 's/^/"/;s/$/"/' | tr '\n' ',' | sed 's/,$//')
    select_values="[$select_values]"
    
    json_output=$("$DIALOG" --title "$title" \
        --message "$message" \
        --selectvalues "$select_values" \
        --selecttitle "Select Option" \
        --button1text "Continue" \
        --button2text "Cancel" \
        --icon "info" \
        --overlayicon "info" \
        --json 2>/dev/null)
    
    if ! check_button1 "$json_output"; then
        return 1
    fi
    
    result=$(parse_dialog_json "$json_output" "selectedOption")
    
    if [[ -z "$result" ]]; then
        return 1
    fi
    echo "$result"
}

# Function to get yes/no confirmation
get_yes_no() {
    local title="$1"
    local message="$2"
    local default="${3:-yes}"
    local result
    local json_output
    
    local button1="Yes"
    local button2="No"
    if [[ "$default" == "no" ]]; then
        button1="No"
        button2="Yes"
    fi
    
    json_output=$("$DIALOG" --title "$title" \
        --message "$message" \
        --button1text "$button1" \
        --button2text "$button2" \
        --icon "question" \
        --overlayicon "question" \
        --json 2>/dev/null)
    
    if check_button1 "$json_output"; then
        if [[ "$default" == "yes" ]]; then
            echo "yes"
        else
            echo "no"
        fi
    else
        if [[ "$default" == "yes" ]]; then
            echo "no"
        else
            echo "yes"
        fi
    fi
}

# Function to add content definition
add_content_definition() {
    local yaml_file="$1"
    
    while true; do
        local add_more=$(get_yes_no "Content Definitions" "Add a content definition?" "yes")
        if [[ "$add_more" != "yes" ]]; then
            break
        fi
        
        local key=$(get_text_input "Content Definition" "Enter content key (e.g., day01, pre_roll):" "")
        if [[ $? -ne 0 ]]; then
            break
        fi
        
        local collection=$(get_text_input "Content Definition" "Enter collection name:" "")
        if [[ $? -ne 0 ]]; then
            break
        fi
        
        local order=$(get_choice "Content Definition" "Select playback order:" "chronological,shuffle")
        if [[ $? -ne 0 ]]; then
            break
        fi
        
        # Append to YAML
        cat >> "$yaml_file" <<EOF
  - key: $key
    collection: $collection
    order: $order
EOF
        
        local continue_add=$(get_yes_no "Content Definition" "Add another content definition?" "yes")
        if [[ "$continue_add" != "yes" ]]; then
            break
        fi
    done
}

# Function to add sequence item
add_sequence_item() {
    local yaml_file="$1"
    local available_content="$2"
    
    local item_type=$(get_choice "Sequence Item" "Select item type:" "duration,all,sequence,pre_roll,mid_roll,post_roll")
    if [[ $? -ne 0 ]]; then
        return 1
    fi
    
    case "$item_type" in
        "duration")
            local duration=$(get_text_input "Duration Item" "Enter duration (HH:MM:SS format, e.g., 00:03:00):" "00:03:00")
            if [[ $? -ne 0 ]]; then
                return 1
            fi
            
            local content_key=$(get_choice "Duration Item" "Select content key:" "$available_content")
            if [[ $? -ne 0 ]]; then
                return 1
            fi
            
            local filler_kind=$(get_choice "Duration Item" "Select filler kind:" "Commercial,Program,Other")
            if [[ $? -ne 0 ]]; then
                return 1
            fi
            
            local trim=$(get_yes_no "Duration Item" "Enable trim?" "yes")
            local discard_attempts=$(get_text_input "Duration Item" "Enter discard attempts (number):" "3")
            if [[ $? -ne 0 ]]; then
                return 1
            fi
            
            cat >> "$yaml_file" <<EOF
      - duration: "$duration"
        content: $content_key
        filler_kind: $filler_kind
        trim: $trim
        discard_attempts: $discard_attempts
EOF
            ;;
        "all")
            local content_key=$(get_choice "All Item" "Select content key:" "$available_content")
            if [[ $? -ne 0 ]]; then
                return 1
            fi
            
            local custom_title=$(get_text_input "All Item" "Enter custom title (optional, press Enter to skip):" "" "CustomTitle")
            if [[ $? -ne 0 && -n "$custom_title" ]]; then
                return 1
            fi
            
            if [[ -n "$custom_title" ]]; then
                cat >> "$yaml_file" <<EOF
      - all: $content_key
        custom_title: "$custom_title"
EOF
            else
                cat >> "$yaml_file" <<EOF
      - all: $content_key
EOF
            fi
            ;;
        "sequence")
            local sequence_key=$(get_text_input "Sequence Reference" "Enter sequence key to reference:" "")
            if [[ $? -ne 0 ]]; then
                return 1
            fi
            
            cat >> "$yaml_file" <<EOF
      - sequence: $sequence_key
EOF
            ;;
        "pre_roll"|"mid_roll"|"post_roll")
            local enabled=$(get_yes_no "${item_type^} Item" "Enable ${item_type}?" "yes")
            local sequence_key=$(get_text_input "${item_type^} Item" "Enter sequence key:" "")
            if [[ $? -ne 0 ]]; then
                return 1
            fi
            
            cat >> "$yaml_file" <<EOF
      - ${item_type}: $enabled
        sequence: $sequence_key
EOF
            
            if [[ "$item_type" == "mid_roll" ]]; then
                local expression=$(get_text_input "Mid-Roll Item" "Enter expression (e.g., 'true'):" "true")
                if [[ $? -eq 0 && -n "$expression" ]]; then
                    cat >> "$yaml_file" <<EOF
        expression: "$expression"
EOF
                fi
            fi
            ;;
    esac
    
    return 0
}

# Function to add sequence
add_sequence() {
    local yaml_file="$1"
    local available_content="$2"
    
    while true; do
        local add_more=$(get_yes_no "Sequences" "Add a sequence?" "yes")
        if [[ "$add_more" != "yes" ]]; then
            break
        fi
        
        local sequence_key=$(get_text_input "Sequence" "Enter sequence key (e.g., mn80-channel, pre-roll):" "")
        if [[ $? -ne 0 ]]; then
            break
        fi
        
        cat >> "$yaml_file" <<EOF
  - key: $sequence_key
    items:
EOF
        
        # Add items to sequence
        while true; do
            local add_item=$(get_yes_no "Sequence Items" "Add an item to this sequence?" "yes")
            if [[ "$add_item" != "yes" ]]; then
                break
            fi
            
            if ! add_sequence_item "$yaml_file" "$available_content"; then
                break
            fi
        done
        
        local continue_add=$(get_yes_no "Sequences" "Add another sequence?" "yes")
        if [[ "$continue_add" != "yes" ]]; then
            break
        fi
    done
}

# Function to add playout
add_playout() {
    local yaml_file="$1"
    local available_sequences="$2"
    
    local sequence_key=$(get_choice "Playout" "Select main sequence key:" "$available_sequences")
    if [[ $? -ne 0 ]]; then
        return 1
    fi
    
    local repeat=$(get_yes_no "Playout" "Enable repeat (loop)?" "yes")
    
    cat >> "$yaml_file" <<EOF
playout:
  - sequence: $sequence_key
  - repeat: $repeat
EOF
}

# Main function
main() {
    # Check if SwiftDialog is installed
    if [[ ! -f "$DIALOG" ]]; then
        echo -e "${RED}Error: SwiftDialog not found at $DIALOG${NC}"
        echo "Please install SwiftDialog from: https://github.com/swiftDialog/swiftDialog"
        exit 1
    fi
    
    # Ensure schedules directory exists
    mkdir -p "$SCHEDULES_DIR"
    
    # Welcome dialog
    local welcome_json=$("$DIALOG" --title "Schedule YAML Creator" \
        --message "Welcome to the Schedule YAML Creator!\n\nThis tool will guide you through creating a schedule YAML file for your channel configuration.\n\nClick Continue to begin." \
        --icon "info" \
        --button1text "Continue" \
        --button2text "Cancel" \
        --overlayicon "info" \
        --json 2>/dev/null)
    
    if ! check_button1 "$welcome_json"; then
        exit 0
    fi
    
    # Create temporary file
    TEMP_FILE=$(mktemp /tmp/schedule_XXXXXX.yml)
    
    # Get basic information
    local name=$(get_text_input "Basic Information" "Enter schedule name:" "")
    if [[ $? -ne 0 ]]; then
        local save=$(get_yes_no "Save Changes?" "Do you want to save your changes?" "no")
        if [[ "$save" != "yes" ]]; then
            cleanup
            exit 0
        fi
        # If user wants to save, we'll continue but name might be empty - handle at save time
    fi
    
    local description=$(get_multiline_input "Basic Information" "Enter schedule description:" "")
    if [[ $? -ne 0 ]]; then
        local save=$(get_yes_no "Save Changes?" "Do you want to save your changes?" "no")
        if [[ "$save" != "yes" ]]; then
            cleanup
            exit 0
        fi
        # If user wants to save, we'll continue but description might be empty - handle at save time
    fi
    
    # Write header
    cat > "$TEMP_FILE" <<EOF
name: $name
description: >-
  $description

content:
EOF
    
    # Add content definitions
    add_content_definition "$TEMP_FILE"
    
    # Add sequences section
    cat >> "$TEMP_FILE" <<EOF

sequence:
EOF
    
    # Get available content keys for sequence items
    local content_keys=$(grep -E "^\s+- key:" "$TEMP_FILE" | sed 's/.*key: //' | tr '\n' ',' | sed 's/,$//')
    
    if [[ -z "$content_keys" ]]; then
        show_error "No content definitions found. Please add at least one content definition."
        cleanup
        exit 1
    fi
    
    # Add sequences
    add_sequence "$TEMP_FILE" "$content_keys"
    
    # Get available sequence keys for playout (all keys under "sequence:" section)
    local sequence_keys=$(awk '/^sequence:/{flag=1; next} /^[a-zA-Z]/{flag=0} flag && /^\s+- key:/{print $3}' "$TEMP_FILE" | tr '\n' ',' | sed 's/,$//')
    
    if [[ -z "$sequence_keys" ]]; then
        show_error "No sequences found. Please add at least one sequence."
        cleanup
        exit 1
    fi
    
    # Add playout
    cat >> "$TEMP_FILE" <<EOF

EOF
    add_playout "$TEMP_FILE" "$sequence_keys"
    
    # Show preview (first 30 lines)
    local preview=$(head -30 "$TEMP_FILE")
    local preview_json=$("$DIALOG" --title "Preview" \
        --message "Preview of your schedule YAML file (first 30 lines):\n\n\`\`\`\n$preview\n\`\`\`\n\nClick Continue to save, or Cancel to exit without saving." \
        --icon "info" \
        --button1text "Continue" \
        --button2text "Cancel" \
        --overlayicon "info" \
        --json 2>/dev/null)
    
    if ! check_button1 "$preview_json"; then
        local save=$(get_yes_no "Save Changes?" "Do you want to save your changes?" "no")
        if [[ "$save" != "yes" ]]; then
            cleanup
            exit 0
        fi
        # If user wants to save, continue
    fi
    
    # Get filename
    local default_filename="mn-olympics-$(date +%Y%m%d).yml"
    local filename=$(get_text_input "Save File" "Enter filename (will be saved to schedules/ directory):" "$default_filename")
    if [[ $? -ne 0 ]]; then
        local save=$(get_yes_no "Save Changes?" "Do you want to save your changes?" "no")
        if [[ "$save" != "yes" ]]; then
            cleanup
            exit 0
        fi
        # Try again to get filename
        filename=$(get_text_input "Save File" "Enter filename:" "$default_filename")
        if [[ $? -ne 0 ]]; then
            cleanup
            exit 0
        fi
    fi
    
    # Ensure filename ends with .yml
    if [[ ! "$filename" =~ \.yml$ ]]; then
        filename="${filename}.yml"
    fi
    
    # Check if file exists
    local output_path="$SCHEDULES_DIR/$filename"
    if [[ -f "$output_path" ]]; then
        local overwrite=$(get_yes_no "File Exists" "File already exists: $output_path\n\nOverwrite?" "no")
        if [[ "$overwrite" != "yes" ]]; then
            cleanup
            exit 0
        fi
    fi
    
    # Save file
    cp "$TEMP_FILE" "$output_path"
    
    # Success message
    show_info "Schedule YAML file created successfully!\n\nSaved to: $output_path"
    
    # Cleanup
    cleanup
}

# Run main function
main "$@"
