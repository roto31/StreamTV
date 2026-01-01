"""HDHomeRun API endpoints for Plex/Emby/Jellyfin integration"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
import json
import logging
import asyncio
import re
from datetime import datetime

from ..database import get_db, Channel, Playlist, PlaylistItem, MediaItem
from ..streaming import StreamManager, StreamSource
from ..config import config

logger = logging.getLogger(__name__)

hdhomerun_router = APIRouter(prefix="/hdhomerun", tags=["HDHomeRun"])

stream_manager = StreamManager()

# HDHomeRun device configuration (now uses config values)
HDHOMERUN_MODEL = "StreamTV"
HDHOMERUN_FIRMWARE = "1.0"


@hdhomerun_router.get("/device.xml")
async def device_description(request: Request):
    """HDHomeRun device description XML (UPnP)"""
    base_url = config.server.base_url
    if request:
        scheme = request.url.scheme
        host = request.url.hostname
        port = request.url.port
        if port:
            base_url = f"{scheme}://{host}:{port}"
        else:
            base_url = f"{scheme}://{host}"
    
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<root xmlns="urn:schemas-upnp-org:device-1-0">
    <specVersion>
        <major>1</major>
        <minor>0</minor>
    </specVersion>
    <device>
        <deviceType>urn:schemas-upnp-org:device:MediaServer:1</deviceType>
        <friendlyName>StreamTV HDHomeRun</friendlyName>
        <manufacturer>StreamTV</manufacturer>
        <manufacturerURL>https://github.com/streamtv</manufacturerURL>
        <modelName>{HDHOMERUN_MODEL}</modelName>
        <modelNumber>{HDHOMERUN_FIRMWARE}</modelNumber>
        <UDN>uuid:{config.hdhomerun.device_id}</UDN>
        <serviceList>
            <service>
                <serviceType>urn:schemas-upnp-org:service:ContentDirectory:1</serviceType>
                <serviceId>urn:upnp-org:serviceId:ContentDirectory</serviceId>
                <SCPDURL>{base_url}/hdhomerun/service.xml</SCPDURL>
                <controlURL>{base_url}/hdhomerun/control</controlURL>
                <eventSubURL>{base_url}/hdhomerun/event</eventSubURL>
            </service>
        </serviceList>
    </device>
</root>'''
    
    return Response(content=xml, media_type="application/xml")


@hdhomerun_router.get("/service.xml")
async def service_description(request: Request):
    """HDHomeRun service description XML (UPnP)"""
    xml = '''<?xml version="1.0" encoding="UTF-8"?>
<scpd xmlns="urn:schemas-upnp-org:service-1-0">
    <specVersion>
        <major>1</major>
        <minor>0</minor>
    </specVersion>
    <actionList>
        <action>
            <name>GetSearchCapabilities</name>
        </action>
        <action>
            <name>GetSortCapabilities</name>
        </action>
        <action>
            <name>GetSystemUpdateID</name>
        </action>
        <action>
            <name>Browse</name>
            <argumentList>
                <argument>
                    <name>ObjectID</name>
                    <direction>in</direction>
                    <relatedStateVariable>A_ARG_TYPE_ObjectID</relatedStateVariable>
                </argument>
                <argument>
                    <name>BrowseFlag</name>
                    <direction>in</direction>
                    <relatedStateVariable>A_ARG_TYPE_BrowseFlag</relatedStateVariable>
                </argument>
                <argument>
                    <name>Filter</name>
                    <direction>in</direction>
                    <relatedStateVariable>A_ARG_TYPE_Filter</relatedStateVariable>
                </argument>
                <argument>
                    <name>StartingIndex</name>
                    <direction>in</direction>
                    <relatedStateVariable>A_ARG_TYPE_Index</relatedStateVariable>
                </argument>
                <argument>
                    <name>RequestedCount</name>
                    <direction>in</direction>
                    <relatedStateVariable>A_ARG_TYPE_Count</relatedStateVariable>
                </argument>
                <argument>
                    <name>SortCriteria</name>
                    <direction>in</direction>
                    <relatedStateVariable>A_ARG_TYPE_SortCriteria</relatedStateVariable>
                </argument>
                <argument>
                    <name>Result</name>
                    <direction>out</direction>
                    <relatedStateVariable>A_ARG_TYPE_Result</relatedStateVariable>
                </argument>
                <argument>
                    <name>NumberReturned</name>
                    <direction>out</direction>
                    <relatedStateVariable>A_ARG_TYPE_Count</relatedStateVariable>
                </argument>
                <argument>
                    <name>TotalMatches</name>
                    <direction>out</direction>
                    <relatedStateVariable>A_ARG_TYPE_Count</relatedStateVariable>
                </argument>
                <argument>
                    <name>UpdateID</name>
                    <direction>out</direction>
                    <relatedStateVariable>A_ARG_TYPE_UpdateID</relatedStateVariable>
                </argument>
            </argumentList>
        </action>
    </actionList>
    <serviceStateTable>
        <stateVariable sendEvents="yes">
            <name>SystemUpdateID</name>
            <dataType>ui4</dataType>
        </stateVariable>
        <stateVariable sendEvents="no">
            <name>A_ARG_TYPE_ObjectID</name>
            <dataType>string</dataType>
        </stateVariable>
        <stateVariable sendEvents="no">
            <name>A_ARG_TYPE_Result</name>
            <dataType>string</dataType>
        </stateVariable>
        <stateVariable sendEvents="no">
            <name>A_ARG_TYPE_BrowseFlag</name>
            <dataType>string</dataType>
            <allowedValueList>
                <allowedValue>BrowseMetadata</allowedValue>
                <allowedValue>BrowseDirectChildren</allowedValue>
            </allowedValueList>
        </stateVariable>
        <stateVariable sendEvents="no">
            <name>A_ARG_TYPE_Filter</name>
            <dataType>string</dataType>
        </stateVariable>
        <stateVariable sendEvents="no">
            <name>A_ARG_TYPE_SortCriteria</name>
            <dataType>string</dataType>
        </stateVariable>
        <stateVariable sendEvents="no">
            <name>A_ARG_TYPE_Index</name>
            <dataType>ui4</dataType>
        </stateVariable>
        <stateVariable sendEvents="no">
            <name>A_ARG_TYPE_Count</name>
            <dataType>ui4</dataType>
        </stateVariable>
        <stateVariable sendEvents="no">
            <name>A_ARG_TYPE_UpdateID</name>
            <dataType>ui4</dataType>
        </stateVariable>
    </serviceStateTable>
</scpd>'''
    
    return Response(content=xml, media_type="application/xml")


@hdhomerun_router.post("/control")
async def control(request: Request):
    """HDHomeRun UPnP control endpoint"""
    # Most media servers don't actually use this, but we provide it for compatibility
    return Response(content="", status_code=200)


@hdhomerun_router.get("/event")
@hdhomerun_router.post("/event")
async def event(request: Request):
    """HDHomeRun UPnP event subscription endpoint"""
    # Most media servers don't actually use this, but we provide it for compatibility
    # UPnP uses both GET (subscribe) and POST (unsubscribe) for events
    return Response(content="", status_code=200)


@hdhomerun_router.get("/discover.json")
async def discover(request: Request, db: Session = Depends(get_db)):
    """HDHomeRun device discovery endpoint"""
    base_url = config.server.base_url
    if request:
        scheme = request.url.scheme
        host = request.url.hostname
        port = request.url.port
        if port:
            base_url = f"{scheme}://{host}:{port}"
        else:
            base_url = f"{scheme}://{host}"
    
    # Get enabled channels count
    channel_count = db.query(Channel).filter(Channel.enabled == True).count()
    
    response = {
        "FriendlyName": config.hdhomerun.friendly_name,
        "ModelNumber": HDHOMERUN_MODEL,
        "FirmwareName": f"streamtv-{HDHOMERUN_FIRMWARE}",
        "FirmwareVersion": HDHOMERUN_FIRMWARE,
        "DeviceID": config.hdhomerun.device_id,
        "DeviceAuth": "streamtv",
        "BaseURL": f"{base_url}/hdhomerun",
        "LineupURL": f"{base_url}/hdhomerun/lineup.json",
        "TunerCount": config.hdhomerun.tuner_count,
        "EPGURL": f"{base_url}/iptv/xmltv.xml"  # XMLTV EPG URL for Plex/Emby/Jellyfin
    }
    
    return response


@hdhomerun_router.get("/lineup.json")
async def lineup(request: Request, db: Session = Depends(get_db)):
    """HDHomeRun channel lineup"""
    # Query channels - handle enum validation errors with fallback to raw SQL
    try:
        channels = db.query(Channel).filter(Channel.enabled == True).order_by(Channel.number).all()
    except (LookupError, ValueError, Exception) as query_error:
        # Handle SQLAlchemy enum validation errors by querying raw values and converting
        error_str = str(query_error)
        error_type = type(query_error).__name__
        # Check if this is an enum validation error (can be LookupError or the message contains the enum error text)
        if isinstance(query_error, LookupError) or "is not among the defined enum values" in error_str or "channeltranscodemode" in error_str.lower() or "transcodemode" in error_str.lower():
            logger.warning(f"SQLAlchemy enum validation error when querying channels for HDHomeRun lineup: {query_error}")
            logger.info("Attempting to query channels using raw SQL to work around enum validation issue...")
            # Query using raw SQL to avoid enum validation, then construct Channel objects
            from sqlalchemy import text
            raw_result = db.execute(text("""
                SELECT * FROM channels WHERE enabled = 1 ORDER BY number
            """)).fetchall()
            channels = []
            from ..database.models import (
                PlayoutMode, StreamingMode, ChannelTranscodeMode, ChannelSubtitleMode,
                ChannelStreamSelectorMode, ChannelMusicVideoCreditsMode, ChannelSongVideoMode,
                ChannelIdleBehavior, ChannelPlayoutSource
            )
            for row in raw_result:
                channel = Channel()
                # Copy all attributes from row, converting enum strings to enums
                for key, value in row._mapping.items():
                    if value is None:
                        setattr(channel, key, None)
                    elif key == 'playout_mode' and isinstance(value, str):
                        normalized = value.lower()
                        enum_val = PlayoutMode.CONTINUOUS
                        for mode in PlayoutMode:
                            if mode.value.lower() == normalized:
                                enum_val = mode
                                break
                        else:
                            try:
                                enum_val = PlayoutMode[value.upper()]
                            except KeyError:
                                pass
                        setattr(channel, key, enum_val)
                    elif key == 'streaming_mode' and isinstance(value, str):
                        normalized = value.lower()
                        enum_val = StreamingMode.TRANSPORT_STREAM_HYBRID
                        for mode in StreamingMode:
                            if mode.value.lower() == normalized:
                                enum_val = mode
                                break
                        else:
                            try:
                                enum_val = StreamingMode[value.upper()]
                            except KeyError:
                                pass
                        setattr(channel, key, enum_val)
                    elif key == 'transcode_mode' and isinstance(value, str):
                        normalized = value.lower()
                        enum_val = ChannelTranscodeMode.ON_DEMAND
                        for mode in ChannelTranscodeMode:
                            if mode.value.lower() == normalized:
                                enum_val = mode
                                break
                        else:
                            try:
                                enum_val = ChannelTranscodeMode[value.upper()]
                            except KeyError:
                                pass
                        setattr(channel, key, enum_val)
                    elif key in ['subtitle_mode', 'stream_selector_mode', 'music_video_credits_mode', 
                                 'song_video_mode', 'idle_behavior', 'playout_source'] and isinstance(value, str):
                        # These will be handled by @reconstructor, just set as string for now
                        setattr(channel, key, value)
                    else:
                        setattr(channel, key, value)
                channels.append(channel)
            logger.info(f"Loaded {len(channels)} channels using raw SQL query for HDHomeRun lineup")
        else:
            # Re-raise if it's a different error
            raise
    
    base_url = config.server.base_url
    if request:
        scheme = request.url.scheme
        host = request.url.hostname
        port = request.url.port
        if port:
            base_url = f"{scheme}://{host}:{port}"
        else:
            base_url = f"{scheme}://{host}"
    
    lineup_data = []
    
    for channel in channels:
        # HDHomeRun expects GuideNumber, GuideName, URL, and optionally HD
        # We'll use the channel number as GuideNumber
        guide_number = channel.number
        
        # Strip channel number prefix from GuideName to avoid duplication in Plex
        # Plex displays channels as "GuideNumber GuideName", so if name already
        # starts with the number, it gets doubled (e.g., "2000 2000's Movies")
        guide_name = channel.name
        if guide_name and guide_number:
            # Check if name starts with the channel number
            name_stripped = guide_name.strip()
            number_str = str(guide_number).strip()
            
            if name_stripped.startswith(number_str):
                # Remove the number prefix
                remaining = name_stripped[len(number_str):].strip()
                
                # Remove common patterns after the number (e.g., "'s ", " - ", " ", "-", "'s")
                # Handle patterns in order of specificity (longer patterns first)
                patterns_to_remove = [
                    r"^'s\s+",      # "'s " (apostrophe-s-space)
                    r"^[\s\-\.\_]+",  # Any combination of spaces, dashes, dots, underscores
                ]
                for pattern in patterns_to_remove:
                    remaining = re.sub(pattern, '', remaining)
                
                # Only use cleaned name if there's content left, otherwise keep original
                if remaining:
                    guide_name = remaining
        
        # Create stream URL - HDHomeRun expects MPEG-TS, but we'll use HLS
        # Plex/Emby/Jellyfin can handle HLS
        stream_url = f"{base_url}/hdhomerun/auto/v{channel.number}"
        
        channel_entry = {
            "GuideNumber": str(guide_number),
            "GuideName": guide_name,
            "URL": stream_url,
            "HD": 1 if "HD" in channel.name.upper() else 0
        }
        
        lineup_data.append(channel_entry)
    
    return lineup_data


@hdhomerun_router.get("/lineup_status.json")
async def lineup_status():
    """HDHomeRun lineup status"""
    return {
        "ScanInProgress": 0,
        "ScanPossible": 1,
        "Source": "Antenna",
        "SourceList": ["Antenna", "Cable"]
    }


@hdhomerun_router.get("/auto/v{channel_number}")
async def stream_channel(
    channel_number: str,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Stream a channel (HDHomeRun format) - Returns MPEG-TS for Plex compatibility"""
    logger.info(f"HDHomeRun stream request for channel {channel_number} from {request.client.host if request else 'unknown'}")
    
    channel = db.query(Channel).filter(
        Channel.number == channel_number,
        Channel.enabled == True
    ).first()
    
    if not channel:
        logger.warning(f"Channel {channel_number} not found or not enabled")
        raise HTTPException(status_code=404, detail="Channel not found")
    
    # Try MPEG-TS streaming first (requires FFmpeg)
    try:
        # Use ChannelManager for continuous streaming (ErsatzTV-style)
        # Get ChannelManager from app state
        channel_manager = None
        if request:
            app = request.app
            if hasattr(app, 'state'):
                channel_manager = getattr(app.state, 'channel_manager', None)
        
        if channel_manager:
            # Use the continuous stream from ChannelManager
            logger.info(f"Client connecting to continuous stream for channel {channel_number} ({channel.name})")
            
            async def generate():
                try:
                    logger.debug(f"Starting stream generation for channel {channel_number}")
                    chunk_count = 0
                    async for chunk in channel_manager.get_channel_stream(channel_number):
                        chunk_count += 1
                        if chunk_count == 1:
                            logger.info(f"First chunk yielded for channel {channel_number} ({len(chunk)} bytes)")
                        yield chunk
                    logger.info(f"Stream generation completed for channel {channel_number} ({chunk_count} chunks total)")
                except asyncio.CancelledError:
                    # Client disconnected - this is normal, don't log as error
                    logger.debug(f"Stream cancelled for channel {channel_number} (client disconnected)")
                    return
                except Exception as e:
                    logger.error(f"Error in continuous stream for channel {channel_number}: {e}", exc_info=True)
                    # Don't raise - let the client handle the connection error gracefully
                    # Raising here causes Plex to show "Error tuning channel"
                    return
            
            return StreamingResponse(
                generate(),
                media_type="video/mp2t",  # MPEG-TS MIME type
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
                    "Cache-Control": "no-cache, no-store, must-revalidate, private",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",  # Disable buffering (nginx)
                    "Transfer-Encoding": "chunked",  # Chunked transfer for streaming
                }
            )
        else:
            # Fallback: create stream on-demand
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
            logger.info(f"Streaming channel {channel_number} ({channel.name}) via MPEG-TS (on-demand)")
            
            async def generate():
                try:
                    async for chunk in streamer.create_continuous_stream(channel, base_url):
                        yield chunk
                except asyncio.CancelledError:
                    # Client disconnected - this is normal, don't log as error
                    logger.debug(f"Stream cancelled for channel {channel_number} (client disconnected)")
                    return
                except Exception as e:
                    logger.error(f"Error in MPEG-TS stream generation: {e}", exc_info=True)
                    # Don't raise - let the client handle the connection error gracefully
                    # Raising here causes Plex to show "Error tuning channel"
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
                }
            )
        
    except RuntimeError as e:
        # FFmpeg not available, fall back to HLS
        if "FFmpeg not found" in str(e):
            logger.warning(f"FFmpeg not available, falling back to HLS: {e}")
            from ..api.iptv import get_hls_stream
            try:
                logger.info(f"Streaming channel {channel_number} ({channel.name}) via HLS (FFmpeg fallback)")
                response = await get_hls_stream(channel_number, None, request, db)
                if hasattr(response, 'headers'):
                    response.headers["Access-Control-Allow-Origin"] = "*"
                    response.headers["Access-Control-Allow-Methods"] = "GET, HEAD, OPTIONS"
                    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                return response
            except Exception as e:
                logger.error(f"Error streaming via HLS fallback: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Error streaming channel: {str(e)}")
        else:
            raise
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error streaming channel {channel_number} via HDHomeRun: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error streaming channel: {str(e)}")


