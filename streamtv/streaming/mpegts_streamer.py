"""MPEG-TS streaming using FFmpeg for HDHomeRun compatibility"""

import asyncio
import logging
import platform
import subprocess
import shutil
import time
from typing import AsyncIterator, Optional, List, Dict, Any, Union
from pathlib import Path
from urllib.parse import unquote, urlparse
import json
from datetime import datetime

from streamtv.config import config
from streamtv.database import Channel, MediaItem
from streamtv.ffmpeg.constants import (
    AVCC_CONTAINER_HINTS,
    BSF_H264_DUMP_EXTRA,
    BSF_H264_MP4TOANNEXB,
    FFLAGS_NETWORK_STREAMING,
    INPUT_FLAG_REALTIME,
)
from streamtv.scheduling.parser import ScheduleParser
from streamtv.scheduling.engine import ScheduleEngine
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# #region agent log
_DEBUG_LOG_PATH = "/home/streamtv/XCode Projects/StreamTV/.cursor/debug-247576.log"


def _agent_dbg_log(
    hypothesis_id: str,
    location: str,
    message: str,
    data: Dict[str, Any],
    *,
    run_id: str = "post-fix",
) -> None:
    try:
        payload = {
            "sessionId": "247576",
            "runId": run_id,
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        with open(_DEBUG_LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, default=str) + "\n")
    except Exception:
        pass


# #endregion


class StreamURLExpiredError(RuntimeError):
    """Signed CDN URL expired mid-stream; caller should re-resolve and retry."""


