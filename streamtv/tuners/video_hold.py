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
# Archive FFmpeg often emits a tiny PAT/PMT/video burst then stdout-stalls while
# the non-faststart MP4 opens. Splicing on that burst (rehold=False) leaves the
# client with no further A/V. Require sustained bytes before leaving the hold.
DEFAULT_ARCHIVE_MIN_SPLICE_BYTES = 65_536

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


HOLD_GEOMETRY_480 = (640, 480)
HOLD_GEOMETRY_720 = (1280, 720)


def default_hold_path() -> Path:
    env = os.environ.get("STREAMTV_PLEX_HOLD_TS", "").strip()
    if env:
        return Path(env).expanduser()
    # Repo root / data/plex_hold.ts relative to this package: streamtv/tuners/
    return Path(__file__).resolve().parents[2] / "data" / "plex_hold.ts"


def default_archive_hold_480_path() -> Path:
    env = os.environ.get("STREAMTV_PLEX_HOLD_ARCHIVE_TS", "").strip()
    if env:
        return Path(env).expanduser()
    return Path(__file__).resolve().parents[2] / "data" / "plex_hold_480.ts"


def archive_hold_paths_by_geometry() -> dict[tuple[int, int], Path]:
    """Hold asset per program geometry; a hold whose SPS differs from the
    program melts Apple TV after the splice (Lesson 41c), so no fallback."""
    return {
        HOLD_GEOMETRY_480: default_archive_hold_480_path(),
        HOLD_GEOMETRY_720: default_hold_path(),
    }


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


# MPEG-TS PSI / common FFmpeg PMT PID — never truncate these for discontinuity.
_PSI_OR_PMT_PIDS = frozenset({0x0000, 0x0001, 0x0010, 0x0011, 0x0012, 0x0013, 0x0014, 0x1000})
# FFmpeg mpegts default elementary video PID in StreamTV holds / remux.
_DEFAULT_VIDEO_PID = 0x0100


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


def discontinuity_flag_media_chunk(chunk: bytes) -> bytes:
    """Like discontinuity_flag_chunk, but never truncates PSI/PMT packets.

    Archive splices often start with SDT/PAT/PMT (payload-only). Mutating those
    by stuffing an adaptation field corrupts table sections and leaves Plex /
    Apple TV decoders in a green/pixel melt after the hold.
    """
    if len(chunk) < TS_PACKET_SIZE or chunk[0] != 0x47:
        return chunk
    n = len(chunk) // TS_PACKET_SIZE
    for i in range(n):
        off = i * TS_PACKET_SIZE
        pkt = chunk[off : off + TS_PACKET_SIZE]
        pid = pid_of_packet(pkt)
        if pid < 0 or pid in _PSI_OR_PMT_PIDS or pid == NULL_PID:
            continue
        flagged = discontinuity_flag_chunk(pkt)
        return chunk[:off] + flagged + chunk[off + TS_PACKET_SIZE :]
    return chunk


