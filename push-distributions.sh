#!/bin/bash
#
# Quick script to push distribution folders to GitHub
# Use this if the main upload script isn't working
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

print_header "Push StreamTV Distributions to GitHub"

# Check git status
if [ ! -d ".git" ]; then
    print_error "Not a git repository"
    exit 1
fi

# Check remote
if ! git remote get-url origin &>/dev/null; then
    print_error "No remote 'origin' configured"
    print_info "Configure with: git remote add origin https://github.com/roto31/StreamTV.git"
    exit 1
fi

REMOTE_URL=$(git remote get-url origin)
print_info "Remote: $REMOTE_URL"

# Check what needs to be pushed
print_header "Checking Status"

# Fetch latest
print_info "Fetching from remote..."
git fetch origin 2>/dev/null || print_warning "Fetch failed (may be normal if remote is new)"

# Check commits to push
LOCAL_COMMITS=$(git rev-list --count origin/main..HEAD 2>/dev/null || echo "0")
print_info "Commits to push: $LOCAL_COMMITS"

# Check distribution files
LOCAL_FILES=$(git ls-files StreamTV-*/ 2>/dev/null | wc -l | tr -d ' ')
REMOTE_FILES=$(git ls-tree -r --name-only origin/main StreamTV-*/ 2>/dev/null | wc -l | tr -d ' ')

print_info "Distribution files - Local: $LOCAL_FILES | Remote: $REMOTE_FILES"

if [ "$LOCAL_FILES" -gt "0" ] && [ "$REMOTE_FILES" -eq "0" ]; then
    print_warning "Distribution files exist locally but not on remote!"
    print_info "These need to be pushed"
fi

# Show what will be pushed
print_header "What Will Be Pushed"

if [ "$LOCAL_COMMITS" -gt "0" ]; then
    print_info "Commits to push:"
    git log --oneline origin/main..HEAD | head -5 | sed 's/^/  /'
    echo ""
fi

# Push
print_header "Pushing to GitHub"

read -p "Push now? (Y/n): " -n 1 -r
echo

if [[ $REPLY =~ ^[Nn]$ ]]; then
    print_info "Cancelled"
    exit 0
fi

print_info "Pushing to origin/main..."
if git push -u origin main; then
    print_success "Push successful!"
    
    # Verify
    echo ""
    print_info "Verifying push..."
    git fetch origin 2>/dev/null || true
    NEW_REMOTE_FILES=$(git ls-tree -r --name-only origin/main StreamTV-*/ 2>/dev/null | wc -l | tr -d ' ')
    print_success "Distribution files on remote: $NEW_REMOTE_FILES"
    
    echo ""
    print_success "Complete! Visit: https://github.com/roto31/StreamTV"
else
    print_error "Push failed!"
    print_info "Check authentication: gh auth status"
    print_info "Or authenticate: gh auth login"
    exit 1
fi
