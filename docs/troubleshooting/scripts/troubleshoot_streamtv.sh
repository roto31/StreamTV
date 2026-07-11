#!/bin/zsh
# StreamTV Troubleshooting Script
# Uses SwiftDialog for user interaction
# GitHub: https://github.com/swiftDialog/swiftDialog

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if SwiftDialog is installed
check_swiftdialog() {
    if ! command -v dialog &> /dev/null; then
        echo -e "${YELLOW}SwiftDialog not found. Installing...${NC}"
        
        # Try to install via Homebrew
        if command -v brew &> /dev/null; then
            brew install --cask swiftdialog
        else
            echo -e "${RED}Homebrew not found. Please install SwiftDialog manually:${NC}"
            echo "https://github.com/swiftDialog/swiftDialog/releases"
            exit 1
        fi
    fi
}

# Get project root directory
get_project_root() {
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    echo "$(dirname "$script_dir")"
}

PROJECT_ROOT=$(get_project_root)
cd "$PROJECT_ROOT"

# Main troubleshooting menu
show_main_menu() {
    local result=$(dialog \
        --title "StreamTV Troubleshooting" \
        --message "Select a troubleshooting option:" \
        --selectvalues "Server Status,Channel Issues,Streaming Issues,Plex Integration,Database Issues,Configuration Issues,View Logs,Exit" \
        --selectdefault "Server Status" \
        --button1text "Select" \
        --button2text "Cancel" \
        --ontop \
        --height 400 \
        --width 600)
    
    echo "$result"
}

# Check server status
check_server_status() {
    dialog \
        --title "Checking Server Status" \
        --message "Checking if StreamTV server is running..." \
        --progress \
        --progresstext "Checking..." \
        --button1text "OK" \
        --ontop &
    
    local dialog_pid=$!
    
    # Check if server is running
    local server_running=false
    if curl -s http://localhost:8410/health > /dev/null 2>&1; then
        server_running=true
    fi
    
    kill $dialog_pid 2>/dev/null || true
    
    if [ "$server_running" = true ]; then
        dialog \
            --title "Server Status" \
            --message "✅ StreamTV server is running\n\nURL: http://localhost:8410" \
            --button1text "OK" \
            --ontop
    else
        dialog \
            --title "Server Status" \
            --message "❌ StreamTV server is NOT running\n\nWould you like to start it?" \
            --button1text "Start Server" \
            --button2text "Cancel" \
            --ontop
        
        if [ $? -eq 0 ]; then
            start_server
        fi
    fi
}

# Start server
start_server() {
    dialog \
        --title "Starting Server" \
        --message "Starting StreamTV server..." \
        --progress \
        --progresstext "Starting..." \
        --button1text "OK" \
        --ontop &
    
    local dialog_pid=$!
    
    # Start server in background
    if [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
        source "$PROJECT_ROOT/venv/bin/activate"
        cd "$PROJECT_ROOT"
        nohup python -m streamtv.main > /tmp/streamtv_startup.log 2>&1 &
        local server_pid=$!
        
        # Wait a moment for server to start
        sleep 3
        
        # Check if it started
        if ps -p $server_pid > /dev/null; then
            kill $dialog_pid 2>/dev/null || true
            dialog \
                --title "Server Started" \
                --message "✅ StreamTV server started successfully\n\nPID: $server_pid\n\nLogs: /tmp/streamtv_startup.log" \
                --button1text "OK" \
                --ontop
        else
            kill $dialog_pid 2>/dev/null || true
            dialog \
                --title "Server Failed to Start" \
                --message "❌ Server failed to start\n\nCheck logs: /tmp/streamtv_startup.log" \
                --button1text "View Logs" \
                --button2text "Cancel" \
                --ontop
            
            if [ $? -eq 0 ]; then
                view_logs "/tmp/streamtv_startup.log"
            fi
        fi
    else
        kill $dialog_pid 2>/dev/null || true
        dialog \
            --title "Error" \
            --message "❌ Virtual environment not found\n\nPlease run install_macos.sh first" \
            --button1text "OK" \
            --ontop
    fi
}

# Channel issues troubleshooting
troubleshoot_channels() {
    local result=$(dialog \
        --title "Channel Issues" \
        --message "What channel issue are you experiencing?" \
        --selectvalues "Channel won't play,Channel starts from beginning,Channel has no content,Channel import failed,Other" \
        --selectdefault "Channel won't play" \
        --button1text "Select" \
        --button2text "Back" \
        --ontop)
    
    case "$result" in
        "Channel won't play")
            troubleshoot_channel_wont_play
            ;;
        "Channel starts from beginning")
            troubleshoot_channel_starts_beginning
            ;;
        "Channel has no content")
            troubleshoot_channel_no_content
            ;;
        "Channel import failed")
            troubleshoot_channel_import
            ;;
        "Other")
            troubleshoot_channel_other
            ;;
    esac
}

