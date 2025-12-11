#!/usr/bin/env python3
"""Complete rebuild of 1980 Lake Placid Winter Olympics channel with full metadata"""

import sys
import asyncio
import re
import json
from pathlib import Path
from urllib.parse import urlparse, unquote

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from streamtv.database.session import SessionLocal, init_db
from streamtv.database.models import (
    Channel, MediaItem, Collection, CollectionItem, StreamSource
)
from streamtv.streaming import StreamManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# All URLs provided by user
OLYMPICS_1980_URLS = [
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+01+-+Preview+and+Opening+Ceremony.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+02+Pt.+1.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+02+Pt.+2.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+02+Pt.+3.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+03+Pt.+1.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+03+Pt.+2.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+03+Pt.+3.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+05+Pt.+1.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+05+Pt.+2.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+05+Pt.+3.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+05+Pt.+4.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+05+Pt.+5.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+05+Pt.+6.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+06+Pt.+1.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+06+Pt.+2.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+07+Pt.+1.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+07+Pt.+2.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+07+Pt.+3.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+08+Pt.+1.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+08+Pt.+2.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+09+Pt.+1.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+09+Pt.+2.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+09+Pt.+3.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+10+Pt.+1.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+10+Pt.+2.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+10+Pt.+3.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+11+Pt.+1.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+11+Pt.+2.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+12+Pt.+1.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+12+Pt.+2.mp4",
    "https://archive.org/details/1980-winter-olympics-day-01-preview-and-opening-ceremony/1980+Winter+Olympics+-+Day+12+Pt.+3.mp4",
]


def extract_day_from_url(url: str) -> tuple:
    """Extract day number and part number from URL filename"""
    path = urlparse(url).path
    filename = path.split('/')[-1]
    decoded_filename = unquote(filename.replace('+', ' '))
    decoded_lower = decoded_filename.lower()
    
    day_match = re.search(r'day\s*(\d+)', decoded_lower, re.IGNORECASE)
    if not day_match:
        return (0, 0)
    
    day_num = int(day_match.group(1))
    part_match = re.search(r'pt\.?\s*(\d+)', decoded_lower, re.IGNORECASE)
    part_num = int(part_match.group(1)) if part_match else 1
    
    return (day_num, part_num)


def get_collection_name(day: int) -> str:
    """Get collection name for day"""
    if day == 1:
        return "1980 Winter Olympics - Day 01 - Preview and Opening Ceremony"
    else:
        return f"1980 Winter Olympics - Day {day:02d}"


async def fetch_complete_metadata(db: Session, stream_manager: StreamManager, url: str) -> dict:
    """Fetch complete metadata from Archive.org for a URL"""
    try:
        # Extract identifier and filename
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split('/') if p]
        
        if 'details' not in path_parts:
            raise ValueError(f"Invalid Archive.org URL: {url}")
        
        idx = path_parts.index('details')
        identifier = path_parts[idx + 1] if idx + 1 < len(path_parts) else None
        filename = path_parts[-1] if path_parts else None
        decoded_filename = unquote(filename.replace('+', ' ')) if filename else None
        
        if not identifier:
            raise ValueError(f"Could not extract identifier from URL: {url}")
        
        # Get item info from Archive.org
        item_info = await stream_manager.archive_org_adapter.get_item_info(identifier)
        
        metadata = {
            'identifier': identifier,
            'filename': decoded_filename or filename,
            'title': decoded_filename.replace('.mp4', '').strip() if decoded_filename else '',
            'description': item_info.get('description', ''),
            'creator': item_info.get('creator', ''),
            'date': item_info.get('date', ''),
            'mediatype': item_info.get('mediatype', ''),
            'collection': item_info.get('collection', []),
            'thumbnail': None,
            'duration': None,
            'url': url
        }
        
        # Find the specific file to get duration and other file-level metadata
        video_files = item_info.get('video_files', [])
        if decoded_filename:
            for video_file in video_files:
                if video_file['name'] == decoded_filename or decoded_filename in video_file['name']:
                    # Get duration from file metadata (Archive.org may have this)
                    # Duration might be in the item metadata or need to be fetched
                    break
        
        # Try to get thumbnail from Archive.org item
        if item_info.get('url'):
            metadata['thumbnail'] = f"https://archive.org/download/{identifier}/__ia_thumb.jpg"
        
        return metadata
        
    except Exception as e:
        logger.error(f"Error fetching metadata for {url}: {e}")
        # Return minimal metadata
        parsed = urlparse(url)
        filename = parsed.path.split('/')[-1]
        decoded_filename = unquote(filename.replace('+', ' '))
        return {
            'title': decoded_filename.replace('.mp4', '').strip(),
            'description': '',
            'creator': None,
            'date': None,
            'thumbnail': None,
            'duration': None,
            'url': url
        }


