#!/usr/bin/env python3
"""
Create Sesame Street Channel
Parses multiple Archive.org collections spanning 1969-2010s
Filters out .ia.mp4 duplicate files (uses only regular .mp4)
"""

import asyncio
import sys
import yaml
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Collection identifiers
COLLECTIONS = [
    {
        'identifier': 'sesame-street_202306',
        'era': '1960s-1970s',
        'description': 'Classic Sesame Street episodes from the early years'
    },
    {
        'identifier': 'sesame-street-1980s',
        'era': '1980s',
        'description': 'Sesame Street episodes from the 1980s'
    },
    {
        'identifier': 'sesame-street-1990s',
        'era': '1990s',
        'description': 'Sesame Street episodes from the 1990s'
    },
    {
        'identifier': 'sesame-street-2000s',
        'era': '2000s',
        'description': 'Sesame Street episodes from the 2000s'
    },
    {
        'identifier': 'sesame-street-2010s',
        'era': '2010s',
        'description': 'Sesame Street episodes from the 2010s'
    },
    {
        'identifier': 'sesame-street_202308',
        'era': 'Additional',
        'description': 'Additional Sesame Street episodes'
    },
    {
        'identifier': 'sesame-street-s-40-e-01-frankly-its-becoming-a-habitat',
        'era': 'Season 40',
        'description': 'Sesame Street Season 40 Episode 1'
    },
]


async def parse_collection(
    identifier: str,
    era: str,
    description: str
) -> List[Dict[str, Any]]:
    """Parse a single collection from Archive.org"""
    print(f"\n{'='*70}")
    print(f"Processing: {identifier}")
    print(f"Era: {era}")
    print(f"{'='*70}")
    
    try:
        # Get collection info using httpx directly
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"https://archive.org/metadata/{identifier}")
            item_info = response.json()
        
        files = item_info.get('files', [])
        
        # Filter video files:
        # 1. Must be .mp4 format (or other video formats)
        # 2. Must NOT end with .ia.mp4 (these are duplicates)
        # 3. Must be original files (not derivatives)
        video_formats = ['MPEG4', 'h.264', 'Matroska', 'AVI', 'WebM']
        video_extensions = ('.mp4', '.mkv', '.webm', '.mov', '.m4v')
        
        video_files = []
        for f in files:
            name = f.get('name', '')
            
            # Skip .ia.mp4 files (duplicates)
            if name.endswith('.ia.mp4'):
                continue
            
            # Check if it's a video file
            is_video = (
                (name.lower().endswith(video_extensions) or
                 f.get('format', '') in video_formats) and
                f.get('source') == 'original'
            )
            
            if is_video:
                video_files.append(f)
        
        print(f"Found {len(video_files)} video files (excluding .ia.mp4 duplicates)")
        
        episodes = []
        
        # Sort files by name
        video_files.sort(key=lambda x: x.get('name', ''))
        
        for idx, file_info in enumerate(video_files, start=1):
            filename = file_info.get('name', '')
            
            # Extract episode number from filename
            # Pattern: "Sesame Street - Episode 0001 (November 10, 1969).mp4"
            episode_match = re.search(r'Episode\s+(\d+)', filename, re.IGNORECASE)
            
            if episode_match:
                episode_num = int(episode_match.group(1))
            else:
                # Fallback: use sequential numbering
                episode_num = idx
            
            # Extract air date from filename if available
            date_match = re.search(r'\(([^)]+\d{4})\)', filename)
            air_date_str = date_match.group(1) if date_match else None
            
            # Build stream URL
            # Use proper URL encoding
            from urllib.parse import quote
            encoded_filename = quote(filename)
            stream_url = f"https://archive.org/download/{identifier}/{encoded_filename}"
            
            # Build episode data
            episode_data = {
                'episode_num': episode_num,
                'filename': filename,
                'url': stream_url,
                'source': 'archive',
                'type': 'event',
                'era': era,
                'collection_name': identifier,
                'air_date_text': air_date_str
            }
            
            # Create title from filename (will be enriched later)
            if air_date_str:
                episode_data['title'] = f"Sesame Street Episode {episode_num} ({air_date_str})"
            else:
                episode_data['title'] = f"Sesame Street Episode {episode_num}"
            
            episode_data['description'] = f"Sesame Street Episode {episode_num} from {era}. Metadata to be enriched from TVDB."
            
            episodes.append(episode_data)
            
            if idx <= 3 or idx > len(video_files) - 3:
                print(f"  {'First' if idx <= 3 else 'Last'} Episode {episode_num}: {filename[:70]}...")
        
        print(f"✅ Processed {len(episodes)} episodes from {era}")
        return episodes
        
    except Exception as e:
        print(f"❌ Error processing {identifier}: {e}")
        return []


async def create_channel_yaml(all_episodes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create the channel YAML structure"""
    
    # Sort episodes by episode number
    all_episodes.sort(key=lambda x: x['episode_num'])
    
    # Build channel structure
    channel_data = {
        'channels': [{
            'number': '123',  # 1-2-3 - iconic Sesame Street counting reference
            'name': 'Sesame Street',
            'group': 'Classic PBS',
            'description': 'Sesame Street - Classic episodes from 1969 to 2010s. Can you tell me how to get to Sesame Street?',
            'enabled': True,
            'streams': []
        }]
    }
    
    # Add all episodes as streams
    for episode in all_episodes:
        stream_entry = {
            'id': f"sesame_e{episode['episode_num']:04d}",
            'collection': f"Sesame Street - {episode['era']}",
            'type': 'event',
            'source': 'archive',
            'url': episode['url'],
            'title': episode['title'],
            'description': episode['description'],
        }
        
        if episode.get('air_date_text'):
            stream_entry['notes'] = f"Original air date: {episode['air_date_text']}"
        
        channel_data['channels'][0]['streams'].append(stream_entry)
    
    return channel_data


async def create_schedule_yaml(all_episodes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create the schedule YAML structure"""
    
    # Group by era for organization
    eras_data = {}
    for episode in all_episodes:
        era = episode['era']
        if era not in eras_data:
            eras_data[era] = []
        eras_data[era].append(episode)
    
    schedule_data = {
        'name': "Sesame Street Marathon",
        'description': "24/7 marathon of classic Sesame Street episodes in chronological order, spanning from 1969 to the 2010s.",
        'content': []
    }
    
    # Add content definitions for each era
    for era in eras_data.keys():
        schedule_data['content'].append({
            'key': era.lower().replace(' ', '_').replace('-', '_'),
            'collection': f"Sesame Street - {era}",
            'order': 'chronological'
        })
    
    # Add sequence (all eras in order)
    schedule_data['sequence'] = []
    for era in eras_data.keys():
        schedule_data['sequence'].append({
            'content': era.lower().replace(' ', '_').replace('-', '_'),
            'type': 'block'
        })
    
    return schedule_data


async def main():
    """Main execution"""
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║                                                                    ║")
    print("║          Sesame Street Channel Creator (Channel 123)              ║")
    print("║            From Archive.org - 1969 to 2010s                        ║")
    print("║                                                                    ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print()
    print("🎭 Filtering: Excluding .ia.mp4 duplicate files")
    print("📺 Format: MP4 only (H.264) for zero transcoding")
    print()
    
    # Process all collections
    all_episodes = []
    
    for collection in COLLECTIONS:
        episodes = await parse_collection(
            collection['identifier'],
            collection['era'],
            collection['description']
        )
        all_episodes.extend(episodes)
        
        # Brief pause between collections
        await asyncio.sleep(1)
    
    print(f"\n{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    print(f"Total episodes collected: {len(all_episodes)}")
    print(f"Collections processed: {len(COLLECTIONS)}")
    print(f"Episode range: {min(e['episode_num'] for e in all_episodes) if all_episodes else 0} - {max(e['episode_num'] for e in all_episodes) if all_episodes else 0}")
    print()
    
    # Create channel YAML
    print("Creating channel YAML...")
    channel_data = await create_channel_yaml(all_episodes)
    
    # Save channel YAML
    channel_yaml_path = Path(__file__).parent.parent / 'data' / 'channels_sesame_street.yaml'
    with open(channel_yaml_path, 'w') as f:
        yaml.dump(channel_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    print(f"✅ Saved channel YAML: {channel_yaml_path}")
    
    # Create schedule YAML
    print("Creating schedule YAML...")
    schedule_data = await create_schedule_yaml(all_episodes)
    
    # Save schedule YAML
    schedule_yaml_path = Path(__file__).parent.parent / 'schedules' / '123.yml'
    with open(schedule_yaml_path, 'w') as f:
        yaml.dump(schedule_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    print(f"✅ Saved schedule YAML: {schedule_yaml_path}")
    
    print()
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║                                                                    ║")
    print("║                    ✅ CHANNEL CREATED! ✅                          ║")
    print("║                                                                    ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print()
    print(f"Channel Number: 123 (1-2-3 counting!)")
    print(f"Channel Name: Sesame Street")
    print(f"Total Episodes: {len(all_episodes)}")
    print(f"Episode Range: {min(e['episode_num'] for e in all_episodes) if all_episodes else 0} - {max(e['episode_num'] for e in all_episodes) if all_episodes else 0}")
    print()
    print("Next steps:")
    print("1. Import channel: python scripts/import_channels.py data/channels_sesame_street.yaml")
    print("2. Enrich metadata: python scripts/enrich_metadata.py --channel 123 --series-name 'Sesame Street' --year 1969")
    print("3. Restart StreamTV: ./start_server.sh")
    print()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