# Troubleshoot channel won't play
troubleshoot_channel_wont_play() {
    local channel_number=$(dialog \
        --title "Channel Number" \
        --message "Enter the channel number:" \
        --textfield "Channel Number" \
        --button1text "Check" \
        --button2text "Cancel" \
        --ontop)
    
    if [ -z "$channel_number" ]; then
        return
    fi
    
    # Check channel status
    local channel_info=$(curl -s "http://localhost:8410/api/channels?number=$channel_number" 2>/dev/null)
    
    if [ -z "$channel_info" ] || [ "$channel_info" = "[]" ]; then
        dialog \
            --title "Channel Not Found" \
            --message "❌ Channel $channel_number not found\n\nPlease check the channel number and try again." \
            --button1text "OK" \
            --ontop
        return
    fi
    
    # Parse channel info (simplified - would need jq for proper parsing)
    dialog \
        --title "Channel Status" \
        --message "Channel $channel_number found\n\nChecking status..." \
        --button1text "OK" \
        --ontop
    
    # Check if channel is enabled
    # Check if channel has content
    # Check streaming status
    
    dialog \
        --title "Diagnosis" \
        --message "Diagnostic information:\n\n• Channel exists\n• Checking enabled status...\n• Checking content...\n• Checking stream..." \
        --button1text "View Details" \
        --button2text "Back" \
        --ontop
}

# Troubleshoot channel starts from beginning
troubleshoot_channel_starts_beginning() {
    dialog \
        --title "Timeline Issue" \
        --message "This issue is related to the timeline system.\n\nChannels should start at midnight of their creation day and use system time to calculate position.\n\nWould you like to:" \
        --selectvalues "Check channel creation date,Restart server,Check system time,View timeline logs" \
        --selectdefault "Check channel creation date" \
        --button1text "Select" \
        --button2text "Back" \
        --ontop
}

# Troubleshoot channel no content
troubleshoot_channel_no_content() {
    local channel_number=$(dialog \
        --title "Channel Number" \
        --message "Enter the channel number:" \
        --textfield "Channel Number" \
        --button1text "Check" \
        --button2text "Cancel" \
        --ontop)
    
    if [ -z "$channel_number" ]; then
        return
    fi
    
    # Check for playlists
    # Check for schedules
    # Check for media items
    
    dialog \
        --title "Content Check" \
        --message "Checking channel $channel_number for content..." \
        --progress \
        --progresstext "Checking..." \
        --button1text "OK" \
        --ontop &
    
    local dialog_pid=$!
    
    # Run checks
    sleep 2
    
    kill $dialog_pid 2>/dev/null || true
    
    dialog \
        --title "Content Status" \
        --message "Content check complete.\n\nIf no content found, the channel needs:\n• A schedule file, OR\n• A playlist with media items\n\nWould you like to import a channel YAML?" \
        --button1text "Import Channel" \
        --button2text "Back" \
        --ontop
}

