"""Stream pre-warming module to reduce startup delay for Plex compatibility

This module pre-starts FFmpeg streams and buffers initial chunks to ensure
sub-second response times when clients connect, preventing Plex "cannot tune channel" errors.
"""

import asyncio
import logging
from typing import Optional, Deque, Dict, AsyncIterator
from collections import deque
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class StreamPrewarmer:
    """Pre-warms streams by starting FFmpeg early and buffering initial chunks"""
    
    def __init__(self, max_buffer_size: int = 10 * 1024 * 1024, max_chunks: int = 50):
        """
        Initialize pre-warmer
        
        Args:
            max_buffer_size: Maximum buffer size in bytes (default: 10MB)
            max_chunks: Maximum number of chunks to buffer (default: 50)
        """
        self.max_buffer_size = max_buffer_size
        self.max_chunks = max_chunks
        self._buffers: Dict[str, Deque[bytes]] = {}  # channel_number -> deque of chunks
        self._buffer_sizes: Dict[str, int] = {}  # channel_number -> total buffer size in bytes
        self._prewarm_tasks: Dict[str, asyncio.Task] = {}  # channel_number -> prewarm task
        self._lock = asyncio.Lock()
    
    async def prewarm_stream(
        self,
        channel_number: str,
        stream_generator: AsyncIterator[bytes]
    ) -> None:
        """
        Pre-warm a stream by buffering initial chunks
        
        Args:
            channel_number: Channel number to pre-warm
            stream_generator: Async generator that yields chunks
        """
        async with self._lock:
            # Clear existing buffer for this channel
            if channel_number in self._buffers:
                self._buffers[channel_number].clear()
                self._buffer_sizes[channel_number] = 0
            
            # Create new buffer
            self._buffers[channel_number] = deque(maxlen=self.max_chunks)
            self._buffer_sizes[channel_number] = 0
        
        try:
            chunk_count = 0
            async for chunk in stream_generator:
                async with self._lock:
                    if channel_number not in self._buffers:
                        # Buffer was cleared (channel stopped)
                        break
                    
                    # Check if buffer is full
                    if len(self._buffers[channel_number]) >= self.max_chunks:
                        # Buffer is full, stop pre-warming
                        logger.debug(f"Pre-warm buffer full for channel {channel_number} ({chunk_count} chunks)")
                        break
                    
                    # Check if buffer size limit reached
                    chunk_size = len(chunk)
                    if self._buffer_sizes[channel_number] + chunk_size > self.max_buffer_size:
                        logger.debug(f"Pre-warm buffer size limit reached for channel {channel_number} ({self._buffer_sizes[channel_number]} bytes)")
                        break
                    
                    # Add chunk to buffer
                    self._buffers[channel_number].append(chunk)
                    self._buffer_sizes[channel_number] += chunk_size
                    chunk_count += 1
                    
                    # Log first chunk (important milestone)
                    if chunk_count == 1:
                        logger.info(f"Pre-warmed first chunk for channel {channel_number} ({chunk_size} bytes)")
                    
                    # Stop after we have enough chunks (typically 5-10 chunks is enough for sub-second response)
                    if chunk_count >= 10:
                        logger.debug(f"Pre-warmed {chunk_count} chunks for channel {channel_number} ({self._buffer_sizes[channel_number]} bytes)")
                        break
        except asyncio.CancelledError:
            logger.debug(f"Pre-warm cancelled for channel {channel_number}")
            raise
        except Exception as e:
            logger.warning(f"Error pre-warming stream for channel {channel_number}: {e}")
        finally:
            async with self._lock:
                if channel_number in self._prewarm_tasks:
                    del self._prewarm_tasks[channel_number]
    
    async def get_buffered_stream(
        self,
        channel_number: str,
        stream_generator: AsyncIterator[bytes]
    ) -> AsyncIterator[bytes]:
        """
        Get a stream that serves buffered chunks first, then continues from generator
        
        Args:
            channel_number: Channel number
            stream_generator: Async generator that yields chunks (continues after buffer)
            
        Yields:
            Chunks from buffer first, then from generator
        """
        # First, yield all buffered chunks
        async with self._lock:
            if channel_number in self._buffers and self._buffers[channel_number]:
                buffer = list(self._buffers[channel_number])
                buffer_size = self._buffer_sizes.get(channel_number, 0)
                logger.info(f"Serving {len(buffer)} pre-warmed chunks for channel {channel_number} ({buffer_size} bytes)")
                
                # Clear buffer after serving (don't serve same chunks twice)
                self._buffers[channel_number].clear()
                self._buffer_sizes[channel_number] = 0
            else:
                buffer = []
                logger.debug(f"No pre-warmed buffer for channel {channel_number}, starting fresh")
        
        # Yield buffered chunks immediately
        for chunk in buffer:
            yield chunk
        
        # Continue from live stream
        async for chunk in stream_generator:
            yield chunk
    
    async def clear_buffer(self, channel_number: str) -> None:
        """Clear the buffer for a channel"""
        async with self._lock:
            if channel_number in self._buffers:
                self._buffers[channel_number].clear()
                self._buffer_sizes[channel_number] = 0
                logger.debug(f"Cleared pre-warm buffer for channel {channel_number}")
    
    async def start_prewarm_task(
        self,
        channel_number: str,
        stream_generator: AsyncIterator[bytes]
    ) -> None:
        """Start a background task to pre-warm a stream"""
        async with self._lock:
            # Cancel existing prewarm task if any
            if channel_number in self._prewarm_tasks:
                task = self._prewarm_tasks[channel_number]
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            
            # Start new prewarm task
            task = asyncio.create_task(
                self.prewarm_stream(channel_number, stream_generator)
            )
            self._prewarm_tasks[channel_number] = task
            logger.debug(f"Started pre-warm task for channel {channel_number}")
    
    async def stop_prewarm_task(self, channel_number: str) -> None:
        """Stop pre-warm task for a channel"""
        async with self._lock:
            if channel_number in self._prewarm_tasks:
                task = self._prewarm_tasks[channel_number]
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                del self._prewarm_tasks[channel_number]
            
            # Clear buffer
            await self.clear_buffer(channel_number)
    
    async def get_buffer_info(self, channel_number: str) -> Dict[str, int]:
        """Get buffer information for a channel"""
        async with self._lock:
            if channel_number in self._buffers:
                return {
                    "chunk_count": len(self._buffers[channel_number]),
                    "buffer_size_bytes": self._buffer_sizes.get(channel_number, 0),
                    "has_buffer": True
                }
            else:
                return {
                    "chunk_count": 0,
                    "buffer_size_bytes": 0,
                    "has_buffer": False
                }

