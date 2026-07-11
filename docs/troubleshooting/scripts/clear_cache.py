#!/usr/bin/env python3
"""
Clear Cache
Clears application cache
"""

import sys
import shutil
from pathlib import Path

def main():
    print("Clear Application Cache")
    print("=" * 50)
    print()
    
    # Common cache locations
    cache_locations = [
        Path.home() / ".cache" / "streamtv",
        Path.home() / "Library" / "Caches" / "StreamTV",  # macOS
        Path.cwd() / ".cache",
        Path.cwd() / "__pycache__",
    ]
    
    cleared = False
    
    for cache_dir in cache_locations:
        if cache_dir.exists():
            try:
                if cache_dir.is_dir():
                    shutil.rmtree(cache_dir)
                    print(f"✓ Cleared: {cache_dir}")
                    cleared = True
                else:
                    cache_dir.unlink()
                    print(f"✓ Removed: {cache_dir}")
                    cleared = True
            except Exception as e:
                print(f"⚠ Could not clear {cache_dir}: {e}")
    
    # Clear __pycache__ directories
    for pycache in Path.cwd().rglob("__pycache__"):
        try:
            shutil.rmtree(pycache)
            print(f"✓ Cleared: {pycache}")
            cleared = True
        except Exception as e:
            print(f"⚠ Could not clear {pycache}: {e}")
    
    if not cleared:
        print("ℹ No cache directories found to clear")
    else:
        print()
        print("Cache cleared successfully!")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
