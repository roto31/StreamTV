#!/usr/bin/env zsh
#
# Complete TailScale Uninstall Script for macOS
# This script removes ALL TailScale components from your system
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored messages
print_header() {
    echo ""
    echo "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo "${CYAN}$1${NC}"
    echo "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

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

# Function to check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_warning "Running as root. Some user-specific files may not be removed."
    fi
}

# Function to stop TailScale services
stop_services() {
    print_info "Stopping TailScale services..."
    
    # Stop TailScale daemon
    if launchctl list | grep -q "com.tailscale.tailscaled"; then
        sudo launchctl unload /Library/LaunchDaemons/com.tailscale.tailscaled.plist 2>/dev/null || true
        print_success "Stopped TailScale daemon"
    fi
    
    # Stop TailScale agent
    if launchctl list | grep -q "com.tailscale.tailscaled"; then
        launchctl unload ~/Library/LaunchAgents/com.tailscale.tailscaled.plist 2>/dev/null || true
        print_success "Stopped TailScale agent"
    fi
    
    # Kill any running TailScale processes
    local pids=$(pgrep -f tailscale 2>/dev/null || true)
    if [[ -n "$pids" ]]; then
        print_info "Killing TailScale processes..."
        sudo killall tailscale 2>/dev/null || true
        sudo killall tailscaled 2>/dev/null || true
        sleep 1
        # Force kill if still running
        sudo killall -9 tailscale 2>/dev/null || true
        sudo killall -9 tailscaled 2>/dev/null || true
        print_success "Terminated TailScale processes"
    else
        print_info "No running TailScale processes found"
    fi
}

# Function to remove application
remove_application() {
    print_info "Removing TailScale application..."
    
    local app_paths=(
        "/Applications/Tailscale.app"
        "/Applications/Utilities/Tailscale.app"
    )
    
    local found=false
    for app_path in "${app_paths[@]}"; do
        if [[ -d "$app_path" ]]; then
            sudo rm -rf "$app_path"
            print_success "Removed ${app_path}"
            found=true
        fi
    done
    
    if [[ "$found" == false ]]; then
        print_info "TailScale application not found in standard locations"
    fi
}

# Function to remove LaunchDaemons and LaunchAgents
remove_launch_agents() {
    print_info "Removing LaunchDaemons and LaunchAgents..."
    
    local plist_files=(
        "/Library/LaunchDaemons/com.tailscale.tailscaled.plist"
        "~/Library/LaunchAgents/com.tailscale.tailscaled.plist"
        "/Library/LaunchDaemons/com.tailscale.tailscaled.plist"
    )
    
    local found=false
    for plist in "${plist_files[@]}"; do
        # Expand ~ in path
        local expanded_plist="${plist/#\~/$HOME}"
        if [[ -f "$expanded_plist" ]]; then
            # Unload first if loaded
            if [[ "$plist" == *"LaunchDaemons"* ]]; then
                sudo launchctl unload "$expanded_plist" 2>/dev/null || true
                sudo rm -f "$expanded_plist"
            else
                launchctl unload "$expanded_plist" 2>/dev/null || true
                rm -f "$expanded_plist"
            fi
            print_success "Removed ${expanded_plist}"
            found=true
        fi
    done
    
    if [[ "$found" == false ]]; then
        print_info "No LaunchAgent/LaunchDaemon plist files found"
    fi
}

# Function to remove configuration files
remove_config_files() {
    print_info "Removing configuration files..."
    
    local config_paths=(
        "${HOME}/Library/Application Support/Tailscale"
        "${HOME}/Library/Preferences/com.tailscale.tailscaled.plist"
        "${HOME}/Library/Preferences/com.tailscale.tailscale.plist"
        "${HOME}/Library/Caches/com.tailscale.tailscale"
        "${HOME}/Library/Caches/com.tailscale.tailscaled"
        "/Library/Preferences/com.tailscale.tailscaled.plist"
        "/var/lib/tailscale"
        "/var/db/tailscale"
    )
    
    local found=false
    for config_path in "${config_paths[@]}"; do
        if [[ -e "$config_path" ]]; then
            if [[ "$config_path" == "/var/lib/tailscale" ]] || [[ "$config_path" == "/var/db/tailscale" ]]; then
                sudo rm -rf "$config_path"
            else
                rm -rf "$config_path"
            fi
            print_success "Removed ${config_path}"
            found=true
        fi
    done
    
    if [[ "$found" == false ]]; then
        print_info "No configuration files found"
    fi
}

# Function to remove binaries
remove_binaries() {
    print_info "Removing TailScale binaries..."
    
    local binary_paths=(
        "/usr/local/bin/tailscale"
        "/usr/local/bin/tailscaled"
        "/usr/bin/tailscale"
        "/usr/bin/tailscaled"
        "/opt/homebrew/bin/tailscale"
        "/opt/homebrew/bin/tailscaled"
        "/usr/local/sbin/tailscale"
        "/usr/local/sbin/tailscaled"
    )
    
    local found=false
    for binary_path in "${binary_paths[@]}"; do
        if [[ -f "$binary_path" ]]; then
            sudo rm -f "$binary_path"
            print_success "Removed ${binary_path}"
            found=true
        fi
    done
    
    if [[ "$found" == false ]]; then
        print_info "No binary files found in standard locations"
    fi
}

