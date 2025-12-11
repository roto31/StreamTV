#!/usr/bin/env python3
"""
Import collections from retro_olympics_streams.yaml

This script:
1. Reads the YAML file with all media items
2. Groups media items by collection name
3. Creates Collection entries in the database
4. Adds media items to their respective collections
"""

import sys
import yaml
from pathlib import Path
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from streamtv.database.session import SessionLocal, init_db
from streamtv.database.models import Collection, CollectionItem, MediaItem

def import_collections():
    """Import collections from YAML file"""
    db = SessionLocal()
    
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
        
        # Group streams by collection name
        collection_map = defaultdict(list)
        for stream in streams:
            collection_name = stream.get('collection')
            if collection_name:
                collection_map[collection_name].append(stream)
        
        print(f"Found {len(collection_map)} unique collections\n")
        
        # Create collections and add items
        created_count = 0
        updated_count = 0
        
        for collection_name, stream_list in collection_map.items():
            # Check if collection already exists
            existing = db.query(Collection).filter(Collection.name == collection_name).first()
            
            if existing:
                collection = existing
                print(f"  Using existing collection: {collection_name}")
            else:
                collection = Collection(
                    name=collection_name,
                    description=f"Collection for {collection_name}"
                )
                db.add(collection)
                db.commit()
                db.refresh(collection)
                created_count += 1
                print(f"  ✓ Created collection: {collection_name}")
            
            # Add media items to collection
            for stream in stream_list:
                url = stream.get('url')
                if not url:
                    continue
                
                # Find media item by URL
                media_item = db.query(MediaItem).filter(MediaItem.url == url).first()
                if not media_item:
                    print(f"    Warning: Media item not found for URL: {url[:50]}...")
                    continue
                
                # Check if already in collection
                existing_item = db.query(CollectionItem).filter(
                    CollectionItem.collection_id == collection.id,
                    CollectionItem.media_item_id == media_item.id
                ).first()
                
                if not existing_item:
                    # Get current max order
                    max_order = db.query(CollectionItem).filter(
                        CollectionItem.collection_id == collection.id
                    ).count()
                    
                    collection_item = CollectionItem(
                        collection_id=collection.id,
                        media_item_id=media_item.id,
                        order=max_order
                    )
                    db.add(collection_item)
                    db.commit()
                    updated_count += 1
                    print(f"    ✓ Added: {media_item.title[:50]}")
        
        print(f"\n{'='*60}")
        print(f"Import complete!")
        print(f"  Created: {created_count} new collections")
        print(f"  Updated: {updated_count} collection items added")
        print(f"  Total collections: {len(collection_map)}")
        print(f"{'='*60}")
        
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    import_collections()

