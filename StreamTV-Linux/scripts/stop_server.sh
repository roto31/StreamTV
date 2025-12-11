#!/usr/bin/env zsh
# Stop StreamTV server script

PORT=${1:-8410}

echo "Stopping StreamTV server on port $PORT..."

# Find and kill all processes on the port
PIDS=$(lsof -ti :$PORT 2>/dev/null)

if [ -z "$PIDS" ]; then
    echo "No process found running on port $PORT"
    exit 0
fi

echo "Found process(es) on port $PORT: $PIDS"

# Kill all processes (but exclude Cursor/IDE processes)
for PID in $PIDS; do
    # Check if it's a Python/uvicorn process
    if ps -p $PID -o comm= | grep -qE "(Python|python|uvicorn)"; then
        echo "Stopping process $PID..."
        kill $PID 2>/dev/null
    fi
done

# Wait a moment
sleep 2

# Force kill any remaining Python processes on the port
REMAINING=$(lsof -ti :$PORT 2>/dev/null | grep -vE "^$(pgrep -f Cursor|head -1)$" || true)
if [ -n "$REMAINING" ]; then
    for PID in $REMAINING; do
        if ps -p $PID -o comm= | grep -qE "(Python|python|uvicorn)"; then
            echo "Force killing process $PID..."
            kill -9 $PID 2>/dev/null
        fi
    done
    sleep 1
fi

# Verify it's stopped (only check for Python processes)
REMAINING_PYTHON=$(lsof -ti :$PORT 2>/dev/null | xargs -I {} sh -c 'ps -p {} -o comm= | grep -qE "(Python|python|uvicorn)" && echo {}' || true)

if [ -n "$REMAINING_PYTHON" ]; then
    echo "❌ Failed to stop server on port $PORT"
    echo "Remaining processes: $REMAINING_PYTHON"
    exit 1
else
    echo "✅ Server stopped successfully"
fi

