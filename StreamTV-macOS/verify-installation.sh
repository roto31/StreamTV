#!/bin/bash
#
# Verify StreamTV Installation
# Run this after installation to verify everything is set up correctly
#

set -e

echo "StreamTV Installation Verification"
echo "===================================="
echo ""

# Check Python
echo -n "Checking Python... "
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo "✓ Found Python $PYTHON_VERSION"
else
    echo "✗ Python 3 not found"
    exit 1
fi

# Check FFmpeg
echo -n "Checking FFmpeg... "
if command -v ffmpeg &> /dev/null; then
    FFMPEG_VERSION=$(ffmpeg -version 2>&1 | head -1 | awk '{print $3}')
    echo "✓ Found FFmpeg $FFMPEG_VERSION"
else
    echo "✗ FFmpeg not found"
    exit 1
fi

# Check virtual environment
echo -n "Checking virtual environment... "
if [ -d "venv" ]; then
    echo "✓ Virtual environment exists"
else
    echo "✗ Virtual environment not found"
    exit 1
fi

# Check dependencies
echo -n "Checking Python dependencies... "
source venv/bin/activate
if python3 -c "import fastapi, uvicorn, sqlalchemy" 2>/dev/null; then
    echo "✓ Dependencies installed"
else
    echo "✗ Dependencies missing"
    exit 1
fi

# Check configuration
echo -n "Checking configuration... "
if [ -f "config.yaml" ]; then
    echo "✓ Configuration file exists"
else
    echo "⚠ Configuration file not found (will be created on first run)"
fi

# Check application code
echo -n "Checking application code... "
if [ -d "streamtv" ] && [ -f "streamtv/main.py" ]; then
    echo "✓ Application code present"
else
    echo "✗ Application code missing"
    exit 1
fi

echo ""
echo "✓ All checks passed! StreamTV is ready to use."
echo ""
echo "To start the server:"
echo "  ./Start-StreamTV.command"
echo "  or"
echo "  ./start_server.sh"
