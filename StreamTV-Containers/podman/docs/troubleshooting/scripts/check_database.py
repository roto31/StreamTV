#!/usr/bin/env python3
"""
Check Database
Checks database integrity and connectivity
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import streamtv modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

def main():
    print("Database Check")
    print("=" * 50)
    print()
    
    try:
        from streamtv.database.session import SessionLocal
        from streamtv.database.models import Channel, MediaItem, Playlist
        from streamtv.config import config
        
        # Check database file
        db_url = config.database.url
        if db_url.startswith("sqlite:///"):
            db_path = db_url.replace("sqlite:///", "")
            if db_path.startswith("./"):
                db_path = Path.cwd() / db_path[2:]
            else:
                db_path = Path(db_path)
            
            if db_path.exists():
                size = db_path.stat().st_size
                print(f"✓ Database file exists: {db_path}")
                print(f"  Size: {size:,} bytes ({size / 1024 / 1024:.2f} MB)")
            else:
                print(f"⚠ WARNING: Database file not found: {db_path}")
                print("   Database will be created on first run")
        
        # Test connection
        db = SessionLocal()
        try:
            # Test query
            channel_count = db.query(Channel).count()
            media_count = db.query(MediaItem).count()
            playlist_count = db.query(Playlist).count()
            
            print("✓ Database connection successful")
            print()
            print("Database Contents:")
            print(f"  Channels: {channel_count}")
            print(f"  Media Items: {media_count}")
            print(f"  Playlists: {playlist_count}")
            
            # Check integrity
            try:
                db.execute("PRAGMA integrity_check;")
                print()
                print("✓ Database integrity check passed")
            except Exception as e:
                print()
                print(f"⚠ WARNING: Could not run integrity check: {e}")
            
        finally:
            db.close()
            
    except ImportError as e:
        print(f"❌ ERROR: Could not import StreamTV modules: {e}")
        print("   Make sure you're running from the StreamTV directory")
        return 1
    except Exception as e:
        print(f"❌ ERROR: Database check failed: {e}")
        return 1
    
    print()
    print("Database check complete!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
