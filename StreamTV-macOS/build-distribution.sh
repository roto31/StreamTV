#!/bin/bash
#
# Build StreamTV macOS Distribution Package
# Creates a clean, ready-to-distribute package
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Building StreamTV macOS Distribution Package..."
echo ""

# Clean any existing build artifacts
echo "Cleaning build artifacts..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
find . -type f -name ".DS_Store" -delete 2>/dev/null || true
rm -rf venv *.db *.log .git .cursor 2>/dev/null || true

echo "✓ Cleaned build artifacts"
echo ""

# Verify essential files
echo "Verifying essential files..."
missing_files=0

essential_files=(
    "streamtv/main.py"
    "requirements.txt"
    "config.example.yaml"
    "install_macos.sh"
    "start_server.sh"
    "README.md"
)

for file in "${essential_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "  ✗ Missing: $file"
        missing_files=$((missing_files + 1))
    else
        echo "  ✓ Found: $file"
    fi
done

if [ $missing_files -gt 0 ]; then
    echo ""
    echo "Error: $missing_files essential file(s) missing"
    exit 1
fi

echo ""
echo "✓ All essential files present"
echo ""

# Create file manifest
echo "Creating file manifest..."
{
    echo "StreamTV macOS Distribution - File Manifest"
    echo "Generated: $(date)"
    echo ""
    echo "Files:"
    find . -type f ! -path "./.git/*" ! -path "./venv/*" ! -path "./__pycache__/*" | sort
} > FILE_MANIFEST.txt

echo "✓ Created FILE_MANIFEST.txt"
echo ""

# Calculate package size
package_size=$(du -sh . | awk '{print $1}')
file_count=$(find . -type f ! -path "./.git/*" ! -path "./venv/*" | wc -l | tr -d ' ')

echo "Package Statistics:"
echo "  Size: $package_size"
echo "  Files: $file_count"
echo ""

echo "✓ Distribution package is ready!"
echo ""
echo "Next steps:"
echo "  1. Test installation: ./install_macos.sh"
echo "  2. Create ZIP: zip -r ../StreamTV-macOS-v1.0.0.zip ."
echo "  3. Create DMG: ./create-dmg.sh (requires create-dmg)"
echo ""