def youtube_expiry_reresolve_budget(duration_seconds: Optional[int]) -> int:
    """Mid-stream yt-dlp refreshes allowed for one YouTube item.

    Short music VODs (~3–5 min) previously got budget=1 (duration//240), so a
    single mid-stream 403 ended the item and continuous playout restarted it
    from t=0. Floor at 4; scale by TTL for long items.
    """
    from ..ffmpeg.constants import YOUTUBE_URL_TTL_VOD_SECONDS

    if not duration_seconds or duration_seconds <= 0:
        return 4
    return max(4, duration_seconds // YOUTUBE_URL_TTL_VOD_SECONDS)


class MPEGTSStreamer:
    """Streams videos as continuous MPEG-TS using FFmpeg"""
    
    def __init__(self, db: Session):
        self.db = db
        self._processes: Dict[str, subprocess.Popen] = {}
        self._ffmpeg_path = self._find_ffmpeg()
        self._stream_manager = None  # Will be set when needed
        self._channel_profile: Optional[str] = None  # Legacy profile
        self._ffmpeg_profile: Optional['FFmpegProfile'] = None  # New profile-based system
        self._watermark: Optional['Watermark'] = None  # Channel watermark
    
    def _find_ffmpeg(self) -> str:
        """Find FFmpeg executable"""
        configured = config.ffmpeg.ffmpeg_path
        configured_exists = bool(configured and Path(configured).exists())
        # Check config first
        if configured_exists:
            return configured
        
        # Try common locations
        for path in ["/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg", "/usr/bin/ffmpeg", "ffmpeg"]:
            resolved = shutil.which(path) if path == "ffmpeg" else (path if Path(path).exists() else None)
            if resolved:
                return resolved
        
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
            first_stream_url = await stream_manager.get_stream_url(
                first_media.url,
                source=first_media.source,
                channel_name=channel_name,
            )
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
                        stream_url = await stream_manager.get_stream_url(
                            media_item.url,
                            source=media_item.source,
                            channel_name=channel_name,
                        )
                    
                    if not stream_url:
                        logger.warning(f"Could not get stream URL for {media_item.title}, skipping")
                        continue
                    
                    logger.info(f"Streaming {media_item.title} for channel {channel.number}")
                    
                    # Load FFmpeg profile and watermark from channel
                    try:
                        # Legacy profile support
                        self._channel_profile = getattr(channel, 'transcode_profile', None)
                        
                        # New profile-based system
                        if hasattr(channel, 'ffmpeg_profile_id') and channel.ffmpeg_profile_id:
                            from ..database.models import FFmpegProfile
                            self._ffmpeg_profile = self.db.query(FFmpegProfile).filter(
                                FFmpegProfile.id == channel.ffmpeg_profile_id
                            ).first()
                        else:
                            self._ffmpeg_profile = None
                        
                        # Load watermark
                        if hasattr(channel, 'watermark_id') and channel.watermark_id:
                            from ..database.models import Watermark
                            self._watermark = self.db.query(Watermark).filter(
                                Watermark.id == channel.watermark_id
                            ).first()
                        else:
                            self._watermark = None
                    except Exception as e:
                        logger.warning(f"Error loading channel profile/watermark: {e}")
                        self._channel_profile = None
                        self._ffmpeg_profile = None
                        self._watermark = None
                    
                    item_source = getattr(media_item, "source", None)
                    if item_source is None:
                        item_source = stream_manager.detect_source(media_item.url)
                    
                    # Transcode to MPEG-TS using FFmpeg
                    chunk_count = 0
                    try:
                        async for chunk in self._transcode_with_youtube_expiry_retries(
                            stream_url,
                            codec_info=None,
                            item_source=item_source,
                            media_item=media_item,
                            stream_manager=stream_manager,
                            channel_name=channel.name if hasattr(channel, 'name') else None,
                            tune_priority=False,
                        ):
                            chunk_count += 1
                            yield chunk
                            
                            if chunk_count == 1:
                                logger.debug(f"First chunk sent for {media_item.title}, stream active")

                    except RuntimeError as e:
                        logger.error(f"FFmpeg error for {media_item.title}: {e}")
                        raise
                    except asyncio.CancelledError:
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
                    channel, parsed_schedule, max_items=None
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
        channel_number: str,
        allow_direct_archive: bool = False,
        *,
        tune_priority: bool = False,
        archive_tune_seek_seconds: float = 0.0,
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
                    self._channel_profile = getattr(channel_obj, 'transcode_profile', None)

            stream_url = None
            if config.cache.enabled and getattr(media_item, "source_id", None):
                try:
                    from ..cache import get_runtime
                    from .cache_first_stream_manager import CacheFirstStreamManager

                    cache_manager, download_queue = get_runtime()
                    if cache_manager and download_queue:
                        cache_first = CacheFirstStreamManager(
                            stream_manager,
                            cache_manager,
                            download_queue,
                            config.server.base_url,
                        )
                        try:
                            stream_url = await cache_first.get_stream_url(
                                media_item, tune_priority=tune_priority
                            )
                        except Exception as cache_exc:
                            from .cache_first_stream_manager import CacheNotReadyError
                            from ..database.models import StreamSource
                            if isinstance(cache_exc, CacheNotReadyError):
                                if allow_direct_archive:
                                    logger.info(
                                        f"Cache not ready; direct archive.org stream for "
                                        f"{media_item.title[:60]}"
                                    )
                                else:
                                    logger.debug(
                                        f"Cache not ready for {media_item.title[:60]}: "
                                        f"{cache_exc}"
                                    )
                                    return
                            elif media_item.source == StreamSource.ARCHIVE_ORG:
                                logger.warning(
                                    f"Archive.org cache failed for "
                                    f"{media_item.title[:60]}: {cache_exc}"
                                )
                                return
                            else:
                                logger.debug(
                                    f"Cache lookup failed ({cache_exc}), "
                                    f"falling back to direct stream"
                                )
                except Exception as cache_exc:
                    logger.debug(
                        f"Cache runtime unavailable ({cache_exc}), "
                        f"falling back to direct stream"
                    )

            if not stream_url:
                from ..database.models import StreamSource
                if media_item.source == StreamSource.ARCHIVE_ORG:
                    if allow_direct_archive:
                        stream_url = await stream_manager.get_stream_url(
                            media_item.url,
                            source=media_item.source,
                            channel_name=channel_name,
                            tune_priority=tune_priority,
                        )
                    else:
                        logger.warning(
                            f"No cached Archive.org file for {media_item.title[:60]}, "
                            f"skipping direct dn*.archive.org stream"
                        )
                        return
                else:
                    stream_url = await stream_manager.get_stream_url(
                        media_item.url,
                        source=media_item.source,
                        channel_name=channel_name,
                        tune_priority=tune_priority,
                    )
            
            if not stream_url:
                logger.warning(f"Could not get stream URL for {media_item.title}, skipping")
                return
            
            if isinstance(stream_url, tuple):
                # YouTube DASH split (video_url, audio_url) — pass through as-is;
                # local-cache path resolution only applies to single URLs.
                playback_url = stream_url
            else:
                playback_url = await self._resolve_playback_url(
                    stream_url,
                    media_item,
                    stream_manager,
                    channel_name,
                    allow_direct_archive,
                )
            if not playback_url:
                return

            from streamtv.streaming.youtube_adapter import YouTubeAdapter

            if isinstance(playback_url, str) and YouTubeAdapter.is_audio_only_stream_url(
                playback_url
            ):
                logger.warning(
                    "Rejecting audio-only YouTube URL for MPEG-TS; re-resolving with tune format"
                )
                playback_url = await stream_manager.get_stream_url(
                    media_item.url,
                    source=media_item.source,
                    channel_name=channel_name,
                    tune_priority=True,
                )
                if not playback_url or (
                    isinstance(playback_url, str)
                    and YouTubeAdapter.is_audio_only_stream_url(playback_url)
                ):
                    logger.error(
                        "YouTube tune re-resolve still audio-only for %s",
                        media_item.title[:60],
                    )
                    return

            logger.info(f"Streaming {media_item.title} for channel {channel_number}")
            
            item_source = getattr(media_item, "source", None)
            if item_source is None:
                item_source = stream_manager.detect_source(media_item.url)
            
            # Check for cancellation before starting transcoding (prevent race condition during shutdown)
            try:
                await asyncio.sleep(0)
            except asyncio.CancelledError:
                logger.info(f"Stream cancelled before transcoding {media_item.title}")
                raise
            
            # Detect input codec for smart transcoding (probe video URL on split)
            probe_url = (
                playback_url[0] if isinstance(playback_url, tuple) else playback_url
            )
            input_codec_info = await self._detect_input_codec(probe_url)
            
            # Check for cancellation again after codec detection (may take time)
            try:
                await asyncio.sleep(0)
            except asyncio.CancelledError:
                logger.info(f"Stream cancelled after codec detection for {media_item.title}")
                raise
            
            # Transcode to MPEG-TS (with smart codec detection)
            async for chunk in self._transcode_with_youtube_expiry_retries(
                playback_url,
                input_codec_info,
                item_source=item_source,
                media_item=media_item,
                stream_manager=stream_manager,
                channel_name=channel_name,
                tune_priority=tune_priority,
                archive_tune_seek_seconds=archive_tune_seek_seconds,
            ):
                yield chunk
                
        except Exception as e:
            logger.error(f"Error streaming {media_item.title}: {e}")
            raise
    
    def _resolve_local_playback_url(self, stream_url: str) -> str:
        """Prefer local cache paths for ffprobe and FFmpeg (faster, no HTTP header limits)."""
        if stream_url.startswith("/") and Path(stream_url).is_file():
            return stream_url

        parsed = urlparse(stream_url)
        if parsed.scheme in ("http", "https") and parsed.path.startswith("/cache/files/"):
            rel = unquote(parsed.path[len("/cache/files/"):])
            local = Path(config.cache.cache_directory).expanduser() / rel
            if local.is_file():
                if self._is_partial_cache_file(str(local)):
                    logger.debug(
                        "Keeping HTTP URL for in-progress cache buffer: %s",
                        local.name,
                    )
                    return stream_url
                logger.debug(f"Using local cache path for playback: {local}")
                return str(local)

        return stream_url

    def _is_local_youtube_cache_path(self, input_url: str) -> bool:
        """True when FFmpeg input is a cached YouTube file on the RAM/disk cache."""
        if not input_url or input_url.startswith("http"):
            return False
        normalized = str(Path(input_url).expanduser()).replace("\\", "/")
        cache_root = str(
            Path(config.cache.cache_directory).expanduser()
        ).replace("\\", "/")
        if f"{cache_root}/youtube/" in normalized:
            return True
        return "/streamtv-cache/youtube/" in normalized

    async def _resolve_playback_url(
        self,
        stream_url: str,
        media_item: MediaItem,
        stream_manager: "StreamManager",
        channel_name: Optional[str],
        allow_direct_archive: bool,
    ) -> Optional[str]:
        """Resolve best FFmpeg input URL; never use incomplete .part files directly."""
        playback_url = self._resolve_local_playback_url(stream_url)

        if self._is_partial_cache_file(playback_url) or self._is_partial_cache_file(
            stream_url
        ):
            from urllib.parse import urlparse
            from ..database.models import StreamSource

            progressive_http = False
            for candidate in (playback_url, stream_url):
                parsed = urlparse(candidate)
                if (
                    parsed.scheme in ("http", "https")
                    and "/cache/files/" in parsed.path
                ):
                    progressive_http = True
                    break
            if progressive_http:
                return playback_url if playback_url.startswith("http") else stream_url

            if (
                media_item.source == StreamSource.ARCHIVE_ORG
                and allow_direct_archive
            ):
                cdn_url = await stream_manager.get_stream_url(
                    media_item.url,
                    source=media_item.source,
                    channel_name=channel_name,
                )
                if cdn_url:
                    logger.info(
                        "Cache buffer in progress for %s — using archive.org CDN",
                        media_item.title[:60],
                    )
                    return cdn_url
            logger.warning(
                "Cache buffer incomplete for %s — waiting for full download",
                media_item.title[:60],
            )
            return None

        return playback_url

    def _is_partial_cache_file(self, path_or_url: str) -> bool:
        target = self._resolve_local_playback_url(path_or_url)
        name = Path(target).name.lower()
        return name.endswith(".part")

    def _default_hwaccel(self) -> Optional[str]:
        """Platform default when config.ffmpeg.hwaccel is unset."""
        if config.ffmpeg.hwaccel:
            return config.ffmpeg.hwaccel
        if platform.system() == "Darwin":
            return "videotoolbox"
        return None

    def _parse_ffprobe_json(self, probe_data: dict, probe_url: str) -> Optional[Dict[str, Any]]:
        """Build codec_info dict from ffprobe JSON output."""
        codec_info = {
            "video_codec": None,
            "audio_codec": None,
            "container_format": None,
            "container": "",
            "can_copy_video": False,
            "can_copy_audio": False,
            "needs_annexb_filter": False,
            "needs_annexb": True,
        }

        if "format" in probe_data:
            codec_info["container_format"] = (
                probe_data["format"].get("format_name", "").lower()
            )

        fmt_name = probe_data.get("format", {}).get("format_name", "") or ""
        codec_info["container"] = fmt_name
        codec_info["needs_annexb"] = any(h in fmt_name for h in AVCC_CONTAINER_HINTS)

        for stream in probe_data.get("streams", []):
            codec_type = stream.get("codec_type")
            codec_name = stream.get("codec_name", "").lower()

            if codec_type == "video":
                codec_info["video_codec"] = codec_name
                codec_info["can_copy_video"] = codec_name in ["h264", "avc"]
                if codec_name in ["h264", "avc"]:
                    container = codec_info["container_format"] or ""
                    if any(token in container for token in ("mp4", "mov", "quicktime")):
                        codec_info["needs_annexb_filter"] = True

            elif codec_type == "audio":
                codec_info["audio_codec"] = codec_name
                codec_info["can_copy_audio"] = codec_name in ["aac", "mp3", "mp2"]

        if not (codec_info["video_codec"] or codec_info["audio_codec"]):
            return None

        if self._is_partial_cache_file(probe_url):
            codec_info["can_copy_video"] = False
            codec_info["can_copy_audio"] = False
            codec_info["needs_annexb_filter"] = False

        return codec_info

    async def _quick_ffprobe_codec(
        self, probe_url: str, *, timeout: float = 5.0
    ) -> Optional[Dict[str, Any]]:
        """Fast ffprobe for Archive.org tune path (small probesize, short timeout)."""
        ffprobe_cmd = [
            config.ffmpeg.ffprobe_path or "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            "-show_format",
            "-timeout", "3000000",
            "-probesize", "500000",
            "-analyzeduration", "500000",
            "-user_agent", "Mozilla/5.0 (compatible; StreamTV/1.0)",
            probe_url,
        ]
        try:
            process = await asyncio.create_subprocess_exec(
                *ffprobe_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
            if process.returncode == 0 and stdout:
                return self._parse_ffprobe_json(
                    json.loads(stdout.decode()), probe_url
                )
        except (asyncio.TimeoutError, json.JSONDecodeError, OSError):
            pass
        return None

    def _infer_mp4_codec_defaults(self, stream_url: str) -> Optional[Dict[str, Any]]:
        """Last-resort when ffprobe unavailable: force transcode (never assume H.264).

        Issue 23: never assume AAC copy. Channel 1992 proved assuming H.264 video
        copy is unsafe — many Archive.org MP4s are MPEG-4 Part 2 (DivX/Xvid era).
        """
        if self._is_partial_cache_file(stream_url):
            return None
        probe_target = self._resolve_local_playback_url(stream_url)
        path_lower = probe_target.lower()
        if not path_lower.endswith(".mp4") and ".mp4" not in path_lower.split("?")[0]:
            return None
        logger.info(
            "Codec probe unavailable; forcing libx264+AAC transcode "
            "(cannot verify H.264 — Issue 23)"
        )
        inferred = {
            "video_codec": "unknown",
            "audio_codec": "unknown",
            "container_format": "mp4",
            "container": "mp4",
            "can_copy_video": False,
            "can_copy_audio": False,
            "needs_annexb_filter": False,
            "needs_annexb": True,
            "probe_inferred": True,
        }
        return inferred

    async def _detect_input_codec(self, stream_url: str) -> Dict[str, Any]:
        """Detect input video/audio codecs and container format using ffprobe"""
        probe_url = self._resolve_local_playback_url(stream_url)
        is_http = probe_url.startswith("http")

        # Derivative .ia.mp4 is not reliable for stream-copy remux — force transcode.
        if ".ia.mp4" in probe_url.lower():
            logger.info(
                "Derivative .ia.mp4 detected — forcing H.264/AAC transcode (no stream copy)"
            )
            return {
                "video_codec": "unknown",
                "audio_codec": "unknown",
                "container_format": "mp4",
                "container": "",
                "can_copy_video": False,
                "can_copy_audio": False,
                "needs_annexb_filter": False,
                "needs_annexb": True,
            }

        # Archive.org HTTP: quick ffprobe first (Issue 23 + MPEG-4 safety).
        # Blind H.264 copy assumption breaks Plex on MPEG-4 Part 2 sources (ch 1992).
        if is_http and "archive.org" in probe_url.lower():
            quick = await self._quick_ffprobe_codec(probe_url, timeout=5.0)
            if quick:
                logger.info(
                    "Archive.org quick probe: video=%s audio=%s copy_v=%s copy_a=%s",
                    quick["video_codec"],
                    quick["audio_codec"],
                    quick["can_copy_video"],
                    quick["can_copy_audio"],
                )
                return quick
            inferred = self._infer_mp4_codec_defaults(stream_url)
            if inferred:
                return inferred

        # Keep local/cache probes reasonably fast.
        probe_timeout = 4.0 if is_http else 15.0

        try:
            ffprobe_cmd = [
                config.ffmpeg.ffprobe_path or "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_streams",
                "-show_format",
            ]

            if is_http:
                ffprobe_cmd.extend([
                    "-timeout", "3000000",
                    "-probesize", "500000",
                    "-analyzeduration", "500000",
                    "-user_agent", "Mozilla/5.0 (compatible; StreamTV/1.0)",
                ])

            ffprobe_cmd.append(probe_url)

            process = await asyncio.create_subprocess_exec(
                *ffprobe_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=probe_timeout
            )

            if process.returncode == 0 and stdout:
                probe_data = json.loads(stdout.decode())
                codec_info = self._parse_ffprobe_json(probe_data, probe_url)
                if codec_info:
                    logger.info(
                        "Codec probe: video=%s audio=%s copy_v=%s copy_a=%s",
                        codec_info["video_codec"],
                        codec_info["audio_codec"],
                        codec_info["can_copy_video"],
                        codec_info["can_copy_audio"],
                    )
                    return codec_info

        except asyncio.TimeoutError:
            logger.warning(
                "Codec detection timed out for %s; will infer or use hardware transcode",
                probe_url[:120],
            )
        except Exception as e:
            logger.warning(
                "Could not detect input codec for %s: %s",
                probe_url[:120],
                e,
            )

        inferred = self._infer_mp4_codec_defaults(stream_url)
        if inferred:
            return inferred

        return {
            "video_codec": "unknown",
            "audio_codec": "unknown",
            "container_format": None,
            "container": "",
            "can_copy_video": False,
            "can_copy_audio": False,
            "needs_annexb_filter": False,
            "needs_annexb": True,
        }

    async def _transcode_with_youtube_expiry_retries(
        self,
        playback_url: Union[str, tuple],
        codec_info: Optional[Dict[str, Any]],
        *,
        item_source: Optional["StreamSource"],
        media_item: MediaItem,
        stream_manager: Any,
        channel_name: Optional[str],
        tune_priority: bool,
        archive_tune_seek_seconds: float = 0.0,
    ) -> AsyncIterator[bytes]:
        """Transcode one item, refreshing signed YouTube URLs on each expiry."""
        from ..database.models import StreamSource as _ModelSS

        if media_item.source != _ModelSS.YOUTUBE:
            async for chunk in self._transcode_to_mpegts(
                playback_url,
                codec_info,
                source=item_source,
                archive_tune_seek_seconds=archive_tune_seek_seconds,
            ):
                yield chunk
            return

        import time

        budget = youtube_expiry_reresolve_budget(media_item.duration)
        current_url = playback_url
        resume_at = 0.0
        item_duration = int(media_item.duration or 0)
        for attempt in range(budget + 1):
            attempt_start = time.monotonic()
            try:
                async for chunk in self._transcode_to_mpegts(
                    current_url,
                    codec_info,
                    source=item_source,
                    archive_tune_seek_seconds=0.0,
                    youtube_resume_seek_seconds=resume_at,
                ):
                    yield chunk
                return
            except StreamURLExpiredError:
                resume_at += time.monotonic() - attempt_start
                if item_duration > 0 and resume_at >= item_duration * 0.85:
                    logger.info(
                        "YouTube 403 after near-complete play for %s "
                        "(%.0fs / %ss); not restarting from zero",
                        media_item.title[:60],
                        resume_at,
                        item_duration,
                    )
                    return
                if attempt >= budget:
                    raise
                logger.info(
                    "Re-resolving expired YouTube URL for %s (refresh %s/%s, resume %.1fs)",
                    media_item.title[:60],
                    attempt + 1,
                    budget,
                    resume_at,
                )
                current_url = await stream_manager.get_stream_url(
                    media_item.url,
                    source=media_item.source,
                    channel_name=channel_name,
                    tune_priority=tune_priority,
                    force_refresh=True,
                )
    
    async def _transcode_to_mpegts(
        self,
        stream_url: Union[str, tuple],
        codec_info: Optional[Dict[str, Any]] = None,
        source: Optional['StreamSource'] = None,
        *,
        archive_tune_seek_seconds: float = 0.0,
        youtube_resume_seek_seconds: float = 0.0,
    ) -> AsyncIterator[bytes]:
        """Transcode a video stream to MPEG-TS using FFmpeg.

        stream_url may be a (video_url, audio_url) tuple for YouTube DASH split.
        """
        # Single URL used for logging and stderr pattern checks (403 watchdog).
        primary_url = stream_url[0] if isinstance(stream_url, tuple) else stream_url

        # Check for cancellation before creating FFmpeg process (prevent race condition during shutdown)
        try:
            # This will raise CancelledError if the task is already cancelled
            await asyncio.sleep(0)
        except asyncio.CancelledError:
            raise
        
        # Build FFmpeg command (with smart codec detection)
        ffmpeg_cmd = self._build_ffmpeg_command(
            stream_url,
            codec_info,
            source=source,
            archive_tune_seek_seconds=archive_tune_seek_seconds,
            youtube_resume_seek_seconds=youtube_resume_seek_seconds,
        )
        
        
        logger.debug(f"FFmpeg command: {' '.join(ffmpeg_cmd)}")
        # #region agent log
        _ff_t0 = time.monotonic()
        _ff_has_re = INPUT_FLAG_REALTIME in ffmpeg_cmd
        _agent_dbg_log(
            "H12",
            "mpegts_streamer.py:ffmpeg_start",
            "FFmpeg process starting",
            {
                "has_re": _ff_has_re,
                "has_ss": "-ss" in ffmpeg_cmd,
                "ss_val": (
                    ffmpeg_cmd[ffmpeg_cmd.index("-ss") + 1]
                    if "-ss" in ffmpeg_cmd
                    else None
                ),
                "c_v": (
                    ffmpeg_cmd[ffmpeg_cmd.index("-c:v") + 1]
                    if "-c:v" in ffmpeg_cmd
                    else None
                ),
                "c_a": (
                    ffmpeg_cmd[ffmpeg_cmd.index("-c:a") + 1]
                    if "-c:a" in ffmpeg_cmd
                    else None
                ),
                "is_archive": "archive.org" in (primary_url or "").lower(),
                "url_prefix": (primary_url or "")[:80],
            },
        )
        # #endregion
        
        # Start FFmpeg process
        process = None
        stderr_task = None
        try:
            process = await asyncio.create_subprocess_exec(
                *ffmpeg_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            
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
            url_expired = False
            async def monitor_stderr():
                nonlocal fatal_error_detected, url_expired
                try:
                    while True:
                        line = await process.stderr.readline()
                        if not line:
                            break
                        line_str = line.decode().strip()
                        stderr_lines.append(line_str)

                        # RC-7: YouTube signed URL expiry — surface for re-resolve
                        if (
                            ('403' in line_str or 'Forbidden' in line_str)
                            and 'googlevideo' in primary_url
                        ):
                            url_expired = True
                            fatal_error_detected = True
                            logger.warning(
                                "YouTube signed URL expired mid-stream (403); will re-resolve"
                            )
                        
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
                        elif 'udta parsing failed' in line_str.lower():
                            logger.debug(f"FFmpeg: {line_str[:120]} (non-fatal metadata parse)")
                        elif 'error applying bitstream filters' in line_str.lower() or \
                             'pps_id' in line_str.lower() and 'out of range' in line_str.lower():
                            logger.warning(
                                f"FFmpeg: {line_str[:200]} "
                                f"(H.264 bitstream filter issue — may recover or retry)"
                            )
                        elif 'error submitting packet to decoder' in line_str.lower() or \
                             'error splitting the input into nal units' in line_str.lower():
                            logger.debug(f"FFmpeg: {line_str[:200]} (non-fatal decode noise)")
                        elif 'error during demuxing' in line_str.lower() or \
                             ('demuxing' in line_str.lower() and 'input/output error' in line_str.lower()):
                            fatal_error_detected = True
                            logger.error(f"FFmpeg: {line_str} (Fatal demuxing error - stream will fail)")
                        elif ('error' in line_str.lower() or 'failed' in line_str.lower()) and \
                                'udta parsing failed' not in line_str.lower():
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
                            # #region agent log
                            _agent_dbg_log(
                                "H12",
                                "mpegts_streamer.py:ffmpeg_exit",
                                "FFmpeg process ended",
                                {
                                    "returncode": process.returncode,
                                    "has_re": _ff_has_re,
                                    "elapsed_s": round(time.monotonic() - _ff_t0, 3),
                                    "url_prefix": (primary_url or "")[:80],
                                    "stderr_tail": "\n".join(stderr_lines[-5:])[:500],
                                },
                            )
                            # #endregion
                            if process.returncode != 0:
                                error_msg = '\n'.join(stderr_lines[-10:])
                                logger.warning(f"FFmpeg exited with code {process.returncode}: {error_msg}")
                            break
                        # Check for fatal errors detected in stderr
                        if fatal_error_detected:
                            await stderr_task
                            error_msg = '\n'.join(stderr_lines[-10:])
                            if url_expired:
                                raise StreamURLExpiredError(
                                    f"YouTube signed URL expired (403): {error_msg}"
                                )
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
                            # #region agent log
                            _agent_dbg_log(
                                "H12",
                                "mpegts_streamer.py:ffmpeg_exit",
                                "FFmpeg process ended (timeout path)",
                                {
                                    "returncode": process.returncode,
                                    "has_re": _ff_has_re,
                                    "elapsed_s": round(time.monotonic() - _ff_t0, 3),
                                    "url_prefix": (primary_url or "")[:80],
                                },
                            )
                            # #endregion
                            # Process ended, likely end of file
                            break
                        # Check for fatal errors detected in stderr
                        if fatal_error_detected:
                            await stderr_task
                            error_msg = '\n'.join(stderr_lines[-10:])
                            if url_expired:
                                raise StreamURLExpiredError(
                                    f"YouTube signed URL expired (403): {error_msg}"
                                )
                            logger.error(f"FFmpeg fatal error detected during timeout: {error_msg}")
                            raise RuntimeError(f"FFmpeg fatal demuxing error: {error_msg}")
                        # Process still running but no data - continue waiting
                        continue

            # Stream ended (process exit / EOF): surface signed-URL expiry
            if url_expired:
                error_msg = '\n'.join(stderr_lines[-10:])
                raise StreamURLExpiredError(
                    f"YouTube signed URL expired (403): {error_msg}"
                )
                
        except asyncio.CancelledError:
            logger.info(f"FFmpeg transcoding cancelled for {primary_url[:80]}")
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
    
    def _apply_source_encoder_policy(
        self,
        *,
        source: Optional['StreamSource'],
        chosen_hwaccel: Optional[str],
        chosen_encoder: Optional[str],
        needs_video_transcode: bool,
        is_mpeg4: bool,
    ) -> tuple[Optional[str], Optional[str]]:
        """Per-source Plex MPEG-TS encoder policy. YouTube and archive.org never share a code path."""
        if not needs_video_transcode or is_mpeg4:
            return chosen_hwaccel, chosen_encoder

        from streamtv.streaming.stream_manager import StreamSource as SSEnum

        src_val = getattr(source, "value", None)
        if isinstance(src_val, str):
            src_val = src_val.lower()

        if src_val == SSEnum.YOUTUBE.value or source == SSEnum.YOUTUBE:
            if chosen_hwaccel == "videotoolbox" or not chosen_encoder:
                logger.info(
                    "YouTube MPEG-TS: libx264 (VideoToolbox encode disabled for yt-dlp sources)"
                )
                return None, "libx264"
            return chosen_hwaccel, chosen_encoder

        if src_val == SSEnum.ARCHIVE_ORG.value or source == SSEnum.ARCHIVE_ORG:
            if chosen_hwaccel == "videotoolbox":
                logger.info(
                    "Archive.org MPEG-TS: libx264 encode (VideoToolbox encode disabled for Plex)"
                )
                return None, "libx264"
            return chosen_hwaccel, chosen_encoder

        if src_val in (SSEnum.PBS.value, SSEnum.PLEX.value) or source in (
            SSEnum.PBS,
            SSEnum.PLEX,
        ):
            if chosen_hwaccel == "videotoolbox":
                logger.info(
                    "%s MPEG-TS: libx264 encode (VideoToolbox encode disabled for Plex)",
                    src_val or getattr(source, "value", source),
                )
                return None, "libx264"
            return chosen_hwaccel, chosen_encoder

        # Unknown / URL-only detection fallback
        if chosen_hwaccel == "videotoolbox":
            logger.info("MPEG-TS: libx264 encode (VideoToolbox encode disabled for Plex)")
            return None, "libx264"
        return chosen_hwaccel, chosen_encoder
    
    def _archive_tune_seek_args(
        self,
        source: Optional["StreamSource"],
        archive_tune_seek_seconds: float,
    ) -> List[str]:
        """Archive-only tune seek (-ss). Never applied to YouTube/PBS/Plex."""
        if archive_tune_seek_seconds <= 0:
            return []

        def _is_archive_org(src: Optional["StreamSource"]) -> bool:
            if src is None:
                return False
            name = getattr(src, "name", None)
            if name == "ARCHIVE_ORG":
                return True
            value = getattr(src, "value", None)
            return str(value).upper() == "ARCHIVE_ORG"

        if not _is_archive_org(source):
            logger.warning(
                "Ignoring archive tune seek %.1fs for non-archive source %s",
                archive_tune_seek_seconds,
                source,
            )
            return []
        logger.info(
            "Archive tune seek: FFmpeg -ss %.1fs (archive.org only)",
            archive_tune_seek_seconds,
        )
        return ["-ss", f"{archive_tune_seek_seconds:.3f}"]

    def _youtube_resume_seek_args(self, youtube_resume_seek_seconds: float) -> List[str]:
        """YouTube-only mid-stream resume (-ss) after signed-URL 403 refresh."""
        if youtube_resume_seek_seconds <= 0:
            return []
        logger.info(
            "YouTube mid-stream resume: FFmpeg -ss %.1fs",
            youtube_resume_seek_seconds,
        )
        return ["-ss", f"{youtube_resume_seek_seconds:.3f}"]

    def _build_ffmpeg_command(
        self,
        input_url: Union[str, tuple],
        codec_info: Optional[Dict[str, Any]] = None,
        source: Optional['StreamSource'] = None,
        *,
        archive_tune_seek_seconds: float = 0.0,
        youtube_resume_seek_seconds: float = 0.0,
    ) -> List[str]:
        """Build FFmpeg command for MPEG-TS transcoding with smart codec selection.

        input_url may be a (video_url, audio_url) tuple for YouTube DASH split
        streams (dual-input FFmpeg). Tuples from any other source are an error.
        """
        aux_audio_url: Optional[str] = None
        if isinstance(input_url, tuple):
            from streamtv.streaming.stream_manager import StreamSource as _SS
            if source != _SS.YOUTUBE:
                raise ValueError(
                    "Split (video_url, audio_url) input is only valid for "
                    f"YouTube sources (got source={source})"
                )
            input_url, aux_audio_url = input_url

        # Use profile-based builder if profile is available
        if self._ffmpeg_profile:
            try:
                from ..transcoding.ffmpeg_builder import build_ffmpeg_command
                # Check for subtitle file (would need to be passed separately)
                subtitle_path = None  # TODO: Implement subtitle file handling
                cmd = build_ffmpeg_command(
                    profile=self._ffmpeg_profile,
                    input_url=input_url,
                    watermark=self._watermark,
                    subtitle_path=subtitle_path,
                    codec_info=codec_info
                )
                logger.debug(f"Using profile-based FFmpeg command: {self._ffmpeg_profile.name}")
                return cmd
            except Exception as e:
                logger.warning(f"Failed to build profile-based command, falling back to legacy: {e}")
                # Fall through to legacy builder
        
        # Legacy builder (existing code)
        cmd = [self._ffmpeg_path]
        
        # Determine if we can use copy mode (no transcoding)
        can_copy_video = codec_info and codec_info.get('can_copy_video', False)
        can_copy_audio = codec_info and codec_info.get('can_copy_audio', False)
        video_codec = codec_info.get('video_codec', 'unknown') if codec_info else 'unknown'
        
        # Prefer adapter-detected source over URL heuristics for accurate preset selection.
        # MediaItem.source is database.models.StreamSource; compare by .value so it matches
        # stream_manager.StreamSource (identity equality across the two Enum classes is False
        # and previously forced YouTube onto the legacy path — no -re, +reconnect_at_eof).
        src_val = getattr(source, "value", None)
        if isinstance(src_val, str):
            src_val = src_val.lower()
        url_l = input_url.lower()
        if src_val == "youtube":
            src_youtube, src_archive, src_pbs, src_plex = True, False, False, False
        elif src_val == "archive_org":
            src_youtube, src_archive, src_pbs, src_plex = False, True, False, False
        elif src_val == "pbs":
            src_youtube, src_archive, src_pbs, src_plex = False, False, True, False
        elif src_val == "plex":
            src_youtube, src_archive, src_pbs, src_plex = False, False, False, True
        else:
            src_youtube = (
                "youtube.com" in url_l
                or "youtu.be" in url_l
                or "googlevideo.com" in url_l
            )
            src_archive = "archive.org" in url_l
            src_pbs = ("pbs.org" in url_l) or ("lls.pbs.org" in url_l)
            src_plex = ("/library/metadata/" in input_url) or ("plex" in url_l)

        # Determine desired hwaccel/encoder via fallback: channel preset -> source override -> global config
        chosen_hwaccel = None
        chosen_encoder = None
        # Try source overrides first (they will be superseded by per-channel profile below when available)
        if src_youtube:
            chosen_hwaccel = config.ffmpeg.youtube_hwaccel or chosen_hwaccel
            chosen_encoder = config.ffmpeg.youtube_video_encoder or chosen_encoder
        elif src_archive:
            chosen_hwaccel = config.ffmpeg.archive_org_hwaccel or chosen_hwaccel
            chosen_encoder = config.ffmpeg.archive_org_video_encoder or chosen_encoder
        elif src_pbs:
            chosen_hwaccel = config.ffmpeg.pbs_hwaccel or chosen_hwaccel
            chosen_encoder = config.ffmpeg.pbs_video_encoder or chosen_encoder
        elif src_plex:
            chosen_hwaccel = config.ffmpeg.plex_hwaccel or chosen_hwaccel
            chosen_encoder = config.ffmpeg.plex_video_encoder or chosen_encoder

        # Resolve per-channel transcode_profile if available
        channel_profile = self._channel_profile
        
        # Map profile to hwaccel/encoder if set
        if channel_profile:
            profile = (channel_profile or '').lower()
            if profile == 'nvidia':
                chosen_hwaccel = 'cuda'
                chosen_encoder = 'h264_nvenc'
            elif profile == 'intel':
                chosen_hwaccel = 'qsv'
                chosen_encoder = 'h264_qsv'
            elif profile == 'cpu':
                chosen_hwaccel = None
                chosen_encoder = 'libx264'

        # Fallback to global / platform default if still unset
        if not chosen_hwaccel:
            chosen_hwaccel = self._default_hwaccel()

        # VideoToolbox only supports H.264 decoding - disable for MPEG-4/AVI
        mpeg4_codecs = ['mpeg4', 'msmpeg4v3', 'msmpeg4v2', 'msmpeg4']
        is_mpeg4 = video_codec in mpeg4_codecs
        needs_video_transcode = not can_copy_video
        chosen_hwaccel, chosen_encoder = self._apply_source_encoder_policy(
            source=source,
            chosen_hwaccel=chosen_hwaccel,
            chosen_encoder=chosen_encoder,
            needs_video_transcode=needs_video_transcode,
            is_mpeg4=is_mpeg4,
        )
        use_hwaccel = bool(chosen_hwaccel and needs_video_transcode and not is_mpeg4)
        
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
                if video_codec == "unknown":
                    logger.info(
                        "Hardware-accelerated transcoding: Using %s (codec probe unavailable)",
                        chosen_hwaccel,
                    )
                else:
                    logger.info(
                        "Hardware-accelerated transcoding: Using %s for %s",
                        chosen_hwaccel,
                        video_codec,
                    )
            else:
                logger.info("Software transcoding: Converting to H.264/AAC")
        
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
            cmd.extend(["-hwaccel", chosen_hwaccel])
            if chosen_hwaccel in ("videotoolbox", "cuda", "qsv", "vaapi"):
                cmd.extend(["-hwaccel_output_format", chosen_hwaccel])
            if config.ffmpeg.hwaccel_device:
                cmd.extend(["-hwaccel_device", config.ffmpeg.hwaccel_device])
            logger.debug(
                "Hardware acceleration enabled (%s) for video_codec=%s",
                chosen_hwaccel,
                video_codec,
            )
        
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
            
            if src_youtube:
                # YouTube: no -reconnect_at_eof — finite VOD items must terminate
                # so the playout loop advances (RC-3). Keep mid-stream reconnects.
                cmd.extend([
                    "-timeout", timeout,
                    "-user_agent", "Mozilla/5.0 (compatible; StreamTV/1.0)",
                    "-reconnect", "1",
                    "-reconnect_streamed", "1",
                    "-reconnect_delay_max", reconnect_delay,
                    "-multiple_requests", "1",
                ])
            else:
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
        
            # Add Archive.org authentication cookies if available (minimal set only).
            # Always resolve an adapter — continuous-stream path may not have set
            # self._stream_manager yet, and restricted CDN URLs 403 without cookies.
            if is_archive_org:
                adapter = None
                if self._stream_manager and self._stream_manager.archive_org_adapter:
                    adapter = self._stream_manager.archive_org_adapter
                else:
                    try:
                        from .stream_manager import StreamManager
                        self._stream_manager = StreamManager()
                        adapter = self._stream_manager.archive_org_adapter
                    except Exception as exc:
                        logger.debug(f"Could not init StreamManager for cookies: {exc}")
                if adapter:
                    cookie_header = adapter.ffmpeg_cookie_header()
                    if cookie_header:
                        # FFmpeg -headers requires CRLF-terminated lines; cookie
                        # values may contain spaces (Archive.org logged-in-sig).
                        cmd.extend(["-headers", f"Cookie: {cookie_header}\r\n"])
                        logger.debug(
                            "Added Archive.org auth cookies to FFmpeg (%d bytes)",
                            len(cookie_header),
                        )
                    else:
                        logger.warning(
                            "Archive.org CDN input without auth cookies — "
                            "restricted items will 403. Refresh "
                            "data/cookies/archive.org_cookies.txt or Keychain login."
                        )

            is_googlevideo = "googlevideo.com" in input_url.lower()
            if is_googlevideo:
                yt_adapter = None
                if self._stream_manager and self._stream_manager.youtube_adapter:
                    yt_adapter = self._stream_manager.youtube_adapter
                else:
                    try:
                        from .stream_manager import StreamManager

                        self._stream_manager = StreamManager()
                        yt_adapter = self._stream_manager.youtube_adapter
                    except Exception as exc:
                        logger.debug(
                            "Could not init StreamManager for YouTube cookies: %s", exc
                        )
                header_blob = "Referer: https://www.youtube.com/\r\n"
                header_blob += (
                    "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36\r\n"
                )
                if yt_adapter:
                    cookie_header = yt_adapter.ffmpeg_cookie_header()
                    if cookie_header:
                        header_blob = f"Cookie: {cookie_header}\r\n" + header_blob
                        logger.debug(
                            "Added YouTube auth cookies to FFmpeg (%d bytes)",
                            len(cookie_header),
                        )
                cmd.extend(["-headers", header_blob])
                logger.debug("Using YouTube/googlevideo HTTP headers for FFmpeg input")
            
            if is_archive_org:
                logger.debug("Using extended timeouts for Archive.org stream")
        
        # Input URL with flags
        # Check if this is a DRM-protected HLS stream (common with PBS live streams)
        is_drm_hls = '.m3u8' in input_url.lower() and ('drm' in input_url.lower() or 'lls.pbs.org' in input_url.lower())

        seek_args = self._archive_tune_seek_args(source, archive_tune_seek_seconds)
        
        
        # Use more lenient settings for MPEG-4/AVI files (often have timing issues).
        # Never use -flags +low_delay or +fastseek (forbidden — breaks MPEG-TS mux).
        if is_mpeg4:
            if seek_args:
                cmd.extend(seek_args)
            if src_archive:
                cmd.append(INPUT_FLAG_REALTIME)
            cmd.extend([
                "-fflags", "+genpts+discardcorrupt+igndts",
                "-err_detect", "ignore_err",
                "-strict", "experimental",
                "-probesize", "5000000",
                "-analyzeduration", "5000000",
                "-thread_queue_size", "4096",
                "-i", input_url,
            ])
            
            logger.debug("Using lenient input settings for MPEG-4/AVI")
        elif is_drm_hls:
            if seek_args:
                cmd.extend(seek_args)
            cmd.extend([
                "-fflags", "+genpts+discardcorrupt",
                "-err_detect", "ignore_err",
                "-strict", "experimental",
                "-probesize", "1000000",
                "-analyzeduration", "2000000",
                "-thread_queue_size", "4096",
                "-i", input_url,
            ])
            logger.debug("Using error-resilient settings for DRM-protected HLS stream")
            
        elif src_youtube and (
            input_url.startswith("http")
            or aux_audio_url
            or self._is_local_youtube_cache_path(input_url)
        ):
            # YouTube CDN/HLS and RAM-disk cache .mp4 paths.
            # No +fastseek, no -flags +low_delay (see streamtv/ffmpeg/constants.py).
            # Pace ALL YouTube VOD (progressive CDN, VOD HLS, and local cache).
            # Without -re, FFmpeg remuxes a multi-minute item in ~seconds of wall
            # clock; continuous playout treats that as EOF and restarts the song
            # (channel 1991: Promises/Forever looping every ~1s). Live HLS stays unpaced.
            _yt_live = (
                "/live/" in input_url.lower()
                or "is_live=1" in input_url.lower()
            )
            yt_seek_args = (
                [] if _yt_live
                else self._youtube_resume_seek_args(youtube_resume_seek_seconds)
            )
            if not _yt_live:
                cmd.append(INPUT_FLAG_REALTIME)
            if yt_seek_args:
                cmd.extend(yt_seek_args)
            cmd.extend([
                "-fflags", FFLAGS_NETWORK_STREAMING,
                "-probesize", "1000000",
                "-analyzeduration", "2000000",
                "-i", input_url,
            ])
            if aux_audio_url:
                if aux_audio_url.startswith("http") and "googlevideo.com" in aux_audio_url.lower():
                    header_blob = (
                        "Referer: https://www.youtube.com/\r\n"
                        "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36\r\n"
                    )
                    yt_adapter = (
                        self._stream_manager.youtube_adapter
                        if self._stream_manager
                        else None
                    )
                    if yt_adapter:
                        cookie_header = yt_adapter.ffmpeg_cookie_header()
                        if cookie_header:
                            header_blob = f"Cookie: {cookie_header}\r\n" + header_blob
                    cmd.extend(["-headers", header_blob])
                if yt_seek_args:
                    cmd.extend(yt_seek_args)
                cmd.extend([
                    INPUT_FLAG_REALTIME,
                    "-fflags", FFLAGS_NETWORK_STREAMING,
                    "-i", aux_audio_url,
                ])
                logger.info(
                    "YouTube DASH split: dual-input FFmpeg (video + separate audio)"
                )
        else:
            # Non-YouTube sources. Archive.org VOD must use -re (same class of bug as
            # YouTube without pacing: ~49x flood → premature CDN EOF → hold_partial
            # restart loop → Plex s1001). PBS live HLS and Plex stay unpaced.
            if seek_args:
                cmd.extend(seek_args)
            if src_archive:
                cmd.append(INPUT_FLAG_REALTIME)
            cmd.extend([
                "-fflags", "+genpts+discardcorrupt",
                "-err_detect", "ignore_err",
                "-strict", "experimental",
                "-probesize", "1000000",
                "-analyzeduration", "2000000",
                "-thread_queue_size", "4096",
                "-i", input_url,
            ])
            
        
        # Output options (come AFTER -i)
        if aux_audio_url:
            cmd.extend(["-map", "0:v:0", "-map", "1:a:0"])
        # Threads (applies to encoding) - only if transcoding
        if config.ffmpeg.threads > 0 and not (can_copy_video and can_copy_audio):
            cmd.extend(["-threads", str(config.ffmpeg.threads)])
        
        # VIDEO CODEC SELECTION (Smart mode)
        # FFmpeg docs: h264_mp4toannexb is auto-inserted for mpegts output.
        # Do not force -bsf:v dump_extra here — it fails on many IA MP4s with
        # "Error applying bitstream filters ... Invalid data" (runtime evidence).
        # https://ffmpeg.org/ffmpeg-bitstream-filters.html#h264_005fmp4toannexb
        if can_copy_video:
            if src_youtube:
                # RC-1: probe-driven Annex-B gating. HLS/TS input is already
                # Annex B — forcing h264_mp4toannexb corrupts it. AVCC (MP4)
                # input needs the conversion. dump_extra is safe for both.
                bsf = (
                    [BSF_H264_MP4TOANNEXB]
                    if (codec_info or {}).get('needs_annexb', True)
                    else []
                )
                bsf.append(BSF_H264_DUMP_EXTRA)
                cmd.extend(["-c:v", "copy", "-bsf:v", ",".join(bsf)])
                logger.debug("Video: copy mode (YouTube, bsf=%s)", ",".join(bsf))
            else:
                # frozen legacy — non-YouTube copy path (golden test)
                cmd.extend(["-c:v", "copy"])
                logger.debug(
                    "Video: copy mode (mpegts auto-inserts h264_mp4toannexb when needed)"
                )
        elif use_hwaccel:
            # Hardware-accelerated H.264 encoding
            hw_encoder = chosen_encoder or (
                "h264_videotoolbox" if chosen_hwaccel == "videotoolbox" else (
                    "h264_nvenc" if chosen_hwaccel == "cuda" else (
                        "h264_qsv" if chosen_hwaccel == "qsv" else "h264_videotoolbox"
                    )
                )
            )
            cmd.extend([
                "-c:v", hw_encoder,
                "-b:v", "6M",  # Higher bitrate for better quality
                "-maxrate", "6M",
                "-bufsize", "12M",
                "-profile:v", "high",  # High profile for better compression
                "-realtime", "1",
                "-pix_fmt", "yuv420p",
            ])
            logger.debug(f"Video: Using hardware-accelerated H.264 ({hw_encoder}) with error correction")
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
                "-g", "50",
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
        
        # Output format (MPEG-TS) — FFmpeg muxers.texi:
        # muxrate default is VBR; forcing CBR (e.g. 4M) on low-bitrate remuxes
        # pads null packets (huge overhead) and breaks Plex HDHomeRun clients.
        # Use VBR whenever video is stream-copied (audio may still be re-encoded).
        video_copy = bool(can_copy_video)
        full_copy = bool(can_copy_video and can_copy_audio)
        if video_copy:
            cmd.extend([
                "-f", "mpegts",
                "-mpegts_flags", "+resend_headers",
                "-pcr_period", "20",
                "-muxdelay", "0",
                "-muxpreload", "0",
            ])
            logger.info(
                "MPEG-TS remux (VBR%s): no -muxrate CBR, no encoder bitrate flags",
                " full copy" if full_copy else " video-copy",
            )
        elif src_youtube:
            # RC-4: no -muxrate CBR for YouTube — copy/1080p bitrate exceeds
            # 4 Mbps and overflows the CBR mux buffer. VBR TS mux instead.
            cmd.extend([
                "-f", "mpegts",
                "-pcr_period", "20",
                "-flush_packets", "1",
                "-fflags", "+flush_packets",
                "-max_interleave_delta", "0",
            ])
            if config.ffmpeg.extra_flags:
                import shlex
                cmd.extend(shlex.split(config.ffmpeg.extra_flags))
        else:
            cmd.extend([
                "-f", "mpegts",
                "-muxrate", "4M",
                "-pcr_period", "20",
                "-flush_packets", "1",
                "-fflags", "+flush_packets",
                "-max_interleave_delta", "0",
            ])
            # Encoder bitrate caps only apply when transcoding video.
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