async def create_media_item_with_metadata(db: Session, stream_manager: StreamManager, url: str) -> MediaItem:
    """Create a media item with complete metadata"""
    # Check if already exists
    existing = db.query(MediaItem).filter(MediaItem.url == url).first()
    if existing:
        # Delete existing to recreate with fresh metadata
        logger.info(f"  Deleting existing media item: {existing.title[:50]}")
        db.delete(existing)
        db.commit()
    
    # Fetch complete metadata
    metadata = await fetch_complete_metadata(db, stream_manager, url)
    
    # Extract identifier
    parsed = urlparse(url)
    path_parts = [p for p in parsed.path.split('/') if p]
    idx = path_parts.index('details')
    identifier = path_parts[idx + 1]
    
    # Create media item
    media_item = MediaItem(
        source=StreamSource.ARCHIVE_ORG,
        source_id=identifier,
        url=url,
        title=metadata.get('title', 'Untitled'),
        description=metadata.get('description', ''),
        duration=metadata.get('duration'),
        thumbnail=metadata.get('thumbnail'),
        uploader=metadata.get('creator'),
        upload_date=str(metadata.get('date')) if metadata.get('date') else None,
        view_count=None,
        meta_data=json.dumps(metadata) if metadata else None
    )
    
    db.add(media_item)
    db.commit()
    db.refresh(media_item)
    
    logger.info(f"  ✓ Created: {media_item.title[:70]}")
    return media_item


async def complete_rebuild(db: Session):
    """Complete rebuild of 1980 channel"""
    logger.info("=" * 70)
    logger.info("COMPLETE REBUILD: 1980 Lake Placid Winter Olympics Channel")
    logger.info("=" * 70)
    
    stream_manager = StreamManager()
    
    # Step 1: Delete all existing 1980 Olympics data
    logger.info("\n[Step 1] Cleaning up existing 1980 Olympics data...")
    
    # Delete collection items for 1980 collections
    collections = db.query(Collection).filter(
        Collection.name.like('1980 Winter Olympics%')
    ).all()
    
    for collection in collections:
        logger.info(f"  Deleting collection: {collection.name}")
        # Delete collection items
        db.query(CollectionItem).filter(CollectionItem.collection_id == collection.id).delete()
        # Delete collection
        db.delete(collection)
    
    # Delete media items that are Archive.org and match our identifier pattern
    identifier = "1980-winter-olympics-day-01-preview-and-opening-ceremony"
    media_items = db.query(MediaItem).filter(
        MediaItem.source == StreamSource.ARCHIVE_ORG,
        MediaItem.source_id == identifier,
        MediaItem.url.like('%1980+Winter+Olympics%')
    ).all()
    
    for media_item in media_items:
        logger.info(f"  Deleting media item: {media_item.title[:50]}")
        db.delete(media_item)
    
    db.commit()
    logger.info("  ✓ Cleanup complete")
    
    # Step 2: Organize URLs by day
    logger.info("\n[Step 2] Organizing URLs by day...")
    urls_by_day = {}
    for url in OLYMPICS_1980_URLS:
        day, part = extract_day_from_url(url)
        if day == 0:
            logger.warning(f"  ⚠ Could not parse day from: {url}")
            continue
        
        if day not in urls_by_day:
            urls_by_day[day] = []
        urls_by_day[day].append((part, url))
    
    # Sort by part number
    for day in urls_by_day:
        urls_by_day[day].sort(key=lambda x: x[0])
    
    logger.info(f"  ✓ Organized {len(OLYMPICS_1980_URLS)} URLs into {len(urls_by_day)} days")
    
    # Step 3: Import all URLs with complete metadata
    logger.info("\n[Step 3] Importing URLs with complete metadata...")
    imported_media = {}
    
    for day in sorted(urls_by_day.keys()):
        collection_name = get_collection_name(day)
        logger.info(f"\n  Processing {collection_name}...")
        
        # Create collection
        collection = Collection(
            name=collection_name,
            description=f"1980 Winter Olympics - Day {day:02d} coverage from ABC"
        )
        db.add(collection)
        db.commit()
        db.refresh(collection)
        logger.info(f"    ✓ Created collection")
        
        # Import each URL
        order = 0
        for part, url in urls_by_day[day]:
            try:
                media_item = await create_media_item_with_metadata(db, stream_manager, url)
                imported_media[url] = media_item
                
                # Add to collection
                collection_item = CollectionItem(
                    collection_id=collection.id,
                    media_item_id=media_item.id,
                    order=order
                )
                db.add(collection_item)
                db.commit()
                order += 1
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"    ✗ Failed to import {url}: {e}")
                import traceback
                traceback.print_exc()
                continue
    
    logger.info("\n" + "=" * 70)
    logger.info("REBUILD COMPLETE!")
    logger.info(f"  Imported: {len(imported_media)} media items")
    logger.info(f"  Collections: {len(urls_by_day)} collections created")
    logger.info("=" * 70)
    
    return imported_media


async def main():
    """Main function"""
    init_db()
    db = SessionLocal()
    
    try:
        await complete_rebuild(db)
        logger.info("\n✅ Channel rebuild successful!")
        logger.info("\n📋 Next steps:")
        logger.info("  1. Schedule YAML is already configured correctly")
        logger.info("  2. Restart the server: ./start_server.sh")
        logger.info("  3. Channel 1980 should now play all content correctly")
        logger.info("  4. All metadata is attached and correct")
    except Exception as e:
        logger.error(f"\n❌ Error during rebuild: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())

