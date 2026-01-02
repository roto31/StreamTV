"""Database models"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, Enum as SQLEnum, event
from sqlalchemy.orm import relationship, reconstructor
from datetime import datetime
from enum import Enum

from .session import Base


class StreamSource(str, Enum):
    YOUTUBE = "youtube"
    ARCHIVE_ORG = "archive_org"
    PBS = "pbs"
    PLEX = "plex"


class PlayoutMode(str, Enum):
    CONTINUOUS = "continuous"  # ErsatzTV-style continuous playout (timeline-based)
    ON_DEMAND = "on_demand"    # On-demand streaming (starts from beginning when requested)


# Enums needed for Channel model (must be defined before Channel)
class StreamingMode(str, Enum):
    TRANSPORT_STREAM = "transport_stream"
    HTTP_LIVE_STREAMING_DIRECT = "http_live_streaming_direct"
    HTTP_LIVE_STREAMING_SEGMENTER = "http_live_streaming_segmenter"
    TRANSPORT_STREAM_HYBRID = "transport_stream_hybrid"


class ChannelTranscodeMode(str, Enum):
    ON_DEMAND = "on_demand"


class ChannelSubtitleMode(str, Enum):
    NONE = "none"
    FORCED = "forced"
    DEFAULT = "default"
    ANY = "any"


class ChannelStreamSelectorMode(str, Enum):
    DEFAULT = "default"
    CUSTOM = "custom"
    TROUBLESHOOTING = "troubleshooting"


class ChannelMusicVideoCreditsMode(str, Enum):
    NONE = "none"
    GENERATE_SUBTITLES = "generate_subtitles"


class ChannelSongVideoMode(str, Enum):
    DEFAULT = "default"
    WITH_PROGRESS = "with_progress"


class ChannelIdleBehavior(str, Enum):
    STOP_ON_DISCONNECT = "stop_on_disconnect"
    KEEP_RUNNING = "keep_running"


class ChannelPlayoutSource(str, Enum):
    GENERATED = "generated"
    MIRROR = "mirror"


# Enum value mapping caches for fast lookup during @reconstructor
_PLAYOUT_MODE_MAP = {mode.value.lower(): mode for mode in PlayoutMode}
_STREAMING_MODE_MAP = {mode.value.lower(): mode for mode in StreamingMode}
_TRANSCODE_MODE_MAP = {mode.value.lower(): mode for mode in ChannelTranscodeMode}
_SUBTITLE_MODE_MAP = {mode.value.lower(): mode for mode in ChannelSubtitleMode}
_STREAM_SELECTOR_MODE_MAP = {mode.value.lower(): mode for mode in ChannelStreamSelectorMode}
_MUSIC_VIDEO_CREDITS_MODE_MAP = {mode.value.lower(): mode for mode in ChannelMusicVideoCreditsMode}
_SONG_VIDEO_MODE_MAP = {mode.value.lower(): mode for mode in ChannelSongVideoMode}
_IDLE_BEHAVIOR_MAP = {mode.value.lower(): mode for mode in ChannelIdleBehavior}
_PLAYOUT_SOURCE_MAP = {mode.value.lower(): mode for mode in ChannelPlayoutSource}


class Channel(Base):
    """TV Channel model"""
    __tablename__ = "channels"
    
    id = Column(Integer, primary_key=True, index=True)
    number = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    group = Column(String, nullable=True)
    enabled = Column(Boolean, default=True)
    logo_path = Column(String, nullable=True)
    # Authoritative source flags and transcoding presets
    is_yaml_source = Column(Boolean, default=False, nullable=False)
    transcode_profile = Column(String, nullable=True)  # e.g., "cpu", "nvidia", "intel" (legacy, use ffmpeg_profile_id instead)
    # Store as String to avoid SQLAlchemy enum validation issues with SQLite
    # Conversion to enum handled by @reconstructor method
    playout_mode = Column(String, default=PlayoutMode.CONTINUOUS.value, nullable=False)  # Continuous or on-demand
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # ErsatzTV-compatible settings
    ffmpeg_profile_id = Column(Integer, ForeignKey("ffmpeg_profiles.id"), nullable=True)
    watermark_id = Column(Integer, ForeignKey("watermarks.id"), nullable=True)
    # Store as String to avoid SQLAlchemy enum validation issues with SQLite
    # Conversion to enum handled by @reconstructor method
    streaming_mode = Column(String, default=StreamingMode.TRANSPORT_STREAM_HYBRID.value, nullable=False)
    transcode_mode = Column(String, default=ChannelTranscodeMode.ON_DEMAND.value, nullable=False)
    subtitle_mode = Column(String, default=ChannelSubtitleMode.NONE.value, nullable=False)
    preferred_audio_language_code = Column(String, nullable=True)  # ISO 639-1 code
    preferred_audio_title = Column(String, nullable=True)
    preferred_subtitle_language_code = Column(String, nullable=True)  # ISO 639-1 code
    stream_selector_mode = Column(String, default=ChannelStreamSelectorMode.DEFAULT.value, nullable=False)
    stream_selector = Column(String, nullable=True)  # Custom stream selector expression
    music_video_credits_mode = Column(String, default=ChannelMusicVideoCreditsMode.NONE.value, nullable=False)
    music_video_credits_template = Column(Text, nullable=True)
    song_video_mode = Column(String, default=ChannelSongVideoMode.DEFAULT.value, nullable=False)
    idle_behavior = Column(String, default=ChannelIdleBehavior.STOP_ON_DISCONNECT.value, nullable=False)
    playout_source = Column(String, default=ChannelPlayoutSource.GENERATED.value, nullable=False)
    mirror_source_channel_id = Column(Integer, ForeignKey("channels.id"), nullable=True)
    playout_offset = Column(Integer, nullable=True)  # Offset in seconds
    show_in_epg = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    schedules = relationship("Schedule", back_populates="channel", cascade="all, delete-orphan")
    playlists = relationship("Playlist", back_populates="channel", cascade="all, delete-orphan")
    ffmpeg_profile = relationship("FFmpegProfile", back_populates="channels")
    watermark = relationship("Watermark", back_populates="channels")
    mirror_source_channel = relationship("Channel", remote_side=[id], foreign_keys=[mirror_source_channel_id])
    
    @reconstructor
    def _on_load(self):
        """Ensure enum fields are always enum instances when loaded from database - optimized with dict lookups"""
        # Optimized enum conversion using pre-built dict mappings for O(1) lookup instead of O(n) iteration
        # Only convert if value is a string (not already an enum instance)
        
        # playout_mode conversion
        if isinstance(getattr(self, 'playout_mode', None), str):
            normalized = self.playout_mode.lower()
            enum_val = _PLAYOUT_MODE_MAP.get(normalized)
            if not enum_val:
                try:
                    enum_val = PlayoutMode[self.playout_mode.upper().replace('-', '_')]
                except KeyError:
                    enum_val = PlayoutMode.CONTINUOUS
            object.__setattr__(self, 'playout_mode', enum_val)
        
        # streaming_mode conversion
        if isinstance(getattr(self, 'streaming_mode', None), str):
            normalized = self.streaming_mode.lower()
            enum_val = _STREAMING_MODE_MAP.get(normalized)
            if not enum_val:
                try:
                    enum_val = StreamingMode[self.streaming_mode.upper().replace('-', '_')]
                except KeyError:
                    enum_val = StreamingMode.TRANSPORT_STREAM_HYBRID
            object.__setattr__(self, 'streaming_mode', enum_val)
        
        # transcode_mode conversion
        if isinstance(getattr(self, 'transcode_mode', None), str):
            normalized = self.transcode_mode.lower()
            enum_val = _TRANSCODE_MODE_MAP.get(normalized)
            if not enum_val:
                try:
                    enum_val = ChannelTranscodeMode[self.transcode_mode.upper().replace('-', '_')]
                except KeyError:
                    enum_val = ChannelTranscodeMode.ON_DEMAND
            object.__setattr__(self, 'transcode_mode', enum_val)
        
        # subtitle_mode conversion
        if isinstance(getattr(self, 'subtitle_mode', None), str):
            normalized = self.subtitle_mode.lower()
            enum_val = _SUBTITLE_MODE_MAP.get(normalized)
            if not enum_val:
                try:
                    enum_val = ChannelSubtitleMode[self.subtitle_mode.upper().replace('-', '_')]
                except KeyError:
                    enum_val = ChannelSubtitleMode.NONE
            object.__setattr__(self, 'subtitle_mode', enum_val)
        
        # stream_selector_mode conversion
        if isinstance(getattr(self, 'stream_selector_mode', None), str):
            normalized = self.stream_selector_mode.lower()
            enum_val = _STREAM_SELECTOR_MODE_MAP.get(normalized)
            if not enum_val:
                try:
                    enum_val = ChannelStreamSelectorMode[self.stream_selector_mode.upper().replace('-', '_')]
                except KeyError:
                    enum_val = ChannelStreamSelectorMode.DEFAULT
            object.__setattr__(self, 'stream_selector_mode', enum_val)
        
        # music_video_credits_mode conversion
        if isinstance(getattr(self, 'music_video_credits_mode', None), str):
            normalized = self.music_video_credits_mode.lower()
            enum_val = _MUSIC_VIDEO_CREDITS_MODE_MAP.get(normalized)
            if not enum_val:
                try:
                    enum_val = ChannelMusicVideoCreditsMode[self.music_video_credits_mode.upper().replace('-', '_')]
                except KeyError:
                    enum_val = ChannelMusicVideoCreditsMode.NONE
            object.__setattr__(self, 'music_video_credits_mode', enum_val)
        
        # song_video_mode conversion
        if isinstance(getattr(self, 'song_video_mode', None), str):
            normalized = self.song_video_mode.lower()
            enum_val = _SONG_VIDEO_MODE_MAP.get(normalized)
            if not enum_val:
                try:
                    enum_val = ChannelSongVideoMode[self.song_video_mode.upper().replace('-', '_')]
                except KeyError:
                    enum_val = ChannelSongVideoMode.DEFAULT
            object.__setattr__(self, 'song_video_mode', enum_val)
        
        # idle_behavior conversion
        if isinstance(getattr(self, 'idle_behavior', None), str):
            normalized = self.idle_behavior.lower()
            enum_val = _IDLE_BEHAVIOR_MAP.get(normalized)
            if not enum_val:
                try:
                    enum_val = ChannelIdleBehavior[self.idle_behavior.upper().replace('-', '_')]
                except KeyError:
                    enum_val = ChannelIdleBehavior.STOP_ON_DISCONNECT
            object.__setattr__(self, 'idle_behavior', enum_val)
        
        # playout_source conversion
        if isinstance(getattr(self, 'playout_source', None), str):
            normalized = self.playout_source.lower()
            enum_val = _PLAYOUT_SOURCE_MAP.get(normalized)
            if not enum_val:
                try:
                    enum_val = ChannelPlayoutSource[self.playout_source.upper().replace('-', '_')]
                except KeyError:
                    enum_val = ChannelPlayoutSource.GENERATED
            object.__setattr__(self, 'playout_source', enum_val)


class MediaItem(Base):
    """Media item from YouTube or Archive.org"""
    __tablename__ = "media_items"
    
    id = Column(Integer, primary_key=True, index=True)
    source = Column(SQLEnum(StreamSource), nullable=False)
    source_id = Column(String, nullable=False)  # YouTube video ID or Archive.org identifier
    url = Column(String, nullable=False, unique=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    duration = Column(Integer, nullable=True)  # Duration in seconds
    thumbnail = Column(String, nullable=True)
    uploader = Column(String, nullable=True)
    upload_date = Column(String, nullable=True)
    view_count = Column(Integer, nullable=True)
    meta_data = Column(Text, nullable=True)  # JSON string for additional metadata (renamed from 'metadata' to avoid SQLAlchemy conflict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    playlist_items = relationship("PlaylistItem", back_populates="media_item", cascade="all, delete-orphan")
    collection_items = relationship("CollectionItem", back_populates="media_item", cascade="all, delete-orphan")


class CollectionTypeEnum(str, Enum):
    MANUAL = "manual"  # Manually selected items
    SMART = "smart"  # Built from search queries
    MULTI = "multi"  # Combination of TV shows and movies


class Collection(Base):
    """Media collection"""
    __tablename__ = "collections"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=True)
    collection_type = Column(SQLEnum(CollectionTypeEnum), default=CollectionTypeEnum.MANUAL, nullable=False)  # manual, smart, multi
    search_query = Column(Text, nullable=True)  # For smart collections - stores the search query
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    items = relationship("CollectionItem", back_populates="collection", cascade="all, delete-orphan")


class CollectionItem(Base):
    """Collection item join table"""
    __tablename__ = "collection_items"
    
    id = Column(Integer, primary_key=True, index=True)
    collection_id = Column(Integer, ForeignKey("collections.id"), nullable=False)
    media_item_id = Column(Integer, ForeignKey("media_items.id"), nullable=False)
    order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    collection = relationship("Collection", back_populates="items")
    media_item = relationship("MediaItem", back_populates="collection_items")


class Playlist(Base):
    """Playlist for channel scheduling"""
    __tablename__ = "playlists"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    channel = relationship("Channel", back_populates="playlists")
    items = relationship("PlaylistItem", back_populates="playlist", cascade="all, delete-orphan", order_by="PlaylistItem.order")


class PlaylistItem(Base):
    """Playlist item"""
    __tablename__ = "playlist_items"
    
    id = Column(Integer, primary_key=True, index=True)
    playlist_id = Column(Integer, ForeignKey("playlists.id"), nullable=False)
    media_item_id = Column(Integer, ForeignKey("media_items.id"), nullable=False)
    order = Column(Integer, default=0)
    start_time = Column(DateTime, nullable=True)  # For scheduled playback
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    playlist = relationship("Playlist", back_populates="items")
    media_item = relationship("MediaItem", back_populates="playlist_items")


class StartType(str, Enum):
    DYNAMIC = "dynamic"
    FIXED = "fixed"


class FixedStartTimeBehavior(str, Enum):
    STRICT = "strict"  # Always wait for exact start time, even if that means waiting until next day
    FLEXIBLE = "flexible"  # Start immediately if waiting would go into next day


class CollectionType(str, Enum):
    COLLECTION = "collection"
    MEDIA_ITEM = "media_item"
    PLAYLIST = "playlist"
    MULTI_COLLECTION = "multi_collection"
    SMART_COLLECTION = "smart_collection"
    RERUN_COLLECTION = "rerun_collection"


class PlaybackOrder(str, Enum):
    CHRONOLOGICAL = "chronological"  # By release date, then season/episode
    RANDOM = "random"  # Random order, may contain repeats
    SHUFFLE = "shuffle"  # Random order, no repeats until all played
    SHUFFLE_IN_ORDER = "shuffle_in_order"  # Groups shuffled, contents chronological
    SEASON_EPISODE = "season_episode"  # By season then episode number


class PlayoutModeItem(str, Enum):
    ONE = "one"
    MULTIPLE = "multiple"


class MultipleMode(str, Enum):
    COUNT = "count"  # Play specific number of items
    COLLECTION_SIZE = "collection_size"  # Play all items from collection
    MULTI_EPISODE_GROUP_SIZE = "multi_episode_group_size"  # Play all items from current multi-part episode group
    PLAYLIST_ITEM_SIZE = "playlist_item_size"  # Play all items from current playlist item


class FillWithGroupMode(str, Enum):
    NONE = "none"  # No change to scheduling behavior
    ORDERED_GROUPS = "ordered_groups"  # Fill with single group, rotate in fixed order
    SHUFFLED_GROUPS = "shuffled_groups"  # Fill with single group, rotate in shuffled order


class TailMode(str, Enum):
    NONE = "none"  # Immediately advance to next schedule item
    OFFLINE = "offline"  # Show offline image for remainder
    FILLER = "filler"  # Fill with specified collection, then offline image if needed


class GuideMode(str, Enum):
    NORMAL = "normal"
    CUSTOM = "custom"
    HIDE = "hide"


class Schedule(Base):
    """Channel schedule - ErsatzTV-style classic schedule"""
    __tablename__ = "schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # Schedule name
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    # Authoritative source flag
    is_yaml_source = Column(Boolean, default=False, nullable=False)
    
    # ErsatzTV Schedule Settings
    keep_multi_part_episodes_together = Column(Boolean, default=False, nullable=False)
    treat_collections_as_shows = Column(Boolean, default=False, nullable=False)
    shuffle_schedule_items = Column(Boolean, default=False, nullable=False)
    random_start_point = Column(Boolean, default=False, nullable=False)
    
    # Legacy fields (kept for backward compatibility, but not used in ErsatzTV-style scheduling)
    playlist_id = Column(Integer, ForeignKey("playlists.id"), nullable=True)
    collection_id = Column(Integer, ForeignKey("collections.id"), nullable=True)
    start_time = Column(DateTime, nullable=True)  # Made nullable for ErsatzTV-style
    end_time = Column(DateTime, nullable=True)
    repeat = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    channel = relationship("Channel", back_populates="schedules")
    items = relationship("ScheduleItem", back_populates="schedule", cascade="all, delete-orphan", order_by="ScheduleItem.index")


class ScheduleItem(Base):
    """Schedule item - ErsatzTV-style schedule item with all options"""
    __tablename__ = "schedule_items"
    
    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("schedules.id"), nullable=False)
    index = Column(Integer, nullable=False, default=0)  # Order in schedule
    
    # Start Type
    start_type = Column(SQLEnum(StartType), default=StartType.DYNAMIC, nullable=False)
    start_time = Column(DateTime, nullable=True)  # For fixed start time
    fixed_start_time_behavior = Column(SQLEnum(FixedStartTimeBehavior), nullable=True)
    
    # Collection Type
    collection_type = Column(SQLEnum(CollectionType), default=CollectionType.COLLECTION, nullable=False)
    collection_id = Column(Integer, ForeignKey("collections.id"), nullable=True)
    media_item_id = Column(Integer, ForeignKey("media_items.id"), nullable=True)
    playlist_id = Column(Integer, ForeignKey("playlists.id"), nullable=True)
    search_title = Column(String, nullable=True)
    search_query = Column(String, nullable=True)
    
    # Plex-specific collection types (store Plex rating keys)
    plex_show_key = Column(String, nullable=True)  # For TELEVISION_SHOW
    plex_season_key = Column(String, nullable=True)  # For TELEVISION_SEASON
    plex_artist_key = Column(String, nullable=True)  # For ARTIST
    
    # Playback Order
    playback_order = Column(SQLEnum(PlaybackOrder), default=PlaybackOrder.CHRONOLOGICAL, nullable=False)
    
    # Playout Mode
    playout_mode = Column(SQLEnum(PlayoutModeItem), default=PlayoutModeItem.ONE, nullable=False)
    multiple_mode = Column(SQLEnum(MultipleMode), nullable=True)
    multiple_count = Column(Integer, nullable=True)
    playout_duration_hours = Column(Integer, default=0, nullable=False)
    playout_duration_minutes = Column(Integer, default=0, nullable=False)
    
    # Fill Options
    fill_with_group_mode = Column(String, nullable=True)  # "none", "ordered_groups", "shuffled_groups"
    tail_mode = Column(String, nullable=True)  # "none", "offline", "filler"
    tail_filler_collection_id = Column(Integer, ForeignKey("collections.id"), nullable=True)  # Collection for tail filler
    discard_to_fill_attempts = Column(Integer, nullable=True)
    
    # Custom Title and Guide
    custom_title = Column(String, nullable=True)
    guide_mode = Column(SQLEnum(GuideMode), default=GuideMode.NORMAL, nullable=False)
    
    # Fillers
    pre_roll_filler_id = Column(Integer, nullable=True)  # Reference to filler preset
    mid_roll_filler_id = Column(Integer, nullable=True)
    post_roll_filler_id = Column(Integer, nullable=True)
    tail_filler_id = Column(Integer, nullable=True)
    fallback_filler_id = Column(Integer, nullable=True)
    
    # Overrides
    watermark_id = Column(Integer, nullable=True)
    preferred_audio_language = Column(String, nullable=True)
    preferred_audio_title = Column(String, nullable=True)
    preferred_subtitle_language = Column(String, nullable=True)
    subtitle_mode = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    schedule = relationship("Schedule", back_populates="items")
    collection = relationship("Collection", foreign_keys=[collection_id])
    tail_filler_collection = relationship("Collection", foreign_keys=[tail_filler_collection_id])
    media_item = relationship("MediaItem")
    playlist = relationship("Playlist")


class ChannelPlaybackPosition(Base):
    """Track playback position for channels (both continuous and on-demand)"""
    __tablename__ = "channel_playback_positions"
    
    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False, unique=True)
    channel_number = Column(String, nullable=False, index=True)
    
    # Position tracking - resume from beginning of last item
    last_item_index = Column(Integer, default=0, nullable=False)  # Index in schedule items (0-based)
    last_item_media_id = Column(Integer, ForeignKey("media_items.id"), nullable=True)
    
    # For CONTINUOUS channels: track when playout started (not midnight-based)
    # This allows resuming from where it left off after server restart
    playout_start_time = Column(DateTime, nullable=True)  # When the continuous playout cycle started
    last_position_update = Column(DateTime, nullable=True)  # Last time position was saved
    
    # Metadata
    last_played_at = Column(DateTime, nullable=True)
    total_items_watched = Column(Integer, default=0)  # Total items completed
    
    # Relationships
    channel = relationship("Channel", backref="playback_position")
    last_item = relationship("MediaItem")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Hardware Acceleration Enums
class HardwareAccelerationKind(str, Enum):
    NONE = "none"
    NVENC = "nvenc"  # NVIDIA
    QSV = "qsv"  # Intel Quick Sync Video
    VAAPI = "vaapi"  # Linux Video Acceleration API
    VIDEOTOOLBOX = "videotoolbox"  # macOS
    AMF = "amf"  # AMD
    V4L2M2M = "v4l2m2m"  # Linux Video4Linux2
    RKMPP = "rkmpp"  # Rockchip Media Process Platform


class VideoFormat(str, Enum):
    NONE = "none"
    H264 = "h264"
    HEVC = "hevc"
    MPEG2VIDEO = "mpeg2video"
    AV1 = "av1"
    COPY = "copy"


class AudioFormat(str, Enum):
    NONE = "none"
    AAC = "aac"
    AC3 = "ac3"
    AACLATM = "aac_latm"
    COPY = "copy"


class BitDepth(str, Enum):
    EIGHT_BIT = "8bit"
    TEN_BIT = "10bit"


class ScalingBehavior(str, Enum):
    SCALE_AND_PAD = "scale_and_pad"
    STRETCH = "stretch"
    CROP = "crop"


class TonemapAlgorithm(str, Enum):
    LINEAR = "linear"
    CLIP = "clip"
    GAMMA = "gamma"
    REINHARD = "reinhard"
    MOBIUS = "mobius"
    HABLE = "hable"


class NormalizeLoudnessMode(str, Enum):
    OFF = "off"
    LOUDNORM = "loudnorm"


class ChannelPlayoutModeEnum(str, Enum):
    CONTINUOUS = "continuous"
    ON_DEMAND = "on_demand"


class VaapiDriver(str, Enum):
    I915 = "i915"  # Intel
    I965 = "i965"  # Intel
    RADEONSI = "radeonsi"  # AMD
    NOUVEAU = "nouveau"  # NVIDIA open source
    R600 = "r600"  # AMD older
    RADEON = "radeon"  # AMD older


class WatermarkLocation(str, Enum):
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"
    CENTER = "center"


class WatermarkSize(str, Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    CUSTOM = "custom"


class ChannelWatermarkMode(str, Enum):
    NONE = "none"
    PERMANENT = "permanent"
    INTERMITTENT = "intermittent"
    OPACITY_EXPRESSION = "opacity_expression"


class ChannelWatermarkImageSource(str, Enum):
    CUSTOM = "custom"
    CHANNEL_LOGO = "channel_logo"
    RESOURCE = "resource"


# Resolution Model
class Resolution(Base):
    """Resolution preset for FFmpeg profiles"""
    __tablename__ = "resolutions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)  # e.g., "720p", "1080p", "4K"
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    is_custom = Column(Boolean, default=False, nullable=False)  # True for user-created resolutions
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    ffmpeg_profiles = relationship("FFmpegProfile", back_populates="resolution")


# FFmpeg Profile Model
class FFmpegProfile(Base):
    """FFmpeg transcoding profile with hardware acceleration support"""
    __tablename__ = "ffmpeg_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    thread_count = Column(Integer, default=0, nullable=False)
    
    # Hardware Acceleration
    hardware_acceleration = Column(SQLEnum(HardwareAccelerationKind), default=HardwareAccelerationKind.NONE, nullable=False)
    vaapi_driver = Column(String, nullable=True)
    vaapi_device = Column(String, nullable=True)
    qsv_extra_hardware_frames = Column(Integer, nullable=True)
    
    # Resolution
    resolution_id = Column(Integer, ForeignKey("resolutions.id"), nullable=False)
    scaling_behavior = Column(SQLEnum(ScalingBehavior), default=ScalingBehavior.SCALE_AND_PAD, nullable=False)
    
    # Video Settings
    video_format = Column(SQLEnum(VideoFormat), default=VideoFormat.H264, nullable=False)
    video_profile = Column(String, nullable=True)  # main, high, high10, high444p
    video_preset = Column(String, nullable=True)  # veryfast, fast, medium, slow, etc.
    allow_b_frames = Column(Boolean, default=False, nullable=False)
    bit_depth = Column(SQLEnum(BitDepth), default=BitDepth.EIGHT_BIT, nullable=False)
    video_bitrate = Column(Integer, default=2000, nullable=False)  # kbps
    video_buffer_size = Column(Integer, default=4000, nullable=False)  # kbps
    tonemap_algorithm = Column(SQLEnum(TonemapAlgorithm), default=TonemapAlgorithm.LINEAR, nullable=False)
    
    # Audio Settings
    audio_format = Column(SQLEnum(AudioFormat), default=AudioFormat.AAC, nullable=False)
    audio_bitrate = Column(Integer, default=192, nullable=False)  # kbps
    audio_buffer_size = Column(Integer, default=384, nullable=False)  # kbps
    normalize_loudness_mode = Column(SQLEnum(NormalizeLoudnessMode), default=NormalizeLoudnessMode.OFF, nullable=False)
    audio_channels = Column(Integer, default=2, nullable=False)
    audio_sample_rate = Column(Integer, default=48000, nullable=False)
    
    # Other Settings
    normalize_framerate = Column(Boolean, default=False, nullable=False)
    deinterlace_video = Column(Boolean, nullable=True)  # None = auto-detect
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    resolution = relationship("Resolution", back_populates="ffmpeg_profiles")
    channels = relationship("Channel", back_populates="ffmpeg_profile")


# Watermark Model
class Watermark(Base):
    """Watermark configuration for channels"""
    __tablename__ = "watermarks"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    mode = Column(SQLEnum(ChannelWatermarkMode), default=ChannelWatermarkMode.PERMANENT, nullable=False)
    image_source = Column(SQLEnum(ChannelWatermarkImageSource), default=ChannelWatermarkImageSource.CUSTOM, nullable=False)
    image = Column(String, nullable=True)  # Path to image file
    original_content_type = Column(String, nullable=True)  # MIME type of uploaded image
    location = Column(SQLEnum(WatermarkLocation), default=WatermarkLocation.BOTTOM_RIGHT, nullable=False)
    size = Column(SQLEnum(WatermarkSize), default=WatermarkSize.MEDIUM, nullable=False)
    width_percent = Column(Float, default=10.0, nullable=False)  # For custom size
    horizontal_margin_percent = Column(Float, default=2.0, nullable=False)
    vertical_margin_percent = Column(Float, default=2.0, nullable=False)
    frequency_minutes = Column(Integer, default=0, nullable=False)  # For intermittent mode (0 = always)
    duration_seconds = Column(Integer, default=0, nullable=False)  # For intermittent mode (0 = until next frequency)
    opacity = Column(Integer, default=100, nullable=False)  # 0-100
    place_within_source_content = Column(Boolean, default=True, nullable=False)
    opacity_expression = Column(String, nullable=True)  # For opacity expression mode
    z_index = Column(Integer, default=0, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    channels = relationship("Channel", back_populates="watermark")