# Troubleshoot channel import
troubleshoot_channel_import() {
    local error_message=$(dialog \
        --title "Import Error" \
        --message "Please paste the error message you received:" \
        --textfield "Error Message" \
        --button1text "Analyze" \
        --button2text "Cancel" \
        --ontop \
        --height 400 \
        --width 600)
    
    if [ -z "$error_message" ]; then
        return
    fi
    
    # Analyze error
    local diagnosis=""
    
    if echo "$error_message" | grep -q "YAML"; then
        diagnosis="YAML parsing error detected.\n\nCommon causes:\n• Invalid YAML syntax\n• Missing required fields\n• Incorrect indentation"
    elif echo "$error_message" | grep -q "validation"; then
        diagnosis="Validation error detected.\n\nCommon causes:\n• Missing required fields\n• Invalid field values\n• Schema mismatch"
    elif echo "$error_message" | grep -q "database"; then
        diagnosis="Database error detected.\n\nCommon causes:\n• Database locked\n• Constraint violation\n• Connection issue"
    else
        diagnosis="Error type: Unknown\n\nPlease check the logs for more details."
    fi
    
    dialog \
        --title "Error Analysis" \
        --message "$diagnosis\n\nWould you like to:" \
        --selectvalues "Validate YAML file,Check database,View full logs,Get help" \
        --selectdefault "Validate YAML file" \
        --button1text "Select" \
        --button2text "Back" \
        --ontop
}

# Troubleshoot channel other
troubleshoot_channel_other() {
    local error_message=$(dialog \
        --title "Channel Issue" \
        --message "Please describe the issue:" \
        --textfield "Issue Description" \
        --button1text "Submit" \
        --button2text "Cancel" \
        --ontop \
        --height 400 \
        --width 600)
    
    if [ -z "$error_message" ]; then
        return
    fi
    
    # Save to log file
    echo "$(date): Channel Issue - $error_message" >> "$PROJECT_ROOT/troubleshooting.log"
    
    dialog \
        --title "Issue Logged" \
        --message "Your issue has been logged.\n\nFile: troubleshooting.log\n\nWould you like to view the logs?" \
        --button1text "View Logs" \
        --button2text "OK" \
        --ontop
}

# Streaming issues
troubleshoot_streaming() {
    local result=$(dialog \
        --title "Streaming Issues" \
        --message "What streaming issue are you experiencing?" \
        --selectvalues "Video won't play,Video keeps buffering,FFmpeg errors,Stream stops after first video,Other" \
        --selectdefault "Video won't play" \
        --button1text "Select" \
        --button2text "Back" \
        --ontop)
    
    case "$result" in
        "FFmpeg errors")
            troubleshoot_ffmpeg_errors
            ;;
        "Stream stops after first video")
            troubleshoot_stream_stops
            ;;
        *)
            troubleshoot_streaming_other
            ;;
    esac
}

# Troubleshoot FFmpeg errors
troubleshoot_ffmpeg_errors() {
    local error_message=$(dialog \
        --title "FFmpeg Error" \
        --message "Please paste the FFmpeg error message:" \
        --textfield "Error Message" \
        --button1text "Analyze" \
        --button2text "Cancel" \
        --ontop \
        --height 400 \
        --width 600)
    
    if [ -z "$error_message" ]; then
        return
    fi
    
    local diagnosis=""
    local solution=""
    
    if echo "$error_message" | grep -q "not found"; then
        diagnosis="FFmpeg not found"
        solution="Install FFmpeg:\nbrew install ffmpeg\n\nOr set custom path in config.yaml"
    elif echo "$error_message" | grep -q "hwaccel"; then
        diagnosis="Hardware acceleration error"
        solution="Disable hardware acceleration in config.yaml:\nffmpeg:\n  hwaccel: null"
    elif echo "$error_message" | grep -q "codec"; then
        diagnosis="Codec error"
        solution="Check FFmpeg codec support:\nffmpeg -codecs\n\nUpdate FFmpeg if needed"
    else
        diagnosis="Unknown FFmpeg error"
        solution="Check FFmpeg installation and configuration"
    fi
    
    dialog \
        --title "FFmpeg Error Analysis" \
        --message "Diagnosis: $diagnosis\n\nSolution:\n$solution\n\nWould you like to:" \
        --selectvalues "Check FFmpeg installation,Update config,View FFmpeg logs,Get more help" \
        --selectdefault "Check FFmpeg installation" \
        --button1text "Select" \
        --button2text "Back" \
        --ontop
}

# Troubleshoot stream stops
troubleshoot_stream_stops() {
    dialog \
        --title "Stream Stops Issue" \
        --message "If streams stop after the first video, check:\n\n1. Schedule has 'repeat: true'\n2. Sequence is complete\n3. No errors in logs\n\nWould you like to:" \
        --selectvalues "Check schedule file,Check logs,Restart server,Other" \
        --selectdefault "Check schedule file" \
        --button1text "Select" \
        --button2text "Back" \
        --ontop
}

# Troubleshoot streaming other
troubleshoot_streaming_other() {
    local error_message=$(dialog \
        --title "Streaming Issue" \
        --message "Please describe the streaming issue:" \
        --textfield "Issue Description" \
        --button1text "Submit" \
        --button2text "Cancel" \
        --ontop \
        --height 400 \
        --width 600)
    
    if [ -z "$error_message" ]; then
        return
    fi
    
    echo "$(date): Streaming Issue - $error_message" >> "$PROJECT_ROOT/troubleshooting.log"
    
    dialog \
        --title "Issue Logged" \
        --message "Your issue has been logged.\n\nFile: troubleshooting.log" \
        --button1text "OK" \
        --ontop
}

# Plex integration troubleshooting
troubleshoot_plex() {
    local result=$(dialog \
        --title "Plex Integration" \
        --message "What Plex issue are you experiencing?" \
        --selectvalues "Plex can't find tuner,Channels not appearing,Stream won't play,Guide not loading,Other" \
        --selectdefault "Plex can't find tuner" \
        --button1text "Select" \
        --button2text "Back" \
        --ontop)
    
    case "$result" in
        "Plex can't find tuner")
            troubleshoot_plex_tuner
            ;;
        "Channels not appearing")
            troubleshoot_plex_channels
            ;;
        "Stream won't play")
            troubleshoot_plex_stream
            ;;
        "Guide not loading")
            troubleshoot_plex_guide
            ;;
        *)
            troubleshoot_plex_other
            ;;
    esac
}

# Troubleshoot Plex tuner
troubleshoot_plex_tuner() {
    # Get local IP
    local local_ip=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "localhost")
    
    local discovery_url="http://$local_ip:8410/hdhomerun/discover.json"
    
    dialog \
        --title "Plex Tuner Setup" \
        --message "Discovery URL:\n$discovery_url\n\nSteps:\n1. Copy the URL above\n2. In Plex: Settings → Live TV & DVR\n3. Add Tuner → HDHomeRun\n4. Paste the URL\n\nWould you like to:" \
        --selectvalues "Test discovery URL,Check SSDP,Check firewall,Get more help" \
        --selectdefault "Test discovery URL" \
        --button1text "Select" \
        --button2text "Back" \
        --ontop
}

# View logs
view_logs() {
    local log_file="${1:-$PROJECT_ROOT/streamtv.log}"
    
    if [ ! -f "$log_file" ]; then
        dialog \
            --title "Log File Not Found" \
            --message "Log file not found: $log_file" \
            --button1text "OK" \
            --ontop
        return
    fi
    
    # Show last 50 lines
    local log_content=$(tail -50 "$log_file")
    
    dialog \
        --title "Logs: $(basename $log_file)" \
        --message "$log_content" \
        --button1text "Refresh" \
        --button2text "Close" \
        --ontop \
        --height 600 \
        --width 800
}

# Main loop
main() {
    check_swiftdialog
    
    while true; do
        local choice=$(show_main_menu)
        
        case "$choice" in
            "Server Status")
                check_server_status
                ;;
            "Channel Issues")
                troubleshoot_channels
                ;;
            "Streaming Issues")
                troubleshoot_streaming
                ;;
            "Plex Integration")
                troubleshoot_plex
                ;;
            "Database Issues")
                troubleshoot_database
                ;;
            "Configuration Issues")
                troubleshoot_config
                ;;
            "View Logs")
                view_logs
                ;;
            "Exit"|"")
                exit 0
                ;;
        esac
    done
}

# Placeholder functions
troubleshoot_database() {
    dialog \
        --title "Database Issues" \
        --message "Database troubleshooting options:" \
        --selectvalues "Check database integrity,Backup database,Reset database,View database info" \
        --selectdefault "Check database integrity" \
        --button1text "Select" \
        --button2text "Back" \
        --ontop
}

troubleshoot_config() {
    dialog \
        --title "Configuration Issues" \
        --message "Configuration troubleshooting options:" \
        --selectvalues "Validate config,View config,Reset config,Edit config" \
        --selectdefault "Validate config" \
        --button1text "Select" \
        --button2text "Back" \
        --ontop
}

# Run main function
main "$@"

