#!/usr/bin/env python3
"""
Update metadata for all media items from their source URLs

This script fetches metadata from Archive.org and YouTube for all media items
and updates the database with accurate information.
"""

import sys
import asyncio
from pathlib import Path
from typing import Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from streamtv.database.session import SessionLocal, init_db
from streamtv.database.models import MediaItem
from streamtv.streaming import StreamManager, StreamSource
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def update_media_metadata(media_item: MediaItem, stream_manager: StreamManager, db) -> bool:
    """Update metadata for a single media item"""
    try:
        # Detect source
        source = stream_manager.detect_source(media_item.url)
        if source == StreamSource.UNKNOWN:
            logger.warning(f"Unknown source for media {media_item.id}: {media_item.url}")
            return False
        
        # Get media information from source
        # For Archive.org URLs with specific files, we need special handling
        if source == StreamSource.ARCHIVE_ORG and stream_manager.archive_org_adapter:
            # Extract identifier and filename from URL
            identifier = stream_manager.archive_org_adapter.extract_identifier(media_item.url)
            filename = None
            
            # Extract filename from URL if it's a direct file URL
            # Format: https://archive.org/details/IDENTIFIER/FILENAME.mp4
            if '/details/' in media_item.url:
                url_parts = media_item.url.split('/details/')
                if len(url_parts) > 1:
                    path_parts = url_parts[1].split('/')
                    if len(path_parts) > 1:
                        filename = path_parts[1]
            
            if identifier:
                # Get item info using identifier
                # We need to access the raw API response to get file-level metadata
                import httpx
                client = await stream_manager.archive_org_adapter._ensure_authenticated()
                try:
                    url = f"{stream_manager.archive_org_adapter.base_url}/metadata/{identifier}"
                    headers = {"Accept": "application/json"}
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    
                    metadata = data.get('metadata', {})
                    files = data.get('files', [])
                    
                    # Build media_info from item metadata
                    media_info = {
                        'title': metadata.get('title', ''),
                        'description': metadata.get('description', ''),
                        'creator': metadata.get('creator', ''),
                        'date': metadata.get('date', ''),
                        'uploader': metadata.get('creator', ''),
                        'upload_date': metadata.get('date', ''),
                    }
                    
                    # If we have a filename, find it in files to get duration
                    if filename:
                        # URL decode the filename for comparison
                        import urllib.parse
                        decoded_filename = urllib.parse.unquote(filename)
                        for file_info in files:
                            file_name = file_info.get('name', '')
                            if decoded_filename == file_name or filename == file_name or decoded_filename in file_name or filename in file_name:
                                # Extract duration from file metadata
                                # Archive.org files have 'length' field in seconds
                                if 'length' in file_info:
                                    try:
                                        length_val = file_info['length']
                                        if isinstance(length_val, str):
                                            media_info['duration'] = int(float(length_val))
                                        else:
                                            media_info['duration'] = int(float(length_val))
                                    except (ValueError, TypeError):
                                        pass
                                break
                finally:
                    await client.aclose()
            else:
                # Fallback to standard method
                media_info = await stream_manager.get_media_info(media_item.url, source)
        else:
            # For YouTube or other sources, use standard method
            media_info = await stream_manager.get_media_info(media_item.url, source)
        
        # Update metadata fields
        updated = False
        
        # Update title if we got a better one
        if media_info.get('title') and media_info.get('title') != media_item.title:
            old_title = media_item.title
            media_item.title = media_info.get('title')
            logger.info(f"  Updated title: {old_title[:50]} -> {media_info.get('title')[:50]}")
            updated = True
        
        # Update description
        if media_info.get('description'):
            media_item.description = media_info.get('description')
            updated = True
        
        # Update duration (prefer source duration if available)
        if media_info.get('duration') and media_info.get('duration') > 0:
            if not media_item.duration or media_item.duration == 0:
                media_item.duration = media_info.get('duration')
                updated = True
        
        # Update thumbnail
        if media_info.get('thumbnail'):
            media_item.thumbnail = media_info.get('thumbnail')
            updated = True
        
        # Update uploader/creator
        uploader = media_info.get('uploader') or media_info.get('creator')
        if uploader:
            media_item.uploader = uploader
            updated = True
        
        # Update upload date
        upload_date = media_info.get('upload_date') or media_info.get('date')
        if upload_date:
            media_item.upload_date = str(upload_date)
            updated = True
        
        # Update view count
        if media_info.get('view_count'):
            media_item.view_count = media_info.get('view_count')
            updated = True
        
        # Update source_id if we can extract it better
        if source == StreamSource.YOUTUBE and stream_manager.youtube_adapter:
            video_id = stream_manager.youtube_adapter.extract_video_id(media_item.url)
            if video_id and video_id != media_item.source_id:
                media_item.source_id = video_id
                updated = True
        elif source == StreamSource.ARCHIVE_ORG and stream_manager.archive_org_adapter:
            identifier = stream_manager.archive_org_adapter.extract_identifier(media_item.url)
            if identifier and identifier != media_item.source_id:
                media_item.source_id = identifier
                updated = True
        
        if updated:
            db.commit()
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error updating metadata for media {media_item.id} ({media_item.url}): {e}")
        return False


async def update_all_metadata():
    """Update metadata for all media items"""
    init_db()
    db = SessionLocal()
    stream_manager = StreamManager()
    
    try:
        # Get all media items
        media_items = db.query(MediaItem).all()
        total = len(media_items)
        
        logger.info(f"Found {total} media items to update")
        logger.info("=" * 60)
        
        updated_count = 0
        error_count = 0
        skipped_count = 0
        
        for i, media_item in enumerate(media_items, 1):
            logger.info(f"[{i}/{total}] Processing: {media_item.title[:60]}...")
            logger.info(f"  URL: {media_item.url[:80]}...")
            
            try:
                result = await update_media_metadata(media_item, stream_manager, db)
                if result:
                    updated_count += 1
                    logger.info(f"  ✓ Metadata updated")
                else:
                    skipped_count += 1
                    logger.info(f"  - No updates needed")
            except Exception as e:
                error_count += 1
                logger.error(f"  ✗ Error: {e}")
            
            # Small delay to avoid rate limiting
            if i % 10 == 0:
                await asyncio.sleep(1)
        
        logger.info("=" * 60)
        logger.info(f"Update complete!")
        logger.info(f"  Total items: {total}")
        logger.info(f"  Updated: {updated_count}")
        logger.info(f"  Skipped: {skipped_count}")
        logger.info(f"  Errors: {error_count}")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(update_all_metadata())

