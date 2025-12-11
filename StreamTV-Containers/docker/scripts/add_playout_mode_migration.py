#!/usr/bin/env python3
"""
Database migration script to add playout_mode column to existing channels.
This script adds the playout_mode field to all existing channels, defaulting to CONTINUOUS.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from streamtv.database.session import SessionLocal, init_db, engine
from streamtv.database.models import Channel, PlayoutMode
from sqlalchemy import text

def migrate():
    """Add playout_mode column to channels table if it doesn't exist"""
    print("🔄 Starting playout_mode migration...")
    
    init_db()
    db = SessionLocal()
    
    try:
        # Check if column exists using PRAGMA
        result = db.execute(text("PRAGMA table_info(channels)"))
        columns = [row[1] for row in result.fetchall()]
        column_exists = 'playout_mode' in columns
        
        if column_exists:
            print("✅ playout_mode column already exists")
        else:
            print("📝 Adding playout_mode column to channels table...")
            
            # SQLite: add column as TEXT with default value (use uppercase to match enum)
            db.execute(text("""
                ALTER TABLE channels 
                ADD COLUMN playout_mode TEXT DEFAULT 'CONTINUOUS'
            """))
            db.commit()
            print("✅ Added playout_mode column")
        
        # Fix any lowercase values and set all channels to CONTINUOUS if not set
        # First, update any lowercase 'continuous' or 'on_demand' to uppercase
        db.execute(text("""
            UPDATE channels 
            SET playout_mode = 'CONTINUOUS' 
            WHERE playout_mode IS NULL 
               OR playout_mode = '' 
               OR LOWER(playout_mode) = 'continuous'
        """))
        
        db.execute(text("""
            UPDATE channels 
            SET playout_mode = 'ON_DEMAND' 
            WHERE LOWER(playout_mode) = 'on_demand'
        """))
        
        updated_count = db.execute(text("SELECT changes()")).scalar()
        
        if updated_count > 0:
            db.commit()
            print(f"✅ Updated {updated_count} channel(s) to use uppercase enum values")
        else:
            print("✅ All channels already have correct playout_mode values")
        
        # Now we can safely query channels (all values are uppercase)
        channels = db.query(Channel).all()
        print(f"\n📊 Migration Summary:")
        print(f"   Total channels: {len(channels)}")
        for channel in channels:
            mode = getattr(channel, 'playout_mode', 'N/A')
            print(f"   - Channel {channel.number} ({channel.name}): {mode}")
        
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()
    
    return 0

if __name__ == "__main__":
    sys.exit(migrate())

