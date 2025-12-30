#!/usr/bin/env zsh
#
# Complete Installation Script for StreamTV
# macOS-specific installation with original source dependencies
#
# This script:
# 1. Checks and installs Python 3.10+ from python.org
# 2. Installs FFmpeg from official source
# 3. Sets up virtual environment
# 4. Installs all Python dependencies
# 5. Configures the platform
# 6. Creates default channels
# 7. Optionally starts the server
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="${HOME}/.streamtv"
PYTHON_MIN_VERSION="3.10"
FFMPEG_VERSION="6.1.1"
VENV_DIR="${INSTALL_DIR}/venv"
APP_DIR="$(cd "$(dirname "$0")" && pwd)"

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

# Function to check if command exists
command_exists() {
    command -v "$1" > /dev/null 2>&1
}

# Function to check Python version
check_python_version() {
    if command_exists python3; then
        local version=$(python3 --version 2>&1 | awk '{print $2}')
        local major=$(echo $version | cut -d. -f1)
        local minor=$(echo $version | cut -d. -f2)
        local min_major=$(echo $PYTHON_MIN_VERSION | cut -d. -f1)
        local min_minor=$(echo $PYTHON_MIN_VERSION | cut -d. -f2)
        
        if [[ $major -gt $min_major ]] || [[ $major -eq $min_major && $minor -ge $min_minor ]]; then
            print_success "Python ${version} found"
            return 0
        fi
    fi
    return 1
}

# Function to install Python from python.org
install_python() {
    print_info "Python 3.10+ not found. Installing from python.org..."
    
    local python_url="https://www.python.org/ftp/python/3.12.7/python-3.12.7-macos11.pkg"
    local pkg_file="/tmp/python-installer.pkg"
    
    print_info "Downloading Python installer..."
    if curl -L -o "$pkg_file" "$python_url"; then
        print_success "Downloaded Python installer"
        print_info "Opening installer. Please follow the installation wizard."
        print_warning "After installation, run this script again."
        open "$pkg_file"
        exit 0
    else
        print_error "Failed to download Python installer"
        print_info "Please download and install Python 3.10+ from https://www.python.org/downloads/"
        exit 1
    fi
}

# Function to check FFmpeg
check_ffmpeg() {
    if command_exists ffmpeg; then
        local version=$(ffmpeg -version 2>&1 | head -n1 | grep -oE 'version [0-9]+\.[0-9]+\.[0-9]+' | cut -d' ' -f2)
        print_success "FFmpeg ${version} found"
        return 0
    fi
    return 1
}

# Function to install FFmpeg from official source
install_ffmpeg() {
    print_info "FFmpeg not found. Installing from official source..."
    
    # Check architecture
    local arch=$(uname -m)
    local ffmpeg_url=""
    local ffmpeg_file=""
    
    if [[ "$arch" == "arm64" ]]; then
        # For Apple Silicon, try static build from evermeet.cx
        ffmpeg_url="https://evermeet.cx/ffmpeg/ffmpeg-${FFMPEG_VERSION}.zip"
        ffmpeg_file="/tmp/ffmpeg.zip"
        
        print_info "Downloading FFmpeg for Apple Silicon from official source..."
        if curl -L -f -o "$ffmpeg_file" "$ffmpeg_url" 2>/dev/null; then
            print_success "Downloaded FFmpeg"
            unzip -q -o "$ffmpeg_file" -d /tmp/ 2>/dev/null
            if [[ -f /tmp/ffmpeg ]]; then
                # Try to install to /usr/local/bin (may require sudo)
                if sudo mv /tmp/ffmpeg /usr/local/bin/ffmpeg 2>/dev/null; then
                    sudo chmod +x /usr/local/bin/ffmpeg
                    rm -f "$ffmpeg_file"
                    print_success "FFmpeg installed to /usr/local/bin/ffmpeg"
                else
                    # Try without sudo to user's local bin
                    mkdir -p "${HOME}/.local/bin"
                    mv /tmp/ffmpeg "${HOME}/.local/bin/ffmpeg"
                    chmod +x "${HOME}/.local/bin/ffmpeg"
                    rm -f "$ffmpeg_file"
                    print_success "FFmpeg installed to ${HOME}/.local/bin/ffmpeg"
                    print_warning "Add ${HOME}/.local/bin to your PATH"
                    export PATH="${HOME}/.local/bin:${PATH}"
                fi
            else
                print_error "FFmpeg binary not found in downloaded archive"
                rm -f "$ffmpeg_file"
                # Fallback to Homebrew
                if command_exists brew; then
                    print_info "Attempting Homebrew as fallback..."
                    brew install ffmpeg
                    print_success "FFmpeg installed via Homebrew"
                else
                    print_error "Please install FFmpeg manually from https://ffmpeg.org/download.html"
                    exit 1
                fi
            fi
        else
            print_warning "Failed to download FFmpeg from primary source"
            # Fallback to Homebrew
            if command_exists brew; then
                print_info "Attempting Homebrew as fallback..."
                brew install ffmpeg
                print_success "FFmpeg installed via Homebrew"
            else
                print_error "Please install FFmpeg manually from https://ffmpeg.org/download.html"
                exit 1
            fi
        fi
    else
        # For Intel Macs, try Homebrew first (most reliable)
        if command_exists brew; then
            print_info "Installing FFmpeg via Homebrew (fallback for Intel Macs)..."
            brew install ffmpeg
            print_success "FFmpeg installed via Homebrew"
        else
            print_error "Please install FFmpeg manually from https://ffmpeg.org/download.html"
            print_info "Or install Homebrew: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
            exit 1
        fi
    fi
}

