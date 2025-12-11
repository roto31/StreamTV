#!/usr/bin/env python3
"""Script to find and remove placeholder URLs from the database"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from streamtv.database import get_db, MediaItem, PlaylistItem, CollectionItem
from sqlalchemy.orm import Session

def cleanup_placeholders(dry_run: bool = True):
    """Find and optionally remove placeholder URLs"""
    db: Session = next(get_db())
    
    try:
        # Find all media items with placeholder URLs
        placeholders = db.query(MediaItem).filter(
            MediaItem.url.like('%PLACEHOLDER%')
        ).all()
        
        if not placeholders:
            print("No placeholder URLs found in database.")
            return
        
        print(f"Found {len(placeholders)} media items with placeholder URLs:")
        print("-" * 80)
        
        for item in placeholders:
            print(f"ID: {item.id}")
            print(f"  Title: {item.title}")
            print(f"  URL: {item.url}")
            print(f"  Source: {item.source.value}")
            print()
        
        if dry_run:
            print("DRY RUN MODE - No changes made.")
            print("Run with --execute to remove these items.")
        else:
            # Count related items
            total_playlist_items = 0
            total_collection_items = 0
            
            for item in placeholders:
                playlist_count = db.query(PlaylistItem).filter(
                    PlaylistItem.media_item_id == item.id
                ).count()
                collection_count = db.query(CollectionItem).filter(
                    CollectionItem.media_item_id == item.id
                ).count()
                total_playlist_items += playlist_count
                total_collection_items += collection_count
            
            print(f"\nThis will remove:")
            print(f"  - {len(placeholders)} media items")
            print(f"  - {total_playlist_items} playlist items")
            print(f"  - {total_collection_items} collection items")
            
            response = input("\nProceed with deletion? (yes/no): ")
            if response.lower() != 'yes':
                print("Cancelled.")
                return
            
            # Delete related items first (cascade should handle this, but being explicit)
            for item in placeholders:
                db.query(PlaylistItem).filter(
                    PlaylistItem.media_item_id == item.id
                ).delete()
                db.query(CollectionItem).filter(
                    CollectionItem.media_item_id == item.id
                ).delete()
            
            # Delete media items
            for item in placeholders:
                db.delete(item)
            
            db.commit()
            print(f"\nSuccessfully removed {len(placeholders)} placeholder items.")
    
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean up placeholder URLs from database")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually remove placeholder items (default is dry-run)"
    )
    
    args = parser.parse_args()
    cleanup_placeholders(dry_run=not args.execute)

