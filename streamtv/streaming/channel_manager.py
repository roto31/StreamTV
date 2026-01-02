"""Channel manager for continuous background streaming (ErsatzTV-style)"""

import asyncio
import logging
from typing import Dict, Optional, AsyncIterator, List
from datetime import datetime, timedelta, time
from collections import deque
import weakref

from streamtv.database import Channel, MediaItem
from streamtv.database.models import ChannelPlaybackPosition, PlayoutMode
from sqlalchemy.orm import Session
from streamtv.streaming.mpegts_streamer import MPEGTSStreamer
from streamtv.streaming.stream_prewarmer import StreamPrewarmer

logger = logging.getLogger(__name__)


class ChannelStream:
    """Manages a continuous stream for a single channel (ErsatzTV-style)"""
    
    def __init__(self, channel: Channel, db_session_factory):
        # Store channel ID and number instead of the object to avoid session issues
        self.channel_id = channel.id
        self.channel_number = channel.number
        self.channel_name = channel.name
        self.db_session_factory = db_session_factory
        self.streamer = None  # Will be created when needed
        self._broadcast_queue: asyncio.Queue = asyncio.Queue(maxsize=50)  # Broadcast queue
        self._stream_task: Optional[asyncio.Task] = None
        self._client_queues: List[asyncio.Queue] = []
        self._is_running = False
        self._lock = asyncio.Lock()
        self._client_count = 0
        
        # Playout timeline tracking (ErsatzTV-style)
        self._playout_start_time: Optional[datetime] = None
        self._schedule_items: List[Dict] = []
        self._current_item_index = 0
        self._current_item_start_time: Optional[datetime] = None
        self._timeline_lock = asyncio.Lock()
        
        # Stream pre-warmer for fast startup
        self._prewarmer = StreamPrewarmer(max_buffer_size=5 * 1024 * 1024, max_chunks=20)  # 5MB, 20 chunks
    
    async def start(self):
        """Start the continuous stream in the background"""
        if self._is_running:
            return
        
        async with self._lock:
            if self._is_running:
                return
            
            # Initialize playout timeline - try to resume from saved position, otherwise start from beginning
            # Uses system time (UTC) for all calculations
            async with self._timeline_lock:
                if not self._playout_start_time:
                    # Try to load saved playout start time from database
                    db = self.db_session_factory()
                    try:
                        from streamtv.database.models import ChannelPlaybackPosition
                        playback_pos = db.query(ChannelPlaybackPosition).filter(
                            ChannelPlaybackPosition.channel_id == self.channel_id
                        ).first()
                        
                        if playback_pos and playback_pos.playout_start_time:
                            # Resume from saved position
                            self._playout_start_time = playback_pos.playout_start_time
                            logger.info(f"Resuming channel {self.channel_number} from saved playout start time: {self._playout_start_time}")
                        else:
                            # First time or no saved position - start from now
                            self._playout_start_time = datetime.utcnow()
                            logger.info(f"Starting channel {self.channel_number} from current time: {self._playout_start_time}")
                            
                            # Save the start time for future resumes
                            if not playback_pos:
                                playback_pos = ChannelPlaybackPosition(
                                    channel_id=self.channel_id,
                                    channel_number=self.channel_number,
                                    playout_start_time=self._playout_start_time,
                                    last_position_update=datetime.utcnow()
                                )
                                db.add(playback_pos)
                            else:
                                playback_pos.playout_start_time = self._playout_start_time
                                playback_pos.last_position_update = datetime.utcnow()
                            db.commit()
                    except Exception as e:
                        logger.error(f"Error loading saved position for channel {self.channel_number}: {e}", exc_info=True)
                        # Fallback to starting from now
                        self._playout_start_time = datetime.utcnow()
                        logger.info(f"Starting channel {self.channel_number} from current time (fallback): {self._playout_start_time}")
                    finally:
                        db.close()
            
            self._is_running = True
            logger.info(f"ChannelStream.start() - Creating background task for channel {self.channel_number}...")
            self._stream_task = asyncio.create_task(self._run_continuous_stream())
            logger.info(f"Started continuous stream for channel {self.channel_number} ({self.channel_name}) - background task created")
    
    async def stop(self):
        """Stop the continuous stream"""
        if not self._is_running:
            return
        
        async with self._lock:
            # Set flag FIRST to prevent new items from starting
            self._is_running = False
            if self._stream_task:
                self._stream_task.cancel()
                try:
                    # Wait for task to complete cancellation (with timeout to prevent hanging)
                    await asyncio.wait_for(self._stream_task, timeout=10.0)
                except asyncio.TimeoutError:
                    logger.warning(f"Stream task for channel {self.channel_number} did not cancel within timeout")
                except asyncio.CancelledError:
                    pass
            
            # Save current position before stopping
            try:
                db = self.db_session_factory()
                try:
                    from streamtv.database.models import ChannelPlaybackPosition
                    position = await self._get_current_position()
                    current_index = position.get('item_index', 0)
                    
                    playback_pos = db.query(ChannelPlaybackPosition).filter(
                        ChannelPlaybackPosition.channel_id == self.channel_id
                    ).first()
                    
                    if not playback_pos:
                        playback_pos = ChannelPlaybackPosition(
                            channel_id=self.channel_id,
                            channel_number=self.channel_number,
                            playout_start_time=self._playout_start_time,
                            last_item_index=current_index,
                            last_position_update=datetime.utcnow()
                        )
                        db.add(playback_pos)
                    else:
                        playback_pos.playout_start_time = self._playout_start_time
                        playback_pos.last_item_index = current_index
                        playback_pos.last_position_update = datetime.utcnow()
                    db.commit()
                    logger.info(f"Saved position for channel {self.channel_number}: item {current_index}, playout_start_time={self._playout_start_time}")
                except Exception as e:
                    logger.error(f"Error saving position for channel {self.channel_number}: {e}", exc_info=True)
                    db.rollback()
                finally:
                    db.close()
            except Exception as e:
                logger.error(f"Error saving position on stop for channel {self.channel_number}: {e}", exc_info=True)
            
            # Clear all client queues
            self._client_queues.clear()
            # DON'T reset playout_start_time - keep timeline continuous for resume
            logger.info(f"Stopped continuous stream for channel {self.channel_number} (position saved for resume)")
    
    async def get_stream(self) -> AsyncIterator[bytes]:
        """Get the current stream - joins existing continuous stream at current position (ErsatzTV-style)"""
        # Check playout mode first
        db_check = self.db_session_factory()
        try:
            channel_check = db_check.query(Channel).filter(Channel.id == self.channel_id).first()
            playout_mode_raw = getattr(channel_check, 'playout_mode', PlayoutMode.CONTINUOUS) if channel_check else PlayoutMode.CONTINUOUS
            # Convert string to enum if needed (handle database string values)
            if isinstance(playout_mode_raw, str):
                normalized = playout_mode_raw.lower()
                for mode in PlayoutMode:
                    if mode.value.lower() == normalized:
                        playout_mode = mode
                        break
                else:
                    # Fallback: try to match by name (uppercase)
                    try:
                        playout_mode = PlayoutMode[playout_mode_raw.upper()]
                    except KeyError:
                        playout_mode = PlayoutMode.CONTINUOUS
            else:
                playout_mode = playout_mode_raw
        finally:
            db_check.close()
        
        # For ON_DEMAND mode, create independent stream starting from saved position or item 0
        if playout_mode == PlayoutMode.ON_DEMAND:
            db_session = None
            try:
                # Always load fresh schedule items for ON_DEMAND (don't use cached/shared state)
                db_session = self.db_session_factory()
                from streamtv.scheduling.parser import ScheduleParser
                from streamtv.scheduling.engine import ScheduleEngine
                
                schedule_file = ScheduleParser.find_schedule_file(self.channel_number)
                if not schedule_file:
                    error_msg = f"No schedule file found for ON_DEMAND channel {self.channel_number}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                
                logger.debug(f"ON_DEMAND: Found schedule file for channel {self.channel_number}: {schedule_file}")
                parsed_schedule = ScheduleParser.parse_file(schedule_file, schedule_file.parent)
                schedule_engine = ScheduleEngine(db_session)
                channel = db_session.query(Channel).filter(Channel.id == self.channel_id).first()
                
                if not channel:
                    error_msg = f"Channel {self.channel_number} not found in database"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                
                logger.debug(f"ON_DEMAND: Generating schedule items for channel {self.channel_number}")
                # Generate fresh schedule items for this ON_DEMAND client
                schedule_items = schedule_engine.generate_playlist_from_schedule(
                    channel, parsed_schedule, max_items=1000
                )
                
                if not schedule_items:
                    error_msg = f"No schedule items generated for ON_DEMAND channel {self.channel_number}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                
                # Check for saved playback position
                playback_pos = db_session.query(ChannelPlaybackPosition).filter(
                    ChannelPlaybackPosition.channel_id == self.channel_id
                ).first()
                
                start_index = 0
                if playback_pos and playback_pos.last_item_index > 0:
                    start_index = playback_pos.last_item_index
                    # Ensure start_index is within bounds
                    if start_index >= len(schedule_items):
                        start_index = 0
                        logger.warning(f"ON_DEMAND: Saved position {playback_pos.last_item_index} exceeds schedule length, starting from beginning")
                    else:
                        first_item_title = schedule_items[start_index].get('media_item', {}).title if schedule_items[start_index].get('media_item') else 'N/A'
                        logger.info(f"ON_DEMAND: Resuming channel {self.channel_number} from saved position: item {start_index}/{len(schedule_items)} - {first_item_title}")
                else:
                    first_item_title = schedule_items[0].get('media_item', {}).title if schedule_items and schedule_items[0].get('media_item') else 'N/A'
                    logger.info(f"ON_DEMAND: Starting channel {self.channel_number} from beginning (item 0): {first_item_title}")
                
                # Create independent streamer for this client
                streamer = MPEGTSStreamer(db_session)
                
                # Track items tried to prevent infinite loops if all items fail
                items_yielded = 0
                consecutive_failures = 0
                max_consecutive_failures = 10
                is_first_loop = True
                
                # Stream all items starting from saved position (or 0)
                while True:
                    # On first loop, start from saved position; on subsequent loops, start from 0
                    loop_start_index = start_index if is_first_loop else 0
                    
                    for idx in range(loop_start_index, len(schedule_items)):
                        schedule_item = schedule_items[idx]
                        media_item = schedule_item.get('media_item')
                        if not media_item:
                            logger.debug(f"ON_DEMAND: Skipping item {idx} - no media_item")
                            continue
                        
                        # Skip placeholder URLs
                        if 'PLACEHOLDER' in media_item.url.upper():
                            logger.debug(f"ON_DEMAND: Skipping item {idx} - placeholder URL")
                            continue
                        
                        # Skip very short videos
                        if media_item.duration and media_item.duration < 5:
                            logger.debug(f"ON_DEMAND: Skipping item {idx} - duration too short ({media_item.duration}s)")
                            continue
                        
                        # Channel 80: Only use H.264/.mp4 files to avoid AVI demuxing errors
                        if self.channel_number == "80":
                            # Check if URL contains .mp4 in the path (before query parameters or fragments)
                            url_lower = media_item.url.lower()
                            # Get the path portion (before ? or #)
                            url_path = url_lower.split('?')[0].split('#')[0]
                            if '.mp4' not in url_path:
                                logger.debug(f"ON_DEMAND: Skipping non-MP4 file for channel 80: {media_item.title} ({media_item.url[:80]})")
                            continue
                        
                        logger.info(f"ON_DEMAND: Streaming item {idx}/{len(schedule_items)}: {media_item.title[:60]} (URL: {media_item.url[:80]})")
                        
                        # Stream this item directly to client with timeout to prevent hanging
                        item_yielded = False
                        first_chunk_time = None
                        try:
                            chunk_iter = streamer._stream_single_item(media_item, self.channel_number)
                            timeout_seconds = 30.0  # 30 second timeout for first chunk
                            start_time = asyncio.get_event_loop().time()
                            
                            async for chunk in chunk_iter:
                                if first_chunk_time is None:
                                    first_chunk_time = asyncio.get_event_loop().time() - start_time
                                    logger.info(f"ON_DEMAND: First chunk received for item {idx} after {first_chunk_time:.2f}s")
                                
                                yield chunk
                                items_yielded += 1
                                item_yielded = True
                                consecutive_failures = 0  # Reset failure counter on success
                                
                                # Reset timeout after first chunk (item is working)
                                timeout_seconds = None
                            
                            if not item_yielded:
                                logger.warning(f"ON_DEMAND: Item {idx} completed without yielding any chunks for channel {self.channel_number}")
                                consecutive_failures += 1
                            else:
                                logger.info(f"ON_DEMAND: Successfully streamed item {idx} for channel {self.channel_number} ({items_yielded} chunks total so far)")
                                
                                # Save playback position after each item completes successfully
                                # Save next item index (idx + 1) so we resume from the next item
                                next_index = idx + 1
                                if next_index >= len(schedule_items):
                                    next_index = 0  # Loop back to beginning
                                
                                self._save_playback_position(
                                    db_session,
                                    self.channel_id,
                                    channel.number,
                                    next_index,
                                    media_item.id
                                )
                                
                        except asyncio.TimeoutError:
                            consecutive_failures += 1
                            logger.error(f"ON_DEMAND: Timeout waiting for first chunk from item {idx} ({media_item.title[:60]}) for channel {self.channel_number} - skipping to next item")
                        except Exception as e:
                            consecutive_failures += 1
                            logger.error(f"Error streaming ON_DEMAND item {idx} ({media_item.title[:60]}) for channel {self.channel_number}: {e}", exc_info=True)
                            # If we've had too many consecutive failures, log a warning but continue
                            if consecutive_failures >= max_consecutive_failures:
                                logger.error(f"ON_DEMAND: {consecutive_failures} consecutive failures for channel {self.channel_number}, but continuing...")
                    
                    # If we've yielded at least some data, reset failure counter for next cycle
                    if items_yielded > 0:
                        consecutive_failures = 0
                    
                    # Mark first loop as complete
                    is_first_loop = False
                    
                    # Loop back to beginning for continuous playback
                    logger.info(f"ON_DEMAND: Completed playout cycle for channel {self.channel_number}, looping back to beginning (total items yielded: {items_yielded})")
            except Exception as e:
                logger.error(f"Error in ON_DEMAND stream for channel {self.channel_number}: {e}", exc_info=True)
                raise
            finally:
                if db_session:
                    try:
                        db_session.close()
                    except Exception:
                        pass
            # Note: The async generator will naturally exit when the while True loop ends
            # No explicit return needed - async generators automatically stop when function completes
        
        # CONTINUOUS mode: use broadcast queue (existing logic)
        # Create a queue for this client (larger size to prevent blocking)
        client_queue = asyncio.Queue(maxsize=50)  # Increased from 10 to 50 to prevent queue full errors
        
        async with self._lock:
            # If stream is not running, start it
            if not self._is_running:
                # #region agent log
                try:
                    import json
                    with open('/Users/roto1231/Documents/XCode Projects/StreamTV/.cursor/debug.log', 'a') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"channel_manager.py:357","message":"CONTINUOUS: Starting stream (not running)","data":{"channel_number":self.channel_number},"timestamp":int(__import__('time').time()*1000)})+'\n')
                except: pass
                # #endregion
                await self.start()
                # Wait for stream to initialize
                await asyncio.sleep(0.5)
            else:
                # #region agent log
                try:
                    import json
                    with open('/Users/roto1231/Documents/XCode Projects/StreamTV/.cursor/debug.log', 'a') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"channel_manager.py:365","message":"CONTINUOUS: Stream already running","data":{"channel_number":self.channel_number,"existing_clients":self._client_count},"timestamp":int(__import__('time').time()*1000)})+'\n')
                except: pass
                # #endregion
            
            # Register this client
            self._client_queues.append(client_queue)
            self._client_count += 1
            
            # #region agent log
            try:
                import json
                with open('/Users/roto1231/Documents/XCode Projects/StreamTV/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"channel_manager.py:373","message":"CONTINUOUS: Client queue registered","data":{"channel_number":self.channel_number,"total_clients":self._client_count,"queue_size":client_queue.qsize()},"timestamp":int(__import__('time').time()*1000)})+'\n')
            except: pass
            # #endregion
            
            # Continuous: calculate position in playout timeline using system time (ErsatzTV-style)
            current_position = await self._get_current_position()
            now = datetime.utcnow()
            elapsed_hours = int(current_position['elapsed_seconds'] // 3600)
            elapsed_minutes = int((current_position['elapsed_seconds'] % 3600) // 60)
            logger.info(f"Client connected to channel {self.channel_number} (CONTINUOUS mode) at {now} - position {current_position['item_index']}/{len(self._schedule_items)} ({elapsed_hours}h {elapsed_minutes}m from midnight, total clients: {self._client_count})")
            
            # Pre-warm current item if no buffer exists and stream is running
            # This ensures fast response even when connecting mid-stream
            if self._is_running and len(self._schedule_items) > 0:
                current_idx = current_position.get('item_index', 0)
                if current_idx < len(self._schedule_items):
                    current_item = self._schedule_items[current_idx]
                    current_media = current_item.get('media_item')
                    if current_media and not ('PLACEHOLDER' in current_media.url.upper()):
                        # Check if buffer already exists
                        buffer_info = await self._prewarmer.get_buffer_info(self.channel_number)
                        if not buffer_info.get("has_buffer"):
                            # Start pre-warming current item in background
                            try:
                                # Ensure streamer exists (it should be created in _run_continuous_stream)
                                if not self.streamer:
                                    # Create a temporary streamer for pre-warming
                                    db_temp = self.db_session_factory()
                                    try:
                                        from streamtv.streaming.mpegts_streamer import MPEGTSStreamer
                                        temp_streamer = MPEGTSStreamer(db_temp)
                                    except Exception as e:
                                        logger.warning(f"Could not create streamer for pre-warming: {e}")
                                        temp_streamer = None
                                else:
                                    temp_streamer = self.streamer
                                    db_temp = None
                                
                                if temp_streamer:
                                    async def current_item_generator():
                                        try:
                                            async for chunk in temp_streamer._stream_single_item(current_media, self.channel_number, skip_codec_detection=True):
                                                yield chunk
                                        finally:
                                            if db_temp:
                                                try:
                                                    db_temp.close()
                                                except:
                                                    pass
                                    
                                    asyncio.create_task(
                                        self._prewarmer.prewarm_stream(self.channel_number, current_item_generator())
                                    )
                                    logger.info(f"Started pre-warming current item (index {current_idx}) for channel {self.channel_number} on client connect")
                                    # #region agent log
                                    try:
                                        import json
                                        with open('/Users/roto1231/Documents/XCode Projects/StreamTV/.cursor/debug.log', 'a') as f:
                                            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"I","location":"channel_manager.py:420","message":"CONTINUOUS: Pre-warming current item on client connect","data":{"channel_number":self.channel_number,"item_index":current_idx,"item_title":current_media.title[:60] if current_media else None,"has_streamer":self.streamer is not None},"timestamp":int(__import__('time').time()*1000)})+'\n')
                                    except: pass
                                    # #endregion
                                else:
                                    logger.warning(f"Could not pre-warm current item for channel {self.channel_number}: streamer not available")
                                    # #region agent log
                                    try:
                                        import json
                                        with open('/Users/roto1231/Documents/XCode Projects/StreamTV/.cursor/debug.log', 'a') as f:
                                            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"I","location":"channel_manager.py:435","message":"CONTINUOUS: Pre-warming skipped (streamer unavailable)","data":{"channel_number":self.channel_number,"item_index":current_idx,"has_streamer":self.streamer is not None},"timestamp":int(__import__('time').time()*1000)})+'\n')
                                    except: pass
                                    # #endregion
                            except Exception as e:
                                logger.warning(f"Failed to pre-warm current item for channel {self.channel_number}: {e}", exc_info=True)
                                # #region agent log
                                try:
                                    import json
                                    import traceback
                                    with open('/Users/roto1231/Documents/XCode Projects/StreamTV/.cursor/debug.log', 'a') as f:
                                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"I","location":"channel_manager.py:443","message":"CONTINUOUS: Pre-warming error","data":{"channel_number":self.channel_number,"item_index":current_idx,"error_type":type(e).__name__,"error_message":str(e),"traceback":traceback.format_exc()[:300]},"timestamp":int(__import__('time').time()*1000)})+'\n')
                                except: pass
                                # #endregion
                        else:
                            # #region agent log
                            try:
                                import json
                                with open('/Users/roto1231/Documents/XCode Projects/StreamTV/.cursor/debug.log', 'a') as f:
                                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"I","location":"channel_manager.py:450","message":"CONTINUOUS: Pre-warming skipped (buffer already exists)","data":{"channel_number":self.channel_number,"item_index":current_idx,"buffer_chunks":buffer_info.get("chunk_count",0)},"timestamp":int(__import__('time').time()*1000)})+'\n')
                            except: pass
                            # #endregion
                else:
                    # #region agent log
                    try:
                        import json
                        with open('/Users/roto1231/Documents/XCode Projects/StreamTV/.cursor/debug.log', 'a') as f:
                            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"I","location":"channel_manager.py:457","message":"CONTINUOUS: Pre-warming skipped (invalid index)","data":{"channel_number":self.channel_number,"item_index":current_idx,"schedule_items_count":len(self._schedule_items)},"timestamp":int(__import__('time').time()*1000)})+'\n')
                    except: pass
                    # #endregion
        
        # Stream from the broadcast queue (with pre-warmed buffer support)
        chunk_count = 0
        timeout_count = 0
        
        # Wait a short time for initial chunks to arrive in the queue
        # This handles the case where client connects right as a new item is starting
        initial_wait_time = 0.1  # 100ms
        initial_chunks_received = False
        
        # Try to get first chunk quickly (with short timeout)
        # #region agent log
        try:
            import json
            import time
            with open('/Users/roto1231/Documents/XCode Projects/StreamTV/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"J","location":"channel_manager.py:496","message":"CONTINUOUS: Attempting immediate chunk check","data":{"channel_number":self.channel_number,"wait_time_ms":initial_wait_time*1000,"queue_size":client_queue.qsize()},"timestamp":int(time.time()*1000)})+'\n')
        except: pass
        # #endregion
        
        try:
            first_chunk = await asyncio.wait_for(client_queue.get(), timeout=initial_wait_time)
            chunk_count += 1
            initial_chunks_received = True
            
            # #region agent log
            try:
                import json
                import time
                with open('/Users/roto1231/Documents/XCode Projects/StreamTV/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"J","location":"channel_manager.py:505","message":"CONTINUOUS: First chunk received immediately","data":{"channel_number":self.channel_number,"chunk_count":chunk_count,"chunk_size":len(first_chunk),"wait_time_ms":initial_wait_time*1000},"timestamp":int(time.time()*1000)})+'\n')
            except: pass
            # #endregion
            
            yield first_chunk
        except asyncio.TimeoutError:
            # No chunks available immediately - check for pre-warmed buffer
            # #region agent log
            try:
                import json
                import time
                with open('/Users/roto1231/Documents/XCode Projects/StreamTV/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"J","location":"channel_manager.py:518","message":"CONTINUOUS: No immediate chunks, checking pre-warmed buffer","data":{"channel_number":self.channel_number,"queue_size":client_queue.qsize()},"timestamp":int(time.time()*1000)})+'\n')
            except: pass
            # #endregion
        
        # Check if we have pre-warmed chunks and serve them first (if we didn't get immediate chunks)
        if not initial_chunks_received:
            # Give pre-warming a moment to start filling (if it just started)
            # Check buffer, and if empty, wait a short time for pre-warming to fill
            buffer_info = await self._prewarmer.get_buffer_info(self.channel_number)
            if not buffer_info.get("has_buffer") or buffer_info.get("chunk_count", 0) == 0:
                # Wait a short time for pre-warming to start filling (if it's running)
                await asyncio.sleep(0.2)  # 200ms - enough for FFmpeg to start and produce first chunk
                buffer_info = await self._prewarmer.get_buffer_info(self.channel_number)
            
            if buffer_info.get("has_buffer") and buffer_info.get("chunk_count", 0) > 0:
                # Serve pre-warmed chunks immediately
                logger.info(f"Serving {buffer_info['chunk_count']} pre-warmed chunks for channel {self.channel_number}")
            # #region agent log
            try:
                import json
                with open('/Users/roto1231/Documents/XCode Projects/StreamTV/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"H","location":"channel_manager.py:405","message":"CONTINUOUS: Serving pre-warmed chunks","data":{"channel_number":self.channel_number,"chunk_count":buffer_info['chunk_count'],"buffer_size":buffer_info['buffer_size_bytes']},"timestamp":int(__import__('time').time()*1000)})+'\n')
            except: pass
            # #endregion
            
            # Get buffered chunks (this will clear the buffer)
            async def get_live_stream():
                while self._is_running:
                    try:
                        chunk = await asyncio.wait_for(client_queue.get(), timeout=2.0)
                        yield chunk
                    except asyncio.TimeoutError:
                        if not self._is_running:
                            break
                        continue
            
            # Use pre-warmer's get_buffered_stream to serve buffer first, then live
            async for chunk in self._prewarmer.get_buffered_stream(self.channel_number, get_live_stream()):
                chunk_count += 1
                if chunk_count <= 10:
                    # #region agent log
                    try:
                        import json
                        with open('/Users/roto1231/Documents/XCode Projects/StreamTV/.cursor/debug.log', 'a') as f:
                            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"H","location":"channel_manager.py:425","message":"CONTINUOUS: Chunk yielded (pre-warmed or live)","data":{"channel_number":self.channel_number,"chunk_count":chunk_count,"chunk_size":len(chunk)},"timestamp":int(__import__('time').time()*1000)})+'\n')
                    except: pass
                    # #endregion
                yield chunk
            return  # Exit after buffered stream completes
        
        # Fallback: stream from queue normally (no pre-warm buffer)
        try:
            while self._is_running:
                try:
                    chunk = await asyncio.wait_for(client_queue.get(), timeout=2.0)
                    chunk_count += 1
                    timeout_count = 0  # Reset timeout counter on successful chunk
                    
                    # Log first few chunks to verify stream is working
                    if chunk_count <= 10:
                        # #region agent log
                        try:
                            import json
                            with open('/Users/roto1231/Documents/XCode Projects/StreamTV/.cursor/debug.log', 'a') as f:
                                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"channel_manager.py:445","message":"CONTINUOUS: Chunk received from client queue (no pre-warm)","data":{"channel_number":self.channel_number,"chunk_count":chunk_count,"chunk_size":len(chunk),"queue_size":client_queue.qsize()},"timestamp":int(__import__('time').time()*1000)})+'\n')
                        except: pass
                        # #endregion
                    
                    yield chunk
                except asyncio.TimeoutError:
                    timeout_count += 1
                    # #region agent log
                    try:
                        import json
                        with open('/Users/roto1231/Documents/XCode Projects/StreamTV/.cursor/debug.log', 'a') as f:
                            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"channel_manager.py:390","message":"CONTINUOUS: Timeout waiting for chunk","data":{"channel_number":self.channel_number,"timeout_count":timeout_count,"is_running":self._is_running,"queue_size":client_queue.qsize()},"timestamp":int(__import__('time').time()*1000)})+'\n')
                    except: pass
                    # #endregion
                    
                    # Check if still running
                    if not self._is_running:
                        logger.debug(f"CONTINUOUS: Stream stopped for channel {self.channel_number}, exiting loop")
                        break
                    
                    # If too many timeouts, log warning but continue
                    if timeout_count >= 5:
                        logger.warning(f"CONTINUOUS: Multiple timeouts ({timeout_count}) for channel {self.channel_number}, but continuing...")
                        timeout_count = 0  # Reset to avoid spam
                    
                    # Continue waiting
                    continue
        finally:
            # Client disconnected
            async with self._lock:
                if client_queue in self._client_queues:
                    self._client_queues.remove(client_queue)
                self._client_count -= 1
                logger.debug(f"Client disconnected from channel {self.channel_number} (remaining clients: {self._client_count}, chunks sent: {chunk_count})")
                
                # #region agent log
                try:
                    import json
                    with open('/Users/roto1231/Documents/XCode Projects/StreamTV/.cursor/debug.log', 'a') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"channel_manager.py:410","message":"CONTINUOUS: Client disconnected","data":{"channel_number":self.channel_number,"chunk_count":chunk_count,"remaining_clients":self._client_count},"timestamp":int(__import__('time').time()*1000)})+'\n')
                except: pass
                # #endregion
    
    def _save_playback_position(
        self,
        db_session: Session,
        channel_id: int,
        channel_number: str,
        item_index: int,
        media_id: Optional[int] = None
    ):
        """Save playback position for on-demand channel"""
        try:
            playback_pos = db_session.query(ChannelPlaybackPosition).filter(
                ChannelPlaybackPosition.channel_id == channel_id
            ).first()
            
            if not playback_pos:
                playback_pos = ChannelPlaybackPosition(
                    channel_id=channel_id,
                    channel_number=channel_number
                )
                db_session.add(playback_pos)
            
            playback_pos.last_item_index = item_index
            playback_pos.last_item_media_id = media_id
            playback_pos.last_played_at = datetime.utcnow()
            playback_pos.total_items_watched = max(playback_pos.total_items_watched, item_index)
            
            db_session.commit()
            logger.debug(f"ON_DEMAND: Saved playback position for channel {channel_number}: item {item_index}")
        except Exception as e:
            logger.error(f"Error saving playback position for channel {channel_number}: {e}", exc_info=True)
            db_session.rollback()
    
    async def _get_current_position(self) -> Dict:
        """Calculate current position in playout timeline based on saved playout start time"""
        async with self._timeline_lock:
            if not self._schedule_items:
                return {'item_index': 0, 'elapsed_seconds': 0}
            
            # Calculate total cycle duration (sum of all item durations)
            total_duration = 0
            for item in self._schedule_items:
                media_item = item.get('media_item')
                if not media_item:
                    continue
                # Prefer cached duration to avoid touching detached ORM instances
                cached = item.get('cached_duration')
                if cached:
                    duration_val = cached
                else:
                    duration_val = getattr(media_item, "__dict__", {}).get("duration") or 1800
                total_duration += duration_val
            
            if total_duration <= 0:
                return {'item_index': 0, 'elapsed_seconds': 0}
            
            # Use saved playout_start_time instead of today's midnight
            # This allows resuming from where we left off after server restart
            now = datetime.utcnow()
            if not self._playout_start_time:
                # Fallback: use now as start time (shouldn't happen if start() was called)
                self._playout_start_time = now
            
            # Calculate elapsed time from when playout started (not midnight)
            elapsed = (now - self._playout_start_time).total_seconds()
            
            # Calculate position within the current cycle using modulo
            # This ensures channels loop correctly while maintaining position across restarts
            cycle_position = elapsed % total_duration if total_duration > 0 else 0
            
            # Calculate which item should be playing based on position within cycle
            current_time = 0
            item_index = 0
            
            for idx, schedule_item in enumerate(self._schedule_items):
                media_item = schedule_item.get('media_item')
                if not media_item:
                    continue
                cached = schedule_item.get('cached_duration')
                duration = cached or getattr(media_item, "__dict__", {}).get("duration") or 1800  # Default 30 minutes
                
                if current_time + duration > cycle_position:
                    # We're in this item
                    item_index = idx
                    break
                
                current_time += duration
                item_index = idx + 1
            
            # Ensure we're within bounds (should be handled by modulo, but double-check)
            if item_index >= len(self._schedule_items):
                item_index = 0
                current_time = 0
            
            return {
                'item_index': item_index,
                'elapsed_seconds': elapsed,
                'current_item_start': current_time,
                'cycle_position': cycle_position,
                'total_duration': total_duration,
                'playout_start_time': self._playout_start_time
            }
    
    async def _run_continuous_stream(self):
        """Run the continuous stream in the background and broadcast to all clients"""
        logger.info(f"ChannelStream._run_continuous_stream() - Starting for channel {self.channel_number}")
        # Create a database session for this stream
        db = self.db_session_factory()
        try:
            # Load schedule items and initialize timeline
            logger.info(f"ChannelStream._run_continuous_stream() - Loading schedule parser/engine for channel {self.channel_number}")
            from streamtv.scheduling.parser import ScheduleParser
            from streamtv.scheduling.engine import ScheduleEngine
            
            logger.info(f"ChannelStream._run_continuous_stream() - Finding schedule file for channel {self.channel_number}")
            schedule_file = ScheduleParser.find_schedule_file(self.channel_number)
            if schedule_file:
                logger.info(f"ChannelStream._run_continuous_stream() - Parsing schedule file for channel {self.channel_number}: {schedule_file}")
                parsed_schedule = ScheduleParser.parse_file(schedule_file, schedule_file.parent)
                logger.info(f"ChannelStream._run_continuous_stream() - Schedule parsed, creating ScheduleEngine for channel {self.channel_number}")
                schedule_engine = ScheduleEngine(db)
                # Query channel from current session
                channel = db.query(Channel).filter(Channel.id == self.channel_id).first()
                if channel:
                    logger.info(f"ChannelStream._run_continuous_stream() - Generating playlist from schedule for channel {self.channel_number}...")
                    self._schedule_items = schedule_engine.generate_playlist_from_schedule(
                        channel, parsed_schedule, max_items=1000
                    )
                    logger.info(f"ChannelStream._run_continuous_stream() - Generated {len(self._schedule_items)} schedule items for channel {self.channel_number}")
                    for itm in self._schedule_items:
                        media = itm.get("media_item")
                        if media:
                            itm["cached_duration"] = getattr(media, "__dict__", {}).get("duration") or 1800
                else:
                    logger.error(f"Channel {self.channel_number} not found in database")
                    self._schedule_items = []
            else:
                # Fallback to playlist
                from streamtv.database import Playlist, PlaylistItem
                playlists = db.query(Playlist).filter(Playlist.channel_id == self.channel_id).all()
                if playlists:
                    playlist = playlists[0]
                    items = db.query(PlaylistItem).filter(
                        PlaylistItem.playlist_id == playlist.id
                    ).order_by(PlaylistItem.order).all()
                    
                    for item in items:
                        media_item = db.query(MediaItem).filter(
                            MediaItem.id == item.media_item_id
                        ).first()
                        if media_item:
                            self._schedule_items.append({
                                'media_item': media_item,
                                'custom_title': None,
                                'filler_kind': None,
                                'start_time': None,
                                'cached_duration': getattr(media_item, "__dict__", {}).get("duration") or 1800
                            })
            
            if not self._schedule_items:
                logger.error(f"No schedule items for channel {self.channel_number}")
                self._is_running = False
                return
            
            # Ensure playout_start_time is set (should be set in start(), but double-check)
            async with self._timeline_lock:
                if not self._playout_start_time:
                    # Try to load from database one more time
                    try:
                        from streamtv.database.models import ChannelPlaybackPosition
                        playback_pos = db.query(ChannelPlaybackPosition).filter(
                            ChannelPlaybackPosition.channel_id == self.channel_id
                        ).first()
                        
                        if playback_pos and playback_pos.playout_start_time:
                            self._playout_start_time = playback_pos.playout_start_time
                            logger.info(f"Loaded playout start time for channel {self.channel_number} from database: {self._playout_start_time}")
                        else:
                            # Fallback: use now
                            self._playout_start_time = datetime.utcnow()
                            logger.info(f"Using current time as playout start for channel {self.channel_number}: {self._playout_start_time}")
                    except Exception as e:
                        logger.error(f"Error loading playout start time in _run_continuous_stream: {e}")
                        self._playout_start_time = datetime.utcnow()
                
                self._current_item_start_time = datetime.utcnow()
            
            logger.info(f"Streaming playout for channel {self.channel_number} with {len(self._schedule_items)} items (resuming from saved position)")
            
            # Create streamer with this session
            self.streamer = MPEGTSStreamer(db)
            
            # Get playout mode from channel (query from DB to get latest value)
            channel = db.query(Channel).filter(Channel.id == self.channel_id).first()
            playout_mode_raw = getattr(channel, 'playout_mode', PlayoutMode.CONTINUOUS) if channel else PlayoutMode.CONTINUOUS
            # Convert string to enum if needed (handle database string values)
            if isinstance(playout_mode_raw, str):
                normalized = playout_mode_raw.lower()
                for mode in PlayoutMode:
                    if mode.value.lower() == normalized:
                        playout_mode = mode
                        break
                else:
                    # Fallback: try to match by name (uppercase)
                    try:
                        playout_mode = PlayoutMode[playout_mode_raw.upper()]
                    except KeyError:
                        playout_mode = PlayoutMode.CONTINUOUS
            else:
                playout_mode = playout_mode_raw
            
            # Calculate starting position based on playout mode
            if playout_mode == PlayoutMode.ON_DEMAND:
                # On-demand channels don't run continuous broadcast - each client gets independent stream
                logger.info(f"Channel {self.channel_number} using ON-DEMAND mode - no continuous broadcast (clients get independent streams)")
                # Don't start continuous stream for ON_DEMAND - clients will get independent streams
                return
            
            # CONTINUOUS mode: calculate position based on ErsatzTV-style cycle (daily reset at midnight UTC)
            start_position = await self._get_current_position()
            start_index = start_position['item_index']
            elapsed = start_position['elapsed_seconds']
            cycle_position = start_position.get('cycle_position', 0)
            total_duration = start_position.get('total_duration', 0)
            
            # Log timeline info for debugging
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            cycle_hours = int(cycle_position // 3600)
            cycle_minutes = int((cycle_position % 3600) // 60)
            playout_start = start_position.get('playout_start_time', self._playout_start_time)
            logger.info(f"Channel {self.channel_number} CONTINUOUS timeline: {hours}h {minutes}m elapsed from playout start ({playout_start}), position in cycle: {cycle_hours}h {cycle_minutes}m, starting from item {start_index}/{len(self._schedule_items)} (cycle duration: {total_duration/3600:.1f}h)")
            
            # Stream continuously, starting from calculated position
            # After first loop, always start from 0
            first_loop = True
            first_item_prewarmed = False
            
            while self._is_running:
                # Determine starting index for this loop
                loop_start = start_index if first_loop else 0
                
                # Pre-warm first item for fast client response (only on first loop, before streaming)
                if first_loop and not first_item_prewarmed and loop_start < len(self._schedule_items):
                    first_item = self._schedule_items[loop_start]
                    first_media = first_item.get('media_item')
                    if first_media and not ('PLACEHOLDER' in first_media.url.upper()):
                        try:
                            # Create a generator for the first item (skip codec detection for speed)
                            async def first_item_generator():
                                async for chunk in self.streamer._stream_single_item(first_media, self.channel_number, skip_codec_detection=True):
                                    yield chunk
                            
                            # Start pre-warming in background (don't await - let it run)
                            asyncio.create_task(
                                self._prewarmer.prewarm_stream(self.channel_number, first_item_generator())
                            )
                            logger.info(f"Started pre-warming first item for channel {self.channel_number} (item {loop_start})")
                            first_item_prewarmed = True
                        except Exception as e:
                            logger.warning(f"Failed to pre-warm first item for channel {self.channel_number}: {e}")
                
                # Loop through schedule items starting from calculated position
                for idx in range(loop_start, len(self._schedule_items)):
                    if not self._is_running:
                        break
                    
                    schedule_item = self._schedule_items[idx]
                    media_item = schedule_item.get('media_item')
                    if not media_item:
                        continue
                    
                    # Skip placeholder URLs
                    if 'PLACEHOLDER' in media_item.url.upper():
                        continue
                    
                    # Skip very short videos
                    if media_item.duration and media_item.duration < 5:
                        continue
                    
                    # Channel 80: Only use H.264/.mp4 files to avoid AVI demuxing errors
                    if self.channel_number == "80":
                        # Check if URL contains .mp4 in the path (before query parameters or fragments)
                        url_lower = media_item.url.lower()
                        # Get the path portion (before ? or #)
                        url_path = url_lower.split('?')[0].split('#')[0]
                        if '.mp4' not in url_path:
                            logger.debug(f"Skipping non-MP4 file for channel 80: {media_item.title} ({media_item.url[:80]})")
                            continue
                    
                    # Check again if still running before starting new item (prevent race condition during shutdown)
                    if not self._is_running:
                        break
                    
                    # Update timeline position using system time
                    async with self._timeline_lock:
                        self._current_item_index = idx
                        self._current_item_start_time = datetime.utcnow()  # Use system time
                    
                    # Pre-warm current item for fast client response (start before streaming)
                    # This ensures buffer is ready when clients connect mid-item
                    buffer_info = await self._prewarmer.get_buffer_info(self.channel_number)
                    if not buffer_info.get("has_buffer") or buffer_info.get("chunk_count", 0) < 5:
                        # Start pre-warming current item in background
                        try:
                            async def current_item_generator():
                                async for chunk in self.streamer._stream_single_item(media_item, self.channel_number, skip_codec_detection=True):
                                    yield chunk
                            
                            # Start pre-warming in background (don't await - let it run)
                            asyncio.create_task(
                                self._prewarmer.prewarm_stream(self.channel_number, current_item_generator())
                            )
                            logger.debug(f"Started pre-warming current item (index {idx}) for channel {self.channel_number}")
                            # #region agent log
                            try:
                                import json
                                import time
                                with open('/Users/roto1231/Documents/XCode Projects/StreamTV/.cursor/debug.log', 'a') as f:
                                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"L","location":"channel_manager.py:930","message":"CONTINUOUS: Pre-warming current item before streaming","data":{"channel_number":self.channel_number,"item_index":idx,"item_title":media_item.title[:60] if media_item else None},"timestamp":int(time.time()*1000)})+'\n')
                            except: pass
                            # #endregion
                        except Exception as e:
                            logger.warning(f"Failed to pre-warm current item for channel {self.channel_number}: {e}")
                    
                    # Periodically save position (every 5 items or every 30 minutes)
                    if idx % 5 == 0 or (self._current_item_start_time and (datetime.utcnow() - self._current_item_start_time).total_seconds() > 1800):
                        try:
                            from streamtv.database.models import ChannelPlaybackPosition
                            playback_pos = db.query(ChannelPlaybackPosition).filter(
                                ChannelPlaybackPosition.channel_id == self.channel_id
                            ).first()
                            
                            if not playback_pos:
                                playback_pos = ChannelPlaybackPosition(
                                    channel_id=self.channel_id,
                                    channel_number=self.channel_number,
                                    playout_start_time=self._playout_start_time,
                                    last_item_index=idx,
                                    last_position_update=datetime.utcnow()
                                )
                                db.add(playback_pos)
                            else:
                                playback_pos.playout_start_time = self._playout_start_time
                                playback_pos.last_item_index = idx
                                playback_pos.last_position_update = datetime.utcnow()
                            db.commit()
                            logger.debug(f"Periodically saved position for channel {self.channel_number}: item {idx}")
                        except Exception as e:
                            logger.debug(f"Error periodically saving position for channel {self.channel_number}: {e}")
                            db.rollback()
                    
                    try:
                        # Stream this item (skip codec detection for first item if pre-warming)
                        skip_codec = (first_loop and idx == loop_start and not first_item_prewarmed)
                        chunk_count_for_item = 0
                        async for chunk in self.streamer._stream_single_item(media_item, self.channel_number, skip_codec_detection=skip_codec):
                            if not self._is_running:
                                break
                            
                            chunk_count_for_item += 1
                            
                            # Log first chunk of item
                            if chunk_count_for_item == 1:
                                # #region agent log
                                try:
                                    import json
                                    with open('/Users/roto1231/Documents/XCode Projects/StreamTV/.cursor/debug.log', 'a') as f:
                                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"G","location":"channel_manager.py:737","message":"CONTINUOUS: First chunk from item","data":{"channel_number":self.channel_number,"item_index":idx,"item_title":media_item.title[:60] if media_item else None,"client_count":len(self._client_queues)},"timestamp":int(__import__('time').time()*1000)})+'\n')
                                except: pass
                                # #endregion
                            
                            # Broadcast to all connected clients
                            disconnected_clients = []
                            clients_received = 0
                            for queue in self._client_queues:
                                try:
                                    queue.put_nowait(chunk)
                                    clients_received += 1
                                except asyncio.QueueFull:
                                    disconnected_clients.append(queue)
                                except Exception as e:
                                    logger.debug(f"Error putting chunk in client queue: {e}")
                                    disconnected_clients.append(queue)
                            
                            # Log if no clients received chunk
                            if chunk_count_for_item <= 5 and clients_received == 0:
                                # #region agent log
                                try:
                                    import json
                                    with open('/Users/roto1231/Documents/XCode Projects/StreamTV/.cursor/debug.log', 'a') as f:
                                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"G","location":"channel_manager.py:757","message":"CONTINUOUS: Chunk broadcasted but no clients","data":{"channel_number":self.channel_number,"item_index":idx,"chunk_count":chunk_count_for_item,"client_queues_count":len(self._client_queues)},"timestamp":int(__import__('time').time()*1000)})+'\n')
                                except: pass
                                # #endregion
                            
                            # Remove disconnected clients
                            for queue in disconnected_clients:
                                if queue in self._client_queues:
                                    self._client_queues.remove(queue)
                    
                    except asyncio.CancelledError:
                        raise
                    except Exception as e:
                        logger.error(f"Error streaming item {idx} ({media_item.title[:60] if media_item else 'unknown'}) for channel {self.channel_number}: {e}")
                        # Skip this item and continue to next - don't let one bad file stop the stream
                        # Log warning but keep streaming
                        logger.warning(f"Skipping item {idx} due to error, continuing to next item")
                        continue
                
                # After first loop, always start from beginning
                first_loop = False
                # Loop back to beginning (continuous playout)
                # Don't reset timeline - keep it continuous so clients join at current position
                logger.debug(f"Channel {self.channel_number} completed playout cycle, looping back to start (timeline continues)")
                
        except asyncio.CancelledError:
            logger.info(f"Continuous stream cancelled for channel {self.channel_number}")
        except Exception as e:
            logger.error(f"Error in continuous stream for channel {self.channel_number}: {e}", exc_info=True)
        finally:
            self._is_running = False
            # Close database session
            try:
                db.close()
            except Exception:
                pass


