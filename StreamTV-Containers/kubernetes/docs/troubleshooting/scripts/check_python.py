#!/usr/bin/env python3
"""
Check Python Installation
Verifies Python installation and version
"""

import sys
import platform

def main():
    print("Python Installation Check")
    print("=" * 50)
    print()
    
    # Check Python version
    version = sys.version_info
    print(f"Python Version: {version.major}.{version.minor}.{version.micro}")
    print(f"Python Executable: {sys.executable}")
    print(f"Platform: {platform.platform()}")
    print()
    
    # Check minimum version
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ ERROR: Python 3.8+ is required")
        print(f"   Current version: {version.major}.{version.minor}.{version.micro}")
        return 1
    else:
        print("✓ Python version is acceptable (3.8+)")
    
    # Check pip
    try:
        import pip
        print("✓ pip is available")
    except ImportError:
        print("⚠ WARNING: pip is not available")
        print("   Install pip: python3 -m ensurepip --upgrade")
    
    # Check virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✓ Running in virtual environment")
        print(f"   Virtual environment: {sys.prefix}")
    else:
        print("⚠ INFO: Not running in virtual environment")
        print("   Consider using a virtual environment for isolation")
    
    print()
    print("Python check complete!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
