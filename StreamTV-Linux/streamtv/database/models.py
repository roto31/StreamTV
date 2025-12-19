"""Database models"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, Enum as SQLEnum
from sqlalchemy.orm import relationship
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


class Channel(Base):
    """TV Channel model"""
    __tablename__ = "channels"
    
    id = Column(Integer, primary_key=True, index=True)
    number = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    group = Column(String, nullable=True)
    enabled = Column(Boolean, default=True)
    logo_path = Column(String, nullable=True)
    playout_mode = Column(SQLEnum(PlayoutMode), default=PlayoutMode.CONTINUOUS, nullable=False)  # Continuous or on-demand
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    schedules = relationship("Schedule", back_populates="channel", cascade="all, delete-orphan")
    playlists = relationship("Playlist", back_populates="channel", cascade="all, delete-orphan")


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
