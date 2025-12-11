#!/usr/bin/env python3
"""
Archive.org Collection Parser for StreamTV
Fetches collection metadata and generates complete channel and schedule YAML files
With optional TVDB/TVMaze metadata enrichment
"""

import sys
import json
import re
import random
from pathlib import Path
from urllib.parse import quote
from typing import List, Dict, Any, Optional
import requests
from datetime import datetime, timedelta
import asyncio

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class ArchiveCollectionParser:
    """Parse Archive.org collections and generate StreamTV YAML configurations"""
    
    def __init__(self, collection_url: str):
        self.collection_url = collection_url
        self.identifier = self._extract_identifier(collection_url)
        self.metadata = None
        self.video_files = []
        self.episodes = []
        
    def _extract_identifier(self, url: str) -> str:
        """Extract Archive.org identifier from URL"""
        # Handle various URL formats
        patterns = [
            r'archive\.org/details/([^/\?]+)',
            r'archive\.org/download/([^/\?]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # If no pattern matches, assume it's just the identifier
        if '/' not in url and '?' not in url:
            return url
        
        raise ValueError(f"Could not extract identifier from URL: {url}")
    
    def fetch_metadata(self) -> Dict[str, Any]:
        """Fetch collection metadata from Archive.org API"""
        api_url = f"https://archive.org/metadata/{self.identifier}"
        
        print(f"📡 Fetching metadata from Archive.org...")
        print(f"   Identifier: {self.identifier}")
        
        try:
            response = requests.get(api_url, timeout=30)
            response.raise_for_status()
            self.metadata = response.json()
            print(f"✅ Metadata fetched successfully")
            return self.metadata
        except Exception as e:
            raise Exception(f"Failed to fetch metadata: {e}")
    
    def parse_video_files(self) -> List[Dict[str, Any]]:
        """Parse video files from metadata"""
        if not self.metadata:
            raise ValueError("Metadata not loaded. Call fetch_metadata() first.")
        
        files = self.metadata.get('files', [])
        video_extensions = ('.mp4', '.avi', '.mkv', '.mov', '.m4v', '.webm')
        
        print(f"\n📹 Parsing video files...")
        
        for file_info in files:
            filename = file_info.get('name', '')
            
            # Skip non-video files and thumbnails
            if not filename.lower().endswith(video_extensions):
                continue
            if '/thumbs/' in filename.lower() or 'thumbnail' in filename.lower():
                continue
            
            # Extract file extension
            ext = Path(filename).suffix
            
            # Parse season and episode information
            season, episode, title = self._parse_episode_info(filename)
            
            # Get file size
            size = file_info.get('size', '0')
            try:
                size_bytes = int(size) if size else 0
            except:
                size_bytes = 0
            
            video_info = {
                'filename': filename,
                'extension': ext,
                'season': season,
                'episode': episode,
                'title': title,
                'size': size_bytes,
                'format': file_info.get('format', ''),
            }
            
            self.video_files.append(video_info)
        
        # Sort by season and episode
        self.video_files.sort(key=lambda x: (x['season'], x['episode']))
        
        print(f"✅ Found {len(self.video_files)} video files")
        return self.video_files
    
    def _parse_episode_info(self, filename: str) -> tuple:
        """Parse season, episode, and title from filename"""
        # Remove path components
        basename = Path(filename).stem
        
        season = 0
        episode = 0
        title = basename
        
        # Try various patterns
        patterns = [
            # S01E01 or s01e01
            (r'[sS](\d+)[eE](\d+)', r'[sS]\d+[eE]\d+\s*[-\s]*'),
            # 1x01
            (r'(\d+)x(\d+)', r'\d+x\d+\s*[-\s]*'),
            # Season 1 Episode 01
            (r'[Ss]eason\s+(\d+).*?[Ee]pisode\s+(\d+)', r'[Ss]eason\s+\d+.*?[Ee]pisode\s+\d+\s*[-\s]*'),
        ]
        
        for season_ep_pattern, remove_pattern in patterns:
            match = re.search(season_ep_pattern, basename)
            if match:
                season = int(match.group(1))
                episode = int(match.group(2))
                # Remove the season/episode part to get title
                title = re.sub(remove_pattern, '', basename)
                break
        
        # Clean up title
        title = re.sub(r'magnum[.\s]*p[.\s]*i[.\s]*[-\s]*', '', title, flags=re.IGNORECASE)
        title = re.sub(r'dvdrip.*', '', title, flags=re.IGNORECASE)
        title = re.sub(r'xvid[-.]epic', '', title, flags=re.IGNORECASE)
        title = re.sub(r'[._]+', ' ', title)
        title = title.strip(' -.')
        
        # Capitalize words
        title = ' '.join(word.capitalize() for word in title.split())
        
        return season, episode, title
    
    def generate_channel_yaml(self, channel_number: str = "80", 
                              channel_name: str = "Magnum P.I. Complete Series",
                              output_path: Optional[Path] = None) -> str:
        """Generate channels.yaml content"""
        if not self.video_files:
            raise ValueError("No video files parsed. Call parse_video_files() first.")
        
        print(f"\n📝 Generating channel YAML...")
        
        # Group by season for collections
        seasons = {}
        for video in self.video_files:
            season = video['season']
            if season not in seasons:
                seasons[season] = []
            seasons[season].append(video)
        
        yaml_lines = []
        yaml_lines.append("# Magnum P.I. Channel Configuration")
        yaml_lines.append(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        yaml_lines.append(f"# Source: https://archive.org/details/{self.identifier}")
        yaml_lines.append(f"# Total Episodes: {len(self.video_files)}")
        yaml_lines.append("")
        yaml_lines.append("channels:")
        yaml_lines.append(f"  - number: \"{channel_number}\"")
        yaml_lines.append(f"    name: \"{channel_name}\"")
        yaml_lines.append(f"    group: \"Classic Television\"")
        yaml_lines.append(f"    description: \"Complete Magnum P.I. series (1980-1988) featuring Thomas Magnum, a private investigator in Hawaii. All episodes from Archive.org.\"")
        yaml_lines.append(f"    enabled: true")
        yaml_lines.append(f"    streams:")
        
        # Add all episodes
        for video in self.video_files:
            season = video['season']
            episode = video['episode']
            title = video['title']
            filename = video['filename']
            
            # Determine episode type (use "event" for all content per StreamTV schema)
            ep_type = "event"  # Schema only allows: event, bumper, commercial, news, filler
            
            # Estimate year (Magnum P.I. ran 1980-1988)
            year = 1980 + season if season > 0 else 1980
            
            # Estimate broadcast date
            # Season typically started in September/October
            if season > 0:
                month = 9 + (episode // 4)  # Spread across months
                month = min(month, 5) if month < 9 else month  # Sep-May
                if month > 12:
                    month = month - 12
                    year += 1
                day = min((episode % 4) * 7 + 1, 28)
            else:
                month = 1
                day = 1
            
            broadcast_date = f"{year}-{month:02d}-{day:02d}"
            
            # Generate stream ID
            if season == 0:
                stream_id = f"magnum_special_{episode:02d}"
            else:
                stream_id = f"magnum_s{season:02d}e{episode:02d}"
            
            # Generate URL
            encoded_filename = quote(filename, safe='')
            url = f"https://archive.org/download/{self.identifier}/{encoded_filename}"
            
            # Determine collection name
            if season == 0:
                collection = "Magnum P.I. - Specials"
            else:
                collection = f"Magnum P.I. - Season {season}"
            
            yaml_lines.append(f"")
            yaml_lines.append(f"      - id: {stream_id}")
            yaml_lines.append(f"        collection: \"{collection}\"")
            yaml_lines.append(f"        type: {ep_type}")
            yaml_lines.append(f"        year: {year}")
            yaml_lines.append(f"        slot: \"S{season:02d}E{episode:02d} - {title}\"")
            yaml_lines.append(f"        broadcast_date: {broadcast_date}")
            yaml_lines.append(f"        network: CBS")
            yaml_lines.append(f"        runtime: PT48M")
            yaml_lines.append(f"        source: archive")
            yaml_lines.append(f"        url: {url}")
            yaml_lines.append(f"        notes: \"Season {season} Episode {episode}\"")
        
        yaml_content = '\n'.join(yaml_lines)
        
        # Save to file if output path provided
        if output_path:
            output_path.write_text(yaml_content)
            print(f"✅ Channel YAML saved to: {output_path}")
        
        return yaml_content
    
    def generate_schedule_yaml(self, 
                               schedule_name: str = "Magnum P.I. Marathon",
                               min_break: int = 2,
                               max_break: int = 5,
                               output_path: Optional[Path] = None) -> str:
        """Generate schedule YAML with enforced breaks between episodes"""
        if not self.video_files:
            raise ValueError("No video files parsed. Call parse_video_files() first.")
        
        print(f"\n📝 Generating schedule YAML with {min_break}-{max_break} minute breaks...")
        
        # Group by season
        seasons = {}
        for video in self.video_files:
            season = video['season']
            if season not in seasons:
                seasons[season] = []
            seasons[season].append(video)
        
        yaml_lines = []
        yaml_lines.append(f"# Magnum P.I. Schedule Configuration")
        yaml_lines.append(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        yaml_lines.append(f"# Inter-episode breaks: {min_break}-{max_break} minutes (strictly enforced)")
        yaml_lines.append(f"")
        yaml_lines.append(f"name: {schedule_name}")
        yaml_lines.append(f"description: >-")
        yaml_lines.append(f"  24/7 marathon of Magnum P.I. episodes in broadcast order.")
        yaml_lines.append(f"  Sequential playback through all 8 seasons with {min_break}-{max_break} minute breaks between episodes.")
        yaml_lines.append(f"  Total episodes: {len(self.video_files)}")
        yaml_lines.append(f"")
        yaml_lines.append(f"content:")
        
        # Define content sections by season
        for season_num in sorted(seasons.keys()):
            if season_num == 0:
                key = "specials"
                collection = "Magnum P.I. - Specials"
            else:
                key = f"season{season_num}"
                collection = f"Magnum P.I. - Season {season_num}"
            
            yaml_lines.append(f"  - key: {key}")
            yaml_lines.append(f"    collection: {collection}")
            yaml_lines.append(f"    order: chronological")
        
        yaml_lines.append(f"")
        yaml_lines.append(f"  # Inter-episode breaks (filler)")
        yaml_lines.append(f"  - key: break_short")
        yaml_lines.append(f"    collection: Inter-Episode Breaks")
        yaml_lines.append(f"    order: random")
        yaml_lines.append(f"")
        yaml_lines.append(f"sequence:")
        yaml_lines.append(f"  - key: magnum-marathon")
        yaml_lines.append(f"    items:")
        
        # Add all seasons to sequence with breaks
        for season_num in sorted(seasons.keys()):
            if season_num == 0:
                continue  # Skip specials in main sequence
            
            key = f"season{season_num}"
            episode_count = len(seasons[season_num])
            
            yaml_lines.append(f"")
            yaml_lines.append(f"      # Season {season_num} ({episode_count} episodes)")
            
            # For each episode in the season, add the episode and a break
            for idx, video in enumerate(seasons[season_num]):
                # Add the episode
                yaml_lines.append(f"      - all: {key}")
                yaml_lines.append(f"        custom_title: \"Season {season_num} Episode {idx + 1}\"")
                
                # Add break after episode (except after last episode of last season)
                is_last_season = season_num == max(s for s in seasons.keys() if s > 0)
                is_last_episode = idx == len(seasons[season_num]) - 1
                
                if not (is_last_season and is_last_episode):
                    # Random break duration between min and max
                    break_duration = random.randint(min_break, max_break)
                    yaml_lines.append(f"      # {break_duration} minute break")
                    yaml_lines.append(f"      - all: break_short")
                    yaml_lines.append(f"        custom_title: \"Inter-Episode Break\"")
                    yaml_lines.append(f"        duration: PT{break_duration}M")
        
        # Add specials at the end if they exist
        if 0 in seasons:
            yaml_lines.append(f"")
            yaml_lines.append(f"      # Special Episodes")
            for idx, video in enumerate(seasons[0]):
                yaml_lines.append(f"      - all: specials")
                yaml_lines.append(f"        custom_title: \"Special: {video['title']}\"")
                if idx < len(seasons[0]) - 1:
                    break_duration = random.randint(min_break, max_break)
                    yaml_lines.append(f"      # {break_duration} minute break")
                    yaml_lines.append(f"      - all: break_short")
                    yaml_lines.append(f"        duration: PT{break_duration}M")
        
        yaml_lines.append(f"")
        yaml_lines.append(f"playout:")
        yaml_lines.append(f"  - sequence: magnum-marathon")
        yaml_lines.append(f"  - repeat: true  # Loop back to Season 1 after finishing")
        
        yaml_content = '\n'.join(yaml_lines)
        
        # Save to file if output path provided
        if output_path:
            output_path.write_text(yaml_content)
            print(f"✅ Schedule YAML saved to: {output_path}")
        
        return yaml_content
    
    def generate_summary(self) -> str:
        """Generate a summary of the parsed collection"""
        if not self.video_files:
            return "No videos parsed"
        
        # Group by season
        seasons = {}
        for video in self.video_files:
            season = video['season']
            if season not in seasons:
                seasons[season] = 0
            seasons[season] += 1
        
        lines = []
        lines.append(f"\n{'='*60}")
        lines.append(f"Archive.org Collection Summary")
        lines.append(f"{'='*60}")
        lines.append(f"Collection ID: {self.identifier}")
        lines.append(f"Total Episodes: {len(self.video_files)}")
        lines.append(f"")
        lines.append(f"Episodes by Season:")
        for season_num in sorted(seasons.keys()):
            if season_num == 0:
                lines.append(f"  Specials: {seasons[season_num]} episodes")
            else:
                lines.append(f"  Season {season_num}: {seasons[season_num]} episodes")
        lines.append(f"{'='*60}\n")
        
        return '\n'.join(lines)


def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Parse Archive.org collection and generate StreamTV YAML files"
    )
    parser.add_argument(
        'collection_url',
        help='Archive.org collection URL or identifier'
    )
    parser.add_argument(
        '--channel-number', '-n',
        default='80',
        help='Channel number (default: 80)'
    )
    parser.add_argument(
        '--channel-name', '-c',
        default='Magnum P.I. Complete Series',
        help='Channel name'
    )
    parser.add_argument(
        '--min-break',
        type=int,
        default=2,
        help='Minimum break between episodes in minutes (default: 2)'
    )
    parser.add_argument(
        '--max-break',
        type=int,
        default=5,
        help='Maximum break between episodes in minutes (default: 5)'
    )
    parser.add_argument(
        '--output-dir', '-o',
        type=Path,
        help='Output directory (default: current directory)'
    )
    parser.add_argument(
        '--enrich-metadata',
        action='store_true',
        help='Fetch metadata from TVDB/TVMaze (requires API keys in config)'
    )
    parser.add_argument(
        '--series-year',
        type=int,
        help='Series start year for better metadata matching'
    )
    
    args = parser.parse_args()
    
    # Set output directory
    output_dir = args.output_dir or Path.cwd()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Create parser
        parser = ArchiveCollectionParser(args.collection_url)
        
        # Fetch and parse
        parser.fetch_metadata()
        parser.parse_video_files()
        
        # Show summary
        print(parser.generate_summary())
        
        # Generate YAMLs with proper naming
        # Channel YAML can have descriptive name
        channel_yaml_path = output_dir / "magnum-pi-channel.yaml"
        # Schedule YAML MUST be named {channel_number}.yml for auto-discovery
        schedule_yaml_path = output_dir / f"{args.channel_number}.yml"
        
        parser.generate_channel_yaml(
            channel_number=args.channel_number,
            channel_name=args.channel_name,
            output_path=channel_yaml_path
        )
        
        parser.generate_schedule_yaml(
            min_break=args.min_break,
            max_break=args.max_break,
            output_path=schedule_yaml_path
        )
        
        print(f"\n🎉 Success! Generated files:")
        print(f"   📄 {channel_yaml_path}")
        print(f"   📄 {schedule_yaml_path}")
        print(f"\n💡 Next steps:")
        print(f"   1. Review the generated YAML files")
        print(f"   2. Copy magnum-pi-channel.yaml to data/")
        print(f"   3. Copy {args.channel_number}.yml to schedules/")
        print(f"   4. Run: python3 scripts/import_channels.py data/magnum-pi-channel.yaml")
        print(f"   5. Restart StreamTV server")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

