"""Browser preview remux — NOT streaming bedrock.

Joins the existing continuous `/iptv/channel/{n}.ts` feed via local FFmpeg
copy-remux so mpegts.js gets regenerated PTS and SPS/PPS on keyframes.
Plex/HDHomeRun keep using the raw IPTV/HDHR endpoints unchanged.
"""

from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from ..config import config
from ..ffmpeg.constants import BSF_H264_DUMP_EXTRA, FFLAGS_NETWORK_STREAMING

logger = logging.getLogger(__name__)

router = APIRouter(tags=["player-preview"])


def _ffmpeg_bin() -> str:
    path = getattr(getattr(config, "ffmpeg", None), "ffmpeg_path", None) or "ffmpeg"
    return str(path)


def _local_iptv_ts_url(request: Request, channel_number: str) -> str:
    # Prefer loopback so preview remux never hairpins via LAN/DNS.
    port = request.url.port or getattr(getattr(config, "server", None), "port", None) or 8410
    return f"http://127.0.0.1:{port}/iptv/channel/{channel_number}.ts"


@router.get("/player/live/{channel_number}.ts")
async def player_live_preview_ts(channel_number: str, request: Request) -> StreamingResponse:
    """MSE-friendly live TS for `/player` (mpegts.js), derived from continuous playout."""
    channel_number = str(channel_number).strip()
    if not channel_number or "/" in channel_number or ".." in channel_number:
        raise HTTPException(status_code=400, detail="Invalid channel number")

    source_url = _local_iptv_ts_url(request, channel_number)
    ffmpeg = _ffmpeg_bin()
    # Copy remux: regenerate timestamps (default) + reinject SPS/PPS at keyframes.
    # Do not touch ChannelManager / mpegts_streamer — read the public IPTV join only.
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-fflags",
        FFLAGS_NETWORK_STREAMING,
        "-i",
        source_url,
        "-c",
        "copy",
        "-bsf:v",
        BSF_H264_DUMP_EXTRA,
        "-f",
        "mpegts",
        "pipe:1",
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=1024 * 1024,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=f"ffmpeg not found: {ffmpeg}") from exc

    logger.info(
        "player preview remux start channel=%s pid=%s source=%s",
        channel_number,
        proc.pid,
        source_url,
    )

    async def generate() -> AsyncIterator[bytes]:
        assert proc.stdout is not None
        try:
            while True:
                if await request.is_disconnected():
                    break
                chunk = await proc.stdout.read(64 * 1024)
                if not chunk:
                    break
                yield chunk
        except asyncio.CancelledError:
            raise
        finally:
            await _stop_proc(proc, channel_number)

    return StreamingResponse(
        generate(),
        media_type="video/mp2t",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate, private",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _stop_proc(proc: asyncio.subprocess.Process, channel_number: str) -> None:
    if proc.returncode is not None:
        return
    try:
        proc.terminate()
    except ProcessLookupError:
        return
    try:
        await asyncio.wait_for(proc.wait(), timeout=3.0)
    except (asyncio.TimeoutError, ProcessLookupError):
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        try:
            await proc.wait()
        except ProcessLookupError:
            pass
    err: Optional[bytes] = None
    if proc.stderr is not None:
        try:
            err = await proc.stderr.read()
        except Exception:
            err = None
    if err:
        logger.warning(
            "player preview remux stderr channel=%s: %s",
            channel_number,
            err.decode("utf-8", "replace")[:500],
        )
    logger.info(
        "player preview remux stop channel=%s rc=%s",
        channel_number,
        proc.returncode,
    )
