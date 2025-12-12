#!/bin/bash
#
# StreamTV macOS Server Launcher
# Double-click this file to start the server
#

cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found."
    echo "Please run install_macos.sh first."
    echo ""
    echo "Press Enter to close this window..."
    read
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if config exists
if [ ! -f "config.yaml" ]; then
    echo "Creating config.yaml from example..."
    cp config.example.yaml config.yaml
fi

# Start server
echo "Starting StreamTV server..."
echo "Access the web interface at: http://localhost:8410"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python3 -m streamtv.main

# Keep terminal open
echo ""
echo "Server stopped. Press Enter to close this window..."
read
