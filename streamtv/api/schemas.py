"""Pydantic schemas for API requests and responses"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Union
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
try:
    from ..database.models import (
        StreamingMode, ChannelTranscodeMode, ChannelSubtitleMode,
        ChannelStreamSelectorMode, ChannelMusicVideoCreditsMode,
        ChannelSongVideoMode, ChannelIdleBehavior, ChannelPlayoutSource
    )
except ImportError:
    # Fallback enums if models not available
    from enum import Enum
    class StreamingMode(str, Enum):
        TRANSPORT_STREAM_HYBRID = "transport_stream_hybrid"
    class ChannelTranscodeMode(str, Enum):
        ON_DEMAND = "on_demand"
    class ChannelSubtitleMode(str, Enum):
        NONE = "none"
    class ChannelStreamSelectorMode(str, Enum):
        DEFAULT = "default"
    class ChannelMusicVideoCreditsMode(str, Enum):
        NONE = "none"
    class ChannelSongVideoMode(str, Enum):
        DEFAULT = "default"
    class ChannelIdleBehavior(str, Enum):
        STOP_ON_DISCONNECT = "stop_on_disconnect"
    class ChannelPlayoutSource(str, Enum):
        GENERATED = "generated"


class ChannelBase(BaseModel):
    number: str
    name: str
    group: Optional[str] = None
    enabled: bool = True
    logo_path: Optional[str] = None
    playout_mode: Union[PlayoutMode, str] = PlayoutMode.CONTINUOUS  # Continuous or on-demand
    transcode_profile: Optional[str] = None  # "cpu", "nvidia", "intel" (legacy)
    is_yaml_source: bool = False
    
    @field_validator('playout_mode', mode='before')
    @classmethod
    def validate_playout_mode(cls, v):
        """Convert string values to enum instances"""
        if isinstance(v, str):
            # Try to match by value first (lowercase)
            v_lower = v.lower()
            if v_lower == "continuous":
                return PlayoutMode.CONTINUOUS
            elif v_lower == "on_demand" or v_lower == "on-demand":
                return PlayoutMode.ON_DEMAND
            # Try to match by name (uppercase)
            try:
                return PlayoutMode[v.upper()]
            except KeyError:
                # If neither works, try direct value match
                for mode in PlayoutMode:
                    if mode.value == v:
                        return mode
                raise ValueError(f"Invalid playout_mode value: {v}. Must be one of: {[m.value for m in PlayoutMode]}")
        return v
    # ErsatzTV-compatible settings
    ffmpeg_profile_id: Optional[int] = None
    watermark_id: Optional[int] = None
    streaming_mode: StreamingMode = StreamingMode.TRANSPORT_STREAM_HYBRID
    transcode_mode: ChannelTranscodeMode = ChannelTranscodeMode.ON_DEMAND
    subtitle_mode: ChannelSubtitleMode = ChannelSubtitleMode.NONE
    preferred_audio_language_code: Optional[str] = None
    preferred_audio_title: Optional[str] = None
    preferred_subtitle_language_code: Optional[str] = None
    stream_selector_mode: ChannelStreamSelectorMode = ChannelStreamSelectorMode.DEFAULT
    stream_selector: Optional[str] = None
    music_video_credits_mode: ChannelMusicVideoCreditsMode = ChannelMusicVideoCreditsMode.NONE
    music_video_credits_template: Optional[str] = None
    song_video_mode: ChannelSongVideoMode = ChannelSongVideoMode.DEFAULT
    idle_behavior: ChannelIdleBehavior = ChannelIdleBehavior.STOP_ON_DISCONNECT
    playout_source: ChannelPlayoutSource = ChannelPlayoutSource.GENERATED
    mirror_source_channel_id: Optional[int] = None
    playout_offset: Optional[int] = None  # Offset in seconds
    show_in_epg: bool = True


class ChannelCreate(ChannelBase):
    pass


class ChannelUpdate(BaseModel):
    number: Optional[str] = None
    name: Optional[str] = None
    group: Optional[str] = None
    enabled: Optional[bool] = None
    logo_path: Optional[str] = None
    playout_mode: Optional[PlayoutMode] = None
    transcode_profile: Optional[str] = None
    # ErsatzTV-compatible settings
    ffmpeg_profile_id: Optional[int] = None
    watermark_id: Optional[int] = None
    streaming_mode: Optional[StreamingMode] = None
    transcode_mode: Optional[ChannelTranscodeMode] = None
    subtitle_mode: Optional[ChannelSubtitleMode] = None
    preferred_audio_language_code: Optional[str] = None
    preferred_audio_title: Optional[str] = None
    preferred_subtitle_language_code: Optional[str] = None
    stream_selector_mode: Optional[ChannelStreamSelectorMode] = None
    stream_selector: Optional[str] = None
    music_video_credits_mode: Optional[ChannelMusicVideoCreditsMode] = None
    music_video_credits_template: Optional[str] = None
    song_video_mode: Optional[ChannelSongVideoMode] = None
    idle_behavior: Optional[ChannelIdleBehavior] = None
    playout_source: Optional[ChannelPlayoutSource] = None
    mirror_source_channel_id: Optional[int] = None
    playout_offset: Optional[int] = None
    show_in_epg: Optional[bool] = None


class ChannelResponse(ChannelBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    updated_at: datetime
    # Include related objects
    ffmpeg_profile: Optional["FFmpegProfileResponse"] = None
    watermark: Optional["WatermarkResponse"] = None


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
    is_yaml_source: bool = False
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
    # Per-source overrides
    youtube_hwaccel: Optional[str] = None
    archive_org_hwaccel: Optional[str] = None
    pbs_hwaccel: Optional[str] = None
    plex_hwaccel: Optional[str] = None
    youtube_video_encoder: Optional[str] = None
    archive_org_video_encoder: Optional[str] = None
    pbs_video_encoder: Optional[str] = None
    plex_video_encoder: Optional[str] = None


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
    youtube_hwaccel: Optional[str]
    archive_org_hwaccel: Optional[str]
    pbs_hwaccel: Optional[str]
    plex_hwaccel: Optional[str]
    youtube_video_encoder: Optional[str]
    archive_org_video_encoder: Optional[str]
    pbs_video_encoder: Optional[str]
    plex_video_encoder: Optional[str]
    
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


# Resolution Schemas
class ResolutionBase(BaseModel):
    name: str
    width: int
    height: int
    is_custom: bool = True


class ResolutionCreate(ResolutionBase):
    pass


class ResolutionUpdate(BaseModel):
    name: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    is_custom: Optional[bool] = None


class ResolutionResponse(ResolutionBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# FFmpeg Profile Schemas
try:
    from ..database.models import (
        HardwareAccelerationKind, VideoFormat, AudioFormat, BitDepth,
        ScalingBehavior, TonemapAlgorithm, NormalizeLoudnessMode
    )
except ImportError:
    # Fallback enums if models not available
    from enum import Enum
    class HardwareAccelerationKind(str, Enum):
        NONE = "none"
    class VideoFormat(str, Enum):
        H264 = "h264"
    class AudioFormat(str, Enum):
        AAC = "aac"
    class BitDepth(str, Enum):
        EIGHT_BIT = "8bit"
    class ScalingBehavior(str, Enum):
        SCALE_AND_PAD = "scale_and_pad"
    class TonemapAlgorithm(str, Enum):
        LINEAR = "linear"
    class NormalizeLoudnessMode(str, Enum):
        OFF = "off"


class FFmpegProfileBase(BaseModel):
    name: str
    thread_count: int = 0
    hardware_acceleration: HardwareAccelerationKind = HardwareAccelerationKind.NONE
    vaapi_driver: Optional[str] = None
    vaapi_device: Optional[str] = None
    qsv_extra_hardware_frames: Optional[int] = None
    resolution_id: int
    scaling_behavior: ScalingBehavior = ScalingBehavior.SCALE_AND_PAD
    video_format: VideoFormat = VideoFormat.H264
    video_profile: Optional[str] = None
    video_preset: Optional[str] = None
    allow_b_frames: bool = False
    bit_depth: BitDepth = BitDepth.EIGHT_BIT
    video_bitrate: int = 2000
    video_buffer_size: int = 4000
    tonemap_algorithm: TonemapAlgorithm = TonemapAlgorithm.LINEAR
    audio_format: AudioFormat = AudioFormat.AAC
    audio_bitrate: int = 192
    audio_buffer_size: int = 384
    normalize_loudness_mode: NormalizeLoudnessMode = NormalizeLoudnessMode.OFF
    audio_channels: int = 2
    audio_sample_rate: int = 48000
    normalize_framerate: bool = False
    deinterlace_video: Optional[bool] = None


class FFmpegProfileCreate(FFmpegProfileBase):
    pass


class FFmpegProfileUpdate(BaseModel):
    name: Optional[str] = None
    thread_count: Optional[int] = None
    hardware_acceleration: Optional[HardwareAccelerationKind] = None
    vaapi_driver: Optional[str] = None
    vaapi_device: Optional[str] = None
    qsv_extra_hardware_frames: Optional[int] = None
    resolution_id: Optional[int] = None
    scaling_behavior: Optional[ScalingBehavior] = None
    video_format: Optional[VideoFormat] = None
    video_profile: Optional[str] = None
    video_preset: Optional[str] = None
    allow_b_frames: Optional[bool] = None
    bit_depth: Optional[BitDepth] = None
    video_bitrate: Optional[int] = None
    video_buffer_size: Optional[int] = None
    tonemap_algorithm: Optional[TonemapAlgorithm] = None
    audio_format: Optional[AudioFormat] = None
    audio_bitrate: Optional[int] = None
    audio_buffer_size: Optional[int] = None
    normalize_loudness_mode: Optional[NormalizeLoudnessMode] = None
    audio_channels: Optional[int] = None
    audio_sample_rate: Optional[int] = None
    normalize_framerate: Optional[bool] = None
    deinterlace_video: Optional[bool] = None


class FFmpegProfileResponse(FFmpegProfileBase):
    id: int
    created_at: datetime
    updated_at: datetime
    resolution: Optional[ResolutionResponse] = None
    
    class Config:
        from_attributes = True


class HardwareAccelerationResponse(BaseModel):
    available: List[str]


# Watermark Schemas
try:
    from ..database.models import (
        ChannelWatermarkMode, ChannelWatermarkImageSource,
        WatermarkLocation, WatermarkSize
    )
except ImportError:
    # Fallback enums if models not available
    from enum import Enum
    class ChannelWatermarkMode(str, Enum):
        PERMANENT = "permanent"
    class ChannelWatermarkImageSource(str, Enum):
        CUSTOM = "custom"
    class WatermarkLocation(str, Enum):
        BOTTOM_RIGHT = "bottom_right"
    class WatermarkSize(str, Enum):
        MEDIUM = "medium"


class WatermarkBase(BaseModel):
    name: str
    mode: ChannelWatermarkMode = ChannelWatermarkMode.PERMANENT
    image_source: ChannelWatermarkImageSource = ChannelWatermarkImageSource.CUSTOM
    location: WatermarkLocation = WatermarkLocation.BOTTOM_RIGHT
    size: WatermarkSize = WatermarkSize.MEDIUM
    width_percent: float = 10.0
    horizontal_margin_percent: float = 2.0
    vertical_margin_percent: float = 2.0
    frequency_minutes: int = 0
    duration_seconds: int = 0
    opacity: int = 100
    place_within_source_content: bool = True
    opacity_expression: Optional[str] = None
    z_index: int = 0


class WatermarkCreate(WatermarkBase):
    image: Optional[str] = None  # Path to image (set via upload endpoint)


class WatermarkUpdate(BaseModel):
    name: Optional[str] = None
    mode: Optional[ChannelWatermarkMode] = None
    image_source: Optional[ChannelWatermarkImageSource] = None
    location: Optional[WatermarkLocation] = None
    size: Optional[WatermarkSize] = None
    width_percent: Optional[float] = None
    horizontal_margin_percent: Optional[float] = None
    vertical_margin_percent: Optional[float] = None
    frequency_minutes: Optional[int] = None
    duration_seconds: Optional[int] = None
    opacity: Optional[int] = None
    place_within_source_content: Optional[bool] = None
    opacity_expression: Optional[str] = None
    z_index: Optional[int] = None
    image: Optional[str] = None


class WatermarkResponse(WatermarkBase):
    id: int
    image: Optional[str] = None
    original_content_type: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