# Function to remove system extensions
remove_system_extensions() {
    print_info "Checking for TailScale system extensions..."
    
    # List system extensions
    local extensions=$(systemextensionsctl list 2>/dev/null | grep -i tailscale || true)
    
    if [[ -n "$extensions" ]]; then
        print_warning "TailScale system extensions found. Attempting to remove..."
        # Note: System extensions require special handling and may need to be disabled
        # in System Preferences > Security & Privacy > General
        print_info "You may need to disable TailScale extensions in:"
        print_info "System Preferences > Security & Privacy > General"
    else
        print_info "No TailScale system extensions found"
    fi
}

# Function to remove network interfaces
remove_network_interfaces() {
    print_info "Checking for TailScale network interfaces..."
    
    # Check for utun interfaces that might be TailScale
    local interfaces=$(ifconfig | grep -i "utun" | grep -i "tailscale" || true)
    
    if [[ -n "$interfaces" ]]; then
        print_warning "TailScale network interfaces may still exist"
        print_info "These will be removed automatically on reboot"
    else
        print_info "No TailScale network interfaces detected"
    fi
}

# Function to remove logs
remove_logs() {
    print_info "Removing log files..."
    
    local log_paths=(
        "${HOME}/Library/Logs/Tailscale"
        "/var/log/tailscale"
        "/Library/Logs/Tailscale"
    )
    
    local found=false
    for log_path in "${log_paths[@]}"; do
        if [[ -e "$log_path" ]]; then
            if [[ "$log_path" == "/var/log/tailscale" ]] || [[ "$log_path" == "/Library/Logs/Tailscale" ]]; then
                sudo rm -rf "$log_path"
            else
                rm -rf "$log_path"
            fi
            print_success "Removed ${log_path}"
            found=true
        fi
    done
    
    if [[ "$found" == false ]]; then
        print_info "No log files found"
    fi
}

# Function to remove Homebrew installation (if applicable)
remove_homebrew() {
    print_info "Checking for Homebrew installation..."
    
    if command -v brew &> /dev/null; then
        if brew list --formula | grep -q tailscale; then
            print_info "Found TailScale installed via Homebrew"
            read -q "?Remove TailScale via Homebrew? (y/N): " && echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                brew uninstall tailscale 2>/dev/null || true
                print_success "Removed TailScale via Homebrew"
            fi
        else
            print_info "TailScale not installed via Homebrew"
        fi
    else
        print_info "Homebrew not found"
    fi
}

# Function to verify removal
verify_removal() {
    print_info "Verifying removal..."
    
    local remaining=()
    
    # Check for application
    if [[ -d "/Applications/Tailscale.app" ]]; then
        remaining+=("/Applications/Tailscale.app")
    fi
    
    # Check for processes
    if pgrep -f tailscale &> /dev/null; then
        remaining+=("Running processes")
    fi
    
    # Check for binaries
    if command -v tailscale &> /dev/null; then
        remaining+=("tailscale binary")
    fi
    
    if [[ ${#remaining[@]} -eq 0 ]]; then
        print_success "Verification complete - no TailScale components found"
        return 0
    else
        print_warning "Some components may still remain:"
        for item in "${remaining[@]}"; do
            print_warning "  - ${item}"
        done
        return 1
    fi
}

# Main uninstall function
main() {
    print_header "TailScale Complete Uninstall Script for macOS"
    
    print_warning "This script will completely remove TailScale from your system."
    print_warning "This includes:"
    echo "  • Application files"
    echo "  • Configuration files"
    echo "  • LaunchDaemons and LaunchAgents"
    echo "  • Binary files"
    echo "  • Log files"
    echo "  • All user data"
    echo ""
    read -q "?Are you sure you want to continue? (y/N): " && echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Uninstallation cancelled"
        exit 0
    fi
    
    echo ""
    
    # Check if running as root
    check_root
    
    # Step 1: Stop services
    print_header "Step 1: Stopping TailScale Services"
    stop_services
    
    # Step 2: Remove application
    print_header "Step 2: Removing Application"
    remove_application
    
    # Step 3: Remove LaunchAgents/Daemons
    print_header "Step 3: Removing LaunchAgents and LaunchDaemons"
    remove_launch_agents
    
    # Step 4: Remove configuration files
    print_header "Step 4: Removing Configuration Files"
    remove_config_files
    
    # Step 5: Remove binaries
    print_header "Step 5: Removing Binary Files"
    remove_binaries
    
    # Step 6: Remove system extensions
    print_header "Step 6: Checking System Extensions"
    remove_system_extensions
    
    # Step 7: Check network interfaces
    print_header "Step 7: Checking Network Interfaces"
    remove_network_interfaces
    
    # Step 8: Remove logs
    print_header "Step 8: Removing Log Files"
    remove_logs
    
    # Step 9: Remove Homebrew installation
    print_header "Step 9: Checking Homebrew Installation"
    remove_homebrew
    
    # Step 10: Verify removal
    print_header "Step 10: Verifying Removal"
    verify_removal
    
    # Uninstallation complete
    print_header "Uninstallation Complete!"
    
    print_success "TailScale has been uninstalled from your system"
    echo ""
    print_info "Note: If you had TailScale system extensions, you may need to:"
    print_info "  1. Go to System Preferences > Security & Privacy > General"
    print_info "  2. Remove any TailScale-related entries"
    print_info "  3. Restart your computer to fully clear network interfaces"
    echo ""
    print_warning "A system restart is recommended to ensure all components are removed"
    echo ""
}

# Run main function
main "$@"

