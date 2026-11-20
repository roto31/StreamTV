"""Plex Live TV video hold — real h264+aac MPEG-TS instead of null keepalives.

Emits a pre-encoded hold loop until upstream produces non-null video TS packets,
then splices. If upstream goes silent (or only null PID 0x1FFF) for silence_sec,
resumes the hold. Does not modify frozen streaming/hdhomerun/cache modules.

Silence default is intentionally high: FFmpeg -re / overlay encodes routinely
gap >2s between stdout flushes; a short timeout flaps back to black hold forever.
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, Optional, Union

from starlette.responses import StreamingResponse

logger = logging.getLogger(__name__)

TS_PACKET_SIZE = 188
NULL_PID = 0x1FFF
# Match mid-stream stall ballpark; override via STREAMTV_PLEX_HOLD_SILENCE_SEC
DEFAULT_SILENCE_SEC = 45.0
DEFAULT_HOLD_CHUNK = 8192
# Pace hold ~1.5 Mbps so Plex is not flooded with black and the event loop yields
HOLD_BITRATE_BPS = 1_500_000

HoldPath = Union[str, Path]


def silence_sec_from_env(default: float = DEFAULT_SILENCE_SEC) -> float:
    raw = os.environ.get("STREAMTV_PLEX_HOLD_SILENCE_SEC", "").strip()
    if not raw:
        return default
    try:
        val = float(raw)
    except ValueError:
        return default
    return val if val > 0 else default


def hold_chunk_pace_sec(chunk_len: int) -> float:
    """Realtime-ish delay for one hold chunk at HOLD_BITRATE_BPS."""
    if chunk_len <= 0:
        return 0.05
    return max(0.02, (chunk_len * 8) / float(HOLD_BITRATE_BPS))


def default_hold_path() -> Path:
    env = os.environ.get("STREAMTV_PLEX_HOLD_TS", "").strip()
    if env:
        return Path(env).expanduser()
    # Repo root / data/plex_hold.ts relative to this package: streamtv/tuners/
    return Path(__file__).resolve().parents[2] / "data" / "plex_hold.ts"


def pid_of_packet(packet: bytes) -> int:
    if len(packet) < 3 or packet[0] != 0x47:
        return -1
    return ((packet[1] & 0x1F) << 8) | packet[2]


def is_null_packet(packet: bytes) -> bool:
    return pid_of_packet(packet) == NULL_PID


def is_all_null_keepalive(chunk: bytes) -> bool:
    """True if chunk is empty or only MPEG-TS null packets (StreamTV keepalive)."""
    if not chunk:
        return True
    if len(chunk) < TS_PACKET_SIZE:
        return False
    # Align to sync byte if needed
    offset = 0
    if chunk[0] != 0x47:
        try:
            offset = chunk.index(0x47)
        except ValueError:
            return False
    body = chunk[offset:]
    n = len(body) // TS_PACKET_SIZE
    if n == 0:
        return False
    for i in range(n):
        pkt = body[i * TS_PACKET_SIZE : (i + 1) * TS_PACKET_SIZE]
        if not is_null_packet(pkt):
            return False
    return True


def strip_null_packets(chunk: bytes) -> bytes:
    """Return only non-null TS packets from chunk (preserve order)."""
    if not chunk:
        return b""
    offset = 0
    if chunk[0] != 0x47:
        try:
            offset = chunk.index(0x47)
        except ValueError:
            return b""
    out = bytearray()
    body = chunk[offset:]
    n = len(body) // TS_PACKET_SIZE
    for i in range(n):
        pkt = body[i * TS_PACKET_SIZE : (i + 1) * TS_PACKET_SIZE]
        if not is_null_packet(pkt):
            out.extend(pkt)
    return bytes(out)


def has_video_payload(chunk: bytes) -> bool:
    """True if chunk contains at least one non-null TS packet."""
    return bool(strip_null_packets(chunk))


def discontinuity_flag_chunk(chunk: bytes) -> bytes:
    """Set discontinuity_indicator on the first TS packet with adaptation field.

    If the first packet has no adaptation field, prepend a minimal discontinuity
    null-PID-free PAT-like approach: set adaptation_field_control and flag on
    the first packet when possible. Best-effort; splice hitch is acceptable.
    """
    if len(chunk) < TS_PACKET_SIZE or chunk[0] != 0x47:
        return chunk
    pkt = bytearray(chunk[:TS_PACKET_SIZE])
    afc = (pkt[3] >> 4) & 0x03
    if afc in (0b10, 0b11) and len(pkt) > 5 and pkt[4] >= 1:
        # adaptation field present; set discontinuity_indicator (bit 7 of flags)
        pkt[5] = pkt[5] | 0x80
        return bytes(pkt) + chunk[TS_PACKET_SIZE:]
    # No adaptation field: insert 1-byte adaptation with discontinuity
    # Original: sync, pid, flags with payload only (afc=01)
    # Rebuild first packet with afc=11 (adaptation + payload), shorten payload
    pid_hi, pid_lo = pkt[1], pkt[2]
    cc = pkt[3] & 0x0F
    payload = bytes(pkt[4:])
    # adaptation_field_length=1, flags=0x80 (discontinuity), then payload truncated
    new_pkt = bytearray(TS_PACKET_SIZE)
    new_pkt[0] = 0x47
    new_pkt[1] = pid_hi
    new_pkt[2] = pid_lo
    new_pkt[3] = 0x30 | cc  # adaptation + payload
    new_pkt[4] = 1
    new_pkt[5] = 0x80
    room = TS_PACKET_SIZE - 6
    new_pkt[6 : 6 + min(room, len(payload))] = payload[:room]
    return bytes(new_pkt) + chunk[TS_PACKET_SIZE:]


async def iter_hold_file(
    hold_path: HoldPath,
    *,
    chunk_size: int = DEFAULT_HOLD_CHUNK,
) -> AsyncIterator[bytes]:
    """Infinite loop reading hold MPEG-TS file in chunk_size pieces (caller paces)."""
    path = Path(hold_path)
    if not path.is_file():
        raise FileNotFoundError(f"Plex hold TS missing: {path}")
    data = path.read_bytes()
    if not data:
        raise ValueError(f"Plex hold TS empty: {path}")
    # Align loop to 188-byte packets
    usable = len(data) - (len(data) % TS_PACKET_SIZE)
    if usable <= 0:
        raise ValueError(f"Plex hold TS too short: {path}")
    data = data[:usable]
    while True:
        for i in range(0, len(data), chunk_size):
            piece = data[i : i + chunk_size]
            # pad to packet boundary for last slice
            rem = len(piece) % TS_PACKET_SIZE
            if rem:
                piece = piece[: len(piece) - rem]
            if piece:
                yield piece


async def video_hold_mux(
    upstream: AsyncIterator[bytes],
    *,
    hold_path: Optional[HoldPath] = None,
    silence_sec: Optional[float] = None,
    rehold_on_silence: bool = True,
) -> AsyncIterator[bytes]:
    """Yield hold until upstream has real video; optionally re-hold on silence/nulls.

    When ``rehold_on_silence`` is False (YouTube wait-phase on native /auto/v*):
    emit hold only until the first non-null splice, then pass upstream forever.
    That avoids Archive-style post-splice black freeze while still covering the
    youtube_full_cache tune-buffer gap that returns Plex to the guide.
    """
    path = Path(hold_path) if hold_path else default_hold_path()
    if silence_sec is None:
        silence_sec = silence_sec_from_env()
    queue: asyncio.Queue[Optional[bytes]] = asyncio.Queue(maxsize=64)
    stop = asyncio.Event()

    async def _pump_upstream() -> None:
        try:
            async for chunk in upstream:
                if stop.is_set():
                    break
                # Drop pure null keepalives; enqueue real (or mixed) data
                if is_all_null_keepalive(chunk):
                    continue
                cleaned = strip_null_packets(chunk)
                if not cleaned:
                    continue
                while True:
                    try:
                        queue.put_nowait(cleaned)
                        break
                    except asyncio.QueueFull:
                        try:
                            queue.get_nowait()
                        except asyncio.QueueEmpty:
                            pass
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("video_hold upstream ended: %s", exc)
        finally:
            try:
                queue.put_nowait(None)  # sentinel EOF
            except asyncio.QueueFull:
                pass

    pump = asyncio.create_task(_pump_upstream(), name="plex-video-hold-upstream")
    holding = True
    hold_iter = iter_hold_file(path)
    first_upstream = True

    try:
        while True:
            if holding:
                # Race paced hold vs upstream so we splice as soon as video arrives
                try:
                    hold_chunk = await hold_iter.__anext__()
                except StopAsyncIteration:
                    hold_iter = iter_hold_file(path)
                    hold_chunk = await hold_iter.__anext__()
                pace = hold_chunk_pace_sec(len(hold_chunk))
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=pace)
                except asyncio.TimeoutError:
                    yield hold_chunk
                    continue
                if item is None:
                    # Upstream EOF while holding — stop (client should disconnect)
                    break
                holding = False
                if first_upstream:
                    item = discontinuity_flag_chunk(item)
                    first_upstream = False
                    logger.info(
                        "video_hold: spliced to upstream "
                        "(silence_sec=%.1f rehold=%s)",
                        silence_sec,
                        rehold_on_silence,
                    )
                yield item
                continue

            # Playing upstream — wait for next chunk or long silence timeout
            if rehold_on_silence:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=silence_sec)
                except asyncio.TimeoutError:
                    logger.info(
                        "video_hold: upstream silent >%.1fs — resuming hold",
                        silence_sec,
                    )
                    holding = True
                    first_upstream = True
                    continue
            else:
                # Wait-phase: block until next real chunk (no black re-hold)
                item = await queue.get()

            if item is None:
                if not rehold_on_silence:
                    # End of upstream after wait-phase splice — stop cleanly
                    break
                logger.info("video_hold: upstream EOF — resuming hold")
                holding = True
                first_upstream = True
                # Do not break — keep hold for mid-show item gaps until client disconnects
                continue
            yield item
    finally:
        stop.set()
        pump.cancel()
        try:
            await pump
        except asyncio.CancelledError:
            pass
        try:
            await hold_iter.aclose()
        except Exception:
            pass


def youtube_wait_hold_env_enabled() -> bool:
    """STREAMTV_PLEX_VIDEO_HOLD_YOUTUBE defaults off (spinner/black while cold).

    Opt-in with STREAMTV_PLEX_VIDEO_HOLD_YOUTUBE=1 once on-air downloads are reliable.
    """
    return os.environ.get("STREAMTV_PLEX_VIDEO_HOLD_YOUTUBE", "0").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def channel_needs_youtube_wait_hold(channel_number: str, db: Any) -> bool:
    """True when youtube_full_cache is on and this channel's on-air/playlist is YouTube.

    Archive/CDN-first channels must not be wrapped (copy-mode splice black freeze).
    """
    if not youtube_wait_hold_env_enabled():
        return False
    try:
        from streamtv.cache.playback_mode import youtube_full_cache_enabled
        from streamtv.database.models import (
            Channel,
            ChannelPlaybackPosition,
            MediaItem,
            Playlist,
            PlaylistItem,
            StreamSource,
        )
    except Exception:
        return False

    if not youtube_full_cache_enabled():
        return False

    ch = (
        db.query(Channel)
        .filter(Channel.number == str(channel_number), Channel.enabled == True)  # noqa: E712
        .first()
    )
    if not ch:
        return False

    pos = (
        db.query(ChannelPlaybackPosition)
        .filter(ChannelPlaybackPosition.channel_id == ch.id)
        .first()
    )
    if pos and pos.last_item_media_id:
        media = (
            db.query(MediaItem).filter(MediaItem.id == pos.last_item_media_id).first()
        )
        if media is not None and media.source == StreamSource.YOUTUBE:
            return True

    hit = (
        db.query(MediaItem.id)
        .join(PlaylistItem, PlaylistItem.media_item_id == MediaItem.id)
        .join(Playlist, Playlist.id == PlaylistItem.playlist_id)
        .filter(
            Playlist.channel_id == ch.id,
            MediaItem.source == StreamSource.YOUTUBE,
        )
        .limit(1)
        .first()
    )
    return hit is not None


def maybe_wrap_mpegts_hold(
    response: Any,
    *,
    hold_path: Optional[HoldPath] = None,
    silence_sec: Optional[float] = None,
    enabled: Optional[bool] = None,
    rehold_on_silence: bool = True,
) -> Any:
    """Wrap a StreamingResponse body with video hold when enabled and hold file exists."""
    if enabled is None:
        enabled = os.environ.get("STREAMTV_PLEX_VIDEO_HOLD", "1").strip() not in (
            "0",
            "false",
            "no",
            "off",
        )
    if not enabled:
        return response
    if not isinstance(response, StreamingResponse):
        return response
    path = Path(hold_path) if hold_path else default_hold_path()
    if not path.is_file():
        logger.warning("Plex video hold disabled — missing %s", path)
        return response

    upstream_body = response.body_iterator
    effective_silence = (
        silence_sec if silence_sec is not None else silence_sec_from_env()
    )

    async def _held() -> AsyncIterator[bytes]:
        async for chunk in video_hold_mux(
            upstream_body,
            hold_path=path,
            silence_sec=effective_silence,
            rehold_on_silence=rehold_on_silence,
        ):
            yield chunk

    return StreamingResponse(
        _held(),
        status_code=response.status_code,
        headers=dict(response.headers),
        media_type=response.media_type or "video/mp2t",
        background=response.background,
    )


def maybe_wrap_youtube_wait_hold(
    response: Any,
    channel_number: str,
    db: Any,
    *,
    hold_path: Optional[HoldPath] = None,
) -> Any:
    """Hold only for YouTube full-cache channels during null-keepalive wait (no re-hold)."""
    if not channel_needs_youtube_wait_hold(channel_number, db):
        return response
    logger.info(
        "video_hold: YouTube wait-phase wrap for channel %s (rehold=False)",
        channel_number,
    )
    return maybe_wrap_mpegts_hold(
        response,
        hold_path=hold_path,
        rehold_on_silence=False,
    )


async def proxy_upstream_bytes(url: str, *, timeout: float = 0.0) -> AsyncIterator[bytes]:
    """Stream bytes from an upstream HTTP MPEG-TS URL (Tunarr etc.)."""
    import httpx

    timeout_cfg = httpx.Timeout(None if timeout <= 0 else timeout, connect=15.0)
    async with httpx.AsyncClient(timeout=timeout_cfg, follow_redirects=True) as client:
        async with client.stream("GET", url) as resp:
            resp.raise_for_status()
            async for chunk in resp.aiter_bytes(chunk_size=DEFAULT_HOLD_CHUNK):
                if chunk:
                    yield chunk
