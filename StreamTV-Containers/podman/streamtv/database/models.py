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


class Collection(Base):
    """Media collection"""
    __tablename__ = "collections"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=True)
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


class Schedule(Base):
    """Channel schedule"""
    __tablename__ = "schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    playlist_id = Column(Integer, ForeignKey("playlists.id"), nullable=True)
    collection_id = Column(Integer, ForeignKey("collections.id"), nullable=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    repeat = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    channel = relationship("Channel", back_populates="schedules")


class ChannelPlaybackPosition(Base):
    """Track playback position for on-demand channels"""
    __tablename__ = "channel_playback_positions"
    
    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False, unique=True)
    channel_number = Column(String, nullable=False, index=True)
    
    # Position tracking - resume from beginning of last item
    last_item_index = Column(Integer, default=0, nullable=False)  # Index in schedule items (0-based)
    last_item_media_id = Column(Integer, ForeignKey("media_items.id"), nullable=True)
    
    # Metadata
    last_played_at = Column(DateTime, nullable=True)
    total_items_watched = Column(Integer, default=0)  # Total items completed
    
    # Relationships
    channel = relationship("Channel", backref="playback_position")
    last_item = relationship("MediaItem")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
