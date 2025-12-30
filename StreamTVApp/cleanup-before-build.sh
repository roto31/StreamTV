#!/bin/bash
#
# Cleanup script to run before Xcode build
# Removes duplicate files and cache directories that cause build errors
# Hides streamtv directory to prevent file system synchronized group from copying it
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STREAMTV_DIR="$SCRIPT_DIR/StreamTV/StreamTV"

echo "Cleaning up before build..."

# Note: streamtv directory has been moved to StreamTV/streamtv_source
# (outside the synchronized group path) to prevent file system sync conflicts
# No need to hide it - it's already outside the scan path

# Remove duplicate files with " 2" suffix
echo "  Removing duplicate files with ' 2' suffix..."
find "$STREAMTV_DIR" -name "* 2.py" -delete 2>/dev/null || true
find "$STREAMTV_DIR" -name "* 2.pyc" -delete 2>/dev/null || true

# Remove __pycache__ directories and .pyc files
echo "  Removing __pycache__ directories and .pyc files..."
find "$STREAMTV_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$STREAMTV_DIR" -name "*.pyc" -delete 2>/dev/null || true
find "$STREAMTV_DIR" -name "*.pyo" -delete 2>/dev/null || true

# Remove duplicate auth_checker.py from utils (keep the one in api)
STREAMTV_SOURCE="$SCRIPT_DIR/StreamTV/streamtv_source"
if [ -f "$STREAMTV_SOURCE/utils/auth_checker.py" ] && [ -f "$STREAMTV_SOURCE/api/auth_checker.py" ]; then
    echo "  Removing duplicate auth_checker.py from utils..."
    rm -f "$STREAMTV_SOURCE/utils/auth_checker.py" 2>/dev/null || true
fi

echo "Cleanup complete"

