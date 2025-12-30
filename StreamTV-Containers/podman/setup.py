#!/usr/bin/env python3
"""Setup script for StreamTV"""

import sys
from pathlib import Path

def main():
    """Setup StreamTV"""
    print("Setting up StreamTV...")
    
    # Check Python version
    if sys.version_info < (3, 10):
        print("Error: Python 3.10 or higher is required")
        sys.exit(1)
    
    # Create config file if it doesn't exist
    config_path = Path("config.yaml")
    if not config_path.exists():
        example_path = Path("config.example.yaml")
        if example_path.exists():
            import shutil
            shutil.copy(example_path, config_path)
            print(f"Created {config_path} from example")
        else:
            print(f"Warning: {config_path} not found and no example available")
    else:
        print(f"{config_path} already exists")
    
    print("\nSetup complete!")
    print("\nNext steps:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Edit config.yaml with your settings")
    print("3. Run: python -m streamtv.main")

if __name__ == "__main__":
    main()
