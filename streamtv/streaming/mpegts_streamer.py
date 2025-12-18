"""MPEG-TS streaming using FFmpeg for HDHomeRun compatibility"""

import asyncio
import logging
import subprocess
import shutil
from typing import AsyncIterator, Optional, List, Dict, Any
from pathlib import Path
import json
from datetime import datetime

from streamtv.config import config
from streamtv.database import Channel, MediaItem
from streamtv.scheduling.parser import ScheduleParser
from streamtv.scheduling.engine import ScheduleEngine
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# #region agent log
DEBUG_LOG_PATH = "/Users/roto1231/Documents/XCode Projects/StreamTV/.cursor/debug.log"
def _debug_log(location: str, message: str, data: dict, hypothesis_id: str):
    """Write debug log entry"""
    try:
        with open(DEBUG_LOG_PATH, "a") as f:
            log_entry = {
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": hypothesis_id,
                "location": location,
                "message": message,
                "data": data,
                "timestamp": int(datetime.now().timestamp() * 1000)
            }
            f.write(json.dumps(log_entry) + "\n")
    except Exception:
        pass
# #endregion


class MPEGTSStreamer:
    """Streams videos as continuous MPEG-TS using FFmpeg"""
    
    def __init__(self, db: Session):
        self.db = db
        self._processes: Dict[str, subprocess.Popen] = {}
        self._ffmpeg_path = self._find_ffmpeg()
        self._stream_manager = None  # Will be set when needed
    
    def _find_ffmpeg(self) -> str:
        """Find FFmpeg executable"""
        # Check config first
        if config.ffmpeg.ffmpeg_path and Path(config.ffmpeg.ffmpeg_path).exists():
            return config.ffmpeg.ffmpeg_path
        
        # Try common locations
        for path in ["/usr/local/bin/ffmpeg", "/usr/bin/ffmpeg", "ffmpeg"]:
            if shutil.which(path):
                return path
        
        raise RuntimeError("FFmpeg not found. Please install FFmpeg or configure ffmpeg_path in config.yaml")
    
    async def create_continuous_stream(
        self,
        channel: Channel,
        request_url: str
    ) -> AsyncIterator[bytes]:
        """Create a continuous MPEG-TS stream from channel's schedule/playlist"""
        # Get all media items from schedule
        schedule_items = await self._get_schedule_items(channel)
        
        if not schedule_items:
            raise ValueError(f"No content available for channel {channel.number}")
        
        logger.info(f"Starting MPEG-TS stream for channel {channel.number} with {len(schedule_items)} items")
        
        # Pre-fetch the first video's stream URL to start immediately
        from .stream_manager import StreamManager
        stream_manager = StreamManager()
        
        # Filter out invalid items upfront
        valid_items = []
        for schedule_item in schedule_items:
            media_item = schedule_item.get('media_item')
            if not media_item:
                continue
            
            # Skip placeholder URLs
            if 'PLACEHOLDER' in media_item.url.upper() or 'placeholder' in media_item.url.lower():
                continue
            
            # Skip very short videos
            if media_item.duration and media_item.duration < 5:
                continue
            
            # Channel 80: Only use H.264/.mp4 files to avoid AVI demuxing errors
            if channel.number == "80":
                # Check if URL contains .mp4 in the path (before query parameters or fragments)
                url_lower = media_item.url.lower()
                # Get the path portion (before ? or #)
                url_path = url_lower.split('?')[0].split('#')[0]
                if '.mp4' not in url_path:
                    logger.debug(f"Skipping non-MP4 file for channel 80: {media_item.title} ({media_item.url[:80]})")
                    continue
            
            valid_items.append(schedule_item)
        
        if not valid_items:
            raise ValueError(f"No valid content available for channel {channel.number}")
        
        # Pre-fetch first video's stream URL for immediate start
        first_item = valid_items[0]
        first_media = first_item.get('media_item')
        try:
            # Pass channel name to help PBS adapter select correct stream
            channel_name = channel.name if hasattr(channel, 'name') else None
            first_stream_url = await stream_manager.get_stream_url(first_media.url, channel_name=channel_name)
            if first_stream_url:
                logger.info(f"Pre-fetched stream URL for first video: {first_media.title}")
        except Exception as e:
            logger.warning(f"Could not pre-fetch first video URL: {e}")
            first_stream_url = None
        
        # Stream videos in a continuous loop
        consecutive_errors = 0
        max_consecutive_errors = 10
        
        while True:
            for idx, schedule_item in enumerate(valid_items):
                media_item = schedule_item.get('media_item')
                if not media_item:
                    continue
                
                try:
                    # Use pre-fetched URL for first video, otherwise fetch it
                    if idx == 0 and first_stream_url:
                        stream_url = first_stream_url
                        # Reset for next loop
                        first_stream_url = None
                    else:
                        # Pass channel name to help PBS adapter select correct stream
                        channel_name = channel.name if hasattr(channel, 'name') else None
                        stream_url = await stream_manager.get_stream_url(media_item.url, channel_name=channel_name)
                    
                    if not stream_url:
                        logger.warning(f"Could not get stream URL for {media_item.title}, skipping")
                        continue
                    
                    logger.info(f"Streaming {media_item.title} for channel {channel.number}")
                    
                    # Transcode to MPEG-TS using FFmpeg
                    chunk_count = 0
                    try:
                        # Start streaming immediately - no delays
                        async for chunk in self._transcode_to_mpegts(stream_url):
                            chunk_count += 1
                            yield chunk
                            
                            # Log first chunk to confirm stream started
                            if chunk_count == 1:
                                logger.debug(f"First chunk sent for {media_item.title}, stream active")
                                
                    except RuntimeError as e:
                        # FFmpeg-specific errors
                        logger.error(f"FFmpeg error for {media_item.title}: {e}")
                        raise
                    except asyncio.CancelledError:
                        # Client disconnected, stop streaming
                        logger.info(f"Stream cancelled for {media_item.title}")
                        raise
                    
                    # Reset error counter on success
                    consecutive_errors = 0
                    if chunk_count == 0:
                        logger.warning(f"No data received for {media_item.title}, skipping")
                        continue
                    
                    logger.debug(f"Successfully streamed {chunk_count} chunks for {media_item.title}, moving to next video")
                        
                except Exception as e:
                    consecutive_errors += 1
                    error_msg = str(e)
                    logger.error(f"Error streaming {media_item.title} (error {consecutive_errors}/{max_consecutive_errors}): {error_msg}")
                    
                    # If too many consecutive errors, log and continue
                    if consecutive_errors >= max_consecutive_errors:
                        logger.error(f"Too many consecutive errors ({consecutive_errors}), but continuing stream...")
                        consecutive_errors = 0  # Reset to allow recovery
                    
                    # Continue to next video
                    continue
    
    async def _get_schedule_items(self, channel: Channel) -> List[Dict[str, Any]]:
        """Get schedule items for a channel"""
        schedule_file = ScheduleParser.find_schedule_file(channel.number)
        schedule_items = []
        
        if schedule_file:
            try:
                parsed_schedule = ScheduleParser.parse_file(schedule_file, schedule_file.parent)
                schedule_engine = ScheduleEngine(self.db)
                schedule_items = schedule_engine.generate_playlist_from_schedule(
                    channel, parsed_schedule, max_items=1000
                )
            except Exception as e:
                logger.warning(f"Failed to load schedule: {e}")
        
        # Fallback to playlist
        if not schedule_items:
            from streamtv.database import Playlist, PlaylistItem
            playlists = self.db.query(Playlist).filter(Playlist.channel_id == channel.id).all()
            if playlists:
                playlist = playlists[0]
                items = self.db.query(PlaylistItem).filter(
                    PlaylistItem.playlist_id == playlist.id
                ).order_by(PlaylistItem.order).all()
                
                for item in items:
                    media_item = self.db.query(MediaItem).filter(
                        MediaItem.id == item.media_item_id
                    ).first()
                    if media_item:
                        schedule_items.append({
                            'media_item': media_item,
                            'custom_title': None,
                            'filler_kind': None,
                            'start_time': None
                        })
        
        return schedule_items
    
    async def _stream_single_item(
        self,
        media_item: MediaItem,
        channel_number: str
    ) -> AsyncIterator[bytes]:
        """Stream a single media item as MPEG-TS"""
        # Skip placeholder URLs
        if 'PLACEHOLDER' in media_item.url.upper():
            logger.warning(f"Skipping placeholder URL for {media_item.title}")
            return
        
        # Skip very short videos
        if media_item.duration and media_item.duration < 5:
            logger.debug(f"Skipping very short video {media_item.title} ({media_item.duration}s)")
            return
        
        try:
            # Get stream URL
            from .stream_manager import StreamManager
            stream_manager = StreamManager()
            self._stream_manager = stream_manager  # Store for cookie access
            # Pass channel name to help PBS adapter select correct stream
            # Note: channel_number is passed, but we need channel name - try to get it from channel
            channel_name = None
            if hasattr(self, 'db') and self.db:
                from streamtv.database import Channel
                channel_obj = self.db.query(Channel).filter(Channel.number == channel_number).first()
                if channel_obj:
                    channel_name = channel_obj.name
            stream_url = await stream_manager.get_stream_url(media_item.url, channel_name=channel_name)
            
            if not stream_url:
                logger.warning(f"Could not get stream URL for {media_item.title}, skipping")
                return
            
            logger.info(f"Streaming {media_item.title} for channel {channel_number}")
            
            # Check for cancellation before starting transcoding (prevent race condition during shutdown)
            try:
                await asyncio.sleep(0)
            except asyncio.CancelledError:
                logger.info(f"Stream cancelled before transcoding {media_item.title}")
                raise
            
            # Detect input codec for smart transcoding
            input_codec_info = await self._detect_input_codec(stream_url)
            
            # Check for cancellation again after codec detection (may take time)
            try:
                await asyncio.sleep(0)
            except asyncio.CancelledError:
                logger.info(f"Stream cancelled after codec detection for {media_item.title}")
                raise
            
            # Transcode to MPEG-TS (with smart codec detection)
            async for chunk in self._transcode_to_mpegts(stream_url, input_codec_info):
                yield chunk
                
        except Exception as e:
            logger.error(f"Error streaming {media_item.title}: {e}")
            raise
    
    async def _detect_input_codec(self, stream_url: str) -> Dict[str, Any]:
        """Detect input video/audio codecs using ffprobe"""
        try:
            # Use ffprobe to detect codecs
            ffprobe_cmd = [
                config.ffmpeg.ffprobe_path or "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_streams",
                "-select_streams", "v:0,a:0",  # First video and audio stream
                stream_url
            ]
            
            # Add timeout for HTTP streams
            if stream_url.startswith("http"):
                ffprobe_cmd.insert(1, "-timeout")
                ffprobe_cmd.insert(2, "10000000")  # 10 seconds
            
            process = await asyncio.create_subprocess_exec(
                *ffprobe_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=15.0)
            
            if process.returncode == 0 and stdout:
                import json
                probe_data = json.loads(stdout.decode())
                
                codec_info = {
                    'video_codec': None,
                    'audio_codec': None,
                    'can_copy_video': False,
                    'can_copy_audio': False
                }
                
                for stream in probe_data.get('streams', []):
                    codec_type = stream.get('codec_type')
                    codec_name = stream.get('codec_name', '').lower()
                    
                    if codec_type == 'video':
                        codec_info['video_codec'] = codec_name
                        # Can copy if already H.264
                        codec_info['can_copy_video'] = codec_name in ['h264', 'avc']
                    
                    elif codec_type == 'audio':
                        codec_info['audio_codec'] = codec_name
                        # Can copy if already AAC or MP2/MP3
                        codec_info['can_copy_audio'] = codec_name in ['aac', 'mp3', 'mp2']
                
                logger.debug(f"Detected codecs: video={codec_info['video_codec']}, audio={codec_info['audio_codec']}")
                return codec_info
            
        except asyncio.TimeoutError:
            logger.warning("Codec detection timed out, will use transcoding")
        except Exception as e:
            logger.warning(f"Could not detect input codec: {e}, will use transcoding")
        
        # Default: assume we need to transcode
        return {
            'video_codec': 'unknown',
            'audio_codec': 'unknown',
            'can_copy_video': False,
            'can_copy_audio': False
        }
    
    async def _transcode_to_mpegts(
        self,
        stream_url: str,
        codec_info: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[bytes]:
        """Transcode a video stream to MPEG-TS using FFmpeg"""
        # Check for cancellation before creating FFmpeg process (prevent race condition during shutdown)
        try:
            # This will raise CancelledError if the task is already cancelled
            await asyncio.sleep(0)
        except asyncio.CancelledError:
            raise
        
        # Build FFmpeg command (with smart codec detection)
        ffmpeg_cmd = self._build_ffmpeg_command(stream_url, codec_info)
        
        # #region agent log
        _debug_log("mpegts_streamer.py:_transcode_to_mpegts:before_start", "Starting FFmpeg", {
            "stream_url_has_token": 'X-Plex-Token' in stream_url if stream_url else False,
            "stream_url_base": stream_url.split('?')[0][:100] if stream_url else None,
            "cmd_length": len(ffmpeg_cmd),
            "is_plex_url": '/library/metadata/' in stream_url if stream_url else False
        }, "B")
        # #endregion
        
        logger.debug(f"FFmpeg command: {' '.join(ffmpeg_cmd)}")
        
        # Start FFmpeg process
        process = None
        stderr_task = None
        try:
            process = await asyncio.create_subprocess_exec(
                *ffmpeg_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # #region agent log
            _debug_log("mpegts_streamer.py:_transcode_to_mpegts:process_created", "FFmpeg process created", {
                "pid": process.pid if process else None
            }, "B")
            # #endregion
            
            # Check for cancellation immediately after creating subprocess (catch late cancellations)
            try:
                await asyncio.sleep(0)
            except asyncio.CancelledError:
                # Terminate the process immediately if we were cancelled
                if process.returncode is None:
                    process.terminate()
                    try:
                        await asyncio.wait_for(process.wait(), timeout=2.0)
                    except asyncio.TimeoutError:
                        if process.returncode is None:
                            process.kill()
                            await process.wait()
                raise
            
            # Monitor stderr in background
            stderr_lines = []
            fatal_error_detected = False
            async def monitor_stderr():
                nonlocal fatal_error_detected
                try:
                    while True:
                        line = await process.stderr.readline()
                        if not line:
                            break
                        line_str = line.decode().strip()
                        stderr_lines.append(line_str)
                        
                        # #region agent log
                        if '401' in line_str or 'Unauthorized' in line_str or '403' in line_str:
                            _debug_log("mpegts_streamer.py:_transcode_to_mpegts:auth_error", "FFmpeg auth error detected", {
                                "error_line": line_str[:200],
                                "line_number": len(stderr_lines)
                            }, "D")
                        if 'error opening input' in line_str.lower() or 'error=8' in line_str:
                            _debug_log("mpegts_streamer.py:_transcode_to_mpegts:input_error", "FFmpeg input error", {
                                "error_line": line_str[:200],
                                "line_number": len(stderr_lines)
                            }, "B")
                        # #endregion
                        # Log errors and warnings
                        # Downgrade expected hardware acceleration errors for unsupported codecs to warnings
                        if 'failed setup for format videotoolbox' in line_str.lower() or \
                           'hwaccel initialisation returned error' in line_str.lower():
                            logger.warning(f"FFmpeg: {line_str} (Expected - will fall back to software encoding)")
                        # Downgrade H.264 macroblock decoding errors to debug - common with DRM-protected streams
                        # FFmpeg continues decoding despite these errors, they're not fatal
                        elif 'error while decoding mb' in line_str.lower() and 'h264' in line_str.lower():
                            # These are non-fatal decoding errors, common with DRM-protected or corrupted streams
                            # FFmpeg handles them gracefully and continues decoding
                            logger.debug(f"FFmpeg: {line_str} (Non-fatal H.264 decoding error - continuing)")
                        # Downgrade HLS reconnection messages to debug - these are normal for live streams
                        # FFmpeg automatically reconnects when segments end, this is expected behavior
                        elif 'will reconnect' in line_str.lower() and 'error=end of file' in line_str.lower():
                            # This is FFmpeg's automatic reconnection mechanism working as intended
                            # Live HLS streams have segments that end, triggering reconnection attempts
                            logger.debug(f"FFmpeg: {line_str} (Normal HLS reconnection - continuing)")
                        # Downgrade Plex HTTP reconnection messages - these can happen with network issues
                        # FFmpeg will automatically retry, so we don't need to log every attempt
                        elif 'will reconnect' in line_str.lower() and 'error=input/output error' in line_str.lower():
                            # Network I/O errors can happen, FFmpeg will retry automatically
                            # Only log if it's happening repeatedly (we'll track this)
                            logger.debug(f"FFmpeg: {line_str} (HTTP I/O error - FFmpeg will retry)")
                        # Detect fatal demuxing errors (especially for AVI files)
                        elif 'error during demuxing' in line_str.lower() or \
                             ('demuxing' in line_str.lower() and 'input/output error' in line_str.lower()):
                            fatal_error_detected = True
                            logger.error(f"FFmpeg: {line_str} (Fatal demuxing error - stream will fail)")
                        elif 'error' in line_str.lower() or 'failed' in line_str.lower():
                            logger.error(f"FFmpeg: {line_str}")
                        elif 'warning' in line_str.lower():
                            logger.warning(f"FFmpeg: {line_str}")
                except Exception as e:
                    logger.debug(f"Stderr monitoring ended: {e}")
            
            stderr_task = asyncio.create_task(monitor_stderr())
            
            # Wait a moment for FFmpeg to start and check for immediate failures
            await asyncio.sleep(0.5)
            if process.returncode is not None:
                # Process failed immediately
                await stderr_task
                error_msg = '\n'.join(stderr_lines[-10:])  # Last 10 lines
                
                # #region agent log
                _debug_log("mpegts_streamer.py:_transcode_to_mpegts:immediate_failure", "FFmpeg failed immediately", {
                    "exit_code": process.returncode,
                    "error_msg": error_msg[:500],
                    "stderr_line_count": len(stderr_lines),
                    "stream_url_has_token": 'X-Plex-Token' in stream_url if stream_url else False
                }, "B")
                # #endregion
                
                raise RuntimeError(f"FFmpeg failed immediately (exit code {process.returncode}): {error_msg}")
            
            # Stream output in chunks
            # Use longer timeout for first chunk to handle problematic files (especially AVI)
            # Some Archive.org AVI files need more time to start
            first_chunk_timeout = 15.0  # Wait up to 15 seconds for first chunk (increased for AVI files)
            first_chunk_received = False
            subsequent_timeout = 5.0  # Increased timeout for subsequent chunks to handle network issues
            
            while True:
                try:
                    if not first_chunk_received:
                        # Wait for first chunk with timeout - critical for immediate start
                        chunk = await asyncio.wait_for(process.stdout.read(8192), timeout=first_chunk_timeout)
                        first_chunk_received = True
                        logger.debug("First chunk received, stream started")
                    else:
                        # Use shorter timeout for subsequent chunks
                        chunk = await asyncio.wait_for(process.stdout.read(8192), timeout=subsequent_timeout)
                    
                    if not chunk:
                        # Check if process is still running
                        if process.returncode is not None:
                            # Process ended, check for errors
                            await stderr_task
                            if process.returncode != 0:
                                error_msg = '\n'.join(stderr_lines[-10:])
                                logger.warning(f"FFmpeg exited with code {process.returncode}: {error_msg}")
                            break
                        # Check for fatal errors detected in stderr
                        if fatal_error_detected:
                            await stderr_task
                            error_msg = '\n'.join(stderr_lines[-10:])
                            logger.error(f"FFmpeg fatal error detected: {error_msg}")
                            raise RuntimeError(f"FFmpeg fatal demuxing error: {error_msg}")
                        # Wait a bit and try again
                        await asyncio.sleep(0.1)
                        continue
                    yield chunk
                    
                except asyncio.TimeoutError:
                    if not first_chunk_received:
                        # No data received within timeout - check if process is still running
                        if process.returncode is None:
                            # Process still running but no data - might be a problematic file
                            # Give it one more chance with extended timeout
                            try:
                                chunk = await asyncio.wait_for(process.stdout.read(8192), timeout=10.0)
                                if chunk:
                                    first_chunk_received = True
                                    yield chunk
                                    continue
                            except asyncio.TimeoutError:
                                # Still no data after extended timeout - file is likely problematic
                                await stderr_task
                                error_msg = '\n'.join(stderr_lines[-10:])
                                raise RuntimeError(f"FFmpeg timeout - no data received after extended wait: {error_msg}")
                        else:
                            # Process ended - get error message
                            await stderr_task
                            error_msg = '\n'.join(stderr_lines[-10:])
                            raise RuntimeError(f"FFmpeg process ended (exit code {process.returncode}): {error_msg}")
                    else:
                        # Subsequent read timeout - might be end of file or network issue
                        # Check if process is still running
                        if process.returncode is not None:
                            # Process ended, likely end of file
                            break
                        # Check for fatal errors detected in stderr
                        if fatal_error_detected:
                            await stderr_task
                            error_msg = '\n'.join(stderr_lines[-10:])
                            logger.error(f"FFmpeg fatal error detected during timeout: {error_msg}")
                            raise RuntimeError(f"FFmpeg fatal demuxing error: {error_msg}")
                        # Process still running but no data - continue waiting
                        continue
                
        except asyncio.CancelledError:
            logger.info(f"FFmpeg transcoding cancelled for {stream_url[:80]}")
            if stderr_task and not stderr_task.done():
                stderr_task.cancel()
                try:
                    await stderr_task
                except asyncio.CancelledError:
                    pass
            raise
        except Exception as e:
            logger.error(f"Error in FFmpeg transcoding: {e}")
            if stderr_task and not stderr_task.done():
                await stderr_task
            # Re-raise to be handled by caller
            raise
        finally:
            # Clean up process
            if process:
                try:
                    if process.returncode is None:
                        process.terminate()
                        try:
                            await asyncio.wait_for(process.wait(), timeout=5.0)
                        except asyncio.TimeoutError:
                            if process.returncode is None:
                                process.kill()
                                await process.wait()
                except Exception as e:
                    error_msg = str(e) if str(e) else type(e).__name__
                    logger.warning(f"Error cleaning up FFmpeg process: {error_msg}")
    
    def _build_ffmpeg_command(self, input_url: str, codec_info: Optional[Dict[str, Any]] = None) -> List[str]:
        """Build FFmpeg command for MPEG-TS transcoding with smart codec selection"""
        # #region agent log
        _debug_log("mpegts_streamer.py:_build_ffmpeg_command:entry", "Building FFmpeg command", {
            "input_url_has_token": 'X-Plex-Token' in input_url if input_url else False,
            "input_url_base": input_url.split('?')[0][:100] if input_url else None,
            "is_plex": '/library/metadata/' in input_url if input_url else False,
            "url_length": len(input_url) if input_url else 0
        }, "B")
        # #endregion
        
        cmd = [self._ffmpeg_path]
        
        # Determine if we can use copy mode (no transcoding)
        can_copy_video = codec_info and codec_info.get('can_copy_video', False)
        can_copy_audio = codec_info and codec_info.get('can_copy_audio', False)
        video_codec = codec_info.get('video_codec', 'unknown') if codec_info else 'unknown'
        
        # VideoToolbox only supports H.264 decoding - disable for MPEG-4/AVI
        mpeg4_codecs = ['mpeg4', 'msmpeg4v3', 'msmpeg4v2', 'msmpeg4']
        is_mpeg4 = video_codec in mpeg4_codecs
        # Disable hardware acceleration for MPEG-4 and when codec is unknown (safer default)
        use_hwaccel = config.ffmpeg.hwaccel and not can_copy_video and not is_mpeg4 and video_codec != 'unknown'
        
        if can_copy_video and can_copy_audio:
            logger.info(f"Smart copy mode: Input already H.264/AAC - zero transcoding! 🚀")
        elif can_copy_video:
            logger.info(f"Smart copy mode: Video already H.264 - copying video, transcoding audio")
        elif can_copy_audio:
            logger.info(f"Smart copy mode: Audio compatible - transcoding video, copying audio")
        else:
            if is_mpeg4:
                logger.info(f"Software transcoding: MPEG-4/AVI detected ({video_codec}) - hwaccel not supported")
            elif use_hwaccel:
                logger.info(f"Hardware-accelerated transcoding: Using {config.ffmpeg.hwaccel} 🔥")
            else:
                logger.info(f"Software transcoding: Converting to H.264/AAC")
        
        # Global options (must come first)
        log_level = config.ffmpeg.log_level or "info"
        cmd.extend(["-loglevel", log_level])
        
        # Input options (must come BEFORE -i)
        # Hardware acceleration (must be before input) - only if transcoding video and NOT MPEG-4
        # Explicitly disable hardware acceleration for MPEG-4 to prevent FFmpeg from trying it
        if is_mpeg4:
            # Explicitly disable hardware acceleration for MPEG-4 (VideoToolbox doesn't support it)
            cmd.extend(["-hwaccel", "none"])
            logger.debug(f"Hardware acceleration explicitly disabled for MPEG-4 codec: {video_codec}")
        elif use_hwaccel and not can_copy_video:
            cmd.extend([
                "-hwaccel", config.ffmpeg.hwaccel,
                "-hwaccel_output_format", config.ffmpeg.hwaccel,  # Output format same as hwaccel
            ])
            if config.ffmpeg.hwaccel_device:
                cmd.extend(["-hwaccel_device", config.ffmpeg.hwaccel_device])
            # Auto-fallback: don't fail if hwaccel doesn't work
            # This allows unsupported codecs to fall back to software decoding
            logger.debug(f"Hardware acceleration enabled for {video_codec}")
        
        # For HTTP inputs, add timeout and user-agent (before -i)
        if input_url.startswith("http"):
            # Use longer timeouts and more aggressive reconnection for Archive.org
            is_archive_org = 'archive.org' in input_url
            is_plex = '/library/metadata/' in input_url or 'plex' in input_url.lower()
            
            if is_archive_org:
                timeout = "60000000"  # 60s for Archive.org
                reconnect_delay = "10"  # Longer delay for Archive.org
            elif is_plex:
                timeout = "60000000"  # 60s for Plex (longer timeout for large files)
                reconnect_delay = "3"  # Shorter delay for Plex (faster reconnection)
            else:
                timeout = "30000000"  # 30s for others
                reconnect_delay = "5"  # Standard delay
            
            cmd.extend([
                "-timeout", timeout,  # Timeout in microseconds
                "-user_agent", "Mozilla/5.0 (compatible; StreamTV/1.0)",
                "-reconnect", "1",
                "-reconnect_at_eof", "1",
                "-reconnect_streamed", "1",
                "-reconnect_delay_max", reconnect_delay,  # Max delay between reconnection attempts
                "-multiple_requests", "1",  # Allow multiple HTTP requests for seeking
            ])
            
            # Plex-specific options for better connection stability
            if is_plex:
                # Note: Plex supports HTTP range requests, so we can seek
                # FFmpeg will handle reconnection automatically with the reconnect options above
                logger.debug("Using Plex-optimized HTTP settings (extended timeout, faster reconnect)")
        
            # Add Archive.org authentication cookies if available
            if is_archive_org and self._stream_manager and self._stream_manager.archive_org_adapter:
                adapter = self._stream_manager.archive_org_adapter
                if adapter.use_authentication and adapter._session_cookies:
                    # Build cookie header for FFmpeg
                    cookie_pairs = [f"{name}={value}" for name, value in adapter._session_cookies.items()]
                    cookie_header = "; ".join(cookie_pairs)
                    cmd.extend(["-headers", f"Cookie: {cookie_header}"])
                    logger.debug("Added Archive.org authentication cookies to FFmpeg")
            
            if is_archive_org:
                logger.debug("Using extended timeouts for Archive.org stream")
        
        # Input URL with flags
        # Check if this is a DRM-protected HLS stream (common with PBS live streams)
        is_drm_hls = '.m3u8' in input_url.lower() and ('drm' in input_url.lower() or 'lls.pbs.org' in input_url.lower())
        
        # #region agent log
        _debug_log("mpegts_streamer.py:_build_ffmpeg_command:before_input", "Before adding input URL to FFmpeg", {
            "input_url_has_token": 'X-Plex-Token' in input_url if input_url else False,
            "input_url_length": len(input_url) if input_url else 0,
            "is_plex": '/library/metadata/' in input_url if input_url else False,
            "is_mpeg4": is_mpeg4,
            "is_drm_hls": is_drm_hls
        }, "B")
        # #endregion
        
        # Use more lenient settings for MPEG-4/AVI files (often have timing issues)
        if is_mpeg4:
            cmd.extend([
                "-fflags", "+genpts+discardcorrupt+igndts",  # Generate PTS, discard corrupt, ignore DTS
                "-err_detect", "ignore_err",  # Ignore errors in MPEG-4 streams
                "-flags", "+low_delay",  # Low latency mode
                "-strict", "experimental",  # Allow experimental codecs
                "-probesize", "5000000",  # Probe 5MB for MPEG-4 (more complex format)
                "-analyzeduration", "5000000",  # Analyze 5 seconds for MPEG-4
                "-i", input_url,
            ])
            
            # #region agent log
            _debug_log("mpegts_streamer.py:_build_ffmpeg_command:input_added", "Input URL added to FFmpeg command", {
                "cmd_has_url": input_url in cmd,
                "url_position": cmd.index(input_url) if input_url in cmd else -1
            }, "B")
            # #endregion
            logger.debug("Using lenient input settings for MPEG-4/AVI")
        elif is_drm_hls:
            # DRM-protected HLS streams may have decoding errors - be more resilient
            cmd.extend([
                "-fflags", "+genpts+discardcorrupt+fastseek",  # Generate PTS, discard corrupt, fast seek
                "-err_detect", "ignore_err",  # Ignore non-fatal decoding errors (common with DRM)
                "-flags", "+low_delay",  # Low latency mode
                "-strict", "experimental",  # Allow experimental codecs
                "-probesize", "1000000",  # Probe 1MB for faster start
                "-analyzeduration", "2000000",  # Analyze 2 seconds for faster start
                "-i", input_url,
            ])
            logger.debug("Using error-resilient settings for DRM-protected HLS stream")
            
            # #region agent log
            _debug_log("mpegts_streamer.py:_build_ffmpeg_command:input_added_drm", "Input URL added (DRM HLS)", {
                "cmd_has_url": input_url in cmd,
                "url_position": cmd.index(input_url) if input_url in cmd else -1
            }, "B")
            # #endregion
        else:
            cmd.extend([
                "-fflags", "+genpts+discardcorrupt+fastseek",  # Generate PTS, discard corrupt, fast seek
                "-flags", "+low_delay",  # Low latency mode
                "-strict", "experimental",  # Allow experimental codecs
                "-probesize", "1000000",  # Probe 1MB for faster start
                "-analyzeduration", "2000000",  # Analyze 2 seconds for faster start
                "-i", input_url,
            ])
            
            # #region agent log
            _debug_log("mpegts_streamer.py:_build_ffmpeg_command:input_added_standard", "Input URL added (standard)", {
                "cmd_has_url": input_url in cmd,
                "url_position": cmd.index(input_url) if input_url in cmd else -1
            }, "B")
            # #endregion
        
        # Output options (come AFTER -i)
        # Threads (applies to encoding) - only if transcoding
        if config.ffmpeg.threads > 0 and not (can_copy_video and can_copy_audio):
            cmd.extend(["-threads", str(config.ffmpeg.threads)])
        
        # VIDEO CODEC SELECTION (Smart mode)
        if can_copy_video:
            # Input is already H.264 - copy directly (zero transcoding!)
            # Add bitstream filters to fix common H.264 issues (PPS errors, etc.)
            cmd.extend([
                "-c:v", "copy",
                "-bsf:v", "h264_mp4toannexb,dump_extra"  # Fix H.264 stream issues
            ])
            logger.debug("Video: Using copy mode with error correction (H.264 detected)")
        elif use_hwaccel:
            # Hardware-accelerated H.264 encoding (VideoToolbox on macOS)
            cmd.extend([
                "-c:v", "h264_videotoolbox",  # macOS hardware encoder
                "-b:v", "6M",  # Higher bitrate for better quality
                "-maxrate", "6M",
                "-bufsize", "12M",
                "-profile:v", "high",  # High profile for better compression
                "-realtime", "1",  # Real-time encoding priority
                "-pix_fmt", "yuv420p",  # Ensure compatibility
                "-bsf:v", "dump_extra"  # Add extra data to stream (fixes some decoder issues)
            ])
            logger.debug("Video: Using hardware-accelerated H.264 with error correction (VideoToolbox)")
        else:
            # Software H.264 encoding (fallback)
            # Use faster preset for MPEG-4/AVI files (already lower quality)
            preset = "ultrafast" if is_mpeg4 else "veryfast"
            cmd.extend([
                "-c:v", "libx264",  # Software H.264 encoder
                "-preset", preset,  # Faster preset for MPEG-4/AVI
                "-crf", "23",  # Quality (18-28, 23 = good balance)
                "-maxrate", "6M",
                "-bufsize", "12M",
                "-profile:v", "high",
                "-level", "4.1",
                "-pix_fmt", "yuv420p",
                "-g", "50",  # GOP size
                "-bsf:v", "dump_extra"  # Add extra data to stream
            ])
            logger.debug(f"Video: Using software H.264 with error correction (libx264, preset={preset})")
        
        # AUDIO CODEC SELECTION (Smart mode)
        if can_copy_audio:
            # Input audio is compatible (AAC/MP3/MP2) - copy directly
            cmd.extend(["-c:a", "copy"])
            logger.debug("Audio: Using copy mode (compatible codec detected)")
        else:
            # Transcode to AAC (Plex-native format)
            cmd.extend([
                "-c:a", "aac",
                "-b:a", "192k",
                "-ar", "48000",
                "-ac", "2",  # Stereo
            ])
            logger.debug("Audio: Transcoding to AAC")
        
        # Output format (MPEG-TS)
        # Use options to reduce buffering and start immediately
        cmd.extend([
            "-f", "mpegts",
            "-muxrate", "4M",  # Mux rate
            "-pcr_period", "20",  # PCR period for TS
            "-flush_packets", "1",  # Flush packets immediately
            "-fflags", "+flush_packets",  # Flush packets flag
            "-max_interleave_delta", "0",  # No interleaving delay
        ])
        
        # Extra flags from config
        if config.ffmpeg.extra_flags:
            import shlex
            cmd.extend(shlex.split(config.ffmpeg.extra_flags))
        
        # Output to stdout
        cmd.append("-")
        
        return cmd
    
    def cleanup(self, channel_number: str):
        """Clean up FFmpeg process for a channel"""
        if channel_number in self._processes:
            process = self._processes[channel_number]
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            del self._processes[channel_number]

