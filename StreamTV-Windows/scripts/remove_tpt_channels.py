#!/usr/bin/env python3
"""
Remove TPT channels (2 and 3) from the database

This script removes channels 2 and 3 (TPT channels) and all associated data
including playlists, playlist items, and media items.

Usage:
    python scripts/remove_tpt_channels.py
"""

import sys
from pathlib import Path

# Add parent directory to path to import streamtv modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from streamtv.database.session import SessionLocal, init_db
from streamtv.database.models import Channel, Playlist, PlaylistItem, MediaItem
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def remove_tpt_channels():
    """Remove TPT channels 2 and 3 from the database"""
    db = SessionLocal()
    
    try:
        # Initialize database
        init_db()
        
        # Find channels 2 and 3
        channels_to_remove = db.query(Channel).filter(Channel.number.in_(["2", "3"])).all()
        
        if not channels_to_remove:
            logger.info("No TPT channels (2 or 3) found in database")
            return True
        
        for channel in channels_to_remove:
            logger.info(f"Removing channel {channel.number} - {channel.name}")
            
            # Get all playlists for this channel
            playlists = db.query(Playlist).filter(Playlist.channel_id == channel.id).all()
            
            for playlist in playlists:
                logger.info(f"  Removing playlist: {playlist.name}")
                
                # Get all playlist items
                playlist_items = db.query(PlaylistItem).filter(
                    PlaylistItem.playlist_id == playlist.id
                ).all()
                
                for item in playlist_items:
                    # Get media item
                    media_item = db.query(MediaItem).filter(MediaItem.id == item.media_item_id).first()
                    if media_item:
                        logger.info(f"    Removing media item: {media_item.title}")
                        # Delete playlist item first (foreign key constraint)
                        db.delete(item)
                        # Delete media item if it's not used by other playlists
                        other_items = db.query(PlaylistItem).filter(
                            PlaylistItem.media_item_id == media_item.id
                        ).count()
                        if other_items == 0:
                            db.delete(media_item)
                            logger.info(f"      Deleted media item: {media_item.title}")
                
                # Delete playlist
                db.delete(playlist)
            
            # Delete channel
            db.delete(channel)
            logger.info(f"  Deleted channel {channel.number}")
        
        db.commit()
        logger.info("\n✅ TPT channels removed successfully!")
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"✗ Error removing TPT channels: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    try:
        success = remove_tpt_channels()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n⚠️  Cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

