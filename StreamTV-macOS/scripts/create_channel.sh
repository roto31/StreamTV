#!/usr/bin/env zsh
#
# Channel creation script for StreamTV
# This zsh script provides an interactive way to create channels via the API
#
# Usage:
#   ./scripts/create_channel.sh
#   ./scripts/create_channel.sh --year 1980
#   ./scripts/create_channel.sh --number 1 --name "My Channel"
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
API_BASE_URL="${STREAMTV_API_URL:-http://localhost:8410}"
API_ENDPOINT="${API_BASE_URL}/api/channels"
ACCESS_TOKEN="${STREAMTV_ACCESS_TOKEN:-}"

# Function to print colored messages
print_success() {
    echo "${GREEN}✓${NC} $1"
}

print_error() {
    echo "${RED}✗${NC} $1" >&2
}

print_info() {
    echo "${BLUE}ℹ${NC} $1"
}

print_warning() {
    echo "${YELLOW}⚠${NC} $1"
}

# Function to check if API server is running
check_api_server() {
    print_info "Checking if API server is running at ${API_BASE_URL}..."
    
    if curl -s -f "${API_BASE_URL}/health" > /dev/null 2>&1; then
        print_success "API server is running"
        return 0
    else
        print_error "API server is not accessible at ${API_BASE_URL}"
        print_info "Make sure StreamTV is running: python3 -m streamtv.main"
        return 1
    fi
}

# Function to create channel via API
create_channel_api() {
    local number=$1
    local name=$2
    local group=${3:-"StreamTV"}
    local enabled=${4:-true}
    local logo_path=${5:-""}
    
    local json_payload=$(cat <<EOF
{
  "number": "${number}",
  "name": "${name}",
  "group": "${group}",
  "enabled": ${enabled}
EOF
)
    
    # Add logo_path if provided
    if [[ -n "$logo_path" ]]; then
        json_payload="${json_payload},\n  \"logo_path\": \"${logo_path}\""
    fi
    
    json_payload="${json_payload}\n}"
    
    # Build curl command
    local curl_cmd="curl -s -X POST '${API_ENDPOINT}' \
        -H 'Content-Type: application/json' \
        -d '$(echo -e "$json_payload")'"
    
    # Add access token if provided
    if [[ -n "$ACCESS_TOKEN" ]]; then
        curl_cmd="${curl_cmd}?access_token=${ACCESS_TOKEN}"
    fi
    
    # Execute and capture response
    local response=$(eval "$curl_cmd")
    local exit_code=$?
    
    if [[ $exit_code -ne 0 ]]; then
        print_error "Failed to create channel (curl error)"
        return 1
    fi
    
    # Check if response contains error
    if echo "$response" | grep -q '"detail"'; then
        local error_msg=$(echo "$response" | grep -o '"detail":"[^"]*"' | cut -d'"' -f4)
        print_error "Failed to create channel: ${error_msg}"
        return 1
    fi
    
    # Extract channel ID if successful
    local channel_id=$(echo "$response" | grep -o '"id":[0-9]*' | cut -d':' -f2)
    if [[ -n "$channel_id" ]]; then
        print_success "Created channel: ${number} - ${name} (ID: ${channel_id})"
        return 0
    else
        print_warning "Channel may have been created, but couldn't parse response"
        echo "$response"
        return 0
    fi
}

# Function to create default channels
create_default_channels() {
    print_info "Creating default Winter Olympics channels for StreamTV..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    local channels=(
        "1980:1980 Lake Placid Winter Olympics:Winter Olympics"
        "1984:1984 Sarajevo Winter Olympics:Winter Olympics"
        "1988:1988 Calgary Winter Olympics:Winter Olympics"
        "1992:1992 Albertville Winter Olympics:Winter Olympics"
        "1994:1994 Lillehammer Winter Olympics:Winter Olympics"
    )
    
    local created=0
    local skipped=0
    
    for channel_data in "${channels[@]}"; do
        IFS=':' read -r number name group <<< "$channel_data"
        if create_channel_api "$number" "$name" "$group"; then
            ((created++))
        else
            ((skipped++))
        fi
    done
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    print_success "Created ${created} channel(s)"
    if [[ $skipped -gt 0 ]]; then
        print_warning "Skipped ${skipped} channel(s) (may already exist)"
    fi
}

