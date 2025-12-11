#!/usr/bin/env python3
"""
Metadata Enrichment Script for StreamTV
Fetches metadata from TVDB/TVMaze/TMDB and enhances channel content
"""

import sys
import asyncio
import json
import re
from pathlib import Path
from typing import Optional
import argparse

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from streamtv.database.session import SessionLocal
from streamtv.database.models import Channel, MediaItem, Collection, CollectionItem
from streamtv.config import config
from streamtv.utils.metadata_providers import create_metadata_manager


def parse_episode_from_title(title: str) -> tuple:
    """Extract season and episode from title"""
    patterns = [
        r'[sS](\d+)[eE](\d+)',  # S01E01
        r'(\d+)x(\d+)',          # 1x01
        r'[Ss]eason\s+(\d+).*?[Ee]pisode\s+(\d+)',  # Season 1 Episode 01
    ]
    
    for pattern in patterns:
        match = re.search(pattern, title)
        if match:
            return int(match.group(1)), int(match.group(2))
    
    return None, None


async def enrich_channel_metadata(
    channel_number: str,
    series_name: str,
    series_year: Optional[int] = None,
    dry_run: bool = False,
    force: bool = False
):
    """
    Enrich all media items in a channel with metadata from TVDB/TVMaze
    
    Args:
        channel_number: Channel number to enrich
        series_name: Name of the TV series (e.g., "Magnum P.I.")
        series_year: Year series started (for better matching)
        dry_run: Preview what would be updated without making changes
        force: Re-fetch metadata even if already exists
    """
    db = SessionLocal()
    
    try:
        # Find channel
        channel = db.query(Channel).filter(Channel.number == channel_number).first()
        if not channel:
            print(f"❌ Channel {channel_number} not found")
            return
        
        print(f"📺 Channel: {channel.name}")
        print(f"   Series: {series_name}")
        if series_year:
            print(f"   Year: {series_year}")
        print()
        
        # Create metadata manager
        metadata_manager = create_metadata_manager(
            tvdb_api_key=config.metadata.tvdb_api_key,
            tvdb_read_token=config.metadata.tvdb_read_token,
            tmdb_api_key=config.metadata.tmdb_api_key,
            enable_tvdb=config.metadata.enable_tvdb,
            enable_tvmaze=config.metadata.enable_tvmaze,
            enable_tmdb=config.metadata.enable_tmdb
        )
        
        # Get all media items for this channel via collections
        collections = db.query(Collection).filter(
            Collection.name.like(f"%{series_name}%")
        ).all()
        
        if not collections:
            print(f"⚠️  No collections found for '{series_name}'")
            return
        
        print(f"📚 Found {len(collections)} collections")
        
        total_items = 0
        updated_items = 0
        skipped_items = 0
        failed_items = 0
        metadata_cache = {}  # Cache fetched metadata to reuse for duplicates
        
        for collection in collections:
            print(f"\n📁 Collection: {collection.name}")
            
            # Parse season from collection name
            season_match = re.search(r'Season\s+(\d+)', collection.name)
            if not season_match:
                print(f"  ⚠️  Could not parse season from collection name")
                continue
            
            season = int(season_match.group(1))
            
            items = db.query(CollectionItem).filter(
                CollectionItem.collection_id == collection.id
            ).order_by(CollectionItem.order).all()
            
            for item in items:
                media_item = db.query(MediaItem).filter(
                    MediaItem.id == item.media_item_id
                ).first()
                
                if not media_item:
                    continue
                
                total_items += 1
                
                # Skip if already has metadata and not forcing
                if not force and media_item.meta_data:
                    skipped_items += 1
                    continue
                
                # Parse episode from URL (to handle duplicates correctly)
                episode_match = re.search(r'(\d+)x(\d+)|[sS](\d+)[eE](\d+)', media_item.url)
                if episode_match:
                    episode = int(episode_match.group(2) or episode_match.group(4))
                else:
                    print(f"  ⚠️  Could not parse episode from URL")
                    failed_items += 1
                    continue
                
                # Check cache for this S/E combo (to reuse for duplicates)
                cache_key = f"S{season:02d}E{episode:02d}"
                if cache_key in metadata_cache:
                    metadata = metadata_cache[cache_key]
                    if metadata:
                        print(f"  💾 Using cached metadata for {cache_key}")
                    else:
                        skipped_items += 1
                        continue
                else:
                    # Fetch metadata
                    print(f"  📡 Fetching {cache_key}...")
                    
                    metadata = await metadata_manager.get_tv_episode_metadata(
                        series_name=series_name,
                        season=season,
                        episode=episode,
                        year=series_year
                    )
                    
                    # Cache the result (even if None)
                    metadata_cache[cache_key] = metadata
                    
                    # Small delay to respect rate limits
                    await asyncio.sleep(0.1)
                
                if metadata:
                    if dry_run:
                        print(f"     [DRY RUN] Would update:")
                        print(f"       Title: {metadata.get('title')}")
                        print(f"       Description: {metadata.get('description', '')[:60]}...")
                        print(f"       Source: {metadata.get('source')}")
                    else:
                        # Update media item
                        media_item.title = metadata.get('title', media_item.title)
                        media_item.description = metadata.get('description', media_item.description)
                        media_item.thumbnail = metadata.get('thumbnail', media_item.thumbnail)
                        
                        # Store duration if available
                        if metadata.get('runtime'):
                            media_item.duration = metadata.get('runtime') * 60  # Convert to seconds
                        
                        # Store full metadata in meta_data field
                        media_item.meta_data = json.dumps(metadata)
                        
                        print(f"     ✅ Updated: {metadata.get('title')}")
                        print(f"        Source: {metadata.get('source')}")
                        updated_items += 1
                else:
                    # No metadata found
                    if cache_key not in metadata_cache:
                        print(f"     ❌ No metadata found for {cache_key}")
                    failed_items += 1
        
        if not dry_run:
            db.commit()
            print(f"\n💾 Changes committed to database")
        
        # Summary
        print(f"\n{'='*60}")
        print(f"📊 Enrichment Summary")
        print(f"{'='*60}")
        print(f"Total items: {total_items}")
        print(f"Updated: {updated_items}")
        print(f"Skipped: {skipped_items} (already had metadata)")
        print(f"Failed: {failed_items} (no metadata found)")
        print(f"{'='*60}")
        
        if dry_run:
            print("\n💡 This was a dry run. Use --apply to actually update the database.")
        else:
            print("\n✅ Metadata enrichment complete!")
            print("   Restart StreamTV server to see the changes in EPG.")
        
    finally:
        db.close()


