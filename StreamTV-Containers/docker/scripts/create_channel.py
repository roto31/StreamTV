#!/usr/bin/env python3
"""
Script to create channels for StreamTV

This script creates channels for StreamTV with customizable names and groups.

Usage:
    python scripts/create_channel.py [--year YEAR] [--number NUMBER] [--name NAME] [--group GROUP]
    
    Or run without arguments to create all three default channels:
    python scripts/create_channel.py
"""

import sys
import argparse
from pathlib import Path
from typing import Optional

# Add parent directory to path to import streamtv modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from streamtv.database.session import SessionLocal, init_db
from streamtv.database.models import Channel
from streamtv.config import config


def create_channel(number: str, name: str, group: Optional[str] = None, enabled: bool = True, logo_path: Optional[str] = None):
    """Create a channel in the database"""
    db = SessionLocal()
    try:
        # Check if channel number already exists
        existing = db.query(Channel).filter(Channel.number == number).first()
        if existing:
            print(f"Channel with number '{number}' already exists: {existing.name}")
            return existing
        
        # Create new channel
        channel = Channel(
            number=number,
            name=name,
            group=group,
            enabled=enabled,
            logo_path=logo_path
        )
        db.add(channel)
        db.commit()
        db.refresh(channel)
        print(f"✓ Created channel: {channel.number} - {channel.name} (ID: {channel.id})")
        return channel
    except Exception as e:
        db.rollback()
        print(f"✗ Error creating channel: {e}")
        raise
    finally:
        db.close()


def create_default_channels():
    """Create default Winter Olympics channels"""
    channels = [
        {
            "number": "1980",
            "name": "1980 Lake Placid Winter Olympics",
            "group": "Winter Olympics",
            "enabled": True,
            "logo_path": None
        },
        {
            "number": "1984",
            "name": "1984 Sarajevo Winter Olympics",
            "group": "Winter Olympics",
            "enabled": True,
            "logo_path": None
        },
        {
            "number": "1988",
            "name": "1988 Calgary Winter Olympics",
            "group": "Winter Olympics",
            "enabled": True,
            "logo_path": None
        },
        {
            "number": "1992",
            "name": "1992 Albertville Winter Olympics",
            "group": "Winter Olympics",
            "enabled": True,
            "logo_path": None
        },
        {
            "number": "1994",
            "name": "1994 Lillehammer Winter Olympics",
            "group": "Winter Olympics",
            "enabled": True,
            "logo_path": None
        }
    ]
    
    print("Creating default Winter Olympics channels for StreamTV...")
    print("=" * 60)
    
    created_channels = []
    for channel_data in channels:
        channel = create_channel(**channel_data)
        created_channels.append(channel)
    
    print("=" * 60)
    print(f"Successfully created {len(created_channels)} channel(s)")
    return created_channels


def main():
    parser = argparse.ArgumentParser(
        description="Create channels for StreamTV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create all default channels (1980, 1984, 1988)
  python scripts/create_channel.py
  
  # Create a custom channel
  python scripts/create_channel.py --number "1" --name "My Channel" --group "Entertainment"
  
  # Create a channel for a specific year
  python scripts/create_channel.py --year 1980
        """
    )
    
    parser.add_argument(
        "--year",
        type=int,
        help="Create channel for specific year (example: 1980, 1984, 1988)"
    )
    parser.add_argument(
        "--number",
        type=str,
        help="Channel number (e.g., '1', '1980')"
    )
    parser.add_argument(
        "--name",
        type=str,
        help="Channel name"
    )
    parser.add_argument(
        "--group",
        type=str,
        default="StreamTV",
        help="Channel group (default: 'StreamTV')"
    )
    parser.add_argument(
        "--logo",
        type=str,
        help="Path to channel logo"
    )
    parser.add_argument(
        "--disabled",
        action="store_true",
        help="Create channel as disabled"
    )
    
    args = parser.parse_args()
    
    # Initialize database
    init_db()
    
    # If year is specified, create channel for that year
    if args.year:
        year = args.year
        create_channel(
            number=str(year),
            name=f"StreamTV Channel {year}",
            group="Retro Olympics",
            enabled=not args.disabled,
            logo_path=args.logo
        )
    # If number and name are provided, create custom channel
    elif args.number and args.name:
        create_channel(
            number=args.number,
            name=args.name,
            group=args.group,
            enabled=not args.disabled,
            logo_path=args.logo
        )
    # Otherwise, create all default channels
    else:
        create_default_channels()


if __name__ == "__main__":
    main()

