#!/usr/bin/env python3
"""
Repair Database
Attempts to repair corrupted database
"""

import sys
import shutil
from pathlib import Path
from datetime import datetime

# Add parent directory to path to import streamtv modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

def main():
    print("Database Repair")
    print("=" * 50)
    print()
    
    try:
        from streamtv.config import config
        from streamtv.database.session import SessionLocal
        
        # Get database path
        db_url = config.database.url
        if not db_url.startswith("sqlite:///"):
            print("❌ ERROR: This script only works with SQLite databases")
            return 1
        
        db_path = db_url.replace("sqlite:///", "")
        if db_path.startswith("./"):
            db_path = Path.cwd() / db_path[2:]
        else:
            db_path = Path(db_path)
        
        if not db_path.exists():
            print(f"❌ ERROR: Database file not found: {db_path}")
            return 1
        
        # Backup database
        backup_path = db_path.with_suffix(f".backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        print(f"Creating backup: {backup_path}")
        shutil.copy2(db_path, backup_path)
        print("✓ Backup created")
        print()
        
        # Try to repair using SQLite VACUUM
        import sqlite3
        try:
            print("Attempting to repair database...")
            conn = sqlite3.connect(str(db_path))
            
            # Run integrity check first
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check;")
            result = cursor.fetchone()
            
            if result and result[0] == "ok":
                print("✓ Database integrity check passed")
                print("  Running VACUUM to optimize...")
                conn.execute("VACUUM;")
                conn.commit()
                print("✓ VACUUM completed")
            else:
                print("⚠ WARNING: Database integrity check found issues:")
                print(f"   {result[0] if result else 'Unknown error'}")
                print()
                print("Trying to recover data...")
                
                # Try to recover
                conn.execute("PRAGMA quick_check;")
                conn.execute("VACUUM;")
                conn.commit()
                print("✓ Recovery attempt completed")
            
            conn.close()
            
        except sqlite3.Error as e:
            print(f"❌ ERROR: Could not repair database: {e}")
            print()
            print("Options:")
            print("  1. Restore from backup:")
            print(f"     cp {backup_path} {db_path}")
            print("  2. Recreate database (will lose data):")
            print("     rm streamtv.db")
            print("     python3 -c \"from streamtv.database.session import init_db; init_db()\"")
            return 1
        
        print()
        print("Database repair complete!")
        print(f"Backup saved to: {backup_path}")
        return 0
        
    except ImportError as e:
        print(f"❌ ERROR: Could not import StreamTV modules: {e}")
        print("   Make sure you're running from the StreamTV directory")
        return 1
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