class ChannelManager:
    """Manages continuous streams for all channels (ErsatzTV-style)"""
    
    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory
        self._streams: Dict[str, ChannelStream] = {}
        self._lock = asyncio.Lock()
        self._running = False
    
    async def start_all_channels(self):
        """Start continuous streaming for all enabled channels"""
        logger.info("ChannelManager.start_all_channels() - Acquiring lock...")
        async with self._lock:
            if self._running:
                logger.info("ChannelManager.start_all_channels() - Already running, returning")
                return
            
            self._running = True
            logger.info("ChannelManager.start_all_channels() - Lock acquired, querying channels...")
            
            # Get all enabled channels
            db = self.db_session_factory()
            try:
                channels = db.query(Channel).filter(Channel.enabled == True).all()
            except (LookupError, ValueError, Exception) as query_error:
                # Handle SQLAlchemy enum validation errors with fallback to raw SQL
                error_str = str(query_error)
                error_type = type(query_error).__name__
                # Check if this is an enum validation error
                if isinstance(query_error, LookupError) or "is not among the defined enum values" in error_str or any(enum_name in error_str.lower() for enum_name in ["playoutmode", "streamingmode", "channeltranscodemode", "transcodemode", "subtitlemode", "streamselectormode"]):
                    logger.warning(f"SQLAlchemy enum validation error when querying channels for startup: {query_error}")
                    logger.info("Attempting to query channels using raw SQL to work around enum validation issue...")
                    # Query using raw SQL to avoid enum validation, then construct Channel objects
                    from sqlalchemy import text
                    # Import enum maps for fast O(1) lookup (same as @reconstructor uses)
                    from ..database.models import (
                        PlayoutMode, StreamingMode, ChannelTranscodeMode, ChannelSubtitleMode,
                        ChannelStreamSelectorMode, ChannelMusicVideoCreditsMode, ChannelSongVideoMode,
                        ChannelIdleBehavior, ChannelPlayoutSource
                    )
                    # Access the pre-built enum maps from models.py module
                    import streamtv.database.models as models_module
                    _PLAYOUT_MODE_MAP = getattr(models_module, '_PLAYOUT_MODE_MAP', {})
                    _STREAMING_MODE_MAP = getattr(models_module, '_STREAMING_MODE_MAP', {})
                    _TRANSCODE_MODE_MAP = getattr(models_module, '_TRANSCODE_MODE_MAP', {})
                    
                    raw_result = db.execute(text("""
                        SELECT * FROM channels WHERE enabled = 1
                    """)).fetchall()
                    channels = []
                    for row in raw_result:
                        channel = Channel()
                        # Copy all attributes from row, converting enum strings to enums using optimized dict lookups
                        for key, value in row._mapping.items():
                            if value is None:
                                setattr(channel, key, None)
                            elif key == 'playout_mode' and isinstance(value, str):
                                normalized = value.lower()
                                enum_val = _PLAYOUT_MODE_MAP.get(normalized)
                                if not enum_val:
                                    try:
                                        enum_val = PlayoutMode[value.upper().replace('-', '_')]
                                    except KeyError:
                                        enum_val = PlayoutMode.CONTINUOUS
                                setattr(channel, key, enum_val)
                            elif key == 'streaming_mode' and isinstance(value, str):
                                normalized = value.lower()
                                enum_val = _STREAMING_MODE_MAP.get(normalized)
                                if not enum_val:
                                    try:
                                        enum_val = StreamingMode[value.upper().replace('-', '_')]
                                    except KeyError:
                                        enum_val = StreamingMode.TRANSPORT_STREAM_HYBRID
                                setattr(channel, key, enum_val)
                            elif key == 'transcode_mode' and isinstance(value, str):
                                normalized = value.lower()
                                enum_val = _TRANSCODE_MODE_MAP.get(normalized)
                                if not enum_val:
                                    try:
                                        enum_val = ChannelTranscodeMode[value.upper().replace('-', '_')]
                                    except KeyError:
                                        enum_val = ChannelTranscodeMode.ON_DEMAND
                                setattr(channel, key, enum_val)
                            elif key in ['subtitle_mode', 'stream_selector_mode', 'music_video_credits_mode', 
                                         'song_video_mode', 'idle_behavior', 'playout_source'] and isinstance(value, str):
                                # These will be handled by @reconstructor, just set as string for now
                                setattr(channel, key, value)
                            else:
                                setattr(channel, key, value)
                        channels.append(channel)
                    logger.info(f"Loaded {len(channels)} channels using raw SQL query for startup")
                else:
                    # Re-raise if it's a different error
                    raise
                
                logger.info(f"ChannelManager.start_all_channels() - Found {len(channels)} enabled channels")
                # Convert playout_mode strings to enums for each channel (handle database string values)
                # This handles cases where the database has string values that need conversion to enum
                for channel in channels:
                    if hasattr(channel, 'playout_mode') and isinstance(channel.playout_mode, str):
                        try:
                            normalized = channel.playout_mode.lower()
                            for mode in PlayoutMode:
                                if mode.value.lower() == normalized:
                                    channel.playout_mode = mode
                                    break
                            else:
                                # Fallback: try to match by name (uppercase)
                                channel.playout_mode = PlayoutMode[channel.playout_mode.upper()]
                        except (KeyError, AttributeError):
                            channel.playout_mode = PlayoutMode.CONTINUOUS
                for idx, channel in enumerate(channels):
                    logger.info(f"ChannelManager.start_all_channels() - Starting channel {idx+1}/{len(channels)}: {channel.number} ({channel.name})")
                    await self._start_channel(channel)
                    logger.info(f"ChannelManager.start_all_channels() - Completed starting channel {channel.number}")
                logger.info(f"Started continuous streaming for {len(channels)} channels")
            finally:
                db.close()
                logger.info("ChannelManager.start_all_channels() - Database session closed")
    
    async def stop_all_channels(self):
        """Stop all continuous streams"""
        async with self._lock:
            self._running = False
            stream_list = list(self._streams.values())
            for stream in stream_list:
                await stream.stop()
            self._streams.clear()
            logger.info("Stopped all continuous streams")
    
    async def get_channel_stream(self, channel_number: str) -> AsyncIterator[bytes]:
        """Get the continuous stream for a channel (async generator)"""
        # Query channel
        db = self.db_session_factory()
        try:
            channel = db.query(Channel).filter(
                Channel.number == channel_number,
                Channel.enabled == True
            ).first()
            
            if not channel:
                raise ValueError(f"Channel {channel_number} not found or not enabled")
            
            async with self._lock:
                if channel_number not in self._streams:
                    await self._start_channel(channel)
                
                stream = self._streams[channel_number]
        finally:
            db.close()
        
        # Yield from the stream's async iterator
        async for chunk in stream.get_stream():
            yield chunk
    
    async def _start_channel(self, channel: Channel):
        """Start continuous streaming for a channel"""
        if channel.number in self._streams:
            logger.info(f"_start_channel() - Channel {channel.number} already started, skipping")
            return
        
        logger.info(f"_start_channel() - Creating ChannelStream for channel {channel.number}...")
        stream = ChannelStream(channel, self.db_session_factory)
        logger.info(f"_start_channel() - ChannelStream created, adding to streams dict...")
        self._streams[channel.number] = stream
        logger.info(f"_start_channel() - Calling stream.start() for channel {channel.number}...")
        await stream.start()
        logger.info(f"_start_channel() - stream.start() completed for channel {channel.number}")
    
    async def stop_channel(self, channel_number: str):
        """Stop continuous streaming for a specific channel"""
        async with self._lock:
            if channel_number in self._streams:
                stream = self._streams[channel_number]
                await stream.stop()
                del self._streams[channel_number]