def main():
    """Main execution"""
    parser = argparse.ArgumentParser(
        description="Enrich channel metadata with TVDB/TVMaze/TMDB data"
    )
    parser.add_argument(
        'channel_number',
        help='Channel number to enrich (e.g., 80)'
    )
    parser.add_argument(
        'series_name',
        help='TV series name (e.g., "Magnum P.I.")'
    )
    parser.add_argument(
        '--year', '-y',
        type=int,
        help='Series start year for better matching'
    )
    parser.add_argument(
        '--dry-run', '-d',
        action='store_true',
        help='Preview changes without updating database'
    )
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Re-fetch metadata even if already exists'
    )
    
    args = parser.parse_args()
    
    # Check if metadata is enabled in config
    if not config.metadata.enabled:
        print("⚠️  Metadata enrichment is disabled in config.yaml")
        print("   Set metadata.enabled = true to enable it")
        sys.exit(1)
    
    # Check if we have API credentials
    if not config.metadata.tvdb_read_token and not config.metadata.tvdb_api_key:
        if not config.metadata.enable_tvmaze:
            print("❌ No TVDB credentials configured and TVMaze is disabled")
            print("   Add TVDB credentials or enable TVMaze in config.yaml")
            sys.exit(1)
        else:
            print("⚠️  No TVDB credentials - using TVMaze only (free fallback)")
    
    # Run enrichment
    asyncio.run(enrich_channel_metadata(
        channel_number=args.channel_number,
        series_name=args.series_name,
        series_year=args.year,
        dry_run=args.dry_run,
        force=args.force
    ))


if __name__ == '__main__':
    main()