@hdhomerun_router.get("/tuner{n}/stream")
async def tuner_stream(
    n: int,
    channel: str,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """HDHomeRun tuner stream endpoint"""
    if n < 0 or n >= config.hdhomerun.tuner_count:
        raise HTTPException(status_code=404, detail="Tuner not found")
    
    # Parse channel parameter (format: auto:v<channel_number>)
    if channel.startswith("auto:v"):
        channel_number = channel.replace("auto:v", "")
    else:
        channel_number = channel
    
    # Stream the channel
    return await stream_channel(channel_number, request, db)


@hdhomerun_router.get("/status.json")
async def status():
    """HDHomeRun device status"""
    return {
        "FriendlyName": config.hdhomerun.friendly_name,
        "ModelNumber": HDHOMERUN_MODEL,
        "FirmwareName": f"streamtv-{HDHOMERUN_FIRMWARE}",
        "FirmwareVersion": HDHOMERUN_FIRMWARE,
        "DeviceID": config.hdhomerun.device_id,
        "DeviceAuth": "streamtv",
        "TunerCount": config.hdhomerun.tuner_count,
        "TunerStatus": [
            {
                "Tuner": i,
                "Status": "Idle",
                "Channel": None,
                "Lock": "none"
            }
            for i in range(config.hdhomerun.tuner_count)
        ]
    }

