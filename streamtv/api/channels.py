"""Channel API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel
import shutil
import logging

from ..database import get_db, Channel
from ..database.models import PlayoutMode, ChannelPlaybackPosition
from ..api.schemas import ChannelCreate, ChannelUpdate, ChannelResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/channels", tags=["Channels"])


@router.get("", response_model=List[ChannelResponse])
def get_all_channels(db: Session = Depends(get_db), include_content_status: bool = False):
    """Get all channels
    
    Args:
        include_content_status: If True, includes 'has_content' field indicating if channel has schedules
    """
    from ..database.models import Schedule, StreamingMode
    from sqlalchemy import text
    
    # Query channels using raw SQL to avoid enum conversion issues, then convert manually
    try:
        channels = db.query(Channel).all()
    except (LookupError, ValueError) as e:
        # If enum conversion fails, query raw and convert manually
        logger.warning(f"Enum conversion error, using raw query: {e}")
        raw_channels = db.execute(text("SELECT * FROM channels")).fetchall()
        channels = []
        for row in raw_channels:
            # Create a mock channel object from row data
            channel = Channel()
            for key, value in row._mapping.items():
                if key == 'streaming_mode' and value:
                    # Convert string to enum
                    try:
                        setattr(channel, key, StreamingMode(value))
                    except ValueError:
                        setattr(channel, key, StreamingMode.TRANSPORT_STREAM_HYBRID)
                else:
                    setattr(channel, key, value)
            channels.append(channel)
    
    if include_content_status:
        # Check which channels have schedules (content)
        channel_ids_with_schedules = {
            schedule.channel_id 
            for schedule in db.query(Schedule.channel_id).distinct()
        }
        
        # Convert to dict with has_content flag
        result = []
        for channel in channels:
            channel_dict = {
                'id': channel.id,
                'number': str(channel.number) if channel.number is not None else '',  # Ensure string type
                'name': channel.name,
                'group': channel.group,
                'enabled': channel.enabled,
                'logo_path': channel.logo_path,
                'playout_mode': channel.playout_mode.value if channel.playout_mode else None,
                'created_at': channel.created_at.isoformat() if channel.created_at else None,
                'updated_at': channel.updated_at.isoformat() if channel.updated_at else None,
                'has_content': channel.id in channel_ids_with_schedules
            }
            result.append(channel_dict)
        return result
    else:
        # Return standard ChannelResponse format
        # Handle enum conversion issues by using raw SQL query and manual conversion
        from ..database.models import StreamingMode, ChannelTranscodeMode, ChannelSubtitleMode, ChannelStreamSelectorMode, ChannelMusicVideoCreditsMode, ChannelSongVideoMode, ChannelIdleBehavior, ChannelPlayoutSource, PlayoutMode
        
        result = []
        # Use raw query to avoid SQLAlchemy enum conversion issues
        raw_channels = db.execute(text("""
            SELECT id, number, name, "group", enabled, logo_path, playout_mode,
                   streaming_mode, transcode_mode, subtitle_mode, 
                   preferred_audio_language_code, preferred_audio_title,
                   preferred_subtitle_language_code, stream_selector_mode,
                   stream_selector, music_video_credits_mode,
                   music_video_credits_template, song_video_mode,
                   idle_behavior, playout_source, mirror_source_channel_id,
                   playout_offset, show_in_epg, created_at, updated_at
            FROM channels
        """)).fetchall()
        
        for row in raw_channels:
            row_dict = dict(row._mapping)
            # Convert enum strings to proper enum values
            if row_dict.get('streaming_mode'):
                try:
                    row_dict['streaming_mode'] = StreamingMode(row_dict['streaming_mode'])
                except (ValueError, KeyError):
                    row_dict['streaming_mode'] = StreamingMode.TRANSPORT_STREAM_HYBRID
            
            if row_dict.get('playout_mode'):
                try:
                    row_dict['playout_mode'] = PlayoutMode(row_dict['playout_mode'])
                except (ValueError, KeyError):
                    row_dict['playout_mode'] = PlayoutMode.CONTINUOUS
            
            # Ensure number is string
            if row_dict.get('number') is not None:
                row_dict['number'] = str(row_dict['number'])
            
            result.append(ChannelResponse(**row_dict))
        return result


@router.get("/{channel_id}", response_model=ChannelResponse)
def get_channel(channel_id: int, db: Session = Depends(get_db)):
    """Get channel by ID"""
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    return channel


@router.get("/number/{channel_number}", response_model=ChannelResponse)
def get_channel_by_number(channel_number: str, db: Session = Depends(get_db)):
    """Get channel by number"""
    channel = db.query(Channel).filter(Channel.number == channel_number).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    return channel


@router.post("", response_model=ChannelResponse, status_code=status.HTTP_201_CREATED)
def create_channel(channel: ChannelCreate, db: Session = Depends(get_db)):
    """Create a new channel"""
    # Check if channel number already exists
    existing = db.query(Channel).filter(Channel.number == channel.number).first()
    if existing:
        raise HTTPException(status_code=400, detail="Channel number already exists")
    
    # Validate FFmpeg profile if provided
    if channel.ffmpeg_profile_id:
        from ..database.models import FFmpegProfile
        profile = db.query(FFmpegProfile).filter(FFmpegProfile.id == channel.ffmpeg_profile_id).first()
        if not profile:
            raise HTTPException(status_code=400, detail="FFmpeg profile not found")
    
    # Validate watermark if provided
    if channel.watermark_id:
        from ..database.models import Watermark
        watermark = db.query(Watermark).filter(Watermark.id == channel.watermark_id).first()
        if not watermark:
            raise HTTPException(status_code=400, detail="Watermark not found")
    
    # Validate mirror source channel if provided
    if channel.mirror_source_channel_id:
        mirror_channel = db.query(Channel).filter(Channel.id == channel.mirror_source_channel_id).first()
        if not mirror_channel:
            raise HTTPException(status_code=400, detail="Mirror source channel not found")
        if channel.mirror_source_channel_id == channel.id if hasattr(channel, 'id') else False:
            raise HTTPException(status_code=400, detail="Channel cannot mirror itself")
    
    db_channel = Channel(**channel.dict())
    db.add(db_channel)
    db.commit()
    db.refresh(db_channel)
    return db_channel


@router.put("/{channel_id}", response_model=ChannelResponse)
def update_channel(channel_id: int, channel_update: ChannelUpdate, db: Session = Depends(get_db)):
    """Update a channel"""
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    # Reject writes for YAML-authoritative channels until export exists
    if getattr(channel, 'is_yaml_source', False):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Channel is defined in YAML. Edit the YAML file and re-import."
        )
    
    update_data = channel_update.dict(exclude_unset=True)
    
    # Validate FFmpeg profile if being updated
    if "ffmpeg_profile_id" in update_data and update_data["ffmpeg_profile_id"] is not None:
        from ..database.models import FFmpegProfile
        profile = db.query(FFmpegProfile).filter(FFmpegProfile.id == update_data["ffmpeg_profile_id"]).first()
        if not profile:
            raise HTTPException(status_code=400, detail="FFmpeg profile not found")
    
    # Validate watermark if being updated
    if "watermark_id" in update_data and update_data["watermark_id"] is not None:
        from ..database.models import Watermark
        watermark = db.query(Watermark).filter(Watermark.id == update_data["watermark_id"]).first()
        if not watermark:
            raise HTTPException(status_code=400, detail="Watermark not found")
    
    # Validate mirror source channel if being updated
    if "mirror_source_channel_id" in update_data and update_data["mirror_source_channel_id"] is not None:
        mirror_channel = db.query(Channel).filter(Channel.id == update_data["mirror_source_channel_id"]).first()
        if not mirror_channel:
            raise HTTPException(status_code=400, detail="Mirror source channel not found")
        if update_data["mirror_source_channel_id"] == channel_id:
            raise HTTPException(status_code=400, detail="Channel cannot mirror itself")
    
    for field, value in update_data.items():
        setattr(channel, field, value)
    
    db.commit()
    db.refresh(channel)
    return channel


@router.delete("/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_channel(channel_id: int, db: Session = Depends(get_db)):
    """Delete a channel"""
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    # Reject deletes for YAML-authoritative channels until export exists
    if getattr(channel, 'is_yaml_source', False):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Channel is defined in YAML. Edit the YAML file and re-import."
        )
    
    db.delete(channel)
    db.commit()
    return None


class PlaybackPositionUpdate(BaseModel):
    """Playback position update model"""
    item_index: int
    media_id: Optional[int] = None


@router.post("/{channel_id}/playback-position")
def save_playback_position(
    channel_id: int,
    position: PlaybackPositionUpdate,
    db: Session = Depends(get_db)
):
    """Save playback position for an on-demand channel"""
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    if channel.playout_mode != PlayoutMode.ON_DEMAND:
        raise HTTPException(
            status_code=400, 
            detail="Position tracking only available for on-demand channels"
        )
    
    # Get or create playback position record
    playback_pos = db.query(ChannelPlaybackPosition).filter(
        ChannelPlaybackPosition.channel_id == channel_id
    ).first()
    
    if not playback_pos:
        playback_pos = ChannelPlaybackPosition(
            channel_id=channel_id,
            channel_number=channel.number
        )
        db.add(playback_pos)
    
    playback_pos.last_item_index = position.item_index
    playback_pos.last_item_media_id = position.media_id
    playback_pos.last_played_at = datetime.utcnow()
    playback_pos.total_items_watched = position.item_index  # Track total items watched
    
    db.commit()
    db.refresh(playback_pos)
    
    return {
        "success": True,
        "channel_id": channel_id,
        "item_index": playback_pos.last_item_index,
        "media_id": playback_pos.last_item_media_id,
        "last_played_at": playback_pos.last_played_at.isoformat() if playback_pos.last_played_at else None
    }


@router.get("/{channel_id}/playback-position")
def get_playback_position(
    channel_id: int,
    db: Session = Depends(get_db)
):
    """Get saved playback position for an on-demand channel"""
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    playback_pos = db.query(ChannelPlaybackPosition).filter(
        ChannelPlaybackPosition.channel_id == channel_id
    ).first()
    
    if not playback_pos:
        return {
            "item_index": 0,
            "media_id": None,
            "last_played_at": None,
            "resume_available": False
        }
    
    return {
        "item_index": playback_pos.last_item_index,
        "media_id": playback_pos.last_item_media_id,
        "last_played_at": playback_pos.last_played_at.isoformat() if playback_pos.last_played_at else None,
        "total_items_watched": playback_pos.total_items_watched,
        "resume_available": True
    }


@router.delete("/{channel_id}/playback-position", status_code=status.HTTP_204_NO_CONTENT)
def reset_playback_position(
    channel_id: int,
    db: Session = Depends(get_db)
):
    """Reset playback position for an on-demand channel (start from beginning)"""
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    playback_pos = db.query(ChannelPlaybackPosition).filter(
        ChannelPlaybackPosition.channel_id == channel_id
    ).first()
    
    if playback_pos:
        db.delete(playback_pos)
        db.commit()
    
    return None


@router.post("/{channel_id}/icon", response_model=ChannelResponse)
async def upload_channel_icon(
    channel_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a PNG icon for a channel"""
    # Validate channel exists
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    # Allow icon uploads regardless of YAML source (non-breaking)
    
    # Validate file is PNG
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    file_ext = Path(file.filename).suffix.lower()
    if file_ext != '.png':
        raise HTTPException(status_code=400, detail="Only PNG files are allowed")
    
    # Validate content type
    if file.content_type and file.content_type not in ['image/png', 'image/x-png']:
        raise HTTPException(status_code=400, detail="File must be a PNG image")
    
    # Determine icons directory (relative to project root)
    project_root = Path(__file__).parent.parent.parent
    icons_dir = project_root / "data" / "channel_icons"
    icons_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename using channel NUMBER (not database ID) for consistency with XMLTV/HDHomeRun
    # This ensures icons match channel numbers used in lineup.json and XMLTV channel IDs
    icon_filename = f"channel_{channel.number}.png"
    icon_path = icons_dir / icon_filename
    
    # If there's an old icon file using database ID, remove it
    old_icon_filename = f"channel_{channel_id}.png"
    old_icon_path = icons_dir / old_icon_filename
    if old_icon_path.exists() and old_icon_path != icon_path:
        try:
            old_icon_path.unlink()
            logger.info(f"Removed old icon file using database ID: {old_icon_filename}")
        except Exception as e:
            logger.warning(f"Could not remove old icon file {old_icon_filename}: {e}")
    
    try:
        # Save the uploaded file
        with open(icon_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Update channel logo_path to point to the static file (using channel number)
        logo_url = f"/static/channel_icons/{icon_filename}"
        channel.logo_path = logo_url
        db.commit()
        db.refresh(channel)
        
        logger.info(f"Uploaded icon for channel {channel.number} (ID: {channel_id}, {channel.name}): {icon_path}")
        
        return channel
    except Exception as e:
        logger.error(f"Error uploading icon for channel {channel_id}: {e}")
        # Clean up file if it was partially written
        if icon_path.exists():
            icon_path.unlink()
        raise HTTPException(status_code=500, detail=f"Failed to upload icon: {str(e)}")


@router.delete("/{channel_id}/icon", response_model=ChannelResponse)
def delete_channel_icon(
    channel_id: int,
    db: Session = Depends(get_db)
):
    """Delete the icon for a channel"""
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    if not channel.logo_path or not channel.logo_path.startswith("/static/channel_icons/"):
        raise HTTPException(status_code=404, detail="Channel has no uploaded icon")
    
    # Determine icons directory
    project_root = Path(__file__).parent.parent.parent
    icons_dir = project_root / "data" / "channel_icons"
    
    # Try channel number first (preferred), then fallback to database ID for backward compatibility
    icon_filename = f"channel_{channel.number}.png"
    icon_path = icons_dir / icon_filename
    if not icon_path.exists():
        # Fallback to database ID for old icons
        icon_filename = f"channel_{channel_id}.png"
        icon_path = icons_dir / icon_filename
    
    # Delete the file if it exists
    if icon_path.exists():
        try:
            icon_path.unlink()
            logger.info(f"Deleted icon for channel {channel_id} ({channel.name}): {icon_path}")
        except Exception as e:
            logger.error(f"Error deleting icon file for channel {channel_id}: {e}")
    
    # Clear logo_path in database
    channel.logo_path = None
    db.commit()
    db.refresh(channel)
    
    return channel
