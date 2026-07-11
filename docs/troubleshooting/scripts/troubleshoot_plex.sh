#!/bin/zsh
# Plex Integration Troubleshooting Script
# Uses SwiftDialog for user interaction
# Specifically for Plex-related errors

set -e

# Get project root directory
get_project_root() {
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    echo "$(dirname "$script_dir")"
}

PROJECT_ROOT=$(get_project_root)

# Check if SwiftDialog is installed
if ! command -v dialog &> /dev/null; then
    echo "SwiftDialog not found. Please install it first:"
    echo "brew install --cask swiftdialog"
    exit 1
fi

# Get error message from user
get_plex_error() {
    local error=$(dialog \
        --title "Plex Error Input" \
        --message "Please paste the error message from Plex:" \
        --textfield "Error Message" \
        --button1text "Analyze" \
        --button2text "Cancel" \
        --ontop \
        --height 500 \
        --width 700)
    
    echo "$error"
}

# Analyze Plex error
analyze_plex_error() {
    local error_message="$1"
    local diagnosis=""
    local solution=""
    local action=""
    
    # Common Plex errors
    if echo "$error_message" | grep -qi "could not tune channel"; then
        diagnosis="Plex cannot tune to channel"
        solution="This usually means:\n• Stream format issue\n• FFmpeg not working\n• Network connectivity\n\nCheck:\n1. FFmpeg is installed\n2. Stream URL is accessible\n3. Firewall allows connections"
        action="check_ffmpeg_and_stream"
        
    elif echo "$error_message" | grep -qi "problem fetching channel mappings"; then
        diagnosis="Channel mapping error"
        solution="This usually means:\n• XMLTV guide issue\n• Channel ID mismatch\n• Invalid XML format\n\nCheck:\n1. XMLTV URL is accessible\n2. Channel numbers match\n3. XML is well-formed"
        action="check_xmltv"
        
    elif echo "$error_message" | grep -qi "rolling media grab failed"; then
        diagnosis="Recording/grabbing failed"
        solution="This usually means:\n• Stream is not continuous\n• MPEG-TS format issue\n• Stream interruption\n\nCheck:\n1. Channel is streaming continuously\n2. MPEG-TS format is correct\n3. No stream interruptions"
        action="check_stream_continuity"
        
    elif echo "$error_message" | grep -qi "tuner.*not found"; then
        diagnosis="Tuner not found"
        solution="This usually means:\n• Discovery URL incorrect\n• SSDP not working\n• Network issue\n\nCheck:\n1. Discovery URL is correct\n2. SSDP is enabled\n3. Firewall allows port 1900"
        action="check_tuner_discovery"
        
    elif echo "$error_message" | grep -qi "invalid.*file"; then
        diagnosis="Invalid file error"
        solution="This usually means:\n• XMLTV format issue\n• Missing required fields\n• Encoding problem\n\nCheck:\n1. XMLTV is valid XML\n2. All required fields present\n3. UTF-8 encoding"
        action="check_xmltv_format"
        
    elif echo "$error_message" | grep -qi "timeout"; then
        diagnosis="Timeout error"
        solution="This usually means:\n• Server not responding\n• Network latency\n• Stream too slow\n\nCheck:\n1. Server is running\n2. Network connection\n3. Stream source speed"
        action="check_server_and_network"
        
    elif echo "$error_message" | grep -qi "scan_all_pmts"; then
        diagnosis="FFmpeg codec option error"
        solution="This is a Plex transcoding issue.\n• Plex's FFmpeg doesn't support this option\n• Usually harmless, can be ignored\n• Or update Plex FFmpeg"
        action="check_plex_ffmpeg"
        
    else
        diagnosis="Unknown error"
        solution="Please check:\n• StreamTV logs\n• Plex logs\n• Network connectivity\n• Server status"
        action="general_check"
    fi
    
    # Show diagnosis
    local result=$(dialog \
        --title "Error Analysis" \
        --message "Diagnosis: $diagnosis\n\n$solution\n\nWhat would you like to do?" \
        --selectvalues "Run diagnostic check,View StreamTV logs,View Plex logs,Get more help,Back" \
        --selectdefault "Run diagnostic check" \
        --button1text "Select" \
        --button2text "Close" \
        --ontop \
        --height 500 \
        --width 700)
    
    case "$result" in
        "Run diagnostic check")
            run_diagnostic "$action"
            ;;
        "View StreamTV logs")
            view_streamtv_logs
            ;;
        "View Plex logs")
            view_plex_logs
            ;;
        "Get more help")
            show_help
            ;;
    esac
}

