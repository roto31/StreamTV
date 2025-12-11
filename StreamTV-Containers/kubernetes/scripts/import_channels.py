#!/usr/bin/env python3
"""
Import channels from YAML configuration file

This script creates channels and all their requirements (collections, playlists, media items)
from a YAML configuration file.

YAML Format:
channels:
  - number: "1980"
    name: "MN 1980 Winter Olympics"
    group: "Winter Olympics"
    description: "1980 Lake Placid coverage"
    enabled: true
    streams:
      - id: stream_id
        collection: "Collection Name"
        url: "https://..."
        source: "youtube" | "archive"
        runtime: "PT3M44S"
        network: "ABC"
        broadcast_date: "1980-02-13"
        notes: "Description"
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from streamtv.importers import import_channels_from_yaml


def main():
    parser = argparse.ArgumentParser(
        description="Import channels and all requirements from YAML file"
    )
    parser.add_argument(
        'yaml_file',
        type=str,
        help='Path to YAML file containing channel definitions'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    yaml_path = Path(args.yaml_file)
    if not yaml_path.exists():
        print(f"Error: YAML file not found: {yaml_path}")
        sys.exit(1)
    
    try:
        channels = import_channels_from_yaml(yaml_path)
        print(f"\n✅ Successfully imported {len(channels)} channels")
        for channel in channels:
            print(f"   - {channel.number}: {channel.name}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

