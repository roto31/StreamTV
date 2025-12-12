#!/bin/bash
#
# Complete Installation Script for StreamTV
# Linux-specific installation
#
# This script:
# 1. Checks and installs Python 3.8+
# 2. Installs FFmpeg
# 3. Sets up virtual environment
# 4. Installs all Python dependencies
# 5. Configures the platform
# 6. Creates systemd service (optional)
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
PYTHON_MIN_VERSION="3.8"
VENV_DIR="${INSTALL_DIR}/venv"
APP_DIR="$(cd "$(dirname "$0")" && pwd)"

# Detect Linux distribution
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
    elif [ -f /etc/debian_version ]; then
        DISTRO="debian"
    elif [ -f /etc/redhat-release ]; then
        DISTRO="rhel"
    elif [ -f /etc/arch-release ]; then
        DISTRO="arch"
    else
        DISTRO="unknown"
    fi
}

# Function to print colored messages
print_header() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1" >&2
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
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
        
        if [ "$major" -gt "$min_major" ] || ([ "$major" -eq "$min_major" ] && [ "$minor" -ge "$min_minor" ]); then
            print_success "Python ${version} found"
            return 0
        fi
    fi
    return 1
}

# Function to install Python
install_python() {
    print_info "Python 3.8+ not found. Installing..."
    
    detect_distro
    case $DISTRO in
        ubuntu|debian)
            print_info "Installing Python via apt..."
            sudo apt update
            sudo apt install -y python3 python3-pip python3-venv
            ;;
        fedora|rhel|centos)
            print_info "Installing Python via dnf..."
            sudo dnf install -y python3 python3-pip
            ;;
        arch|manjaro)
            print_info "Installing Python via pacman..."
            sudo pacman -S --noconfirm python python-pip
            ;;
        *)
            print_error "Unsupported distribution: $DISTRO"
            print_info "Please install Python 3.8+ manually"
            exit 1
            ;;
    esac
    
    if check_python_version; then
        print_success "Python installed"
    else
        print_error "Python installation failed"
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

# Function to install FFmpeg
install_ffmpeg() {
    print_info "FFmpeg not found. Installing..."
    
    detect_distro
    case $DISTRO in
        ubuntu|debian)
            print_info "Installing FFmpeg via apt..."
            sudo apt update
            sudo apt install -y ffmpeg
            ;;
        fedora|rhel|centos)
            print_info "Installing FFmpeg via dnf..."
            sudo dnf install -y ffmpeg
            ;;
        arch|manjaro)
            print_info "Installing FFmpeg via pacman..."
            sudo pacman -S --noconfirm ffmpeg
            ;;
        *)
            print_error "Unsupported distribution: $DISTRO"
            print_info "Please install FFmpeg manually from https://ffmpeg.org/download.html"
            exit 1
            ;;
    esac
    
    if check_ffmpeg; then
        print_success "FFmpeg installed"
    else
        print_error "FFmpeg installation failed"
        exit 1
    fi
}

# Function to create virtual environment
setup_venv() {
    print_info "Setting up virtual environment..."
    
    if [ -d "$VENV_DIR" ]; then
        print_warning "Virtual environment already exists at ${VENV_DIR}"
        read -p "Do you want to recreate it? (y/N): " -n 1 -r
        echo
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
    if [ ! -f "$requirements_file" ]; then
        print_error "requirements.txt not found at ${requirements_file}"
        exit 1
    fi
    
    pip install -r "$requirements_file"
    print_success "Python dependencies installed"
}

# Function to setup configuration
setup_config() {
    print_info "Setting up configuration..."
    
    local config_file="${APP_DIR}/config.yaml"
    local example_config="${APP_DIR}/config.example.yaml"
    
    if [ ! -f "$config_file" ]; then
        if [ -f "$example_config" ]; then
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

# Function to create launch script
create_launch_script() {
    print_info "Creating launch script..."
    
    local launch_script="${INSTALL_DIR}/start_server.sh"
    cat > "$launch_script" <<EOF
#!/bin/bash
# Launch script for StreamTV

cd "${APP_DIR}"
source "${VENV_DIR}/bin/activate"
python3 -m streamtv.main
EOF
    chmod +x "$launch_script"
    print_success "Launch script created at ${launch_script}"
}

# Function to create systemd service
create_systemd_service() {
    print_info "Creating systemd service..."
    
    read -p "Do you want to create a systemd service? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Skipping systemd service creation"
        return 0
    fi
    
    local service_file="/etc/systemd/system/streamtv.service"
    
    if [ ! -w "/etc/systemd/system" ]; then
        print_warning "Cannot write to /etc/systemd/system (requires sudo)"
        print_info "Creating service file template at ${INSTALL_DIR}/streamtv.service"
        service_file="${INSTALL_DIR}/streamtv.service"
    fi
    
    cat > "$service_file" <<EOF
[Unit]
Description=StreamTV Media Streaming Server
After=network.target

[Service]
Type=simple
User=${USER}
WorkingDirectory=${APP_DIR}
Environment="PATH=${VENV_DIR}/bin"
ExecStart=${VENV_DIR}/bin/python3 -m streamtv.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    if [ -w "/etc/systemd/system" ]; then
        print_success "Systemd service created at ${service_file}"
        print_info "To enable and start:"
        print_info "  sudo systemctl enable streamtv"
        print_info "  sudo systemctl start streamtv"
        print_info "To check status: sudo systemctl status streamtv"
    else
        print_success "Service file template created at ${service_file}"
        print_info "To install:"
        print_info "  sudo cp ${service_file} /etc/systemd/system/"
        print_info "  sudo systemctl daemon-reload"
        print_info "  sudo systemctl enable streamtv"
        print_info "  sudo systemctl start streamtv"
    fi
}

# Main installation function
main() {
    print_header "StreamTV - Linux Installation"
    
    # Detect distribution
    detect_distro
    print_info "Detected distribution: ${DISTRO}"
    
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
    
    # Step 8: Create launch scripts
    print_header "Step 8: Creating Launch Scripts"
    create_launch_script
    create_systemd_service
    
    # Installation complete
    print_header "Installation Complete!"
    
    echo ""
    print_success "StreamTV has been installed successfully!"
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
    read -p "Would you like to start the server now? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Starting server..."
        cd "$APP_DIR"
        source "${VENV_DIR}/bin/activate"
        python3 -m streamtv.main
    else
        print_info "You can start the server later using the launch script"
    fi
    
    echo ""
    print_success "Installation finished successfully!"
}

# Run main function
main "$@"
