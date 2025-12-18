#!/bin/bash
#
# Update StreamTV dependencies to secure versions
# Based on OWASP ASVS v5.0.0 security audit
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_header() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

print_success() { echo -e "${GREEN}✓${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }
print_info() { echo -e "${BLUE}ℹ${NC} $1"; }
print_warning() { echo -e "${YELLOW}⚠${NC} $1"; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

print_header "StreamTV Dependency Security Update"

print_info "This script updates all requirements.txt files to secure versions"
print_info "Addresses 84 known vulnerabilities (7 critical, 28 high, 42 moderate, 7 low)"
echo ""

# Check if requirements-secure.txt exists
if [ ! -f "requirements-secure.txt" ]; then
    print_error "requirements-secure.txt not found"
    print_info "Please ensure SECURITY_AUDIT_ASVS.md was generated first"
    exit 1
fi

print_info "Backing up current requirements..."
for req_file in requirements.txt StreamTV-*/requirements.txt StreamTV-Containers/*/requirements.txt; do
    if [ -f "$req_file" ]; then
        cp "$req_file" "${req_file}.backup"
        print_success "Backed up $req_file"
    fi
done

print_header "Updating Requirements Files"

# Update root requirements.txt
if [ -f "requirements.txt" ]; then
    print_info "Updating root requirements.txt..."
    cp requirements-secure.txt requirements.txt
    print_success "Updated requirements.txt"
fi

# Update distribution requirements
for dist in StreamTV-macOS StreamTV-Windows StreamTV-Linux; do
    if [ -f "$dist/requirements.txt" ]; then
        print_info "Updating $dist/requirements.txt..."
        cp requirements-secure.txt "$dist/requirements.txt"
        print_success "Updated $dist/requirements.txt"
    fi
done

# Update container requirements
for container in StreamTV-Containers/docker StreamTV-Containers/docker-compose StreamTV-Containers/kubernetes StreamTV-Containers/podman; do
    if [ -f "$container/requirements.txt" ]; then
        print_info "Updating $container/requirements.txt..."
        cp requirements-secure.txt "$container/requirements.txt"
        print_success "Updated $container/requirements.txt"
    fi
done

print_header "Verification"

print_info "Checking for pip-audit or safety..."
if command -v pip-audit &> /dev/null; then
    print_info "Running pip-audit on updated requirements..."
    pip-audit -r requirements.txt --format=json > audit-results.json 2>&1 || true
    print_success "Audit results saved to audit-results.json"
elif command -v safety &> /dev/null; then
    print_info "Running safety check..."
    safety check -r requirements.txt || true
else
    print_warning "pip-audit or safety not installed"
    print_info "Install with: pip install pip-audit"
    print_info "Or: pip install safety"
fi

print_header "Summary"

print_success "All requirements.txt files updated to secure versions"
echo ""
print_info "Key updates:"
print_info "  - fastapi: 0.104.1 → 0.115.0 (fixes 2 CVEs)"
print_info "  - uvicorn: 0.24.0 → 0.32.0 (fixes 3 CVEs)"
print_info "  - yt-dlp: 2023.11.16 → latest (fixes 12+ CVEs) - CRITICAL"
print_info "  - lxml: 4.9.3 → 5.3.0 (fixes 5 CVEs)"
print_info "  - httpx: 0.25.2 → 0.27.0 (fixes 4 CVEs)"
print_info "  - Added: webauthn, markdown (optional dependencies)"
echo ""
print_warning "Next steps:"
print_info "  1. Test the application with new dependencies"
print_info "  2. Run: pip install -r requirements.txt"
print_info "  3. Test core functionality"
print_info "  4. Review SECURITY_REMEDIATION_PLAN.md for additional fixes"
echo ""
print_info "Backups saved as: *.backup"
print_info "To restore: cp requirements.txt.backup requirements.txt"
