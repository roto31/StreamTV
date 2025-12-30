#!/bin/bash
#
# Cleanup script to run before Xcode build
# Removes duplicate files and cache directories that cause build errors
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STREAMTV_DIR="$SCRIPT_DIR/StreamTV/StreamTV"

echo "Cleaning up before build..."

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
if [ -f "$STREAMTV_DIR/streamtv/utils/auth_checker.py" ] && [ -f "$STREAMTV_DIR/streamtv/api/auth_checker.py" ]; then
    echo "  Removing duplicate auth_checker.py from utils..."
    rm -f "$STREAMTV_DIR/streamtv/utils/auth_checker.py"
fi

# Note: Multiple __init__.py files will still conflict when Xcode flattens to Resources
# This is a limitation of PBXFileSystemSynchronizedRootGroup
# The files are needed for Python imports, so they must be included
# Xcode will show warnings but the build should proceed if cache files are removed

echo "Cleanup complete"

