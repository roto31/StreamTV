#!/bin/bash
#
# StreamTV macOS Installation Launcher
# Double-click this file to start installation
#

cd "$(dirname "$0")"

# Make install script executable
chmod +x install_macos.sh

# Run installation
./install_macos.sh

# Keep terminal open if there was an error
if [ $? -ne 0 ]; then
    echo ""
    echo "Press Enter to close this window..."
    read
fi
