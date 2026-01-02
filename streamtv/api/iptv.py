"""IPTV streaming endpoints (m3u, xmltv.xml, HLS)"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta, time as dt_time
import urllib.parse
import httpx
import logging
from xml.sax.saxutils import escape as xml_escape

from ..database import get_db, Channel, Playlist, PlaylistItem, MediaItem, Schedule
from ..streaming import StreamManager, StreamSource
from ..streaming.plex_api_client import PlexAPIClient
from ..config import config
from ..scheduling import ScheduleParser, ScheduleEngine

logger = logging.getLogger(__name__)

router = APIRouter(tags=["IPTV"])

stream_manager = StreamManager()


def _xml(value) -> str:
    """Safely escape XML text/attribute values."""
    if value is None:
        return ""
    return xml_escape(str(value), {'"': '&quot;', "'": '&apos;'})


def _resolve_logo_url(channel, base_url: str) -> Optional[str]:
    """
    Build an absolute logo URL for M3U/XMLTV.
    - Uses channel.logo_path if provided and it matches the channel number.
    - Falls back to /static/channel_icons/channel_<number>.png.
    
    Note: Some channels have incorrect logo_path values using database IDs instead of channel numbers.
    We validate and use the correct path based on channel number.
    """
    logo_path = channel.logo_path
    if logo_path:
        # If it's an external URL, use it directly
        if logo_path.startswith('http'):
            return logo_path
        
        # Check if logo_path contains a channel number that matches this channel
        # Extract any number from the logo_path filename
        import re
        logo_filename = logo_path.split('/')[-1]  # Get just the filename
        logo_match = re.search(r'channel_(\d+)\.png', logo_filename)
        
        if logo_match:
            logo_number = logo_match.group(1)
            channel_number_str = str(channel.number)
            # If the logo path number matches the channel number, use it
            if logo_number == channel_number_str:
                if logo_path.startswith('/'):
                    return f"{base_url}{logo_path}"
                return f"{base_url}/{logo_path}"
            else:
                # Logo path has wrong number (likely database ID), use fallback
                logger.debug(f"Channel {channel.number}: logo_path '{logo_path}' has number {logo_number} (doesn't match channel number), using fallback")
        else:
            # No number found in logo_path, might be a custom path - use it if it's a static path
            if '/static/channel_icons/' in logo_path or '/channel_icons/' in logo_path:
                if logo_path.startswith('/'):
                    return f"{base_url}{logo_path}"
                return f"{base_url}/{logo_path}"
            # Custom path not in channel_icons - use it as-is
            if logo_path.startswith('/'):
                return f"{base_url}{logo_path}"
            return f"{base_url}/{logo_path}"
    
    # Default fallback based on channel number icon
    return f"{base_url}/static/channel_icons/channel_{channel.number}.png"


@router.get("/iptv/channels.m3u")
async def get_channel_playlist(
    mode: str = "mixed",
    access_token: Optional[str] = None,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Get IPTV channel playlist (M3U format)"""
    try:
        # Validate access token if required
        # If access_token is None in config, allow requests without token (for Plex compatibility)
        if config.security.api_key_required:
            if config.security.access_token is None:
                # Token required but not configured - allow access (backward compatibility)
                logger.debug("API key required but access_token not set - allowing access for M3U")
            elif access_token != config.security.access_token:
                raise HTTPException(status_code=401, detail="Invalid access token")
        
        channels = db.query(Channel).filter(Channel.enabled == True).all()
        
        # Fix: Ensure playout_mode is properly converted from string to enum if needed
        from ..database.models import PlayoutMode
        for channel in channels:
            if isinstance(channel.playout_mode, str):
                # Convert string to enum instance
                try:
                    # Normalize the string (lowercase, handle dashes)
                    normalized = channel.playout_mode.lower().replace('-', '_')
                    # Try to match by value first (enum values are lowercase: "continuous", "on_demand")
                    matched = False
                    for mode in PlayoutMode:
                        if mode.value.lower() == normalized:
                            channel.playout_mode = mode
                            matched = True
                            break
                    if not matched:
                        # Try to match by name (enum names are uppercase: CONTINUOUS, ON_DEMAND)
                        name_upper = channel.playout_mode.upper().replace('-', '_')
                        if name_upper in ["CONTINUOUS", "ON_DEMAND"]:
                            channel.playout_mode = PlayoutMode[name_upper]
                        else:
                            # Try direct lookup
                            channel.playout_mode = PlayoutMode[channel.playout_mode.upper()]
                except (KeyError, AttributeError) as e:
                    # If conversion fails, default to CONTINUOUS
                    logger.warning(f"Invalid playout_mode '{channel.playout_mode}' for channel {channel.number}, defaulting to CONTINUOUS: {e}")
                    channel.playout_mode = PlayoutMode.CONTINUOUS
        
        # Always derive base_url from the incoming request so tvg-logo/icon URLs match
        # the address Plex/clients use (avoids 127.0.0.1 vs LAN IP issues).
        base_url = config.server.base_url
        if request:
            scheme = request.url.scheme
            host = request.url.hostname
            port = request.url.port
            if port and port not in [80, 443]:
                base_url = f"{scheme}://{host}:{port}"
            else:
                base_url = f"{scheme}://{host}"
        
        m3u_content = "#EXTM3U\n"
        
        for channel in channels:
            try:
                token_param = f"?access_token={access_token}" if access_token else ""
                
                if mode == "hls" or mode == "mixed":
                    stream_url = f"{base_url}/iptv/channel/{channel.number}.m3u8{token_param}"
                else:
                    stream_url = f"{base_url}/iptv/channel/{channel.number}.ts{token_param}"
                
                logo_url = _resolve_logo_url(channel, base_url)
                m3u_content += f'#EXTINF:-1 tvg-id="{channel.number}" tvg-name="{channel.name}"'
                if channel.group:
                    m3u_content += f' group-title="{channel.group}"'
                if logo_url:
                    m3u_content += f' tvg-logo="{logo_url}"'
                m3u_content += f',{channel.name}\n'
                m3u_content += f"{stream_url}\n"
            except Exception as e:
                logger.error(f"Error processing channel {channel.number if channel else 'unknown'} for M3U: {e}", exc_info=True)
                # Continue with next channel instead of failing entire request
        
        return Response(content=m3u_content, media_type="application/vnd.apple.mpegurl")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating M3U playlist: {e}", exc_info=True)
        error_m3u = "#EXTM3U\n"
        error_m3u += f"#EXTINF:-1,Error: {str(e)}\n"
        error_m3u += "#\n"
        return Response(
            content=error_m3u,
            media_type="application/vnd.apple.mpegurl",
            status_code=500
        )


