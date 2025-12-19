"""Pydantic schemas for API requests and responses"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# Import StreamSource and PlayoutMode from database models to ensure consistency
try:
    from ..database.models import StreamSource, PlayoutMode
except ImportError:
    from enum import Enum
    class StreamSource(str, Enum):
        YOUTUBE = "youtube"
        ARCHIVE_ORG = "archive_org"
    class PlayoutMode(str, Enum):
        CONTINUOUS = "continuous"
        ON_DEMAND = "on_demand"


# Channel Schemas
class ChannelBase(BaseModel):
    number: str
    name: str
    group: Optional[str] = None
    enabled: bool = True
    logo_path: Optional[str] = None
    playout_mode: PlayoutMode = PlayoutMode.CONTINUOUS  # Continuous or on-demand


class ChannelCreate(ChannelBase):
    pass


class ChannelUpdate(BaseModel):
    number: Optional[str] = None
    name: Optional[str] = None
    group: Optional[str] = None
    enabled: Optional[bool] = None
    logo_path: Optional[str] = None
    playout_mode: Optional[PlayoutMode] = None


class ChannelResponse(ChannelBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Media Item Schemas
class MediaItemBase(BaseModel):
    source: StreamSource
    url: str
    title: str
    description: Optional[str] = None
    duration: Optional[int] = None
    thumbnail: Optional[str] = None


class MediaItemCreate(MediaItemBase):
    pass


class MediaItemResponse(MediaItemBase):
    id: int
    source_id: str
    uploader: Optional[str] = None
    upload_date: Optional[str] = None
    view_count: Optional[int] = None
    meta_data: Optional[str] = None  # JSON string with additional metadata
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Collection Schemas
class CollectionBase(BaseModel):
    name: str
    description: Optional[str] = None
    collection_type: Optional[str] = "manual"  # "manual", "smart", "multi"
    search_query: Optional[str] = None  # For smart collections


class CollectionCreate(CollectionBase):
    pass


class CollectionItemResponse(BaseModel):
    id: int
    media_item_id: int
    order: int
    media_item: Optional[MediaItemResponse] = None
    
    class Config:
        from_attributes = True


class CollectionResponse(CollectionBase):
    id: int
    created_at: datetime
    updated_at: datetime
    items: List[CollectionItemResponse] = []
    
    class Config:
        from_attributes = True
        # Pydantic will automatically serialize enum values to their string values


# Playlist Schemas
class PlaylistBase(BaseModel):
    name: str
    description: Optional[str] = None
    channel_id: Optional[int] = None


class PlaylistCreate(PlaylistBase):
    pass


class PlaylistItemResponse(BaseModel):
    id: int
    media_item_id: int
    order: int
    media_item: Optional[MediaItemResponse] = None
    
    class Config:
        from_attributes = True


class PlaylistResponse(PlaylistBase):
    id: int
    created_at: datetime
    updated_at: datetime
    items: List[PlaylistItemResponse] = []
    
    class Config:
        from_attributes = True


# Schedule Schemas
class ScheduleBase(BaseModel):
    name: str
    channel_id: int
    keep_multi_part_episodes_together: bool = False
    treat_collections_as_shows: bool = False
    shuffle_schedule_items: bool = False
    random_start_point: bool = False
    # Legacy fields (optional for backward compatibility)
    playlist_id: Optional[int] = None
    collection_id: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    repeat: bool = False


class ScheduleCreate(ScheduleBase):
    pass


class ScheduleUpdate(BaseModel):
    name: Optional[str] = None
    channel_id: Optional[int] = None
    keep_multi_part_episodes_together: Optional[bool] = None
    treat_collections_as_shows: Optional[bool] = None
    shuffle_schedule_items: Optional[bool] = None
    random_start_point: Optional[bool] = None


class ScheduleResponse(ScheduleBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Schedule Item Schemas
class ScheduleItemBase(BaseModel):
    schedule_id: int
    index: Optional[int] = None
    
    # Start Type
    start_type: Optional[str] = "dynamic"  # "dynamic" or "fixed"
    start_time: Optional[datetime] = None
    fixed_start_time_behavior: Optional[str] = None  # "start_immediately", "skip_item", "wait_for_next"
    
    # Collection Type
    collection_type: Optional[str] = "collection"  # "collection", "television_show", "television_season", "artist", "multi_collection", "smart_collection", "playlist"
    collection_id: Optional[int] = None
    media_item_id: Optional[int] = None
    playlist_id: Optional[int] = None
    search_title: Optional[str] = None
    search_query: Optional[str] = None
    # Plex-specific collection types
    plex_show_key: Optional[str] = None  # For TELEVISION_SHOW
    plex_season_key: Optional[str] = None  # For TELEVISION_SEASON
    plex_artist_key: Optional[str] = None  # For ARTIST
    
    # Playback Order
    playback_order: Optional[str] = "chronological"  # "chronological", "random", "shuffle", "shuffle_in_order", "season_episode"
    
    # Playout Mode
    playout_mode: Optional[str] = "one"  # "flood", "one", "multiple", "duration"
    multiple_mode: Optional[str] = None  # "count", "collection_size", "multi_episode_group_size", "playlist_item_size"
    multiple_count: Optional[int] = None
    playout_duration_hours: Optional[int] = 0
    playout_duration_minutes: Optional[int] = 0
    
    # Fill Options
    fill_with_group_mode: Optional[str] = None  # "none", "ordered_groups", "shuffled_groups"
    tail_mode: Optional[str] = None  # "none", "offline", "filler"
    tail_filler_collection_id: Optional[int] = None
    discard_to_fill_attempts: Optional[int] = None
    
    # Custom Title and Guide
    custom_title: Optional[str] = None
    guide_mode: Optional[str] = "normal"  # "normal", "custom", "hide"
    
    # Fillers
    pre_roll_filler_id: Optional[int] = None
    mid_roll_filler_id: Optional[int] = None
    post_roll_filler_id: Optional[int] = None
    tail_filler_id: Optional[int] = None
    fallback_filler_id: Optional[int] = None
    
    # Overrides
    watermark_id: Optional[int] = None
    preferred_audio_language: Optional[str] = None
    preferred_audio_title: Optional[str] = None
    preferred_subtitle_language: Optional[str] = None
    subtitle_mode: Optional[str] = None


class ScheduleItemCreate(ScheduleItemBase):
    pass


class ScheduleItemUpdate(BaseModel):
    index: Optional[int] = None
    start_type: Optional[str] = None
    start_time: Optional[datetime] = None
    fixed_start_time_behavior: Optional[str] = None
    collection_type: Optional[str] = None
    collection_id: Optional[int] = None
    media_item_id: Optional[int] = None
    playlist_id: Optional[int] = None
    search_title: Optional[str] = None
    search_query: Optional[str] = None
    plex_show_key: Optional[str] = None
    plex_season_key: Optional[str] = None
    plex_artist_key: Optional[str] = None
    playback_order: Optional[str] = None
    playout_mode: Optional[str] = None
    multiple_mode: Optional[str] = None
    multiple_count: Optional[int] = None
    playout_duration_hours: Optional[int] = None
    playout_duration_minutes: Optional[int] = None
    fill_with_group_mode: Optional[str] = None
    tail_mode: Optional[str] = None
    tail_filler_collection_id: Optional[int] = None
    discard_to_fill_attempts: Optional[int] = None
    custom_title: Optional[str] = None
    guide_mode: Optional[str] = None
    pre_roll_filler_id: Optional[int] = None
    mid_roll_filler_id: Optional[int] = None
    post_roll_filler_id: Optional[int] = None
    tail_filler_id: Optional[int] = None
    fallback_filler_id: Optional[int] = None
    watermark_id: Optional[int] = None
    preferred_audio_language: Optional[str] = None
    preferred_audio_title: Optional[str] = None
    preferred_subtitle_language: Optional[str] = None
    subtitle_mode: Optional[str] = None


class ScheduleItemResponse(ScheduleItemBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Settings Schemas
class FFmpegSettingsBase(BaseModel):
    ffmpeg_path: Optional[str] = None
    ffprobe_path: Optional[str] = None
    log_level: Optional[str] = None
    threads: Optional[int] = None
    hwaccel: Optional[str] = None
    hwaccel_device: Optional[str] = None
    extra_flags: Optional[str] = None


class FFmpegSettingsUpdate(FFmpegSettingsBase):
    pass


class FFmpegSettingsResponse(BaseModel):
    ffmpeg_path: str
    ffprobe_path: str
    log_level: str
    threads: int
    hwaccel: Optional[str]
    hwaccel_device: Optional[str]
    extra_flags: Optional[str]
    
    class Config:
        from_attributes = True


# HDHomeRun Settings Schemas
class HDHomeRunSettingsBase(BaseModel):
    enabled: Optional[bool] = None
    device_id: Optional[str] = None
    friendly_name: Optional[str] = None
    tuner_count: Optional[int] = None
    enable_ssdp: Optional[bool] = None


class HDHomeRunSettingsUpdate(HDHomeRunSettingsBase):
    pass


class HDHomeRunSettingsResponse(BaseModel):
    enabled: bool
    device_id: str
    friendly_name: str
    tuner_count: int
    enable_ssdp: bool
    
    class Config:
        from_attributes = True


# Playout Settings Schemas
class PlayoutSettingsBase(BaseModel):
    build_days: Optional[int] = None


class PlayoutSettingsUpdate(PlayoutSettingsBase):
    pass


class PlayoutSettingsResponse(BaseModel):
    build_days: int
    
    class Config:
        from_attributes = True


# Plex Settings Schemas
class PlexSettingsBase(BaseModel):
    enabled: Optional[bool] = None
    base_url: Optional[str] = None
    token: Optional[str] = None
    use_for_epg: Optional[bool] = None


class PlexSettingsUpdate(PlexSettingsBase):
    pass


class PlexSettingsResponse(BaseModel):
    enabled: bool
    base_url: Optional[str]
    token: Optional[str]
    use_for_epg: bool
    
    class Config:
        from_attributes = True
