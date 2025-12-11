#!/usr/bin/env python3
"""Rebuild 1980 Lake Placid Winter Olympics channel with specific URLs and metadata"""

import sys
import asyncio
import re
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from streamtv.database.session import SessionLocal, init_db
from streamtv.database.models import (
    Channel, MediaItem, Collection, CollectionItem, StreamSource
)
from streamtv.streaming import StreamManager
import logging
from urllib.parse import urlparse, unquote

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# All URLs provided by user
OLYMPICS_1980_URLS = [
    # Day 01
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+01+-+Preview+and+Opening+Ceremony.mp4",
    
    # Day 02
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+02+Pt.+1.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+02+Pt.+2.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+02+Pt.+3.mp4",
    
    # Day 03
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+03+Pt.+1.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+03+Pt.+2.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+03+Pt.+3.mp4",
    
    # Day 05
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+05+Pt.+1.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+05+Pt.+2.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+05+Pt.+3.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+05+Pt.+4.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+05+Pt.+5.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+05+Pt.+6.mp4",
    
    # Day 06
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+06+Pt.+1.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+06+Pt.+2.mp4",
    
    # Day 07
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+07+Pt.+1.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+07+Pt.+2.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+07+Pt.+3.mp4",
    
    # Day 08
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+08+Pt.+1.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+08+Pt.+2.mp4",
    
    # Day 09
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+09+Pt.+1.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+09+Pt.+2.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+09+Pt.+3.mp4",
    
    # Day 10
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+10+Pt.+1.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+10+Pt.+2.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+10+Pt.+3.mp4",
    
    # Day 11
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+11+Pt.+1.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+11+Pt.+2.mp4",
    
    # Day 12
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+12+Pt.+1.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+12+Pt.+2.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+12+Pt.+3.mp4",
]


def extract_day_from_url(url: str) -> tuple:
    """Extract day number and part number from URL filename"""
    # Extract filename from URL
    path = urlparse(url).path
    filename = path.split('/')[-1]
    
    # URL decode the filename (handles + as spaces and % encoding)
    decoded_filename = unquote(filename.replace('+', ' '))
    
    # Make case-insensitive for matching
    decoded_lower = decoded_filename.lower()
    
    # Extract day number using regex
    day_match = re.search(r'day\s*(\d+)', decoded_lower, re.IGNORECASE)
    if not day_match:
        return (0, 0)
    
    day_num = int(day_match.group(1))
    
    # Extract part number
    part_match = re.search(r'pt\.?\s*(\d+)', decoded_lower, re.IGNORECASE)
    part_num = int(part_match.group(1)) if part_match else 1
    
    return (day_num, part_num)


def get_collection_name(day: int) -> str:
    """Get collection name for day"""
    if day == 1:
        return "1980 Winter Olympics - Day 01 - Preview and Opening Ceremony"
    else:
        return f"1980 Winter Olympics - Day {day:02d}"


async def import_url_with_metadata(db: Session, stream_manager: StreamManager, url: str) -> MediaItem:
    """Import a single URL with full metadata from Archive.org"""
    # Extract identifier
    parsed = urlparse(url)
    path_parts = [p for p in parsed.path.split('/') if p]
    
    if 'details' in path_parts:
        idx = path_parts.index('details')
        if idx + 1 < len(path_parts):
            identifier = path_parts[idx + 1]
        else:
            raise ValueError(f"Could not extract identifier from URL: {url}")
    else:
        raise ValueError(f"Invalid Archive.org URL format: {url}")
    
    # Extract filename
    filename = path_parts[-1] if path_parts else None
    decoded_filename = unquote(filename.replace('+', ' ')) if filename else None
    
    # Check if media item already exists
    existing = db.query(MediaItem).filter(MediaItem.url == url).first()
    if existing:
        logger.info(f"  Media item already exists: {existing.title[:60]}")
        # Still update metadata if needed
        return existing
    
    # Fetch metadata from Archive.org
    logger.info(f"  Fetching metadata for: {decoded_filename or identifier}")
    try:
        item_info = await stream_manager.archive_org_adapter.get_item_info(identifier)
        
        # Find the specific file in the item
        video_files = item_info.get('video_files', [])
        selected_file = None
        if decoded_filename:
            # Try to find exact match
            selected_file = next((f for f in video_files if f['name'] == decoded_filename), None)
            if not selected_file:
                # Try partial match
                selected_file = next((f for f in video_files if decoded_filename.split('/')[-1] in f['name']), None)
        
        if not selected_file and video_files:
            selected_file = video_files[0]
        
        # Get metadata from Archive.org
        title = item_info.get('title', '')
        description = item_info.get('description', '')
        creator = item_info.get('creator', '')
        date = item_info.get('date', '')
        
        # Extract proper title from filename
        if decoded_filename:
            # Clean up filename to create a proper title
            file_title = decoded_filename.replace('.mp4', '').strip()
            # Use the filename as the title (it's more specific than item title)
            title = file_title
        
        # Create media item with full metadata
        media_item = MediaItem(
            source=StreamSource.ARCHIVE_ORG,
            source_id=identifier,
            url=url,
            title=title or decoded_filename or 'Untitled',
            description=description or '',
            duration=None,  # Will be fetched separately if needed
            thumbnail=None,  # Will be set if available
            uploader=creator or None,
            upload_date=date or None,
            view_count=None,
            meta_data=None  # Can store additional metadata as JSON
        )
        
        db.add(media_item)
        db.commit()
        db.refresh(media_item)
        
        logger.info(f"  ✓ Created: {media_item.title[:60]}")
        return media_item
        
    except Exception as e:
        logger.error(f"  ✗ Error importing {url}: {e}")
        raise


