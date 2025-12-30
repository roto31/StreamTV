#!/bin/bash
#
# Sync Python code and requirements.txt to StreamTVApp for bundling
# This ensures the app bundle has the latest code changes
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TARGET_DIR="$SCRIPT_DIR/StreamTV/StreamTV"

echo "🔄 Syncing Python code to StreamTVApp..."

# Copy streamtv directory
if [ -d "$ROOT_DIR/streamtv" ]; then
    echo "  Copying streamtv/ directory..."
    rm -rf "$TARGET_DIR/streamtv" 2>/dev/null || true
    cp -R "$ROOT_DIR/streamtv" "$TARGET_DIR/"
    echo "  ✅ streamtv/ copied"
else
    echo "  ❌ Error: streamtv/ directory not found in root"
    exit 1
fi

# Copy requirements.txt
if [ -f "$ROOT_DIR/requirements.txt" ]; then
    echo "  Copying requirements.txt..."
    cp "$ROOT_DIR/requirements.txt" "$TARGET_DIR/"
    echo "  ✅ requirements.txt copied"
    
    # Verify jsonschema versions
    if grep -q "jsonschema==4.25.1" "$TARGET_DIR/requirements.txt" && \
       grep -q "jsonschema-specifications==2024.10.1" "$TARGET_DIR/requirements.txt"; then
        echo "  ✅ requirements.txt has updated jsonschema versions"
    else
        echo "  ⚠️  Warning: requirements.txt may not have latest jsonschema versions"
    fi
else
    echo "  ❌ Error: requirements.txt not found in root"
    exit 1
fi

echo ""
echo "✅ Sync complete!"
echo ""
echo "⚠️  IMPORTANT: These files must be added to Xcode project's 'Copy Bundle Resources' build phase:"
echo "   - streamtv/ (as folder reference)"
echo "   - requirements.txt"
echo ""
echo "To add in Xcode:"
echo "  1. Select the StreamTV target"
echo "  2. Go to Build Phases → Copy Bundle Resources"
echo "  3. Click '+' and add streamtv/ folder (select 'Create folder references')"
echo "  4. Click '+' and add requirements.txt"

