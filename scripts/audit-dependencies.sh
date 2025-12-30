#!/bin/bash
#
# Dependency Security Audit Script for StreamTV
# Scans dependencies for known security vulnerabilities
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
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REQUIREMENTS_FILE="${PROJECT_ROOT}/requirements.txt"
OUTPUT_DIR="${PROJECT_ROOT}/security-reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

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

# Check Python version
check_python_version() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        exit 1
    fi
    
    local version=$(python3 --version 2>&1 | awk '{print $2}')
    local major=$(echo $version | cut -d. -f1)
    local minor=$(echo $version | cut -d. -f2)
    
    if [ "$major" -lt 3 ] || ([ "$major" -eq 3 ] && [ "$minor" -lt 10 ]); then
        print_error "Python 3.10+ is required. Found: $version"
        exit 1
    fi
    
    print_success "Python $version found"
}

# Check if pip-audit is installed
check_pip_audit() {
    # Check if pip-audit is available as a command or module
    if ! command -v pip-audit &> /dev/null && ! python3 -m pip show pip-audit &> /dev/null; then
        print_warning "pip-audit not found. Installing..."
        python3 -m pip install --user pip-audit>=2.10.0 --quiet
        
        # Add user bin directory to PATH if pip-audit was installed there
        local user_bin="$HOME/Library/Python/$(python3 --version | cut -d' ' -f2 | cut -d. -f1,2)/bin"
        if [ -d "$user_bin" ] && [[ ":$PATH:" != *":$user_bin:"* ]]; then
            export PATH="$user_bin:$PATH"
            print_info "Added $user_bin to PATH for this session"
        fi
    fi
    
    # Verify pip-audit is accessible
    if command -v pip-audit &> /dev/null || python3 -m pip_audit --help &> /dev/null; then
        print_success "pip-audit is available"
    else
        print_error "pip-audit installation failed or not accessible"
        print_info "Try: python3 -m pip install --user pip-audit>=2.10.0"
        exit 1
    fi
}

# Run pip-audit
run_pip_audit() {
    print_header "Running pip-audit Security Scan"
    
    local output_file="${OUTPUT_DIR}/pip-audit-${TIMESTAMP}.json"
    mkdir -p "$OUTPUT_DIR"
    
    print_info "Scanning ${REQUIREMENTS_FILE}..."
    
    # Try pip-audit as command first, then as module
    local pip_audit_cmd=""
    if command -v pip-audit &> /dev/null; then
        pip_audit_cmd="pip-audit"
    elif python3 -m pip_audit --help &> /dev/null; then
        pip_audit_cmd="python3 -m pip_audit"
    else
        print_error "pip-audit not found. Please install it first."
        return 1
    fi
    
    if $pip_audit_cmd -r "$REQUIREMENTS_FILE" --format json --output "$output_file" 2>&1; then
        print_success "Security scan completed"
        print_info "Results saved to: $output_file"
        
        # Also print summary to console
        echo ""
        print_header "Security Scan Summary"
        $pip_audit_cmd -r "$REQUIREMENTS_FILE" --format console 2>&1 || true
    else
        print_error "Security scan found vulnerabilities"
        return 1
    fi
}

# Generate dependency tree
generate_dependency_tree() {
    print_header "Generating Dependency Tree"
    
    local output_file="${OUTPUT_DIR}/dependency-tree-${TIMESTAMP}.txt"
    
    # Check if pipdeptree is installed, if not install it
    if ! python3 -m pip show pipdeptree &> /dev/null; then
        print_info "pipdeptree not found. Installing..."
        python3 -m pip install --user pipdeptree>=2.0.0 --quiet
    fi
    
    if python3 -m pip show pipdeptree &> /dev/null; then
        print_info "Generating dependency tree..."
        python3 -m pipdeptree -r -p "$REQUIREMENTS_FILE" > "$output_file" 2>&1 || true
        print_success "Dependency tree saved to: $output_file"
        echo ""
        print_info "Top-level dependencies:"
        head -20 "$output_file"
    else
        print_warning "pipdeptree installation failed. Skipping dependency tree generation."
    fi
}

# Main function
main() {
    print_header "StreamTV Dependency Security Audit"
    
    # Check prerequisites
    check_python_version
    check_pip_audit
    
    # Create output directory
    mkdir -p "$OUTPUT_DIR"
    
    # Run audits
    if run_pip_audit; then
        print_success "No critical vulnerabilities found"
    else
        print_warning "Vulnerabilities detected. Review the report for details."
    fi
    
    # Generate dependency tree
    generate_dependency_tree
    
    # Summary
    echo ""
    print_header "Audit Complete"
    print_info "Reports saved to: $OUTPUT_DIR"
    print_info "Review the reports and update dependencies as needed"
    echo ""
}

# Run main function
main "$@"