# Function for interactive channel creation
interactive_create() {
    print_info "Interactive channel creation"
    echo ""
    
    # Get channel number
    echo -n "Channel number (e.g., 1, 1980): "
    read channel_number
    if [[ -z "$channel_number" ]]; then
        print_error "Channel number is required"
        return 1
    fi
    
    # Get channel name
    echo -n "Channel name: "
    read channel_name
    if [[ -z "$channel_name" ]]; then
        print_error "Channel name is required"
        return 1
    fi
    
    # Get channel group (optional)
    echo -n "Channel group [StreamTV]: "
    read channel_group
    channel_group=${channel_group:-"StreamTV"}
    
    # Get enabled status (optional)
    echo -n "Enable channel? [Y/n]: "
    read enabled_input
    local enabled="true"
    if [[ "$enabled_input" =~ ^[Nn] ]]; then
        enabled="false"
    fi
    
    # Get logo path (optional)
    echo -n "Logo path (optional): "
    read logo_path
    
    # Create channel
    echo ""
    create_channel_api "$channel_number" "$channel_name" "$channel_group" "$enabled" "$logo_path"
}

# Function to show usage
show_usage() {
    local script_name="create_channel.sh"
    cat <<EOF
    ${BLUE}Channel Creation Script for StreamTV${NC}

Usage:
  ./scripts/${script_name} [OPTIONS]

Options:
  --year YEAR              Create channel for specific year (example: 1980, 1984, 1988)
  --number NUMBER          Channel number
  --name NAME              Channel name
  --group GROUP            Channel group (default: "StreamTV")
  --logo PATH              Path to channel logo
  --disabled               Create channel as disabled
  --interactive, -i        Interactive mode
  --api-url URL            API base URL (default: http://localhost:8410)
  --token TOKEN            Access token for authenticated API
  --help, -h               Show this help message

Examples:
  # Create all default channels
  ${script_name}

  # Create channel for specific year
  ${script_name} --year 1980

  # Create custom channel
  ${script_name} --number "1" --name "My Channel" --group "Entertainment"

  # Interactive mode
  ${script_name} --interactive

Environment Variables:
  STREAMTV_API_URL         API base URL (overrides --api-url)
  STREAMTV_ACCESS_TOKEN    Access token (overrides --token)

EOF
}

# Main function
main() {
    # Parse arguments
    local year=""
    local number=""
    local name=""
    local group="StreamTV"
    local logo_path=""
    local enabled="true"
    local interactive=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --year)
                year="$2"
                shift 2
                ;;
            --number)
                number="$2"
                shift 2
                ;;
            --name)
                name="$2"
                shift 2
                ;;
            --group)
                group="$2"
                shift 2
                ;;
            --logo)
                logo_path="$2"
                shift 2
                ;;
            --disabled)
                enabled="false"
                shift
                ;;
            --interactive|-i)
                interactive=true
                shift
                ;;
            --api-url)
                API_BASE_URL="$2"
                API_ENDPOINT="${API_BASE_URL}/api/channels"
                shift 2
                ;;
            --token)
                ACCESS_TOKEN="$2"
                shift 2
                ;;
            --help|-h)
                show_usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Check API server
    if ! check_api_server; then
        print_info "Falling back to Python script method..."
        # Fallback to Python script if API is not available
        if command -v python3 > /dev/null 2>&1; then
            if [[ -f "scripts/create_channel.py" ]]; then
                python3 scripts/create_channel.py "$@"
                exit $?
            fi
        fi
        exit 1
    fi
    
    # Handle different modes
    if [[ "$interactive" == true ]]; then
        interactive_create
    elif [[ -n "$year" ]]; then
        # Create channel for specific year
        case "$year" in
            *)
                create_channel_api "$year" "StreamTV Channel ${year}" "StreamTV" "$enabled" "$logo_path"
                ;;
                ;;
        esac
    elif [[ -n "$number" && -n "$name" ]]; then
        # Create custom channel
        create_channel_api "$number" "$name" "$group" "$enabled" "$logo_path"
    else
        # Create default channels
        create_default_channels
    fi
}

# Run main function
main "$@"