def pending_has_video_pusi(chunks: list[bytes], *, video_pid: int = _DEFAULT_VIDEO_PID) -> bool:
    """True if buffered upstream contains a video PES start (random-access hint)."""
    for chunk in chunks:
        if len(chunk) < TS_PACKET_SIZE or chunk[0] != 0x47:
            continue
        n = len(chunk) // TS_PACKET_SIZE
        for i in range(n):
            pkt = chunk[i * TS_PACKET_SIZE : (i + 1) * TS_PACKET_SIZE]
            if pid_of_packet(pkt) != video_pid:
                continue
            if pkt[1] & 0x40:  # payload_unit_start_indicator
                return True
    return False


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
    hold_label: Optional[str] = None,
    min_splice_bytes: int = 0,
    require_video_pusi: bool = False,
) -> AsyncIterator[bytes]:
    """Yield hold until upstream has real video; optionally re-hold on silence/nulls.

    When ``rehold_on_silence`` is False (YouTube wait-phase on native /auto/v*):
    emit hold only until the first non-null splice, then pass upstream forever.
    That avoids Archive-style post-splice black freeze while still covering the
    youtube_full_cache tune-buffer gap that returns Plex to the guide.

    ``min_splice_bytes`` (Archive wait-phase) keeps emitting hold until at least
    that many cleaned upstream bytes are buffered, so a tiny first FFmpeg burst
    followed by stdout stall does not leave the client with no A/V.
    ``require_video_pusi`` also waits for a video PES start before splicing so
    decoders are not handed mid-GOP after the black hold.
    """
    path = Path(hold_path) if hold_path else default_hold_path()
    if silence_sec is None:
        silence_sec = silence_sec_from_env()
    splice_floor = max(0, int(min_splice_bytes))
    queue: asyncio.Queue[Optional[bytes]] = asyncio.Queue(maxsize=64)
    stop = asyncio.Event()

    async def _pump_upstream() -> None:
        # FFmpeg reads are 8192 bytes (43 TS packets + 96 byte tail). Cutting
        # each read on its own drops the straddling packet and the next read
        # resyncs, which is a continuity jump every chunk — Plex tears.
        carry = b""
        try:
            async for chunk in upstream:
                if stop.is_set():
                    break
                # A new chunk that already starts on 0x47 is not the tail of the
                # previous packet (tests, or a resync). Drop the orphan tail.
                # A real FFmpeg read that continues a split packet does not
                # start with 0x47, so the tail is prepended.
                if carry and chunk[:1] == b"\x47" and carry[:1] == b"\x47":
                    carry = b""
                data = carry + chunk
                if data and data[0] != 0x47:
                    sync_at = data.find(0x47)
                    if sync_at < 0:
                        carry = b""
                        continue
                    data = data[sync_at:]
                usable = len(data) - (len(data) % TS_PACKET_SIZE)
                carry = data[usable:]
                piece = data[:usable]
                if not piece or is_all_null_keepalive(piece):
                    continue
                cleaned = strip_null_packets(piece)
                if not cleaned:
                    continue
                # Block when full. Dropping the oldest chunk opens continuity
                # gaps and Plex/Apple TV tear for the rest of the item.
                await queue.put(cleaned)
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
    pending: list[bytes] = []
    pending_bytes = 0

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
                    # Upstream EOF while holding — flush any buffered burst, else stop
                    if not pending:
                        break
                    item = b""  # fall through to splice pending only
                else:
                    pending.append(item)
                    pending_bytes += len(item)
                    thin = splice_floor > 0 and pending_bytes < splice_floor
                    no_pusi = require_video_pusi and not pending_has_video_pusi(
                        pending
                    )
                    if thin or no_pusi:
                        continue
                holding = False
                flush = pending
                pending = []
                flush_bytes = pending_bytes
                pending_bytes = 0
                if first_upstream and flush:
                    first = flush[0]
                    # Flag discontinuity on first media PID — never truncate SDT/PAT/PMT.
                    flush[0] = discontinuity_flag_media_chunk(first)
                    first_upstream = False
                    logger.info(
                        "video_hold: spliced to upstream "
                        "(silence_sec=%.1f rehold=%s hold=%s flush_bytes=%d)",
                        silence_sec,
                        rehold_on_silence,
                        hold_label or path.name,
                        flush_bytes,
                    )
                for piece in flush:
                    if piece:
                        yield piece
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
    hold_label: Optional[str] = None,
    min_splice_bytes: int = 0,
    require_video_pusi: bool = False,
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
            hold_label=hold_label,
            min_splice_bytes=min_splice_bytes,
            require_video_pusi=require_video_pusi,
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


def archive_wait_hold_channels() -> frozenset[str]:
    """Channels allowlisted for Archive wait-phase hold (Lesson 41c).

    STREAMTV_PLEX_VIDEO_HOLD_ARCHIVE_CHANNELS is a comma list; empty means none.
    Archive copy-mode splices can black-freeze Apple TV, so there is no wildcard.
    """
    raw = os.environ.get("STREAMTV_PLEX_VIDEO_HOLD_ARCHIVE_CHANNELS", "")
    return frozenset(c.strip() for c in raw.split(",") if c.strip())


