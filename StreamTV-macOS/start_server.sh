#!/usr/bin/env zsh
# Quick start script for StreamTV

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run: python3 -m venv venv"
    echo "Then: source venv/bin/activate"
    echo "Then: pip install -r requirements.txt"
    exit 1
fi

# Use venv Python directly (don't rely on activation script which may have old paths)
VENV_PYTHON="$SCRIPT_DIR/venv/bin/python3"

# Check if venv Python exists
if [ ! -f "$VENV_PYTHON" ]; then
    echo "❌ Virtual environment Python not found at $VENV_PYTHON"
    exit 1
fi

# Check if FastAPI is installed using venv Python
if ! "$VENV_PYTHON" -c "import fastapi" 2>/dev/null; then
    echo "❌ FastAPI not found in virtual environment!"
    echo "Installing dependencies..."
    "$VENV_PYTHON" -m pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install dependencies"
        exit 1
    fi
    echo "✅ Dependencies installed"
fi

# Start the server
echo "🚀 Starting StreamTV server..."
"$VENV_PYTHON" -m streamtv.main