@router.get("/iptv/xmltv.xml")
async def get_epg(
    access_token: Optional[str] = None,
    request: Request = None,
    plain: bool = True,
    db: Session = Depends(get_db)
):
    """Get Electronic Program Guide (XMLTV format)"""
    import time
    perf_start_time = time.time()  # Performance timing (float)
    
    try:
        # Validate access token if required
        # If access_token is None in config, allow requests without token (for Plex compatibility)
        if config.security.api_key_required:
            if config.security.access_token is None:
                # Token required but not configured - allow access (backward compatibility)
                logger.debug("API key required but access_token not set - allowing access for XMLTV")
            elif access_token != config.security.access_token:
                raise HTTPException(status_code=401, detail="Invalid access token")
        
        # Query channels - handle enum validation errors with fallback to raw SQL
        try:
            channels = db.query(Channel).filter(Channel.enabled == True).all()
        except (LookupError, ValueError) as query_error:
            # Handle SQLAlchemy enum validation errors by querying raw values and converting
            error_str = str(query_error)
            if "is not among the defined enum values" in error_str or "streamingmode" in error_str.lower() or "playoutmode" in error_str.lower():
                logger.warning(f"SQLAlchemy enum validation error when querying channels for XMLTV: {query_error}")
                logger.info("Attempting to query channels using raw SQL to work around enum validation issue...")
                # Query using raw SQL to avoid enum validation, then construct Channel objects
                from sqlalchemy import text
                raw_result = db.execute(text("""
                    SELECT id, number, name, playout_mode, enabled, "group", logo_path,
                           streaming_mode, is_yaml_source, transcode_profile, created_at, updated_at
                    FROM channels WHERE enabled = 1
                """)).fetchall()
                channels = []
                from ..database.models import PlayoutMode, StreamingMode
                for row in raw_result:
                    channel = Channel()
                    channel.id = row[0]
                    channel.number = row[1]
                    channel.name = row[2]
                    # Convert playout_mode string to enum
                    playout_mode_str = row[3] if row[3] else "continuous"
                    normalized = playout_mode_str.lower()
                    playout_mode_enum = PlayoutMode.CONTINUOUS
                    for mode in PlayoutMode:
                        if mode.value.lower() == normalized:
                            playout_mode_enum = mode
                            break
                    else:
                        try:
                            playout_mode_enum = PlayoutMode[playout_mode_str.upper()]
                        except KeyError:
                            playout_mode_enum = PlayoutMode.CONTINUOUS
                    channel.playout_mode = playout_mode_enum
                    # Convert streaming_mode string to enum
                    streaming_mode_str = row[7] if row[7] else "transport_stream_hybrid"
                    normalized = streaming_mode_str.lower()
                    streaming_mode_enum = StreamingMode.TRANSPORT_STREAM_HYBRID
                    for mode in StreamingMode:
                        if mode.value.lower() == normalized:
                            streaming_mode_enum = mode
                            break
                    else:
                        try:
                            streaming_mode_enum = StreamingMode[streaming_mode_str.upper()]
                        except KeyError:
                            streaming_mode_enum = StreamingMode.TRANSPORT_STREAM_HYBRID
                    channel.streaming_mode = streaming_mode_enum
                    channel.enabled = bool(row[4])
                    channel.group = row[5]
                    channel.logo_path = row[6]
                    channel.is_yaml_source = bool(row[8])
                    channel.transcode_profile = row[9]
                    channels.append(channel)
                logger.info(f"Loaded {len(channels)} channels using raw SQL query for XMLTV")
            else:
                # Re-raise if it's a different error
                raise
        
        # Fix: Ensure playout_mode is properly converted from string to enum if needed
        from ..database.models import PlayoutMode
        for channel in channels:
            if isinstance(channel.playout_mode, str):
                # Convert string to enum instance
                try:
                    # Normalize the string (lowercase, handle dashes)
                    normalized = channel.playout_mode.lower().replace('-', '_')
                    # Try to match by value first (enum values are lowercase: "continuous", "on_demand")
                    matched = False
                    for mode in PlayoutMode:
                        if mode.value.lower() == normalized:
                            channel.playout_mode = mode
                            matched = True
                            break
                    if not matched:
                        # Try to match by name (enum names are uppercase: CONTINUOUS, ON_DEMAND)
                        name_upper = channel.playout_mode.upper().replace('-', '_')
                        if name_upper in ["CONTINUOUS", "ON_DEMAND"]:
                            channel.playout_mode = PlayoutMode[name_upper]
                    else:
                            # Try direct lookup
                        channel.playout_mode = PlayoutMode[channel.playout_mode.upper()]
                except (KeyError, AttributeError) as e:
                    # If conversion fails, default to CONTINUOUS
                    logger.warning(f"Invalid playout_mode '{channel.playout_mode}' for channel {channel.number}, defaulting to CONTINUOUS: {e}")
                    channel.playout_mode = PlayoutMode.CONTINUOUS
        
        logger.info(f"Generating XMLTV EPG for {len(channels)} channels")
        
        base_url = config.server.base_url
        if request:
            scheme = request.url.scheme
            host = request.url.hostname
            port = request.url.port
            if port and port not in [80, 443]:
                base_url = f"{scheme}://{host}:{port}"
            else:
                base_url = f"{scheme}://{host}"
        
        # Generate EPG based on configured build days
        now = datetime.utcnow()
        build_days = config.playout.build_days
        end_time = now + timedelta(days=build_days)
        
        # Build XML header; optionally include XSL stylesheet for browsers
        xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
        if not plain:
            xml_content += '<?xml-stylesheet type="text/xsl" href="https://raw.githubusercontent.com/XMLTV/xmltv/master/xmltv.xsl"?>\n'
        xml_content += '<tv generator-info-name="StreamTV" generator-info-url="https://github.com/streamtv" source-info-name="StreamTV">\n'
        
        # Initialize Plex API client if configured for schedule/EPG integration
        plex_client = None
        plex_channel_map = {}
        if config.plex.enabled and config.plex.base_url and config.plex.use_for_epg and config.plex.token:
            try:
                plex_client = PlexAPIClient(
                    base_url=config.plex.base_url,
                    token=config.plex.token
                )
                logger.info(f"Plex API client initialized for EPG/schedule integration (server: {config.plex.base_url})")
                
                # Try to get channel mappings from Plex if DVR is configured
                try:
                    dvrs = await plex_client.get_dvrs()
                    if dvrs:
                        logger.info(f"Found {len(dvrs)} Plex DVR(s) for channel mapping")
                        # Store channel mappings for later use
                        for dvr in dvrs:
                            if dvr.get('enabled'):
                                # Get channels for this DVR's lineup if available
                                pass  # Channel mapping will be enhanced in future
                except Exception as e:
                    logger.debug(f"Plex DVR channel mapping: {e}")
                    
            except Exception as e:
                logger.warning(f"Plex API client initialization failed: {e}. EPG will use standard format.")
                plex_client = None
        
        # Channel definitions - ensure Plex-compatible format
        # #region agent log
        import json
        try:
            with open('/Users/roto1231/Documents/XCode Projects/StreamTV/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"api/iptv.py:311","message":"XMLTV: Starting channel definitions","data":{"channel_count":len(channels),"base_url":base_url},"timestamp":int(__import__('time').time()*1000)})+'\n')
        except: pass
        # #endregion
        
        for channel in channels:
            # Use channel number as ID (Plex expects numeric or alphanumeric IDs)
            channel_id = str(channel.number).strip()
            
            # #region agent log
            try:
                with open('/Users/roto1231/Documents/XCode Projects/StreamTV/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"api/iptv.py:316","message":"XMLTV: Channel ID generated","data":{"channel_number":channel.number,"channel_id":channel_id,"channel_id_type":type(channel_id).__name__,"channel_id_repr":repr(channel_id),"channel_name":channel.name},"timestamp":int(__import__('time').time()*1000)})+'\n')
            except: pass
            # #endregion
            
            xml_content += f'  <channel id="{_xml(channel_id)}">\n'
            
            # Primary display name (required)
            xml_content += f'    <display-name>{_xml(channel.name)}</display-name>\n'
            
            # Additional display names for grouping
            if channel.group:
                xml_content += f'    <display-name>{_xml(channel.group)}</display-name>\n'
            
            # Channel number as display name (Plex compatibility)
            xml_content += f'    <display-name>{_xml(channel_id)}</display-name>\n'
            
            # Logo/icon (Plex expects absolute URLs). Fall back to default icon by number.
            logo_url = _resolve_logo_url(channel, base_url)
            
            # #region agent log
            try:
                with open('/Users/roto1231/Documents/XCode Projects/StreamTV/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"api/iptv.py:332","message":"XMLTV: Icon URL resolved","data":{"channel_number":channel.number,"logo_url":logo_url,"logo_path":getattr(channel,'logo_path',None)},"timestamp":int(__import__('time').time()*1000)})+'\n')
            except: pass
            # #endregion
            
            if logo_url:
                xml_content += f'    <icon src="{_xml(logo_url)}"/>\n'
            
            xml_content += '  </channel>\n'
        
        # Program listings - optimized with early exit
        for channel in channels:
            # Try to load schedule file first
            schedule_file = ScheduleParser.find_schedule_file(channel.number)
            schedule_items = []
            
            # Get playout_start_time from database to match actual stream timing
            # This ensures EPG metadata matches what's actually being streamed
            from streamtv.database.models import ChannelPlaybackPosition
            playback_pos = db.query(ChannelPlaybackPosition).filter(
                ChannelPlaybackPosition.channel_id == channel.id
            ).first()
            
            # Use playout_start_time if available (for CONTINUOUS channels), otherwise use now
            # This matches the logic in channel_manager._get_current_position()
            playout_start_time = None
            if playback_pos and playback_pos.playout_start_time:
                playout_start_time = playback_pos.playout_start_time
                logger.debug(f"Channel {channel.number}: Using playout_start_time {playout_start_time} for EPG")
            else:
                # No saved playout_start_time - use now (first time or ON_DEMAND channel)
                playout_start_time = now
                logger.debug(f"Channel {channel.number}: No saved playout_start_time, using now ({now}) for EPG")
            
            if schedule_file:
                try:
                    parsed_schedule = ScheduleParser.parse_file(schedule_file, schedule_file.parent)
                    schedule_engine = ScheduleEngine(db)
                    # Generate items to fill 24 hours (max 500 items per channel for performance)
                    schedule_items = schedule_engine.generate_playlist_from_schedule(
                        channel, parsed_schedule, max_items=500
                    )
                    logger.info(f"Generated {len(schedule_items)} schedule items for channel {channel.number}")
                    
                    # Calculate total cycle duration (sum of all item durations)
                    total_duration = sum(
                        (item.get('media_item', {}).duration or 1800)
                        for item in schedule_items
                        if item.get('media_item')
                    )
                    
                    # Calculate which item should be playing "now" using same logic as stream
                    # This ensures EPG matches what's actually streaming
                    if total_duration > 0 and playout_start_time:
                        elapsed = (now - playout_start_time).total_seconds()
                        cycle_position = elapsed % total_duration if total_duration > 0 else 0
                        
                        # Find which item index corresponds to cycle_position
                        current_time = 0
                        current_item_index = 0
                        for idx, item in enumerate(schedule_items):
                            media_item = item.get('media_item')
                            if not media_item:
                                continue
                            duration = media_item.duration or 1800
                            if current_time + duration > cycle_position:
                                current_item_index = idx
                                break
                            current_time += duration
                            current_item_index = idx + 1
                        
                        if current_item_index >= len(schedule_items):
                            current_item_index = 0
                        
                        logger.debug(f"Channel {channel.number}: EPG calculated current item index {current_item_index} based on playout_start_time")
                    
                    # Assign start times if not set (for repeat=True schedules)
                    # Start from the item that should be playing "now" based on playout_start_time
                    items_without_time = sum(1 for item in schedule_items if not item.get('start_time'))
                    if items_without_time > 0:
                        logger.info(f"Assigning start times to {items_without_time} items without start_time for channel {channel.number}")
                        
                        # Calculate when the current item started playing
                        if total_duration > 0 and playout_start_time:
                            # Calculate how many full cycles have elapsed
                            elapsed = (now - playout_start_time).total_seconds()
                            cycles_completed = int(elapsed // total_duration) if total_duration > 0 else 0
                            cycle_position = elapsed % total_duration if total_duration > 0 else 0
                            
                            # Find start time of current item within the cycle
                            current_time_in_cycle = 0
                            current_item_start_in_cycle = 0
                            for idx, item in enumerate(schedule_items):
                                media_item = item.get('media_item')
                                if not media_item:
                                    continue
                                duration = media_item.duration or 1800
                                if current_time_in_cycle + duration > cycle_position:
                                    current_item_start_in_cycle = current_time_in_cycle
                                    break
                                current_time_in_cycle += duration
                            
                            # Calculate absolute start time of current item
                            current_item_start_time = playout_start_time + timedelta(
                                seconds=(cycles_completed * total_duration) + current_item_start_in_cycle
                            )
                        else:
                            # Fallback: start from now
                            current_item_start_time = now
                        
                        # Assign start times starting from current item
                        current_item_time = current_item_start_time
                        # Start from current_item_index to maintain continuity
                        for i in range(len(schedule_items)):
                            idx = (current_item_index + i) % len(schedule_items)
                            item = schedule_items[idx]
                            if not item.get('start_time'):
                                item['start_time'] = current_item_time
                                media_item = item.get('media_item')
                                if media_item:
                                    duration = media_item.duration or 1800
                                else:
                                    duration = 1800
                                    logger.warning(f"Schedule item missing media_item for channel {channel.number}")
                                current_item_time = current_item_time + timedelta(seconds=duration)
                    
                    # Filter to only items within time range (now to end_time)
                    # Ensure all items have start_time set
                    filtered_items = []
                    for item in schedule_items:
                        if not item.get('start_time'):
                            # Skip items without start_time - they should have been assigned above
                            continue
                        start = item['start_time']
                        # Include items that start between now and end_time
                        # Also include items that are currently playing (start < now but end > now)
                        media_item = item.get('media_item')
                        if media_item:
                            duration = media_item.duration or 1800
                            end = start + timedelta(seconds=duration)
                            # Include if it starts in the future OR is currently playing
                            if (start >= now and start <= end_time) or (start < now and end > now):
                                filtered_items.append(item)
                        elif start >= now and start <= end_time:
                            filtered_items.append(item)
                    schedule_items = filtered_items
                    logger.info(f"After filtering: {len(schedule_items)} items within time range ({now} to {end_time}) for channel {channel.number}")
                except Exception as e:
                    logger.warning(f"Failed to load schedule file for EPG: {e}")
            
            # Fallback to database schedules if schedule file not available
            if not schedule_items:
                schedules = db.query(Schedule).filter(
                    Schedule.channel_id == channel.id,
                    Schedule.start_time <= end_time
                ).all()
                logger.debug(f"Channel {channel.number} ({channel.name}): Found {len(schedules)} database schedules")
                
                # Get playlists for this channel with eager loading
                playlists = db.query(Playlist).filter(Playlist.channel_id == channel.id).all()
                logger.debug(f"Channel {channel.number} ({channel.name}): Found {len(playlists)} playlists")
                
                # Generate programs from schedules
                for schedule in schedules:
                    if schedule.playlist_id:
                        playlist = db.query(Playlist).filter(Playlist.id == schedule.playlist_id).first()
                        if playlist:
                            # Eager load playlist items with media items
                            items = db.query(PlaylistItem).filter(
                                PlaylistItem.playlist_id == playlist.id
                            ).order_by(PlaylistItem.order).limit(200).all()  # Limit to 200 items
                            
                            # Batch load all media items
                            media_ids = [item.media_item_id for item in items]
                            if media_ids:
                                media_items_dict = {
                                    mi.id: mi for mi in db.query(MediaItem).filter(MediaItem.id.in_(media_ids)).all()
                                }
                            else:
                                media_items_dict = {}
                            
                            schedule_time = schedule.start_time
                            for item in items:
                                media_item = media_items_dict.get(item.media_item_id)
                                if media_item and schedule_time <= end_time:
                                    schedule_items.append({
                                        'media_item': media_item,
                                        'custom_title': None,
                                        'filler_kind': None,
                                        'start_time': schedule_time
                                    })
                                    schedule_time = schedule_time + timedelta(seconds=media_item.duration or 1800)
                                    
                                    if schedule_time > end_time or len(schedule_items) >= 500:
                                        break
                
                # Fill remaining time with placeholder programs if needed (limit to 200 items)
                if not schedule_items and playlists:
                    # Use first playlist to fill schedule
                    playlist = playlists[0]
                    logger.info(f"Channel {channel.number} ({channel.name}): Using playlist '{playlist.name}' (ID: {playlist.id}) for EPG generation")
                    items = db.query(PlaylistItem).filter(
                        PlaylistItem.playlist_id == playlist.id
                    ).order_by(PlaylistItem.order).limit(200).all()
                    logger.debug(f"Channel {channel.number} ({channel.name}): Found {len(items)} playlist items")
                    
                    if items:
                        # Batch load all media items
                        media_ids = [item.media_item_id for item in items]
                        if media_ids:
                            media_items_dict = {
                                mi.id: mi for mi in db.query(MediaItem).filter(MediaItem.id.in_(media_ids)).all()
                            }
                        else:
                            media_items_dict = {}
                        
                        # Use playout_start_time if available (for CONTINUOUS channels), otherwise use now
                        # This ensures EPG matches what's actually being streamed
                        if playback_pos and playback_pos.playout_start_time:
                            playout_start_time = playback_pos.playout_start_time
                            
                            # Calculate which item should be playing "now" using same logic as stream
                            total_duration = sum(
                                (media_items_dict.get(item.media_item_id, {}).duration or 1800)
                                for item in items
                                if media_items_dict.get(item.media_item_id)
                            )
                            
                            if total_duration > 0:
                                elapsed = (now - playout_start_time).total_seconds()
                                cycle_position = elapsed % total_duration
                                
                                # Find which item index corresponds to cycle_position
                                current_time = 0
                                current_item_index = 0
                                for idx, item in enumerate(items):
                                    media_item = media_items_dict.get(item.media_item_id)
                                    if not media_item:
                                        continue
                                    duration = media_item.duration or 1800
                                    if current_time + duration > cycle_position:
                                        current_item_index = idx
                                        break
                                    current_time += duration
                                    current_item_index = idx + 1
                                
                                if current_item_index >= len(items):
                                    current_item_index = 0
                                
                                # Calculate when the current item started playing
                                cycles_completed = int(elapsed // total_duration) if total_duration > 0 else 0
                                current_time_in_cycle = 0
                                current_item_start_in_cycle = 0
                                for idx, item in enumerate(items):
                                    media_item = media_items_dict.get(item.media_item_id)
                                    if not media_item:
                                        continue
                                    duration = media_item.duration or 1800
                                    if current_time_in_cycle + duration > cycle_position:
                                        current_item_start_in_cycle = current_time_in_cycle
                                        break
                                    current_time_in_cycle += duration
                                
                                # Calculate absolute start time of current item
                                schedule_time = playout_start_time + timedelta(
                                    seconds=(cycles_completed * total_duration) + current_item_start_in_cycle
                                )
                                item_index = current_item_index
                                logger.debug(f"Channel {channel.number}: EPG fallback using playout_start_time, starting from item {item_index} at {schedule_time}")
                            else:
                                schedule_time = now
                                item_index = 0
                        else:
                            schedule_time = now
                            item_index = 0
                        
                        while schedule_time < end_time and items and len(schedule_items) < 500:
                            item = items[item_index % len(items)]
                            media_item = media_items_dict.get(item.media_item_id)
                            if media_item:
                                schedule_items.append({
                                    'media_item': media_item,
                                    'custom_title': None,
                                    'filler_kind': None,
                                    'start_time': schedule_time
                                })
                                schedule_time = schedule_time + timedelta(seconds=media_item.duration or 1800)
                                item_index += 1
                            else:
                                logger.warning(f"Channel {channel.number} ({channel.name}): Playlist item {item.id} has no associated media_item")
                                break
                    
                    if not schedule_items and items:
                        logger.warning(f"Channel {channel.number} ({channel.name}): Playlist has {len(items)} items but no valid media_items found")
            
            # Generate EPG entries from schedule items
            # If no schedule items, add a placeholder programme so Plex can map the channel
            # Plex requires at least one programme entry per channel
            if not schedule_items:
                logger.warning(f"No schedule items found for channel {channel.number} ({channel.name}) - adding placeholder")
                # Add a placeholder programme for the full EPG build period to ensure Plex shows something
                # Use the full end_time instead of just 24 hours to cover the entire EPG period
                start_str = now.strftime("%Y%m%d%H%M%S +0000")
                end_str = end_time.strftime("%Y%m%d%H%M%S +0000")
                channel_id = str(channel.number).strip()
                xml_content += f'  <programme start="{_xml(start_str)}" stop="{_xml(end_str)}" channel="{_xml(channel_id)}">\n'
                # Use a more descriptive title that Plex will recognize
                xml_content += f'    <title lang="en">{_xml(channel.name)} - Live Stream</title>\n'
                xml_content += f'    <desc lang="en">Continuous live programming on {_xml(channel.name)}. This channel streams content 24/7.</desc>\n'
                xml_content += '    <category lang="en">General</category>\n'
                xml_content += '    <category lang="en">Live</category>\n'
                xml_content += '  </programme>\n'
            else:
                # Log first and last programme times for debugging
                if schedule_items:
                    first_start = schedule_items[0].get('start_time')
                    last_item = schedule_items[-1] if schedule_items else None
                    if first_start:
                        logger.debug(f"Channel {channel.number} EPG: First programme at {first_start}, {len(schedule_items)} total items")
            
            current_time = now
            programme_count = 0
            max_programmes_per_channel = 200  # Limit programmes per channel for performance
            
            for schedule_item in schedule_items:
                if programme_count >= max_programmes_per_channel:
                    break
                    
                media_item = schedule_item.get('media_item')
                if not media_item:
                    logger.debug(f"Skipping schedule item without media_item for channel {channel.number}")
                    continue
                
                # Use custom title if available, otherwise use media item title.
                # If missing, fall back to the URL basename to avoid Plex showing "Unknown Airing".
                title = schedule_item.get('custom_title') or media_item.title
                if not title or not title.strip():
                    try:
                        from pathlib import Path
                        parsed_url = urllib.parse.unquote(media_item.url or "")
                        fallback_base = Path(parsed_url).name.rsplit('.', 1)[0]
                        title = fallback_base or channel.name
                    except Exception:
                        title = channel.name
                title = title.strip()
                
                # Extract episode-specific information from metadata for better titles
                episode_title = None
                season_num = None
                episode_num = None
                if media_item.meta_data:
                    try:
                        import json
                        meta = json.loads(media_item.meta_data)
                        episode_title = meta.get('episode_title') or meta.get('title')
                        season_num = meta.get('season')
                        episode_num = meta.get('episode')
                    except Exception:
                        pass
                
                # Also try to extract season/episode from title if it matches patterns like "S03E05" or "S03E00"
                import re
                if season_num is None or episode_num is None:
                    title_match = re.search(r'[Ss](\d+)[Ee](\d+)', title)
                    if title_match:
                        if season_num is None:
                            season_num = int(title_match.group(1))
                        if episode_num is None:
                            episode_num = int(title_match.group(2))
                
                # For Sesame Street and similar shows, try to extract episode info from description
                # Descriptions like "Original air date: July 21, 1969" can help identify episodes
                air_date = None
                if not episode_title and media_item.description:
                    desc = media_item.description
                    # If description has air date but no episode title, use air date as identifier
                    # Match full date including year: "July 21, 1969" or "November 10, 1969"
                    air_date_match = re.search(r'Original air date:\s*([A-Za-z]+\s+\d+,\s+\d{4})', desc)
                    if air_date_match:
                        air_date = air_date_match.group(1).strip()
                        if air_date:
                            # Use air date as episode identifier for better EPG display
                            episode_title = f"Original air date: {air_date}"
                
                # Enhance title with episode information if available
                # For series like Sesame Street and Mister Rogers, show episode details
                # Keep the main show name as title, use sub-title for episode details
                # Clean up title to remove collection suffixes and season/episode patterns for better display
                show_name = title
                # Remove season/episode pattern from title (e.g., "Show Name S03E00" -> "Show Name")
                title_clean = re.sub(r'\s+[Ss]\d+[Ee]\d+$', '', title)
                if title_clean != title:
                    show_name = title_clean
                    title = show_name
                
                # Remove collection suffixes like "- 1960s-1970s" for better display
                if ' - ' in title:
                    # Try to extract just the show name (before collection suffix)
                    parts = title.split(' - ')
                    if len(parts) >= 2:
                        # Check if second part looks like a collection name (e.g., "1960s-1970s", "Season 3")
                        second_part = parts[1]
                        if any(x in second_part.lower() for x in ['season', '1960s', '1970s', '1980s', '1990s', '2000s', '2010s']):
                            show_name = parts[0].strip()
                            # Keep collection info for reference but use clean show name
                            title = show_name
                
                if season_num is not None and episode_num is not None:
                    # Format: "Show Name" with sub-title "S03E05 - Episode Title"
                    # Don't modify title here, will use sub-title field below
                    pass
                elif episode_num is not None:
                    # Format: "Show Name" with sub-title "Episode X"
                    # Don't modify title, will use sub-title
                    pass
                elif episode_title and air_date:
                    # For Sesame Street with air dates, keep title clean, use sub-title
                    # Don't modify title here
                    pass
                
                duration = media_item.duration or 1800
                
                # Calculate start/end times
                if schedule_item.get('start_time'):
                    start_time = schedule_item['start_time']
                else:
                    start_time = current_time
                
                end_time_prog = start_time + timedelta(seconds=duration)
                
                # Only include if within EPG time range
                # Include programmes that are currently playing (start < now but end > now) or start in the future
                is_currently_playing = start_time < now and end_time_prog > now
                is_future = start_time >= now and start_time <= end_time
                if is_currently_playing or is_future:
                    programme_count += 1
                    start_str = start_time.strftime("%Y%m%d%H%M%S +0000")
                    end_str = end_time_prog.strftime("%Y%m%d%H%M%S +0000")
                    
                    # Use channel number as ID (must match channel definition)
                    channel_id = str(channel.number).strip()
                    xml_content += f'  <programme start="{_xml(start_str)}" stop="{_xml(end_str)}" channel="{_xml(channel_id)}">\n'
                    
                    # Title is required by XMLTV spec and Plex
                    xml_content += f'    <title lang="en">{_xml(title.strip())}</title>\n'
                    
                    # Add sub-title if we have episode-specific information
                    # This helps Plex display episode details better
                    if season_num is not None and episode_num is not None:
                        sub_title = f"S{int(season_num):02d}E{int(episode_num):02d}"
                        if episode_title and episode_title != title and 'Original air date' not in episode_title:
                            sub_title = f"{sub_title} - {episode_title}"
                        xml_content += f'    <sub-title lang="en">{_xml(sub_title)}</sub-title>\n'
                    elif episode_num is not None:
                        sub_title = f"Episode {int(episode_num)}"
                        if episode_title and episode_title != title and 'Original air date' not in episode_title:
                            sub_title = f"{sub_title} - {episode_title}"
                        xml_content += f'    <sub-title lang="en">{_xml(sub_title)}</sub-title>\n'
                    elif episode_title and air_date:
                        # For Sesame Street with air dates, use air date as sub-title
                        xml_content += f'    <sub-title lang="en">{_xml(air_date)}</sub-title>\n'
                    elif episode_title and episode_title != title and 'Original air date' not in episode_title:
                        xml_content += f'    <sub-title lang="en">{_xml(episode_title)}</sub-title>\n'
                    
                    # Description - always include for Plex compatibility
                    # Plex requires desc tag even if empty
                    desc = media_item.description or ""
                    # Enhance description with episode info if available
                    if episode_title and episode_title not in desc and episode_title != title:
                        if desc:
                            desc = f"{episode_title}\n\n{desc}"
                        else:
                            desc = episode_title
                    if not desc:
                        # Provide a non-empty description to avoid "Unknown Airing" in Plex
                        desc = title
                    if desc:
                        xml_content += f'    <desc lang="en">{_xml(desc)}</desc>\n'
                    else:
                        # Include empty desc to ensure Plex compatibility
                        xml_content += '    <desc lang="en"></desc>\n'
                    
                    # Thumbnail/icon - ensure absolute URL for Plex
                    if media_item.thumbnail:
                        # Ensure thumbnail URL is absolute
                        if media_item.thumbnail.startswith('http'):
                            # Already absolute, use as-is (may already include Plex token)
                            thumb_url = media_item.thumbnail
                        else:
                            # Relative path - make absolute
                            thumb_url = f"{base_url}{media_item.thumbnail}" if media_item.thumbnail.startswith('/') else f"{base_url}/{media_item.thumbnail}"
                        xml_content += f'    <icon src="{_xml(thumb_url)}"/>\n'
                    
                    # Enhanced EPG metadata - use standard XMLTV fields only
                    # Plex expects at least one category
                    filler_kind = schedule_item.get('filler_kind')
                    if filler_kind:
                        xml_content += f'    <category lang="en">{_xml(filler_kind)}</category>\n'
                    else:
                        # Default category for Plex compatibility
                        xml_content += '    <category lang="en">General</category>\n'
                    
                    # Uploader/Creator (standard XMLTV credits field)
                    if media_item.uploader:
                        xml_content += f'    <credits>\n'
                        xml_content += f'      <director>{_xml(media_item.uploader)}</director>\n'
                        xml_content += f'    </credits>\n'
                    
                    # Upload date (standard XMLTV date field)
                    if media_item.upload_date:
                        xml_content += f'    <date>{_xml(media_item.upload_date)}</date>\n'
                    
                    # Simplified metadata parsing (reduced for performance)
                    # Only parse essential fields to speed up XML generation
                    if media_item.meta_data:
                        try:
                            import json
                            meta = json.loads(media_item.meta_data)
                            
                            # Only include most important metadata fields
                            if meta.get('episode'):
                                xml_content += f'    <episode-num system="onscreen">{_xml(str(meta.get("episode")))}</episode-num>\n'
                            
                            if meta.get('season') and meta.get('episode'):
                                try:
                                    season_idx = int(meta.get("season", 0)) - 1
                                    episode_idx = int(meta.get("episode", 0)) - 1
                                    season_ep = f'{season_idx}.{episode_idx}.'
                                    xml_content += f'    <episode-num system="xmltv_ns">{_xml(season_ep)}</episode-num>\n'
                                except (ValueError, TypeError):
                                    pass
                            
                            # Limit categories to first 3 for performance
                            # Add lang attribute for Plex compatibility
                            if meta.get('categories'):
                                for cat in list(meta.get('categories', []))[:3]:
                                    xml_content += f'    <category lang="en">{_xml(str(cat))}</category>\n'
                        except Exception as e:
                            # Skip metadata parsing errors to avoid slowing down EPG generation
                            pass
                    
                    # Only include standard XMLTV fields - remove custom fields that might confuse Plex
                    # URL field is optional in XMLTV and can cause issues if it's not accessible
                    # We'll skip it to avoid Plex metadata grab failures
                    
                    xml_content += '  </programme>\n'
                
                current_time = end_time_prog
                
                if current_time > end_time:
                    break
        
        xml_content += '</tv>\n'
        
        # Clean up Plex API client if used
        if plex_client:
            try:
                await plex_client.__aexit__(None, None, None)
            except Exception as e:
                logger.debug(f"Plex client cleanup: {e}")
        
        generation_time = time.time() - perf_start_time
        logger.info(f"XMLTV EPG generated in {generation_time:.2f}s ({len(xml_content)} bytes)")
        
        # #region agent log
        try:
            import json
            with open('/Users/roto1231/Documents/XCode Projects/StreamTV/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"api/iptv.py:887","message":"XMLTV: Response prepared","data":{"content_length":len(xml_content),"media_type":"application/xml; charset=utf-8","generation_time":generation_time},"timestamp":int(__import__('time').time()*1000)})+'\n')
        except: pass
        # #endregion
        
        return Response(
            content=xml_content,
            media_type="application/xml; charset=utf-8",
            headers={
                "Content-Disposition": "inline; filename=xmltv.xml",
                "Cache-Control": "public, max-age=300",  # Cache for 5 minutes
                "X-Generated-At": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "X-Generation-Time": f"{generation_time:.2f}s"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating XMLTV EPG: {e}", exc_info=True)
        error_xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        error_xml += '<tv generator-info-name="StreamTV">\n'
        error_xml += f'  <error>{_xml(str(e))}</error>\n'
        error_xml += '</tv>\n'
        return Response(
            content=error_xml,
            media_type="application/xml; charset=utf-8",
            status_code=500,
            headers={
                "Content-Disposition": "inline; filename=xmltv.xml"
            }
        )


@router.get("/iptv/channel/{channel_number}.m3u8")
async def get_hls_stream(
    channel_number: str,
    access_token: Optional[str] = None,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Get HLS stream for a channel"""
    # Validate access token if required
    # If access_token is None in config, allow requests without token (for Plex compatibility)
    if config.security.api_key_required:
        if config.security.access_token is None:
            # Token required but not configured - allow access (backward compatibility)
            logger.debug("API key required but access_token not set - allowing access for HLS")
        elif access_token != config.security.access_token:
            raise HTTPException(status_code=401, detail="Invalid access token")
    
    # Query channel using raw SQL to avoid enum conversion issues
    from sqlalchemy import text
    from ..database.models import StreamingMode
    
    channel = None
    try:
        channel = db.query(Channel).filter(
            Channel.number == channel_number,
            Channel.enabled == True
        ).first()
    except (LookupError, ValueError) as e:
        # If enum conversion fails, query raw and convert manually
        logger.warning(f"Enum conversion error in HLS endpoint, using raw query: {e}")
        result = db.execute(
            text("SELECT * FROM channels WHERE number = :number AND enabled = :enabled"),
            {"number": channel_number, "enabled": True}
        ).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Channel not found")
        
        # Create channel object from row
        channel = Channel()
        for key, value in result._mapping.items():
            if key == 'streaming_mode' and value:
                try:
                    setattr(channel, key, StreamingMode(value))
                except ValueError:
                    setattr(channel, key, StreamingMode.TRANSPORT_STREAM_HYBRID)
            else:
                setattr(channel, key, value)
    
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    # Try to load schedule file first
    schedule_file = ScheduleParser.find_schedule_file(channel_number)
    schedule_items = []
    
    if schedule_file:
        try:
            logger.info(f"Loading schedule from: {schedule_file}")
            parsed_schedule = ScheduleParser.parse_file(schedule_file, schedule_file.parent)
            schedule_engine = ScheduleEngine(db)
            schedule_items = schedule_engine.generate_playlist_from_schedule(
                channel, parsed_schedule, max_items=1000  # Limit to prevent huge playlists
            )
            logger.info(f"Generated {len(schedule_items)} items from schedule")
        except Exception as e:
            logger.warning(f"Failed to load schedule file {schedule_file}: {e}")
            logger.info("Falling back to playlist-based streaming")
    
    # Fallback to playlist if schedule not available or failed
    if not schedule_items:
        # Get active playlist for channel
        playlists = db.query(Playlist).filter(Playlist.channel_id == channel.id).all()
        if not playlists:
            raise HTTPException(status_code=404, detail="No playlist found for channel")
        
        playlist = playlists[0]  # Use first playlist
        playlist_items = db.query(PlaylistItem).filter(
            PlaylistItem.playlist_id == playlist.id
        ).order_by(PlaylistItem.order).all()
        
        if not playlist_items:
            raise HTTPException(status_code=404, detail="Playlist is empty")
        
        # Convert playlist items to schedule format
        for item in playlist_items:
            media_item = db.query(MediaItem).filter(MediaItem.id == item.media_item_id).first()
            if media_item:
                schedule_items.append({
                    'media_item': media_item,
                    'custom_title': None,
                    'filler_kind': None,
                    'start_time': None
                })
    
    # If we still have no items, return 404
    if not schedule_items:
        raise HTTPException(status_code=404, detail="No media items found for channel")
    
    # ------------------------------------------------------------------
    # Time-align playlist to behave like a live channel (join-in-progress)
    # ------------------------------------------------------------------
    #
    # We emulate the same playout timeline as ChannelManager:
    # - Playout starts at midnight UTC of the day the channel was created
    # - Use current UTC time to find position within the repeating schedule
    # - Start the HLS playlist from the item that should be playing now
    #
    now_utc = datetime.utcnow()
    try:
        creation_date_utc = channel.created_at.replace(tzinfo=None)
    except Exception:
        creation_date_utc = now_utc
    playout_start_time = datetime.combine(creation_date_utc.date(), dt_time.min)
    
    elapsed_since_start = (now_utc - playout_start_time).total_seconds()
    if elapsed_since_start < 0:
        elapsed_since_start = 0
    
    # Total duration of one full schedule loop
    total_schedule_duration = 0
    for item in schedule_items:
        media = item.get("media_item")
        if not media:
            continue
        dur = media.duration or 1800  # Default 30 minutes if unknown
        if dur <= 0:
            dur = 1800
        total_schedule_duration += dur
    
    # Fallback: if total duration is zero, start from the first item
    current_index = 0
    if total_schedule_duration > 0:
        loop_position = elapsed_since_start % total_schedule_duration
        time_offset = 0.0
        idx_candidate = 0
        for idx, item in enumerate(schedule_items):
            media = item.get("media_item")
            if not media:
                continue
            dur = media.duration or 1800
            if dur <= 0:
                dur = 1800
            
            if time_offset + dur > loop_position:
                idx_candidate = idx
                break
            time_offset += dur
            idx_candidate = idx + 1
        
        if idx_candidate >= len(schedule_items):
            idx_candidate = 0
        
        current_index = idx_candidate
    
    # Reorder items so playlist starts from the live position
    if current_index > 0:
        ordered_items = schedule_items[current_index:] + schedule_items[:current_index]
    else:
        ordered_items = schedule_items
    
    # Generate HLS playlist (ErsatzTV-compatible approach)
    # Create a playlist that ensures continuous playback of all videos in sequence,
    # starting from the item that should be live right now.
    # Note: This uses MP4 files as segments for simplicity; true HLS would use FFmpeg segmentation.
    
    base_url = config.server.base_url
    if request:
        scheme = request.url.scheme
        host = request.url.hostname
        port = request.url.port
        if port:
            base_url = f"{scheme}://{host}:{port}"
        else:
            base_url = f"{scheme}://{host}"
    
    token_param = f"?access_token={access_token}" if access_token else ""
    
    m3u8_content = "#EXTM3U\n"
    m3u8_content += "#EXT-X-VERSION:3\n"
    
    # Calculate target duration (use max segment duration)
    max_duration = 0
    total_duration = 0
    for schedule_item in ordered_items:
        media_item = schedule_item['media_item']
        if media_item:
            duration = media_item.duration or 1800
            max_duration = max(max_duration, duration)
            total_duration += duration
    
    # Target duration should be at least the longest segment
    target_duration = max(30, int(max_duration) + 1)
    m3u8_content += f"#EXT-X-TARGETDURATION:{target_duration}\n"
    # Use current_index as media sequence so players see this as a rolling playlist
    m3u8_content += f"#EXT-X-MEDIA-SEQUENCE:{current_index}\n"
    
    # Treat this as an EVENT-like playlist (no ENDLIST) so it feels live.
    # We intentionally omit #EXT-X-PLAYLIST-TYPE to keep clients flexible.
    
    # Add all schedule items in sequence with 100% metadata, starting from live position
    for idx, schedule_item in enumerate(ordered_items):
        media_item = schedule_item['media_item']
        if media_item:
            duration = media_item.duration or 1800
            # Use custom title if available (ErsatzTV supports custom titles)
            title = schedule_item.get('custom_title') or media_item.title
            
            # Build comprehensive metadata string for EXTINF
            metadata_parts = [title]
            
            # Add ALL available metadata
            if media_item.description:
                desc = media_item.description[:200].replace('\n', ' ').replace('\r', ' ').replace(',', '\\,')
                metadata_parts.append(f"Description: {desc}")
            
            if media_item.uploader:
                metadata_parts.append(f"Uploader: {media_item.uploader}")
            
            if media_item.upload_date:
                metadata_parts.append(f"Date: {media_item.upload_date}")
            
            if media_item.view_count:
                metadata_parts.append(f"Views: {media_item.view_count}")
            
            if media_item.source_id:
                metadata_parts.append(f"Source ID: {media_item.source_id}")
            
            if media_item.source:
                metadata_parts.append(f"Source: {media_item.source.value}")
            
            # Parse and add meta_data JSON fields
            if media_item.meta_data:
                try:
                    import json
                    meta = json.loads(media_item.meta_data)
                    for key, value in meta.items():
                        if value and str(value) not in ['None', 'null', '']:
                            value_str = str(value)[:100].replace(',', '\\,')
                            metadata_parts.append(f"{key}: {value_str}")
                except:
                    pass
            
            # Combine all metadata (escape commas for M3U8)
            full_metadata = " | ".join(metadata_parts).replace('\n', ' ').replace('\r', ' ')
            
            m3u8_content += f"#EXTINF:{duration:.3f},{full_metadata}\n"
            
            # Add custom metadata tags (some players support these)
            m3u8_content += f"#EXT-X-METADATA:SOURCE={media_item.source.value}\n"
            if media_item.uploader:
                m3u8_content += f"#EXT-X-METADATA:UPLOADER={media_item.uploader.replace(',', '\\,')}\n"
            if media_item.upload_date:
                m3u8_content += f"#EXT-X-METADATA:UPLOAD_DATE={media_item.upload_date}\n"
            if media_item.thumbnail:
                m3u8_content += f"#EXT-X-METADATA:THUMBNAIL={media_item.thumbnail}\n"
            if media_item.view_count:
                m3u8_content += f"#EXT-X-METADATA:VIEW_COUNT={media_item.view_count}\n"
            if media_item.source_id:
                m3u8_content += f"#EXT-X-METADATA:SOURCE_ID={media_item.source_id}\n"
            
            # Stream URL points to the actual media stream
            # For direct HLS URLs (like PBS streams), use MPEG-TS endpoint instead
            # Browsers cannot play DRM-protected HLS streams directly, so we need to transcode
            # However, include the original URL as a comment for the web player to use if possible
            if media_item.url and '.m3u8' in media_item.url.lower():
                # Direct HLS stream - use MPEG-TS endpoint for browser compatibility
                # The MPEG-TS endpoint will transcode the HLS stream for browser playback
                # Include original URL as comment for web player
                original_url = media_item.url
                m3u8_content += f"#EXT-X-ORIGINAL-URL:{original_url}\n"
                stream_url = f"{base_url}/iptv/channel/{channel.number}.ts{token_param}"
                logger.debug(f"Using MPEG-TS endpoint for HLS stream (media {media_item.id}), original URL: {original_url}")
            else:
                # Non-HLS stream - proxy through StreamTV endpoint
                stream_url = f"{base_url}/iptv/stream/{media_item.id}{token_param}"
            m3u8_content += f"{stream_url}\n"
    
    # Mark end of playlist (VOD type)
    # Note: For live streaming, ErsatzTV would omit this and update the playlist dynamically
    m3u8_content += "#EXT-X-ENDLIST\n"
    
    logger.info(f"Generated HLS playlist with {len(schedule_items)} items (total duration: {total_duration}s)")
    
    return Response(content=m3u8_content, media_type="application/vnd.apple.mpegurl")


@router.get("/iptv/channel/{channel_number}.ts")
async def get_transport_stream(
    channel_number: str,
    access_token: Optional[str] = None,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Get transport stream for a channel (TS format), using the same continuous
    playout method as the HDHomeRun endpoint (ErsatzTV-style).

    This returns a continuous MPEG-TS stream so clients (including Plex IPTV)
    can join the live channel in progress instead of starting from the first item.
    """
    # Validate access token if required
    # If access_token is None in config, allow requests without token (for Plex compatibility)
    if config.security.api_key_required:
        if config.security.access_token is None:
            # Token required but not configured - allow access (backward compatibility)
            logger.debug("API key required but access_token not set - allowing access for IPTV")
        elif access_token != config.security.access_token:
            raise HTTPException(status_code=401, detail="Invalid access token")
    
    # Query channel using raw SQL to avoid enum conversion issues
    from sqlalchemy import text
    from ..database.models import StreamingMode
    
    channel = None
    try:
        channel = db.query(Channel).filter(
            Channel.number == channel_number,
            Channel.enabled == True
        ).first()
    except (LookupError, ValueError) as e:
        # If enum conversion fails, query raw and convert manually
        logger.warning(f"Enum conversion error in TS endpoint, using raw query: {e}")
        result = db.execute(
            text("SELECT * FROM channels WHERE number = :number AND enabled = :enabled"),
            {"number": channel_number, "enabled": True}
        ).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Channel not found")
        
        # Create channel object from row
        channel = Channel()
        for key, value in result._mapping.items():
            if key == 'streaming_mode' and value:
                try:
                    setattr(channel, key, StreamingMode(value))
                except ValueError:
                    setattr(channel, key, StreamingMode.TRANSPORT_STREAM_HYBRID)
            else:
                setattr(channel, key, value)
    
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    logger.info(f"IPTV TS stream request for channel {channel_number} from {request.client.host if request else 'unknown'}")
    
    # Try to use ChannelManager for continuous streaming (same as HDHomeRun)
    try:
        channel_manager = None
        if request:
            app = request.app
            if hasattr(app, "state"):
                channel_manager = getattr(app.state, "channel_manager", None)
        
        if channel_manager:
            logger.info(f"Client connecting to continuous TS stream for channel {channel_number} ({channel.name}) via IPTV endpoint")
            
            async def generate():
                try:
                    async for chunk in channel_manager.get_channel_stream(channel_number):
                        yield chunk
                except Exception as e:
                    logger.error(f"Error in continuous TS stream for channel {channel_number} ({channel.name}): {e}", exc_info=True)
                    # Don't raise - let the client handle the connection error gracefully
                    return
            
            return StreamingResponse(
                generate(),
                media_type="video/mp2t",
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
                    "Cache-Control": "no-cache, no-store, must-revalidate, private",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                    "Transfer-Encoding": "chunked",
                },
            )
        else:
            # Fallback to on-demand MPEG-TS streamer (like HDHomeRun fallback)
            from ..streaming.mpegts_streamer import MPEGTSStreamer
            
            base_url = config.server.base_url
            if request:
                scheme = request.url.scheme
                host = request.url.hostname
                port = request.url.port
                if port:
                    base_url = f"{scheme}://{host}:{port}"
                else:
                    base_url = f"{scheme}://{host}"
            
            streamer = MPEGTSStreamer(db)
            logger.info(f"Streaming channel {channel_number} ({channel.name}) via MPEG-TS (IPTV on-demand fallback)")
            
            async def generate():
                try:
                    async for chunk in streamer.create_continuous_stream(channel, base_url):
                        yield chunk
                except Exception as e:
                    logger.error(f"Error in MPEG-TS IPTV stream generation for channel {channel_number} ({channel.name}): {e}", exc_info=True)
                    # Don't raise - let the client handle the connection error gracefully
                    return
            
            return StreamingResponse(
                generate(),
                media_type="video/mp2t",
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
                    "Cache-Control": "no-cache, no-store, must-revalidate, private",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                    "Transfer-Encoding": "chunked",
                },
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error streaming channel {channel_number} via IPTV TS: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error streaming channel: {str(e)}")


@router.options("/iptv/stream/{media_id}")
async def stream_media_options(media_id: int):
    """Handle CORS preflight for stream endpoint"""
    return Response(
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
            "Access-Control-Allow-Headers": "Range, Content-Range, Content-Type",
            "Access-Control-Max-Age": "3600"
        }
    )


@router.head("/iptv/stream/{media_id}")
@router.get("/iptv/stream/{media_id}")
async def stream_media(
    media_id: int,
    access_token: Optional[str] = None,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Stream a media item directly (supports GET and HEAD)"""
    # Validate access token if required
    # If access_token is None in config, allow requests without token
    if config.security.api_key_required:
        if config.security.access_token is None:
            # Token required but not configured - allow access (backward compatibility)
            logger.warning("API key required but access_token not set in config - allowing access")
        elif access_token != config.security.access_token:
            raise HTTPException(status_code=401, detail="Invalid access token")
    
    media_item = db.query(MediaItem).filter(MediaItem.id == media_id).first()
    if not media_item:
        raise HTTPException(status_code=404, detail="Media item not found")
    
    # Validate media item has a URL
    if not media_item.url:
        logger.error(f"Media item {media_id} has no URL")
        raise HTTPException(status_code=400, detail="Media item has no URL configured")
    
    try:
        # Get streaming URL
        try:
            stream_url = await stream_manager.get_stream_url(media_item.url)
            if not stream_url:
                raise ValueError("Stream URL is empty")
        except ValueError as e:
            logger.error(f"Error getting stream URL for media {media_id} (URL: {media_item.url}): {e}")
            raise HTTPException(status_code=400, detail=f"Unsupported media source or invalid URL: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error getting stream URL for media {media_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to get stream URL: {str(e)}")
        
        # Detect source for authenticated streaming
        try:
            source = stream_manager.detect_source(media_item.url)
        except Exception as e:
            logger.warning(f"Error detecting source for media {media_id}, using UNKNOWN: {e}")
            # Detect source from URL
            if 'youtube.com' in media_item.url or 'youtu.be' in media_item.url:
                source = StreamSource.YOUTUBE
            elif 'archive.org' in media_item.url:
                source = StreamSource.ARCHIVE_ORG
            elif 'plex://' in media_item.url or '/library/metadata/' in media_item.url:
                source = StreamSource.PLEX
            else:
                source = StreamSource.UNKNOWN
        
        # Handle range requests for seeking
        range_header = request.headers.get("Range") if request else None
        start = None
        end = None
        
        # Browsers often send "bytes=0-" for initial load, handle that
        if range_header:
            # Parse range header: "bytes=start-end"
            range_match = range_header.replace("bytes=", "").split("-")
            if range_match[0]:
                try:
                    start = int(range_match[0])
                except ValueError:
                    start = None
            if len(range_match) > 1 and range_match[1]:
                try:
                    end = int(range_match[1])
                except ValueError:
                    end = None
        
        # Get content length and type from upstream
        content_length = None
        upstream_content_type = "video/mp4"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Try HEAD request first
                try:
                    # Follow redirects and validate the stream URL
                    head_response = await client.head(stream_url, follow_redirects=True, timeout=10.0)
                    
                    # If redirected, use the final URL
                    if head_response.status_code in [301, 302, 303, 307, 308]:
                        redirect_url = head_response.headers.get('Location')
                        if redirect_url:
                            if redirect_url.startswith('/'):
                                from urllib.parse import urlparse
                                parsed = urlparse(stream_url)
                                redirect_url = f"{parsed.scheme}://{parsed.netloc}{redirect_url}"
                            stream_url = redirect_url
                            logger.info(f"Stream URL redirected to: {stream_url}")
                            # Re-validate the redirected URL
                            head_response = await client.head(stream_url, follow_redirects=True, timeout=10.0)
                    content_length = head_response.headers.get("Content-Length")
                    upstream_content_type = head_response.headers.get("Content-Type", "video/mp4")
                except:
                    pass
                
                # If HEAD doesn't work or no Content-Length, try a small range request
                if not content_length:
                    try:
                        range_headers = {"Range": "bytes=0-1023"}
                        test_response = await client.get(stream_url, headers=range_headers, follow_redirects=True, timeout=10.0)
                        content_range = test_response.headers.get("Content-Range")
                        if content_range:
                            # Extract total from "bytes 0-1023/1234567"
                            if "/" in content_range:
                                content_length = content_range.split("/")[-1]
                        if not content_length:
                            content_length = test_response.headers.get("Content-Length")
                        if not upstream_content_type or upstream_content_type == "application/octet-stream":
                            upstream_content_type = test_response.headers.get("Content-Type", "video/mp4")
                    except:
                        pass
        except Exception as e:
            logger.warning(f"Could not determine content length: {e}")
            # Continue without content length - browser will handle it
        
        # Determine content type
        content_type = upstream_content_type
        if not content_type or content_type == "application/octet-stream":
            if source == StreamSource.YOUTUBE:
                content_type = "video/mp4"
            elif source == StreamSource.ARCHIVE_ORG:
                if media_item.url.endswith('.mp4'):
                    content_type = "video/mp4"
                elif media_item.url.endswith('.webm'):
                    content_type = "video/webm"
                else:
                    content_type = "video/mp4"
            elif source == StreamSource.PLEX:
                # Plex typically serves MP4 or MKV, default to MP4
                content_type = "video/mp4"
            else:
                content_type = "video/mp4"
        
        headers = {
            "Accept-Ranges": "bytes",
            "Content-Type": content_type,
            "Cache-Control": "public, max-age=3600",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
            "Access-Control-Allow-Headers": "Range, Content-Range, Content-Type"
        }
        
        # Don't set Content-Length for streaming responses - it causes issues with range requests
        # The Content-Length will be determined by the actual stream
        # Only set it for HEAD requests where we're not streaming
        
        # Handle HEAD request - return headers only
        if request and request.method == "HEAD":
            # Add Content-Range header if range request
            if range_header and content_length:
                try:
                    total_size = int(content_length)
                    range_start = start or 0
                    range_end = end if end is not None else (total_size - 1)
                    actual_end = min(range_end, total_size - 1)
                    headers["Content-Range"] = f"bytes {range_start}-{actual_end}/{total_size}"
                    headers["Content-Length"] = str(actual_end - range_start + 1)
                    return Response(status_code=206, headers=headers)
                except (ValueError, TypeError):
                    pass
            return Response(status_code=200, headers=headers)
        
        # Stream the media for GET requests
        async def generate():
            try:
                async for chunk in stream_manager.stream_chunked(stream_url, start=start, end=end, source=source):
                    yield chunk
            except httpx.HTTPError as e:
                logger.error(f"HTTP error streaming media {media_id}: {e}")
                # Note: We can't raise HTTPException here since we're in a generator
                # The client will see a connection error
                raise
            except Exception as e:
                logger.error(f"Error in stream generator for media {media_id}: {e}", exc_info=True)
                raise
        
        # Add Content-Range header if range request
        # Note: Don't set Content-Length for streaming responses - let the stream determine it
        if range_header and content_length:
            try:
                total_size = int(content_length)
                range_start = start or 0
                range_end = end if end is not None else (total_size - 1)
                actual_end = min(range_end, total_size - 1)
                headers["Content-Range"] = f"bytes {range_start}-{actual_end}/{total_size}"
                # Remove Content-Length for streaming - it will be determined by the stream
                headers.pop("Content-Length", None)
                return StreamingResponse(
                    generate(),
                    status_code=206,  # Partial Content
                    headers=headers,
                    media_type=upstream_content_type
                )
            except (ValueError, TypeError):
                pass
        
        return StreamingResponse(
            generate(),
            headers=headers,
            media_type=upstream_content_type
        )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except httpx.TimeoutException as e:
        logger.error(f"Timeout streaming media {media_id}: {e}")
        raise HTTPException(status_code=504, detail="Request to media source timed out")
    except httpx.HTTPError as e:
        logger.error(f"HTTP error streaming media {media_id}: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"Failed to connect to media source: {str(e)}")
    except ValueError as e:
        logger.error(f"Invalid value error streaming media {media_id}: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error streaming media {media_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

