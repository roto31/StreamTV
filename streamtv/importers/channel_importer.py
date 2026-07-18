"""Import channels and all requirements from YAML files"""

import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
import re

from ..database.session import SessionLocal, init_db
from ..database.models import (
    Channel, MediaItem, Collection, CollectionItem, 
    Playlist, PlaylistItem, StreamSource
)
from ..streaming import StreamManager
from ..validation import YAMLValidator, ValidationError
from .stream_metadata import (
    build_stream_meta_data,
    resolve_media_title,
    resolve_show_name,
)

logger = logging.getLogger(__name__)


class ChannelImporter:
    """Import channels and all requirements from YAML configuration"""
    
    def __init__(self, db_session=None):
        self.db = db_session or SessionLocal()
        self.stream_manager = StreamManager()
        self.created_channels = []
        self.created_collections = {}
        self.created_media = {}
    
    def parse_duration(self, duration_str: str) -> Optional[int]:
        """Parse ISO 8601 duration (PT3M44S) to seconds"""
        if not duration_str:
            return None
        
        try:
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
        except Exception as e:
            logger.warning(f"Could not parse duration '{duration_str}': {e}")
            return None
    
    def _apply_yaml_stream_fields(
        self,
        media_item: MediaItem,
        stream_data: Dict[str, Any],
        *,
        channel_name: str = "",
    ) -> None:
        """Sync title/description/meta from YAML onto an existing or new media row."""
        title = resolve_media_title(stream_data)
        if title and title != "Untitled":
            media_item.title = title
        description = stream_data.get("description")
        if description:
            media_item.description = description
        duration = self.parse_duration(stream_data.get("runtime"))
        if duration:
            media_item.duration = duration
        thumbnail = stream_data.get("thumbnail")
        if thumbnail:
            media_item.thumbnail = thumbnail
        network = stream_data.get("network")
        if network:
            media_item.uploader = network
        meta_json = build_stream_meta_data(stream_data, channel_name=channel_name)
        if meta_json:
            media_item.meta_data = meta_json
        if stream_data.get("network") and not media_item.uploader:
            media_item.uploader = stream_data.get("network")
        bd = stream_data.get("broadcast_date")
        if bd and not media_item.upload_date:
            media_item.upload_date = str(bd)

    async def get_or_create_media_item(
        self, stream_data: Dict[str, Any], *, channel_name: str = ""
    ) -> MediaItem:
        """Get existing media item or create new one"""
        url = stream_data.get('url')
        if not url:
            raise ValueError("Stream data missing 'url' field")
        
        # Check if media item already exists
        existing = self.db.query(MediaItem).filter(MediaItem.url == url).first()
        if existing:
            self._apply_yaml_stream_fields(
                existing, stream_data, channel_name=channel_name
            )
            if (
                not existing.duration
                and existing.source == StreamSource.YOUTUBE
                and self.stream_manager
                and self.stream_manager.youtube_adapter
            ):
                try:
                    yt_info = await self.stream_manager.get_media_info(
                        url, StreamSource.YOUTUBE
                    )
                    yt_dur = yt_info.get("duration") if yt_info else None
                    if yt_dur and int(yt_dur) > 0:
                        existing.duration = int(yt_dur)
                except Exception as e:
                    logger.warning(
                        f"  Could not refresh YouTube duration for {url}: {e}"
                    )
            self.db.commit()
            self.db.refresh(existing)
            return existing
        
        # Determine source
        source_str = stream_data.get('source', '').lower()
        if source_str == 'plex' or 'plex://' in url:
            source = StreamSource.PLEX
        elif 'youtube' in source_str or 'youtu.be' in url or 'youtube.com' in url:
            source = StreamSource.YOUTUBE
        elif 'archive' in source_str or 'archive.org' in url:
            source = StreamSource.ARCHIVE_ORG
        elif source_str == 'pbs' or 'pbs.org' in url or 'pbskids.org' in url:
            source = StreamSource.PBS
        else:
            source = StreamSource.YOUTUBE  # Default
        
        # Extract source ID
        source_id = ""
        if source == StreamSource.PLEX:
            # Extract rating key from Plex URL
            plex_rating_key = stream_data.get('plex_rating_key')
            if plex_rating_key:
                source_id = str(plex_rating_key)
            else:
                # Try to extract from URL
                match = re.search(r'/library/metadata/(\d+)', url)
                if match:
                    source_id = match.group(1)
                else:
                    source_id = url
        
        # For Plex sources, fetch full metadata from Plex API
        title = resolve_media_title(stream_data)
        description = stream_data.get('description', '')
        duration = self.parse_duration(stream_data.get('runtime'))
        thumbnail = stream_data.get('thumbnail')
        
        if source == StreamSource.PLEX and self.stream_manager and self.stream_manager.plex_adapter:
            try:
                plex_info = await self.stream_manager.plex_adapter.get_media_info(url)
                if plex_info:
                    # Use Plex metadata if available
                    if plex_info.get('title'):
                        title = plex_info['title']
                    if plex_info.get('summary'):
                        description = plex_info['summary']
                    if plex_info.get('duration'):
                        duration = plex_info['duration']
                    
                    # Format thumbnail URL - make it absolute if it's a relative path
                    if plex_info.get('thumb'):
                        thumb_path = plex_info['thumb']
                        if thumb_path.startswith('/'):
                            # Relative path - make it absolute using Plex base URL
                            if self.stream_manager.plex_adapter.base_url:
                                thumbnail = f"{self.stream_manager.plex_adapter.base_url}{thumb_path}?X-Plex-Token={self.stream_manager.plex_adapter.token or ''}"
                            else:
                                thumbnail = thumb_path
                        elif thumb_path.startswith('http'):
                            # Already absolute
                            thumbnail = thumb_path
                        else:
                            # Relative path without leading slash
                            if self.stream_manager.plex_adapter.base_url:
                                thumbnail = f"{self.stream_manager.plex_adapter.base_url}/{thumb_path}?X-Plex-Token={self.stream_manager.plex_adapter.token or ''}"
                            else:
                                thumbnail = thumb_path
                    
                    logger.debug(f"  Fetched Plex metadata for {title[:50]}")
            except Exception as e:
                logger.warning(f"  Could not fetch Plex metadata for {url}: {e}. Using YAML data.")
        
        # Fallback to YAML data if Plex metadata fetch failed
        if not title or title == 'Untitled':
            title = stream_data.get('id', 'Media Item')

        meta_json = build_stream_meta_data(stream_data, channel_name=channel_name)
        
        # Parse duration from YAML if not set from Plex
        if not duration:
            duration = self.parse_duration(stream_data.get('runtime'))

        # YouTube: fetch duration from source when YAML has no runtime (matches Tunarr per-video slots)
        if (
            not duration
            and source == StreamSource.YOUTUBE
            and self.stream_manager
            and self.stream_manager.youtube_adapter
        ):
            try:
                yt_info = await self.stream_manager.get_media_info(url, StreamSource.YOUTUBE)
                yt_dur = yt_info.get('duration') if yt_info else None
                if yt_dur and int(yt_dur) > 0:
                    duration = int(yt_dur)
                    logger.debug(f"  Fetched YouTube duration {duration}s for {title[:50]}")
            except Exception as e:
                logger.warning(f"  Could not fetch YouTube duration for {url}: {e}")
        
        # Extract source ID for non-Plex sources
        if source == StreamSource.YOUTUBE:
            match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
            if match:
                source_id = match.group(1)
        elif source == StreamSource.ARCHIVE_ORG:
            yaml_id = stream_data.get("id")
            if yaml_id:
                source_id = str(yaml_id)
            else:
                from ..streaming.archive_org_playback import archive_org_source_id

                source_id = archive_org_source_id(url)
        elif source == StreamSource.PBS:
            yaml_id = stream_data.get("id")
            source_id = str(yaml_id) if yaml_id else url
        
        # Create media item
        media_item = MediaItem(
            source=source,
            source_id=source_id or url,
            url=url,
            title=title,
            description=description,
            duration=duration,
            thumbnail=thumbnail,
            uploader=stream_data.get('network', None),
            upload_date=str(stream_data.get('broadcast_date', '')) if stream_data.get('broadcast_date') else None,
            meta_data=meta_json,
        )
        
        self.db.add(media_item)
        self.db.commit()
        self.db.refresh(media_item)
        
        logger.info(f"  ✓ Created media item: {title[:50]}")
        return media_item
    
    def get_or_create_collection(self, collection_name: str) -> Collection:
        """Get existing collection or create new one"""
        if collection_name in self.created_collections:
            return self.created_collections[collection_name]
        
        # Check if collection already exists
        existing = self.db.query(Collection).filter(Collection.name == collection_name).first()
        if existing:
            self.created_collections[collection_name] = existing
            return existing
        
        # Create new collection
        collection = Collection(
            name=collection_name,
            description=f"Collection: {collection_name}"
        )
        self.db.add(collection)
        self.db.commit()
        self.db.refresh(collection)
        
        self.created_collections[collection_name] = collection
        logger.info(f"  ✓ Created collection: {collection_name}")
        return collection
    
    def add_media_to_collection(self, collection: Collection, media_item: MediaItem, order: int = 0):
        """Add media item to collection"""
        # Check if already in collection
        existing = self.db.query(CollectionItem).filter(
            CollectionItem.collection_id == collection.id,
            CollectionItem.media_item_id == media_item.id
        ).first()
        
        if existing:
            if existing.order != order:
                existing.order = order
                self.db.commit()
            return
        
        collection_item = CollectionItem(
            collection_id=collection.id,
            media_item_id=media_item.id,
            order=order
        )
        self.db.add(collection_item)
        self.db.commit()

    def sync_collection_media(
        self, collection: Collection, ordered_media: List[MediaItem]
    ) -> None:
        """Replace collection membership to match YAML import (drops stale items)."""
        keep_ids = {m.id for m in ordered_media}
        stale = self.db.query(CollectionItem).filter(
            CollectionItem.collection_id == collection.id,
        )
        if keep_ids:
            stale = stale.filter(~CollectionItem.media_item_id.in_(keep_ids))
        removed = stale.delete(synchronize_session=False)
        for order, media_item in enumerate(ordered_media):
            self.add_media_to_collection(collection, media_item, order)
        self.db.commit()
        if removed:
            logger.info(
                f"  ✓ Synced collection {collection.name}: {len(ordered_media)} items "
                f"(removed {removed} stale)"
            )

    def sync_playlist_media(
        self, playlist: Playlist, ordered_media: List[MediaItem]
    ) -> None:
        """Replace playlist items to match YAML import order."""
        keep_ids = {m.id for m in ordered_media}
        stale = self.db.query(PlaylistItem).filter(
            PlaylistItem.playlist_id == playlist.id,
        )
        if keep_ids:
            stale = stale.filter(~PlaylistItem.media_item_id.in_(keep_ids))
        removed = stale.delete(synchronize_session=False)
        existing = {
            pi.media_item_id: pi
            for pi in self.db.query(PlaylistItem).filter(
                PlaylistItem.playlist_id == playlist.id
            ).all()
        }
        for order, media_item in enumerate(ordered_media):
            if media_item.id in existing:
                pi = existing[media_item.id]
                if pi.order != order:
                    pi.order = order
            else:
                self.db.add(
                    PlaylistItem(
                        playlist_id=playlist.id,
                        media_item_id=media_item.id,
                        order=order,
                    )
                )
        self.db.commit()
        logger.info(
            f"  ✓ Synced playlist {playlist.name}: {len(ordered_media)} items "
            f"(removed {removed} stale)"
        )
    
    async def import_channel_from_config(self, channel_config: Dict[str, Any]) -> Channel:
        """Import a single channel from configuration"""
        channel_number = str(channel_config.get('number', ''))
        channel_name = channel_config.get('name', f'Channel {channel_number}')
        
        if not channel_number:
            raise ValueError("Channel config missing 'number' field")
        
        # Check if channel already exists
        existing = self.db.query(Channel).filter(Channel.number == channel_number).first()
        yaml_playout = channel_config.get("playout_mode")
        if existing:
            logger.info(f"Channel {channel_number} already exists, updating...")
            existing.name = channel_name
            existing.group = channel_config.get('group')
            existing.description = channel_config.get('description')
            existing.enabled = channel_config.get('enabled', True)
            if channel_config.get("logo_path"):
                existing.logo_path = channel_config["logo_path"]
            if yaml_playout:
                existing.playout_mode = str(yaml_playout).lower().replace("-", "_")
            yaml_sync = channel_config.get("epg_sync_class")
            if yaml_sync:
                existing.epg_sync_class = str(yaml_sync).strip().upper()[:1]
            self.db.commit()
            self.db.refresh(existing)
            channel = existing
        else:
            create_kwargs = dict(
                number=channel_number,
                name=channel_name,
                group=channel_config.get('group'),
                enabled=channel_config.get('enabled', True),
                is_yaml_source=True,
                transcode_profile=channel_config.get('transcode_profile'),
                logo_path=channel_config.get('logo_path'),
            )
            if yaml_playout:
                create_kwargs["playout_mode"] = str(yaml_playout).lower().replace("-", "_")
            yaml_sync = channel_config.get("epg_sync_class")
            if yaml_sync:
                create_kwargs["epg_sync_class"] = str(yaml_sync).strip().upper()[:1]
            channel = Channel(**create_kwargs)
            self.db.add(channel)
            self.db.commit()
            self.db.refresh(channel)
            
            logger.info(f"✓ Created channel: {channel_number} - {channel_name}")
            self.created_channels.append(channel)
        
        # Import media items and collections
        streams = channel_config.get('streams', [])
        if streams:
            logger.info(f"  Importing {len(streams)} media items...")
            
            # Group streams by collection
            collection_map = {}
            for i, stream_data in enumerate(streams):
                collection_name = stream_data.get('collection')
                if collection_name:
                    if collection_name not in collection_map:
                        collection_map[collection_name] = []
                    collection_map[collection_name].append((i, stream_data))
            
            # Create collections and add media
            for collection_name, stream_list in collection_map.items():
                collection = self.get_or_create_collection(collection_name)
                ordered_media: List[MediaItem] = []
                for order, stream_data in stream_list:
                    try:
                        media_item = await self.get_or_create_media_item(
                            stream_data, channel_name=channel_name
                        )
                        ordered_media.append(media_item)
                    except Exception as e:
                        logger.error(f"  ✗ Error importing media item: {e}")
                        continue
                self.sync_collection_media(collection, ordered_media)
            
            # Sync main playlist for channel
            playlist_name = f"{channel_name} - Main Playlist"
            existing_playlist = self.db.query(Playlist).filter(
                Playlist.name == playlist_name,
                Playlist.channel_id == channel.id
            ).first()
            
            all_media: List[MediaItem] = []
            for stream_data in streams:
                try:
                    media_item = await self.get_or_create_media_item(
                        stream_data, channel_name=channel_name
                    )
                    all_media.append(media_item)
                except Exception as e:
                    logger.error(f"  ✗ Error adding to playlist: {e}")
                    continue

            if not existing_playlist:
                playlist = Playlist(
                    name=playlist_name,
                    description=f"Main playlist for {channel_name}",
                    channel_id=channel.id
                )
                self.db.add(playlist)
                self.db.commit()
                self.db.refresh(playlist)
                for order, media_item in enumerate(all_media):
                    self.db.add(
                        PlaylistItem(
                            playlist_id=playlist.id,
                            media_item_id=media_item.id,
                            order=order,
                        )
                    )
                self.db.commit()
                logger.info(f"  ✓ Created playlist with {len(all_media)} items")
            else:
                self.sync_playlist_media(existing_playlist, all_media)
        
        return channel
    
    async def import_from_yaml(self, yaml_path: Path, validate: bool = True) -> List[Channel]:
        """
        Import channels from YAML file
        
        Args:
            yaml_path: Path to YAML file
            validate: Whether to validate against JSON schema (default: True)
        
        Returns:
            List of imported Channel objects
        """
        if not yaml_path.exists():
            raise FileNotFoundError(f"YAML file not found: {yaml_path}")
        
        # Validate YAML file against schema if requested
        if validate:
            try:
                validator = YAMLValidator()
                result = validator.validate_channel_file(yaml_path)
                if not result.get('valid', False):
                    raise ValidationError(f"Validation failed: {result.get('errors', [])}")
                logger.info(f"✓ Validated {yaml_path.name} before import")
            except ValidationError as e:
                logger.error(f"Validation error: {e.message}")
                raise
            except Exception as e:
                logger.warning(f"Validation skipped due to error: {e}")
                # Continue with import even if validation fails (non-blocking)

            # Hard invariant: stream ids must be globally unique across the
            # whole data set (cache source_id collisions — Issues 18-21).
            from streamtv.importers.stream_id_registry import assert_unique_stream_ids
            assert_unique_stream_ids(yaml_path.parent)
        
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)
        
        # Initialize database
        init_db()
        
        channels_config = data.get('channels', [])
        if not channels_config:
            raise ValueError("YAML file must contain a 'channels' list")
        
        logger.info(f"Importing {len(channels_config)} channels from {yaml_path.name}...")
        
        imported_channels = []
        for channel_config in channels_config:
            try:
                channel = await self.import_channel_from_config(channel_config)
                imported_channels.append(channel)
            except Exception as e:
                logger.error(f"Error importing channel: {e}")
                continue

        self._apply_two_layer_playout_defaults(imported_channels)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Import complete!")
        logger.info(f"  Created/Updated: {len(imported_channels)} channels")
        logger.info(f"  Created: {len(self.created_collections)} collections")
        logger.info(f"{'='*60}")
        
        return imported_channels

    def _apply_two_layer_playout_defaults(self, channels: List[Channel]) -> None:
        """Enforce StreamTV two-layer model: schedule file + CONTINUOUS when present."""
        from streamtv.database.models import PlayoutMode
        from streamtv.scheduling.parser import ScheduleParser

        for channel in channels:
            number = str(channel.number)
            schedule_path = ScheduleParser.find_schedule_file(number)
            if schedule_path:
                mode = getattr(channel, "playout_mode", None)
                mode_val = str(getattr(mode, "value", mode) or "").lower().replace("-", "_")
                if mode_val not in ("on_demand", "ondemand"):
                    channel.playout_mode = PlayoutMode.CONTINUOUS.value
                    logger.info(
                        f"Channel {number}: schedule {schedule_path.name} present → "
                        f"playout_mode=continuous"
                    )
                else:
                    logger.info(
                        f"Channel {number}: schedule present but YAML requested on_demand"
                    )
            else:
                logger.warning(
                    f"Channel {number}: no schedule file "
                    f"(expected schedules/{number}.yml or schedules/mn-olympics-{number}.yml). "
                    f"Plex EPG/playout may drift. See docs/channel-two-layer-model.md"
                )
        try:
            self.db.commit()
        except Exception as e:
            logger.warning(f"Could not persist playout_mode defaults: {e}")
            self.db.rollback()
    
    def close(self):
        """Close database session"""
        if self.db:
            self.db.close()


async def import_channels_from_yaml(yaml_path: Path, validate: bool = True, db_session=None) -> List[Channel]:
    """
    Convenience function to import channels from YAML file

    Args:
        yaml_path: Path to YAML file
        validate: Whether to validate against JSON schema (default: True)
        db_session: Optional SQLAlchemy session to use. When provided (e.g. the
            request-scoped session from a FastAPI endpoint), it is NOT closed
            here so the returned Channel objects remain attached for response
            serialization. When omitted, a private session is created and closed.

    Returns:
        List of imported Channel objects
    """
    # Reuse the caller's session when supplied so returned ORM objects stay bound
    # to a live session while FastAPI serializes the response (avoids
    # DetachedInstanceError). Only close sessions we created ourselves.
    owns_session = db_session is None
    importer = ChannelImporter(db_session=db_session)
    try:
        return await importer.import_from_yaml(yaml_path, validate=validate)
    finally:
        if owns_session:
            importer.close()

