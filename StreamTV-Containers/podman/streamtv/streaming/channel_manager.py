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
            self._stream_task = asyncio.create_task(self._run_continuous_stream())
            logger.info(f"Started continuous stream for channel {self.channel_number} ({self.channel_name})")
    
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
            playout_mode = getattr(channel_check, 'playout_mode', PlayoutMode.CONTINUOUS) if channel_check else PlayoutMode.CONTINUOUS
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
        # Create a queue for this client
        client_queue = asyncio.Queue(maxsize=10)
        
        async with self._lock:
            # If stream is not running, start it
            if not self._is_running:
                await self.start()
                # Wait for stream to initialize
                await asyncio.sleep(0.5)
            
            # Register this client
            self._client_queues.append(client_queue)
            self._client_count += 1
            
            # Continuous: calculate position in playout timeline using system time (ErsatzTV-style)
            current_position = await self._get_current_position()
            now = datetime.utcnow()
            elapsed_hours = int(current_position['elapsed_seconds'] // 3600)
            elapsed_minutes = int((current_position['elapsed_seconds'] % 3600) // 60)
            logger.info(f"Client connected to channel {self.channel_number} (CONTINUOUS mode) at {now} - position {current_position['item_index']}/{len(self._schedule_items)} ({elapsed_hours}h {elapsed_minutes}m from midnight, total clients: {self._client_count})")
        
        # Stream from the broadcast queue
        try:
            while self._is_running:
                try:
                    chunk = await asyncio.wait_for(client_queue.get(), timeout=2.0)
                    yield chunk
                except asyncio.TimeoutError:
                    # Check if still running
                    if not self._is_running:
                        break
                    # Continue waiting
                    continue
        finally:
            # Client disconnected
            async with self._lock:
                if client_queue in self._client_queues:
                    self._client_queues.remove(client_queue)
                self._client_count -= 1
                logger.debug(f"Client disconnected from channel {self.channel_number} (remaining clients: {self._client_count})")
    
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
            total_duration = sum(
                (item.get('media_item', {}).duration or 1800)
                for item in self._schedule_items
                if item.get('media_item')
            )
            
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
                
                duration = media_item.duration or 1800  # Default 30 minutes
                
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
        # Create a database session for this stream
        db = self.db_session_factory()
        try:
            # Load schedule items and initialize timeline
            from streamtv.scheduling.parser import ScheduleParser
            from streamtv.scheduling.engine import ScheduleEngine
            
            schedule_file = ScheduleParser.find_schedule_file(self.channel_number)
            if schedule_file:
                parsed_schedule = ScheduleParser.parse_file(schedule_file, schedule_file.parent)
                schedule_engine = ScheduleEngine(db)
                # Query channel from current session
                channel = db.query(Channel).filter(Channel.id == self.channel_id).first()
                if channel:
                    self._schedule_items = schedule_engine.generate_playlist_from_schedule(
                        channel, parsed_schedule, max_items=1000
                    )
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
                                'start_time': None
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
            playout_mode = getattr(channel, 'playout_mode', PlayoutMode.CONTINUOUS) if channel else PlayoutMode.CONTINUOUS
            
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
            while self._is_running:
                # Determine starting index for this loop
                loop_start = start_index if first_loop else 0
                
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
                        # Stream this item
                        async for chunk in self.streamer._stream_single_item(media_item, self.channel_number):
                            if not self._is_running:
                                break
                            
                            # Broadcast to all connected clients
                            disconnected_clients = []
                            for queue in self._client_queues:
                                try:
                                    queue.put_nowait(chunk)
                                except asyncio.QueueFull:
                                    disconnected_clients.append(queue)
                                except Exception:
                                    disconnected_clients.append(queue)
                            
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
        async with self._lock:
            if self._running:
                return
            
            self._running = True
            
            # Get all enabled channels
            db = self.db_session_factory()
            try:
                channels = db.query(Channel).filter(Channel.enabled == True).all()
                for channel in channels:
                    await self._start_channel(channel)
                logger.info(f"Started continuous streaming for {len(channels)} channels")
            finally:
                db.close()
    
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
            return
        
        stream = ChannelStream(channel, self.db_session_factory)
        self._streams[channel.number] = stream
        await stream.start()
    
    async def stop_channel(self, channel_number: str):
        """Stop continuous streaming for a specific channel"""
        async with self._lock:
            if channel_number in self._streams:
                stream = self._streams[channel_number]
                await stream.stop()
                del self._streams[channel_number]

