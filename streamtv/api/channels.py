"""Channel API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel
import shutil
import logging

from ..database import get_db, Channel, Playlist, PlaylistItem
from ..database.models import PlayoutMode, ChannelPlaybackPosition
from ..api.schemas import ChannelCreate, ChannelUpdate, ChannelResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/channels", tags=["Channels"])


def _get_channel_manager(request: Request):
    mgr = getattr(request.app.state, "channel_manager", None)
    if mgr is None:
        raise HTTPException(
            status_code=503,
            detail="ChannelManager not available (server still starting?)",
        )
    return mgr


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
    channel = (
        db.query(Channel)
        .options(joinedload(Channel.playlists).joinedload(Playlist.items).joinedload(PlaylistItem.media_item))
        .filter(Channel.number == channel_number)
        .first()
    )
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


class BulkChannelEnabledRequest(BaseModel):
    channel_ids: List[int]
    enabled: bool


@router.post("/bulk-enabled", response_model=List[ChannelResponse])
def bulk_set_channel_enabled(
    body: BulkChannelEnabledRequest,
    db: Session = Depends(get_db),
):
    """Enable or disable multiple channels in one request."""
    if not body.channel_ids:
        raise HTTPException(status_code=400, detail="channel_ids must not be empty")

    channels = db.query(Channel).filter(Channel.id.in_(body.channel_ids)).all()
    if len(channels) != len(set(body.channel_ids)):
        raise HTTPException(status_code=404, detail="One or more channels not found")

    for channel in channels:
        if getattr(channel, "is_yaml_source", False):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Channel {channel.number} is YAML-authoritative; edit YAML instead.",
            )
        channel.enabled = body.enabled

    db.commit()
    for channel in channels:
        db.refresh(channel)
    return channels


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
    """Delete playback position row (legacy). Prefer POST .../playout-reset for CONTINUOUS."""
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


class PlayoutResetRequest(BaseModel):
    """Optional ISO8601 UTC start; default is now."""
    at: Optional[str] = None
    item_index: Optional[int] = None
    item_title: Optional[str] = None
    restart_stream: bool = True


def _apply_playout_reset(
    channel: Channel,
    db: Session,
    *,
    at: Optional[str] = None,
    item_index: Optional[int] = None,
    item_title: Optional[str] = None,
) -> tuple[datetime, int]:
    from streamtv.scheduling.playout_timeline import (
        find_item_index_by_title,
        load_channel_stream_schedule,
        playout_anchor_for_item_index,
    )

    anchor = datetime.utcnow()
    if at:
        try:
            anchor = datetime.fromisoformat(at.replace("Z", ""))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid at timestamp: {e}") from e

    resolved_index = 0
    start = anchor
    if item_title or (item_index is not None and item_index > 0):
        try:
            schedule_items = load_channel_stream_schedule(channel, db)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        if item_title:
            try:
                found = find_item_index_by_title(schedule_items, item_title)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e)) from e
            if found is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"No playout item matches title {item_title!r}",
                )
            resolved_index = found
        elif item_index is not None:
            resolved_index = int(item_index)
            if resolved_index >= len(schedule_items):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"item_index {resolved_index} out of range "
                        f"(playlist has {len(schedule_items)} items)"
                    ),
                )
        start, resolved_index = playout_anchor_for_item_index(
            schedule_items,
            resolved_index,
            anchor=anchor,
        )

    playback_pos = db.query(ChannelPlaybackPosition).filter(
        ChannelPlaybackPosition.channel_id == channel.id
    ).first()
    if not playback_pos:
        playback_pos = ChannelPlaybackPosition(
            channel_id=channel.id,
            channel_number=str(channel.number),
        )
        db.add(playback_pos)

    playback_pos.playout_start_time = start
    playback_pos.last_item_index = resolved_index
    playback_pos.last_item_media_id = None
    playback_pos.last_position_update = datetime.utcnow()
    playback_pos.last_played_at = None
    db.commit()
    return start, resolved_index


@router.post("/{channel_id}/playout-reset")
async def reset_continuous_playout(
    channel_id: int,
    request: Request,
    body: Optional[PlayoutResetRequest] = None,
    db: Session = Depends(get_db),
):
    """Reset CONTINUOUS playout_start_time so EPG and MPEG-TS share a fresh cycle anchor.

    By default also restarts only this channel's continuous stream (no global restart).
    Pass restart_stream=false to update the DB anchor only.
    """
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    body = body or PlayoutResetRequest()
    mgr = None
    if body.restart_stream:
        mgr = _get_channel_manager(request)
        # Stop first (without saving old in-memory anchor), then write DB, then start.
        # Avoids stop()/periodic-save racing over a fresh playout_start_time.
        try:
            await mgr.stop_channel(str(channel.number))
        except Exception as e:
            logger.warning(
                "Channel %s stop before playout-reset failed (continuing): %s",
                channel.number,
                e,
            )

    start, last_idx = _apply_playout_reset(
        channel,
        db,
        at=body.at,
        item_index=body.item_index,
        item_title=body.item_title,
    )

    restarted = None
    if body.restart_stream and mgr is not None:
        try:
            restarted = await mgr.restart_channel(str(channel.number))
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Channel %s stream restart failed: %s", channel.number, e, exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Playout reset saved but stream restart failed: {e}",
            ) from e

    logger.info(
        "Channel %s playout reset: playout_start_time=%s restarted=%s",
        channel.number,
        start.isoformat(),
        bool(restarted),
    )
    return {
        "status": "ok",
        "channel_number": channel.number,
        "playout_start_time": start.isoformat(),
        "last_item_index": last_idx,
        "stream_restarted": bool(restarted),
        "stream": restarted,
    }


@router.post("/by-number/{channel_number}/playout-reset")
async def reset_continuous_playout_by_number(
    channel_number: str,
    request: Request,
    body: Optional[PlayoutResetRequest] = None,
    db: Session = Depends(get_db),
):
    """Same as playout-reset, keyed by channel number (operator-friendly)."""
    channel = db.query(Channel).filter(Channel.number == str(channel_number)).first()
    if not channel:
        raise HTTPException(status_code=404, detail=f"Channel {channel_number} not found")
    return await reset_continuous_playout(channel.id, request, body, db)


@router.post("/{channel_id}/stream-restart")
async def restart_channel_stream(
    channel_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Restart only this channel's continuous MPEG-TS stream (reload schedule + playout anchor)."""
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    if not channel.enabled:
        raise HTTPException(status_code=400, detail="Channel is disabled")

    mgr = _get_channel_manager(request)
    try:
        result = await mgr.restart_channel(str(channel.number))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error("Channel %s stream restart failed: %s", channel.number, e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e

    return {"status": "ok", **result}


@router.post("/by-number/{channel_number}/stream-restart")
async def restart_channel_stream_by_number(
    channel_number: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Restart continuous stream keyed by channel number."""
    channel = db.query(Channel).filter(Channel.number == str(channel_number)).first()
    if not channel:
        raise HTTPException(status_code=404, detail=f"Channel {channel_number} not found")
    return await restart_channel_stream(channel.id, request, db)


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
    
    # Generate filename: channel_{channel_id}.png
    icon_filename = f"channel_{channel_id}.png"
    icon_path = icons_dir / icon_filename
    
    try:
        # Save the uploaded file
        with open(icon_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Update channel logo_path to point to the static file
        logo_url = f"/static/channel_icons/{icon_filename}"
        channel.logo_path = logo_url
        db.commit()
        db.refresh(channel)
        
        logger.info(f"Uploaded icon for channel {channel_id} ({channel.name}): {icon_path}")
        
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
