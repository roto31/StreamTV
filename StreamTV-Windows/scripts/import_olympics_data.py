#!/usr/bin/env python3
"""
Import Winter Olympics media data from retro_olympics_streams.yaml

This script:
1. Reads the YAML file with all media items
2. Creates media items in the database
3. Creates playlists for each Olympic year (1980, 1984, 1988)
4. Adds media items to the appropriate playlists
5. Assigns playlists to channels
"""

import sys
import yaml
from pathlib import Path
from datetime import datetime
import re

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from streamtv.database.session import SessionLocal, init_db
from streamtv.database.models import Channel, MediaItem, Playlist, PlaylistItem, StreamSource
from streamtv.streaming import StreamManager

def parse_duration(duration_str):
    """Parse ISO 8601 duration (PT3M44S) to seconds"""
    if not duration_str:
        return None
    
    # Remove PT prefix
    duration_str = duration_str.replace('PT', '')
    
    total_seconds = 0
    
    # Parse hours
    hours_match = re.search(r'(\d+)H', duration_str)
    if hours_match:
        total_seconds += int(hours_match.group(1)) * 3600
    
    # Parse minutes
    minutes_match = re.search(r'(\d+)M', duration_str)
    if minutes_match:
        total_seconds += int(minutes_match.group(1)) * 60
    
    # Parse seconds
    seconds_match = re.search(r'(\d+)S', duration_str)
    if seconds_match:
        total_seconds += int(seconds_match.group(1))
    
    return total_seconds if total_seconds > 0 else None

def import_media_data():
    """Import media data from YAML file"""
    db = SessionLocal()
    stream_manager = StreamManager()
    
    try:
        # Initialize database
        init_db()
        
        # Load YAML file
        yaml_file = Path(__file__).parent.parent / "data" / "retro_olympics_streams.yaml"
        if not yaml_file.exists():
            print(f"Error: {yaml_file} not found")
            return
        
        with open(yaml_file, 'r') as f:
            data = yaml.safe_load(f)
        
        streams = data.get('streams', [])
        print(f"Found {len(streams)} media items in YAML file\n")
        
        # Get channels
        channel_1980 = db.query(Channel).filter(Channel.number == "1980").first()
        channel_1984 = db.query(Channel).filter(Channel.number == "1984").first()
        channel_1988 = db.query(Channel).filter(Channel.number == "1988").first()
        
        if not all([channel_1980, channel_1984, channel_1988]):
            print("Error: Winter Olympics channels not found. Please create them first.")
            return
        
        # Create playlists for each year
        playlists = {}
        for year in [1980, 1984, 1988]:
            channel = db.query(Channel).filter(Channel.number == str(year)).first()
            playlist_name = f"MN Winter Olympics {year} - Main Playlist"
            
            # Check if playlist already exists
            existing = db.query(Playlist).filter(
                Playlist.name == playlist_name,
                Playlist.channel_id == channel.id
            ).first()
            
            if existing:
                playlists[year] = existing
                print(f"Using existing playlist for {year}")
            else:
                playlist = Playlist(
                    name=playlist_name,
                    description=f"Main playlist for {year} Winter Olympics",
                    channel_id=channel.id
                )
                db.add(playlist)
                db.commit()
                db.refresh(playlist)
                playlists[year] = playlist
                print(f"✓ Created playlist for {year}")
        
        # Import media items
        imported_count = 0
        skipped_count = 0
        
        for stream in streams:
            year = stream.get('year')
            if not year or year not in [1980, 1984, 1988]:
                continue
            
            url = stream.get('url')
            if not url:
                continue
            
            # Check if media item already exists
            existing = db.query(MediaItem).filter(MediaItem.url == url).first()
            if existing:
                media_item = existing
                skipped_count += 1
            else:
                # Determine source
                source_str = stream.get('source', '').lower()
                if 'youtube' in source_str or 'youtu.be' in url or 'youtube.com' in url:
                    source = StreamSource.YOUTUBE
                elif 'archive' in source_str or 'archive.org' in url:
                    source = StreamSource.ARCHIVE_ORG
                else:
                    source = StreamSource.YOUTUBE  # Default
                
                # Extract source ID
                source_id = ""
                if source == StreamSource.YOUTUBE:
                    # Extract YouTube video ID
                    import re
                    match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
                    if match:
                        source_id = match.group(1)
                elif source == StreamSource.ARCHIVE_ORG:
                    # Extract Archive.org identifier
                    match = re.search(r'archive\.org\/details\/([^\/\?]+)', url)
                    if match:
                        source_id = match.group(1)
                
                # Get title
                title = stream.get('collection', 'Untitled')
                if not title or title == 'Untitled':
                    title = stream.get('id', 'Media Item')
                
                # Parse duration
                duration = parse_duration(stream.get('runtime'))
                
                # Create media item
                media_item = MediaItem(
                    source=source,
                    source_id=source_id or url,
                    url=url,
                    title=title,
                    description=stream.get('notes', ''),
                    duration=duration,
                    uploader=stream.get('network', None),
                    upload_date=str(stream.get('broadcast_date', '')) if stream.get('broadcast_date') else None
                )
                db.add(media_item)
                db.commit()
                db.refresh(media_item)
                imported_count += 1
                print(f"  ✓ Imported: {title[:50]}")
            
            # Add to playlist
            playlist = playlists[year]
            
            # Check if already in playlist
            existing_item = db.query(PlaylistItem).filter(
                PlaylistItem.playlist_id == playlist.id,
                PlaylistItem.media_item_id == media_item.id
            ).first()
            
            if not existing_item:
                # Get current max order
                max_order = db.query(PlaylistItem).filter(
                    PlaylistItem.playlist_id == playlist.id
                ).count()
                
                playlist_item = PlaylistItem(
                    playlist_id=playlist.id,
                    media_item_id=media_item.id,
                    order=max_order
                )
                db.add(playlist_item)
                db.commit()
        
        print(f"\n{'='*60}")
        print(f"Import complete!")
        print(f"  Imported: {imported_count} new media items")
        print(f"  Skipped: {skipped_count} existing media items")
        print(f"  Total streams processed: {len(streams)}")
        print(f"{'='*60}")
        
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    import_media_data()