# Function to create virtual environment
setup_venv() {
    print_info "Setting up virtual environment..."
    
    if [[ -d "$VENV_DIR" ]]; then
        print_warning "Virtual environment already exists at ${VENV_DIR}"
        read -q "?Do you want to recreate it? (y/N): " && echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$VENV_DIR"
        else
            print_info "Using existing virtual environment"
            return 0
        fi
    fi
    
    python3 -m venv "$VENV_DIR"
    print_success "Virtual environment created at ${VENV_DIR}"
}

# Function to activate virtual environment
activate_venv() {
    source "${VENV_DIR}/bin/activate"
    print_success "Virtual environment activated"
}

# Function to upgrade pip
upgrade_pip() {
    print_info "Upgrading pip..."
    pip install --upgrade pip setuptools wheel > /dev/null 2>&1
    print_success "pip upgraded"
}

# Function to install Python dependencies
install_dependencies() {
    print_info "Installing Python dependencies..."
    
    local requirements_file="${APP_DIR}/requirements.txt"
    if [[ ! -f "$requirements_file" ]]; then
        print_error "requirements.txt not found at ${requirements_file}"
        exit 1
    fi
    
    # Install dependencies with progress
    pip install -r "$requirements_file" 2>&1 | while IFS= read -r line; do
        if [[ "$line" =~ "Collecting" ]] || [[ "$line" =~ "Installing" ]] || [[ "$line" =~ "Successfully" ]]; then
            echo "  $line"
        fi
    done
    
    print_success "Python dependencies installed"
}

# Function to setup configuration
setup_config() {
    print_info "Setting up configuration..."
    
    local config_file="${APP_DIR}/config.yaml"
    local example_config="${APP_DIR}/config.example.yaml"
    
    if [[ ! -f "$config_file" ]]; then
        if [[ -f "$example_config" ]]; then
            cp "$example_config" "$config_file"
            print_success "Configuration file created from example"
        else
            print_warning "No example configuration found, creating default config..."
            cat > "$config_file" <<EOF
server:
  host: "0.0.0.0"
  port: 8410
  base_url: "http://localhost:8410"

database:
  url: "sqlite:///./streamtv.db"

streaming:
  buffer_size: 8192
  chunk_size: 1024
  timeout: 30
  max_retries: 3

youtube:
  enabled: true
  quality: "best"
  extract_audio: false

archive_org:
  enabled: true
  preferred_format: "h264"
  username: null
  password: null
  use_authentication: false

security:
  api_key_required: false
  access_token: null

logging:
  level: "INFO"
  file: "streamtv.log"
EOF
            print_success "Default configuration file created"
        fi
    else
        print_info "Configuration file already exists"
    fi
}

# Function to initialize database
init_database() {
    print_info "Initializing database..."
    
    cd "$APP_DIR"
    python3 -c "
from streamtv.database.session import init_db
init_db()
print('Database initialized')
" 2>&1 | grep -v "^$" || true
    
    print_success "Database initialized"
}

# Function to create default channels
create_channels() {
    print_info "Creating default channels..."
    
    cd "$APP_DIR"
    
    # Try Python script first (direct database access)
    if [[ -f "scripts/create_channel.py" ]]; then
        python3 scripts/create_channel.py 2>&1 | while IFS= read -r line; do
            if [[ "$line" =~ "Created channel" ]] || [[ "$line" =~ "already exists" ]] || [[ "$line" =~ "Successfully" ]]; then
                echo "  $line"
            fi
        done
        print_success "Channels created via Python script"
    else
        print_warning "Channel creation script not found, skipping channel creation"
        print_info "You can create channels later using: python3 scripts/create_channel.py"
    fi
}

