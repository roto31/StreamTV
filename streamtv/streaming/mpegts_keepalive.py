"""MPEG-TS null-packet keepalive for HDHomeRun / Plex tune timeouts."""

# Standard 188-byte MPEG-TS null packet (sync 0x47, PID 0x1FFF)
_MPEGTS_NULL_PACKET = bytes([0x47, 0x1F, 0xFF, 0x10] + [0xFF] * 184)
# Exactly N full packets (~8 KiB). Never truncate mid-packet: 8192 % 188 == 108
# would orphan trailing bytes and desync Plex/Apple TV demuxers (s1001).
_KEEPALIVE_PACKET_COUNT = 43  # 43 * 188 = 8084
_KEEPALIVE_CHUNK = _MPEGTS_NULL_PACKET * _KEEPALIVE_PACKET_COUNT


def keepalive_chunk() -> bytes:
    """One ~8 KiB chunk of valid MPEG-TS null packets for tune keepalive."""
    return _KEEPALIVE_CHUNK
