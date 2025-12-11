#!/usr/bin/env python3
"""
Script to rename existing channels to Winter Olympics names

This script updates existing channels in the database to use the correct
Winter Olympics channel names and numbers.

Usage:
    python scripts/rename_channels.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from streamtv.database.session import SessionLocal, init_db
from streamtv.database.models import Channel

# Channel mappings: number -> name
CHANNEL_MAPPINGS = {
    "1980": "1980 Lake Placid Winter Olympics",
    "1984": "1984 Sarajevo Winter Olympics",
    "1988": "1988 Calgary Winter Olympics",
    "1992": "1992 Albertville Winter Olympics",
    "1994": "1994 Lillehammer Winter Olympics",
}

def rename_channels():
    """Rename existing channels to Winter Olympics names"""
    db = SessionLocal()
    try:
        init_db()
        
        print("Renaming channels to Winter Olympics names...")
        print("=" * 60)
        
        updated_count = 0
        created_count = 0
        
        for number, name in CHANNEL_MAPPINGS.items():
            # Check if channel exists
            channel = db.query(Channel).filter(Channel.number == number).first()
            
            if channel:
                # Update existing channel
                old_name = channel.name
                channel.name = name
                channel.group = "Winter Olympics"
                db.commit()
                db.refresh(channel)
                print(f"✓ Updated channel {number}: '{old_name}' → '{name}'")
                updated_count += 1
            else:
                # Create new channel if it doesn't exist
                channel = Channel(
                    number=number,
                    name=name,
                    group="Winter Olympics",
                    enabled=True
                )
                db.add(channel)
                db.commit()
                db.refresh(channel)
                print(f"✓ Created channel {number}: '{name}'")
                created_count += 1
        
        print("=" * 60)
        print(f"Successfully updated {updated_count} channel(s)")
        print(f"Successfully created {created_count} channel(s)")
        
    except Exception as e:
        db.rollback()
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    rename_channels()