async def rebuild_channel(db: Session):
    """Rebuild the 1980 channel with all URLs"""
    logger.info("=" * 60)
    logger.info("Rebuilding 1980 Lake Placid Winter Olympics Channel")
    logger.info("=" * 60)
    
    # Initialize stream manager
    stream_manager = StreamManager()
    
    # Organize URLs by day
    urls_by_day = {}
    for url in OLYMPICS_1980_URLS:
        day, part = extract_day_from_url(url)
        if day == 0:
            logger.warning(f"Could not parse day from URL: {url}")
            continue
        
        if day not in urls_by_day:
            urls_by_day[day] = []
        urls_by_day[day].append((part, url))
    
    # Sort each day's URLs by part number
    for day in urls_by_day:
        urls_by_day[day].sort(key=lambda x: x[0])
    
    # Delete existing collections for 1980 Olympics
    logger.info("\nCleaning up existing 1980 collections...")
    existing_collections = db.query(Collection).filter(
        Collection.name.like('1980 Winter Olympics%')
    ).all()
    
    for collection in existing_collections:
        logger.info(f"  Deleting collection: {collection.name}")
        # Delete collection items
        db.query(CollectionItem).filter(CollectionItem.collection_id == collection.id).delete()
        # Delete collection
        db.delete(collection)
    
    db.commit()
    logger.info("  ✓ Cleaned up existing collections")
    
    # Import all URLs with metadata
    logger.info("\nImporting URLs with metadata...")
    imported_media = {}
    
    for day in sorted(urls_by_day.keys()):
        collection_name = get_collection_name(day)
        logger.info(f"\nProcessing {collection_name}...")
        
        # Create or get collection
        collection = db.query(Collection).filter(Collection.name == collection_name).first()
        if not collection:
            collection = Collection(
                name=collection_name,
                description=f"1980 Winter Olympics - Day {day:02d} coverage from ABC"
            )
            db.add(collection)
            db.commit()
            db.refresh(collection)
            logger.info(f"  ✓ Created collection: {collection_name}")
        
        # Import each URL for this day
        order = 0
        for part, url in urls_by_day[day]:
            try:
                media_item = await import_url_with_metadata(db, stream_manager, url)
                imported_media[url] = media_item
                
                # Add to collection
                existing_item = db.query(CollectionItem).filter(
                    CollectionItem.collection_id == collection.id,
                    CollectionItem.media_item_id == media_item.id
                ).first()
                
                if not existing_item:
                    collection_item = CollectionItem(
                        collection_id=collection.id,
                        media_item_id=media_item.id,
                        order=order
                    )
                    db.add(collection_item)
                    db.commit()
                    order += 1
                    logger.info(f"    ✓ Added to collection (order {order})")
                
            except Exception as e:
                logger.error(f"  ✗ Failed to import {url}: {e}")
                import traceback
                traceback.print_exc()
                continue
    
    logger.info("\n" + "=" * 60)
    logger.info("Rebuild complete!")
    logger.info(f"  Imported {len(imported_media)} media items")
    logger.info(f"  Created {len(set(get_collection_name(day) for day in urls_by_day))} collections")
    logger.info("=" * 60)
    
    return imported_media


async def main():
    """Main function"""
    # Initialize database
    init_db()
    
    db = SessionLocal()
    try:
        await rebuild_channel(db)
        logger.info("\n✅ Channel rebuild successful!")
        logger.info("\nNext steps:")
        logger.info("  1. The schedule YAML file is already configured correctly")
        logger.info("  2. Restart the server to apply changes")
        logger.info("  3. The channel should now play all content correctly")
    except Exception as e:
        logger.error(f"\n❌ Error during rebuild: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
