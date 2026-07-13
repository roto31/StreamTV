"""MPEG-TS null-packet keepalive for HDHomeRun / Plex tune timeouts."""

# Standard 188-byte MPEG-TS null packet (sync 0x47, PID 0x1FFF)
_MPEGTS_NULL_PACKET = bytes([0x47, 0x1F, 0xFF, 0x10] + [0xFF] * 184)
_CHUNK_SIZE = 8192
_KEEPALIVE_CHUNK = (_MPEGTS_NULL_PACKET * ((_CHUNK_SIZE // 188) + 1))[:_CHUNK_SIZE]


def keepalive_chunk() -> bytes:
    """One ~8 KiB chunk of valid MPEG-TS null packets for tune keepalive."""
    return _KEEPALIVE_CHUNK
