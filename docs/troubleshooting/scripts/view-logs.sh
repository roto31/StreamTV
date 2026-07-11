#!/usr/bin/env bash
# View StreamTV logs from ~/Library/Logs/StreamTV/

LOG_DIR="$HOME/Library/Logs/StreamTV"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}StreamTV Log Viewer${NC}"
echo -e "${YELLOW}=================${NC}"
echo ""

# Check if log directory exists
if [ ! -d "$LOG_DIR" ]; then
    echo -e "${YELLOW}⚠️  Log directory not found: $LOG_DIR${NC}"
    echo "The application may not have been started yet."
    exit 1
fi

# Count log files
LOG_COUNT=$(find "$LOG_DIR" -name "*.log*" -type f | wc -l | tr -d ' ')

echo -e "${BLUE}Log directory:${NC} $LOG_DIR"
echo -e "${BLUE}Log files found:${NC} $LOG_COUNT"
echo ""

# Function to list log files
list_logs() {
    echo -e "${YELLOW}Available log files:${NC}"
    ls -lht "$LOG_DIR" | grep -E "\.log" | head -20
    echo ""
}

# Function to tail the latest log
tail_latest() {
    LATEST_LOG=$(ls -t "$LOG_DIR"/*.log 2>/dev/null | head -1)
    if [ -z "$LATEST_LOG" ]; then
        echo -e "${YELLOW}No log files found${NC}"
        exit 1
    fi
    echo -e "${GREEN}Tailing latest log:${NC} $LATEST_LOG"
    echo -e "${YELLOW}(Press Ctrl+C to exit)${NC}"
    echo ""
    tail -f "$LATEST_LOG"
}

# Function to view today's log
view_today() {
    TODAY=$(date +"%Y-%m-%d")
    TODAY_LOG="$LOG_DIR/streamtv-$TODAY.log"
    
    if [ -f "$TODAY_LOG" ]; then
        echo -e "${GREEN}Viewing today's log:${NC} $TODAY_LOG"
        echo ""
        less +G "$TODAY_LOG"
    else
        echo -e "${YELLOW}No log file found for today: $TODAY_LOG${NC}"
        exit 1
    fi
}

# Function to search logs
search_logs() {
    if [ -z "$1" ]; then
        echo -e "${YELLOW}Please provide a search term${NC}"
        exit 1
    fi
    echo -e "${GREEN}Searching for:${NC} $1"
    echo ""
    grep -r --color=always "$1" "$LOG_DIR"/*.log 2>/dev/null
}

# Function to open log directory in Finder
open_finder() {
    open "$LOG_DIR"
}

# Parse command line arguments
case "${1:-tail}" in
    list|ls)
        list_logs
        ;;
    tail|follow|f)
        tail_latest
        ;;
    today|view|cat)
        view_today
        ;;
    search|grep)
        search_logs "$2"
        ;;
    open|finder)
        open_finder
        ;;
    help|--help|-h)
        echo "Usage: $0 [command] [options]"
        echo ""
        echo "Commands:"
        echo "  list, ls          List all log files"
        echo "  tail, follow, f   Tail the latest log file (default)"
        echo "  today, view, cat  View today's log file"
        echo "  search, grep      Search logs for a term"
        echo "  open, finder      Open log directory in Finder"
        echo "  help              Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0                # Tail latest log"
        echo "  $0 list           # List all logs"
        echo "  $0 search ERROR   # Search for errors"
        echo "  $0 today          # View today's log"
        echo "  $0 open           # Open in Finder"
        ;;
    *)
        echo -e "${YELLOW}Unknown command: $1${NC}"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac

