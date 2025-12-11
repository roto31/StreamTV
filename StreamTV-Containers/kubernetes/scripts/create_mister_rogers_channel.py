#!/usr/bin/env python3
"""
Create Mister Rogers' Neighborhood Channel (IPOY 143)
Parses 29 seasons from Archive.org and enriches with TVDB metadata
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

from streamtv.streaming.archive_org_adapter import ArchiveOrgAdapter
from streamtv.utils.metadata_providers import MetadataManager
from streamtv.config import config

# Season collections mapping
SEASON_COLLECTIONS = {
    3: "ipoy143season3",
    4: "ipoy143season4",
    5: "ipoy143season5",
    6: "ipoy143season6",
    7: "ipoy143season7",
    8: "ipoy143season8",
    9: "ipoy143season9",
    10: "ipoy143season10",
    11: "ipoy143season11",
    12: "ipoy143season12",
    13: "ipoy143season13",
    14: "ipoy143season14",
    15: "ipoy143season15",
    16: "ipoy143season16",
    17: "ipoy143season17",
    18: "ipoy143season18",
    19: "ipoy143season19",
    20: "ipoy143season20",
    21: "ipoy143season21",
    22: "ipoy143season22",
    23: "ipoy143season23",
    24: "ipoy143season24",
    25: "ipoy143season25",
    26: "ipoy143season26",
    27: "ipoy143season27",
    28: "ipoy143season28",
    29: "ipoy143season29",
    30: "ipoy143season30",
    31: "ipoy143season31",
}

# TVDB Series ID for Mister Rogers' Neighborhood
TVDB_SERIES_ID = "77526"  # From the TVDB URL


async def fetch_tvdb_metadata(season: int, episode: int) -> Optional[Dict[str, Any]]:
    """Fetch TVDB metadata for a specific episode"""
    # Skip TVDB for now - we'll enrich metadata after import using enrich_metadata.py
    # This speeds up the initial channel creation significantly
    return None


async def parse_season_collection(
    identifier: str,
    season: int,
    archive_adapter: ArchiveOrgAdapter
) -> List[Dict[str, Any]]:
    """Parse a single season collection from Archive.org"""
    print(f"\n{'='*70}")
    print(f"Processing Season {season}: {identifier}")
    print(f"{'='*70}")
    
    try:
        # Get collection info using httpx directly
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"https://archive.org/metadata/{identifier}")
            item_info = response.json()
        
        files = item_info.get('files', [])
        
        # Filter video files (check both extension and format field)
        video_formats = ['MPEG4', 'h.264', 'Matroska', 'AVI', 'WebM']
        video_extensions = ('.mp4', '.avi', '.mkv', '.webm', '.mov', '.m4v', '.mpg', '.mpeg')
        
        video_files = [
            f for f in files
            if (f.get('name', '').lower().endswith(video_extensions) or
                f.get('format', '') in video_formats) and
               f.get('source') == 'original'  # Only original files, not derivatives
        ]
        
        print(f"Found {len(video_files)} video files")
        
        episodes = []
        
        # Sort files by name
        video_files.sort(key=lambda x: x.get('name', ''))
        
        for idx, file_info in enumerate(video_files, start=1):
            filename = file_info.get('name', '')
            
            # Try to extract episode number from filename
            # Files are named like 1066.mp4, 1067.mp4 etc. (episode numbers)
            # Also try patterns like: S03E01, 3x01, Episode 01, etc.
            
            # First try: just the number (like 1066.mp4)
            number_match = re.search(r'^(\d+)\.', filename)
            if number_match:
                # Use last 2 digits as episode number (1066 -> episode 66)
                full_num = int(number_match.group(1))
                episode_num = full_num % 100 if full_num >= 100 else full_num
            else:
                # Try other patterns
                episode_match = re.search(r'(?:e|ep|episode)[\s_-]?(\d+)', filename, re.IGNORECASE)
                if episode_match:
                    episode_num = int(episode_match.group(1))
                else:
                    # Fallback: use file index
                    episode_num = idx
            
            print(f"  Episode {episode_num}: {filename[:60]}...")
            
            # Build stream URL
            stream_url = f"https://archive.org/download/{identifier}/{filename}"
            
            # Build episode data (metadata will be enriched after import)
            episode_data = {
                'season': season,
                'episode': episode_num,
                'filename': filename,
                'url': stream_url,
                'source': 'archive',
                'type': 'event',
                'title': f"Mister Rogers' Neighborhood - Season {season} Episode {episode_num}",
                'description': f"Episode {episode_num} from Season {season}. Metadata will be enriched from TVDB."
            }
            
            print(f"    ✅ S{season:02d}E{episode_num:02d}: {filename[:50]}")
            
            episodes.append(episode_data)
        
        print(f"✅ Processed {len(episodes)} episodes for Season {season}")
        return episodes
        
    except Exception as e:
        print(f"❌ Error processing Season {season}: {e}")
        return []


async def create_channel_yaml(all_episodes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create the channel YAML structure"""
    
    # Group episodes by season
    seasons_data = {}
    for episode in all_episodes:
        season = episode['season']
        if season not in seasons_data:
            seasons_data[season] = []
        seasons_data[season].append(episode)
    
    # Build channel structure
    channel_data = {
        'channels': [{
            'number': '143',
            'name': 'IPOY 143',
            'group': 'Classic PBS',
            'description': "Mister Rogers' Neighborhood - Seasons 3-31. Won't you be my neighbor?",
            'enabled': True,
            'streams': []
        }]
    }
    
    # Add all episodes as streams
    stream_id = 1
    for season in sorted(seasons_data.keys()):
        episodes = seasons_data[season]
        
        # Sort episodes by episode number
        episodes.sort(key=lambda x: x['episode'])
        
        for episode in episodes:
            stream_entry = {
                'id': f"mr_s{season:02d}e{episode['episode']:02d}",
                'collection': f"Mister Rogers' Neighborhood - Season {season}",
                'type': 'event',
                'year': 1968 + (season - 1),  # Approximate year
                'source': 'archive',
                'url': episode['url'],
                'title': episode['title'],
                'description': episode['description'],
            }
            
            if episode.get('air_date'):
                stream_entry['broadcast_date'] = episode['air_date']
            
            channel_data['channels'][0]['streams'].append(stream_entry)
            stream_id += 1
    
    return channel_data


async def create_schedule_yaml(all_episodes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create the schedule YAML structure"""
    
    # Group by season for content definitions
    seasons_data = {}
    for episode in all_episodes:
        season = episode['season']
        if season not in seasons_data:
            seasons_data[season] = []
        seasons_data[season].append(episode)
    
    schedule_data = {
        'name': "Mister Rogers' Neighborhood Marathon",
        'description': "24/7 marathon of Mister Rogers' Neighborhood episodes from Seasons 3-31 in broadcast order.",
        'content': []
    }
    
    # Add content definitions for each season
    for season in sorted(seasons_data.keys()):
        schedule_data['content'].append({
            'key': f'season{season}',
            'collection': f"Mister Rogers' Neighborhood - Season {season}",
            'order': 'chronological'
        })
    
    # Add sequence (all seasons in order)
    schedule_data['sequence'] = []
    for season in sorted(seasons_data.keys()):
        schedule_data['sequence'].append({
            'content': f'season{season}',
            'type': 'block'
        })
    
    return schedule_data


async def main():
    """Main execution"""
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║                                                                    ║")
    print("║     Mister Rogers' Neighborhood Channel Creator (IPOY 143)        ║")
    print("║                   Seasons 3-31 from Archive.org                    ║")
    print("║                                                                    ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print()
    
    # Initialize Archive.org adapter
    archive_adapter = ArchiveOrgAdapter()
    
    # Process all seasons
    all_episodes = []
    
    for season, identifier in SEASON_COLLECTIONS.items():
        episodes = await parse_season_collection(identifier, season, archive_adapter)
        all_episodes.extend(episodes)
        
        # Brief pause between seasons
        await asyncio.sleep(1)
    
    print(f"\n{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    print(f"Total episodes collected: {len(all_episodes)}")
    print(f"Seasons processed: {len(SEASON_COLLECTIONS)}")
    print()
    
    # Create channel YAML
    print("Creating channel YAML...")
    channel_data = await create_channel_yaml(all_episodes)
    
    # Save channel YAML
    channel_yaml_path = Path(__file__).parent.parent / 'data' / 'channels_mister_rogers.yaml'
    with open(channel_yaml_path, 'w') as f:
        yaml.dump(channel_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    print(f"✅ Saved channel YAML: {channel_yaml_path}")
    
    # Create schedule YAML
    print("Creating schedule YAML...")
    schedule_data = await create_schedule_yaml(all_episodes)
    
    # Save schedule YAML
    schedule_yaml_path = Path(__file__).parent.parent / 'schedules' / '143.yml'
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
    print(f"Channel Number: 143")
    print(f"Channel Name: IPOY 143")
    print(f"Total Episodes: {len(all_episodes)}")
    print(f"Seasons: 3-31")
    print()
    print("Next steps:")
    print("1. Import channel: python scripts/import_channels.py data/channels_mister_rogers.yaml")
    print("2. Enrich metadata: python scripts/enrich_metadata.py --channel 143")
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

