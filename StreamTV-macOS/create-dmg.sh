#!/bin/bash
#
# Create macOS DMG distribution package
# Requires: create-dmg (install via: brew install create-dmg)
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DMG_NAME="StreamTV-macOS"
VERSION="1.0.0"
DMG_FILE="${DMG_NAME}-${VERSION}.dmg"

echo "Creating DMG distribution package..."

# Check if create-dmg is installed
if ! command -v create-dmg &> /dev/null; then
    echo "Error: create-dmg is required"
    echo "Install with: brew install create-dmg"
    exit 1
fi

# Create temporary directory for DMG contents
TEMP_DIR=$(mktemp -d)
DMG_CONTENTS="$TEMP_DIR/StreamTV"

# Copy distribution files
echo "Preparing DMG contents..."
cp -R "$SCRIPT_DIR" "$DMG_CONTENTS"

# Remove unnecessary files
cd "$DMG_CONTENTS"
rm -rf .git .cursor __pycache__ *.pyc .DS_Store venv *.db *.log

# Create Applications symlink
ln -s /Applications "$DMG_CONTENTS/Applications"

# Create DMG
echo "Creating DMG..."
cd "$TEMP_DIR"
create-dmg \
    --volname "StreamTV" \
    --window-pos 200 120 \
    --window-size 800 500 \
    --icon-size 100 \
    --icon "StreamTV" 200 300 \
    --hide-extension "StreamTV" \
    --app-drop-link 600 300 \
    "$DMG_FILE" \
    "StreamTV"

# Move DMG to script directory
mv "$DMG_FILE" "$SCRIPT_DIR/"

# Cleanup
rm -rf "$TEMP_DIR"

echo ""
echo "✓ DMG created: $SCRIPT_DIR/$DMG_FILE"
echo ""
echo "To distribute:"
echo "  1. Test the DMG by mounting it"
echo "  2. Verify all files are present"
echo "  3. Share the DMG file"
