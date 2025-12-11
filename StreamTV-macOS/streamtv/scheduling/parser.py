"""Schedule YAML file parser"""

import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import timedelta
import re
import logging

logger = logging.getLogger(__name__)


class ParsedSchedule:
    """Parsed schedule data structure (ErsatzTV-compatible)"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.content_map: Dict[str, Dict[str, Any]] = {}  # key -> content definition
        self.sequences: Dict[str, List[Dict[str, Any]]] = {}  # sequence_key -> items
        self.playout: List[Dict[str, Any]] = []  # playout instructions
        self.main_sequence_key: Optional[str] = None
        self.imports: List[str] = []  # Import other YAML files (ErsatzTV feature)
        self.reset: List[Dict[str, Any]] = []  # Reset instructions (ErsatzTV feature)


class ScheduleParser:
    """Parser for schedule YAML files"""
    
    @staticmethod
    def parse_duration(duration_str: str) -> Optional[int]:
        """Parse duration string (HH:MM:SS or MM:SS) to seconds"""
        if not duration_str:
            return None
        
        try:
            # Handle ISO 8601 format (PT3M44S) if needed
            if duration_str.startswith('PT'):
                duration_str = duration_str.replace('PT', '')
                total_seconds = 0
                
                hours_match = re.search(r'(\d+)H', duration_str)
                if hours_match:
                    total_seconds += int(hours_match.group(1)) * 3600
                
                minutes_match = re.search(r'(\d+)M', duration_str)
                if minutes_match:
                    total_seconds += int(minutes_match.group(1)) * 60
                
                seconds_match = re.search(r'(\d+)S', duration_str)
                if seconds_match:
                    total_seconds += int(seconds_match.group(1))
                
                return total_seconds if total_seconds > 0 else None
            else:
                # Handle HH:MM:SS or MM:SS format
                parts = duration_str.split(':')
                if len(parts) == 3:  # HH:MM:SS
                    hours, minutes, seconds = map(int, parts)
                    return hours * 3600 + minutes * 60 + seconds
                elif len(parts) == 2:  # MM:SS
                    minutes, seconds = map(int, parts)
                    return minutes * 60 + seconds
                else:
                    return None
        except (ValueError, AttributeError):
            logger.warning(f"Could not parse duration: {duration_str}")
            return None
    
    @staticmethod
    def parse_file(file_path: Path, base_dir: Optional[Path] = None) -> ParsedSchedule:
        """Parse a schedule YAML file (ErsatzTV-compatible with import support)"""
        if not file_path.exists():
            raise FileNotFoundError(f"Schedule file not found: {file_path}")
        
        if base_dir is None:
            base_dir = file_path.parent
        
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        
        if not data:
            raise ValueError(f"Empty or invalid YAML file: {file_path}")
        
        name = data.get('name', 'Unknown Schedule')
        description = data.get('description', '')
        
        schedule = ParsedSchedule(name, description)
        
        # Parse imports (ErsatzTV feature)
        imports = data.get('import', [])
        if isinstance(imports, list):
            schedule.imports = imports
        elif isinstance(imports, str):
            schedule.imports = [imports]
        
        # Process imports first (ErsatzTV merges imported content)
        for import_path in schedule.imports:
            try:
                # Resolve import path (relative to current file or absolute)
                if not Path(import_path).is_absolute():
                    import_file = base_dir / import_path
                else:
                    import_file = Path(import_path)
                
                if import_file.exists():
                    imported_schedule = ScheduleParser.parse_file(import_file, base_dir)
                    # Merge imported content (only if not already present)
                    for key, content_def in imported_schedule.content_map.items():
                        if key not in schedule.content_map:
                            schedule.content_map[key] = content_def
                    # Merge imported sequences (only if not already present)
                    for key, sequence_items in imported_schedule.sequences.items():
                        if key not in schedule.sequences:
                            schedule.sequences[key] = sequence_items
                    logger.info(f"Imported {len(imported_schedule.content_map)} content items and {len(imported_schedule.sequences)} sequences from {import_path}")
                else:
                    logger.warning(f"Import file not found: {import_path}")
            except Exception as e:
                logger.warning(f"Failed to import {import_path}: {e}")
        
        # Parse content definitions
        content_list = data.get('content', [])
        for content_def in content_list:
            key = content_def.get('key')
            if key:
                schedule.content_map[key] = {
                    'collection': content_def.get('collection'),
                    'order': content_def.get('order', 'chronological')
                }
        
        # Parse sequences
        sequence_list = data.get('sequence', [])
        for seq_def in sequence_list:
            key = seq_def.get('key')
            if key:
                schedule.sequences[key] = seq_def.get('items', [])
        
        # Parse reset instructions (ErsatzTV feature)
        reset_list = data.get('reset', [])
        if reset_list:
            schedule.reset = reset_list
        
        # Parse playout instructions
        playout_list = data.get('playout', [])
        for playout_item in playout_list:
            if 'sequence' in playout_item:
                schedule.main_sequence_key = playout_item['sequence']
            schedule.playout.append(playout_item)
        
        logger.info(f"Parsed schedule: {name} with {len(schedule.content_map)} content items, {len(schedule.sequences)} sequences, and {len(schedule.playout)} playout instructions")
        
        return schedule
    
    @staticmethod
    def find_schedule_file(channel_number: str) -> Optional[Path]:
        """Find schedule file for a channel number"""
        schedules_dir = Path(__file__).parent.parent.parent / "schedules"
        
        # Try to find matching schedule file
        possible_names = [
            f"mn-olympics-{channel_number}.yml",
            f"mn-olympics-{channel_number}.yaml",
            f"{channel_number}.yml",
            f"{channel_number}.yaml"
        ]
        
        for name in possible_names:
            file_path = schedules_dir / name
            if file_path.exists():
                return file_path
        
        return None

