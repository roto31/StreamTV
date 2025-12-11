#!/usr/bin/env python3
"""Test script to verify logging system is working correctly"""

import sys
from pathlib import Path

# Add parent directory to path to import streamtv modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from streamtv.utils.logging_setup import setup_logging, get_logger, log_system_info


def test_logging():
    """Test the logging system"""
    print("=" * 80)
    print("StreamTV Logging System Test")
    print("=" * 80)
    print()
    
    # Setup logging
    print("Setting up logging...")
    logger = setup_logging(log_level="INFO")
    print()
    
    # Log system info
    print("Logging system information...")
    log_system_info()
    print()
    
    # Get module logger
    test_logger = get_logger(__name__)
    
    # Test different log levels
    print("Testing different log levels...")
    print("(Check ~/Library/Logs/StreamTV/ for the log file)")
    print()
    
    test_logger.debug("This is a DEBUG message (may not appear if level is INFO)")
    test_logger.info("This is an INFO message")
    test_logger.warning("This is a WARNING message")
    test_logger.error("This is an ERROR message")
    test_logger.critical("This is a CRITICAL message")
    
    # Test exception logging
    print()
    print("Testing exception logging...")
    try:
        # Deliberately cause an exception
        result = 1 / 0
    except ZeroDivisionError as e:
        test_logger.error(f"Caught exception: {e}", exc_info=True)
    
    # Show log location
    log_dir = Path.home() / "Library" / "Logs" / "StreamTV"
    print()
    print("=" * 80)
    print("✅ Logging test complete!")
    print(f"📁 Log directory: {log_dir}")
    print()
    
    # List log files
    if log_dir.exists():
        log_files = list(log_dir.glob("*.log*"))
        if log_files:
            print(f"Found {len(log_files)} log file(s):")
            for log_file in sorted(log_files, key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
                size_kb = log_file.stat().st_size / 1024
                print(f"  - {log_file.name} ({size_kb:.1f} KB)")
        else:
            print("⚠️  No log files found (this shouldn't happen)")
    else:
        print("⚠️  Log directory not found (this shouldn't happen)")
    
    print()
    print("To view logs:")
    print(f"  tail -f {log_dir}/streamtv-*.log")
    print("  OR")
    print("  ./scripts/view-logs.sh")
    print("=" * 80)


if __name__ == "__main__":
    test_logging()