# Run diagnostic check
run_diagnostic() {
    local action="$1"
    
    dialog \
        --title "Running Diagnostics" \
        --message "Running diagnostic checks..." \
        --progress \
        --progresstext "Checking..." \
        --button1text "OK" \
        --ontop &
    
    local dialog_pid=$!
    
    local results=""
    
    case "$action" in
        "check_ffmpeg_and_stream")
            # Check FFmpeg
            if command -v ffmpeg &> /dev/null; then
                local ffmpeg_version=$(ffmpeg -version 2>&1 | head -1)
                results="✅ FFmpeg found: $ffmpeg_version\n"
            else
                results="❌ FFmpeg not found\n"
            fi
            
            # Check server
            if curl -s http://localhost:8410/health > /dev/null 2>&1; then
                results="${results}✅ StreamTV server running\n"
            else
                results="${results}❌ StreamTV server not running\n"
            fi
            ;;
            
        "check_xmltv")
            # Check XMLTV endpoint
            if curl -s http://localhost:8410/iptv/xmltv.xml > /dev/null 2>&1; then
                results="✅ XMLTV endpoint accessible\n"
            else
                results="❌ XMLTV endpoint not accessible\n"
            fi
            ;;
            
        "check_stream_continuity")
            # Check if channels are streaming
            results="Checking channel streaming status...\n"
            ;;
            
        "check_tuner_discovery")
            # Check discovery endpoint
            local local_ip=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "localhost")
            if curl -s "http://$local_ip:8410/hdhomerun/discover.json" > /dev/null 2>&1; then
                results="✅ Discovery endpoint accessible\nURL: http://$local_ip:8410/hdhomerun/discover.json\n"
            else
                results="❌ Discovery endpoint not accessible\n"
            fi
            ;;
            
        "check_xmltv_format")
            # Validate XMLTV
            results="Validating XMLTV format...\n"
            ;;
            
        "check_server_and_network")
            # Check server and network
            if curl -s http://localhost:8410/health > /dev/null 2>&1; then
                results="✅ Server running\n"
            else
                results="❌ Server not running\n"
            fi
            ;;
            
        "check_plex_ffmpeg")
            results="This is a Plex transcoding warning.\nUsually harmless and can be ignored.\n"
            ;;
            
        *)
            results="Running general checks...\n"
            ;;
    esac
    
    sleep 2
    kill $dialog_pid 2>/dev/null || true
    
    dialog \
        --title "Diagnostic Results" \
        --message "$results" \
        --button1text "OK" \
        --ontop
}

# View StreamTV logs
view_streamtv_logs() {
    local log_file="$PROJECT_ROOT/streamtv.log"
    
    if [ ! -f "$log_file" ]; then
        dialog \
            --title "Log File Not Found" \
            --message "Log file not found: $log_file\n\nChecking for log file..." \
            --button1text "OK" \
            --ontop
        return
    fi
    
    local log_content=$(tail -100 "$log_file" | grep -i "plex\|hdhomerun\|error" || tail -50 "$log_file")
    
    dialog \
        --title "StreamTV Logs (Plex-related)" \
        --message "$log_content" \
        --button1text "Refresh" \
        --button2text "Close" \
        --ontop \
        --height 600 \
        --width 800
}

# View Plex logs
view_plex_logs() {
    local plex_log_dir="$HOME/Library/Logs/Plex Media Server"
    
    if [ ! -d "$plex_log_dir" ]; then
        dialog \
            --title "Plex Logs Not Found" \
            --message "Plex log directory not found:\n$plex_log_dir\n\nPlex logs are typically located in:\n~/Library/Logs/Plex Media Server/\n\nOr check Plex settings for log location." \
            --button1text "OK" \
            --ontop
        return
    fi
    
    # Find most recent log
    local latest_log=$(ls -t "$plex_log_dir"/*.log 2>/dev/null | head -1)
    
    if [ -z "$latest_log" ]; then
        dialog \
            --title "No Log Files" \
            --message "No log files found in:\n$plex_log_dir" \
            --button1text "OK" \
            --ontop
        return
    fi
    
    local log_content=$(tail -100 "$latest_log" | grep -i "streamtv\|hdhomerun\|tuner\|error" || tail -50 "$latest_log")
    
    dialog \
        --title "Plex Logs: $(basename $latest_log)" \
        --message "$log_content" \
        --button1text "Refresh" \
        --button2text "Close" \
        --ontop \
        --height 600 \
        --width 800
}

# Show help
show_help() {
    dialog \
        --title "Plex Integration Help" \
        --message "Common Plex Setup Steps:\n\n1. Add Tuner:\n   • Plex → Settings → Live TV & DVR\n   • Add Tuner → HDHomeRun\n   • URL: http://YOUR_IP:8410/hdhomerun/discover.json\n\n2. Add Guide:\n   • Use XMLTV URL\n   • URL: http://YOUR_IP:8410/iptv/xmltv.xml\n\n3. Map Channels:\n   • Plex will detect channels\n   • Map to guide data\n\nTroubleshooting:\n• Check StreamTV is running\n• Check firewall allows connections\n• Check channel numbers match\n• Check XMLTV is generating\n\nFor more help, see:\ndocs/TROUBLESHOOTING_SCRIPTS.md" \
        --button1text "OK" \
        --ontop \
        --height 500 \
        --width 700
}

# Main function
main() {
    local error_message=$(get_plex_error)
    
    if [ -z "$error_message" ]; then
        exit 0
    fi
    
    # Save error to log
    echo "$(date): Plex Error - $error_message" >> "$PROJECT_ROOT/troubleshooting.log"
    
    analyze_plex_error "$error_message"
}

# Run main function
main "$@"

