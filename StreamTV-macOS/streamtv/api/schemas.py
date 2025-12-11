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
    channel_id: int
    playlist_id: Optional[int] = None
    collection_id: Optional[int] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    repeat: bool = False


class ScheduleCreate(ScheduleBase):
    pass


class ScheduleResponse(ScheduleBase):
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