def archive_hold_pick(
    stream_url: Optional[str],
) -> tuple[Optional[Path], Optional[tuple[int, int]], str]:
    """Pick the hold asset matching an Archive item's sidecar geometry.

    Returns (hold_path or None, geometry or None, reason). None means skip the
    wrap: unknown geometry or a size with no hold asset must not be guessed.
    """
    from streamtv.utils import archive_probe_cache

    if not stream_url or archive_probe_cache.archive_item_key(stream_url) is None:
        return None, None, "not an archive.org item"
    geometry = archive_probe_cache.video_geometry(archive_probe_cache.load(stream_url))
    if geometry is None:
        return None, None, "no sidecar geometry (run warm_archive_probe_cache.py)"
    path = archive_hold_paths_by_geometry().get(geometry)
    if path is None:
        return None, geometry, f"no hold asset for {geometry[0]}x{geometry[1]}"
    if not path.is_file():
        return None, geometry, f"hold asset missing: {path}"
    return path, geometry, "geometry match"


def on_air_media_url(channel_number: str, db: Any) -> Optional[str]:
    """URL of the channel's current playout item (continuous playout anchor)."""
    from streamtv.database.models import Channel, ChannelPlaybackPosition, MediaItem

    ch = (
        db.query(Channel)
        .filter(Channel.number == str(channel_number), Channel.enabled == True)  # noqa: E712
        .first()
    )
    if not ch:
        return None
    pos = (
        db.query(ChannelPlaybackPosition)
        .filter(ChannelPlaybackPosition.channel_id == ch.id)
        .first()
    )
    if not pos or not pos.last_item_media_id:
        return None
    media = db.query(MediaItem).filter(MediaItem.id == pos.last_item_media_id).first()
    return media.url if media is not None else None


def maybe_wrap_archive_wait_hold(
    response: Any,
    channel_number: str,
    db: Any,
) -> Any:
    """Hold an allowlisted Archive channel until first real video (no re-hold).

    Non-faststart multi-GB Archive MP4s can take ~40s to open over HTTP; null
    keepalives make Plex abandon the tune before the first program TS. The hold
    must match the on-air item's geometry, otherwise the wrap is skipped.
    """
    if str(channel_number) not in archive_wait_hold_channels():
        return response
    try:
        url = on_air_media_url(channel_number, db)
    except Exception as exc:
        logger.warning(
            "video_hold: Archive wait-phase skip for channel %s — on-air lookup failed: %s",
            channel_number,
            exc,
        )
        return response
    path, geometry, reason = archive_hold_pick(url)
    if path is None or geometry is None:
        logger.info(
            "video_hold: Archive wait-phase skip for channel %s — %s",
            channel_number,
            reason,
        )
        return response
    label = f"{geometry[0]}x{geometry[1]}"
    logger.info(
        "video_hold: Archive wait-phase wrap for channel %s hold=%s path=%s (rehold=False)",
        channel_number,
        label,
        path,
    )
    return maybe_wrap_mpegts_hold(
        response,
        hold_path=path,
        rehold_on_silence=False,
        hold_label=label,
        min_splice_bytes=DEFAULT_ARCHIVE_MIN_SPLICE_BYTES,
        require_video_pusi=True,
    )


async def proxy_upstream_bytes(url: str, *, timeout: float = 0.0) -> AsyncIterator[bytes]:
    """Stream bytes from an upstream HTTP MPEG-TS URL."""
    import httpx

    timeout_cfg = httpx.Timeout(None if timeout <= 0 else timeout, connect=15.0)
    async with httpx.AsyncClient(timeout=timeout_cfg, follow_redirects=True) as client:
        async with client.stream("GET", url) as resp:
            resp.raise_for_status()
            async for chunk in resp.aiter_bytes(chunk_size=DEFAULT_HOLD_CHUNK):
                if chunk:
                    yield chunk