# Function to create launch script
create_launch_script() {
    print_info "Creating launch script..."
    
    local launch_script="${INSTALL_DIR}/start_server.sh"
    cat > "$launch_script" <<EOF
#!/usr/bin/env zsh
# Launch script for StreamTV

cd "${APP_DIR}"
source "${VENV_DIR}/bin/activate"
python3 -m streamtv.main
EOF
    chmod +x "$launch_script"
    print_success "Launch script created at ${launch_script}"
}

# Function to create service script (launchd)
create_service_script() {
    print_info "Creating macOS service script..."
    
    local plist_file="${HOME}/Library/LaunchAgents/com.streamtv.plist"
    cat > "$plist_file" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.streamtv</string>
    <key>ProgramArguments</key>
    <array>
        <string>${VENV_DIR}/bin/python3</string>
        <string>-m</string>
        <string>streamtv.main</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${APP_DIR}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${INSTALL_DIR}/server.log</string>
    <key>StandardErrorPath</key>
    <string>${INSTALL_DIR}/server.error.log</string>
</dict>
</plist>
EOF
    print_success "Service plist created at ${plist_file}"
    print_info "To start as service: launchctl load ${plist_file}"
    print_info "To stop service: launchctl unload ${plist_file}"
}

# Function to start server
start_server() {
    print_info "Starting server..."
    print_warning "Server will run in the background. Press Ctrl+C to stop."
    print_info "Access the server at: http://localhost:8410"
    print_info "API docs at: http://localhost:8410/docs"
    echo ""
    
    cd "$APP_DIR"
    source "${VENV_DIR}/bin/activate"
    python3 -m streamtv.main &
    local server_pid=$!
    echo $server_pid > "${INSTALL_DIR}/server.pid"
    print_success "Server started with PID ${server_pid}"
    print_info "To stop: kill ${server_pid} or use: pkill -f 'streamtv.main'"
}

# Main installation function
main() {
    print_header "Retro TV Simulator - macOS Installation"
    
    # Check macOS version
    local macos_version=$(sw_vers -productVersion)
    print_info "macOS version: ${macos_version}"
    
    # Create install directory
    mkdir -p "$INSTALL_DIR"
    
    # Step 1: Check/Install Python
    print_header "Step 1: Checking Python Installation"
    if ! check_python_version; then
        install_python
    fi
    
    # Step 2: Check/Install FFmpeg
    print_header "Step 2: Checking FFmpeg Installation"
    if ! check_ffmpeg; then
        install_ffmpeg
    fi
    
    # Step 3: Setup virtual environment
    print_header "Step 3: Setting Up Virtual Environment"
    setup_venv
    activate_venv
    
    # Step 4: Upgrade pip
    print_header "Step 4: Upgrading pip"
    upgrade_pip
    
    # Step 5: Install dependencies
    print_header "Step 5: Installing Python Dependencies"
    install_dependencies
    
    # Step 6: Setup configuration
    print_header "Step 6: Setting Up Configuration"
    setup_config
    
    # Step 7: Initialize database
    print_header "Step 7: Initializing Database"
    init_database
    
    # Step 8: Create channels
    print_header "Step 8: Creating Default Channels"
    create_channels
    
    # Step 9: Create launch scripts
    print_header "Step 9: Creating Launch Scripts"
    create_launch_script
    create_service_script
    
    # Installation complete
    print_header "Installation Complete!"
    
    echo ""
    print_success "Retro TV Simulator has been installed successfully!"
    echo ""
    print_info "Installation directory: ${INSTALL_DIR}"
    print_info "Virtual environment: ${VENV_DIR}"
    print_info "Application directory: ${APP_DIR}"
    echo ""
    print_info "To start the server:"
    echo "  ${INSTALL_DIR}/start_server.sh"
    echo ""
    print_info "Or run directly:"
    echo "  cd ${APP_DIR}"
    echo "  source ${VENV_DIR}/bin/activate"
    echo "  python3 -m streamtv.main"
    echo ""
    print_info "Access the server at: http://localhost:8410"
    print_info "API documentation: http://localhost:8410/docs"
    echo ""
    
    # Ask if user wants to start server
    read -q "?Would you like to start the server now? (y/N): " && echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        start_server
    else
        print_info "You can start the server later using the launch script"
    fi
    
    echo ""
    print_success "Installation finished successfully!"
}

# Run main function
main "$@"

