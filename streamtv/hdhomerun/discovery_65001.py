"""Native HDHomeRun UDP discovery on port 65001.

Plex's primary HDHR scan uses this protocol (not only SSDP on 1900).
Implements a minimal discover-request / discover-reply so StreamTV remains
visible when UDP 1900 is contended by Tunarr/Plex.

Wire format follows the Silicondust HDHomeRun protocol (TLV tags):
  tag 0x01 DeviceID, 0x02 DeviceAuth, 0x27 BaseURL, 0x2A LineupURL, …
"""

from __future__ import annotations

import logging
import socket
import struct
import threading
from typing import Optional

logger = logging.getLogger(__name__)

HDHR_DISCOVER_PORT = 65001
# Request type 2 = discover request; type 3 = discover reply
_TYPE_DISCOVER_REQ = 2
_TYPE_DISCOVER_REPLY = 3

_TAG_DEVICE_ID = 0x01
_TAG_DEVICE_AUTH = 0x02
_TAG_TUNER_COUNT = 0x10
_TAG_BASE_URL = 0x27
_TAG_LINEUP_URL = 0x2A


def _tlv(tag: int, value: bytes) -> bytes:
    return bytes([tag, len(value)]) + value


def _crc32_mpeg(data: bytes) -> int:
    """MPEG-style CRC32 used by HDHomeRun frames (poly 0x04C11DB7, init 0xFFFFFFFF)."""
    crc = 0xFFFFFFFF
    for byte in data:
        crc ^= byte << 24
        for _ in range(8):
            if crc & 0x80000000:
                crc = ((crc << 1) ^ 0x04C11DB7) & 0xFFFFFFFF
            else:
                crc = (crc << 1) & 0xFFFFFFFF
    return crc


def build_discover_reply(
    device_id: str,
    base_url: str,
    tuner_count: int = 4,
    device_auth: str = "streamtv",
) -> bytes:
    """Build a binary discover-reply frame for the given device."""
    device_id_bytes = bytes.fromhex(device_id.zfill(8)[:8])
    base = base_url.rstrip("/")
    payload = b"".join(
        [
            _tlv(_TAG_DEVICE_ID, device_id_bytes),
            _tlv(_TAG_DEVICE_AUTH, device_auth.encode("ascii")),
            _tlv(_TAG_TUNER_COUNT, bytes([tuner_count & 0xFF])),
            _tlv(_TAG_BASE_URL, base.encode("ascii")),
            _tlv(_TAG_LINEUP_URL, f"{base}/lineup.json".encode("ascii")),
        ]
    )
    header = struct.pack(">HH", _TYPE_DISCOVER_REPLY, len(payload))
    body = header + payload
    crc = _crc32_mpeg(body)
    return body + struct.pack(">I", crc)


class HDHomeRunDiscoveryServer:
    """UDP listener on port 65001 answering HDHomeRun discover requests."""

    def __init__(
        self,
        device_id: str,
        base_url: str,
        tuner_count: int = 4,
        bind_host: str = "0.0.0.0",
        port: int = HDHR_DISCOVER_PORT,
    ):
        self.device_id = device_id.upper()
        self.base_url = base_url.rstrip("/")
        self.tuner_count = tuner_count
        self.bind_host = bind_host
        self.port = port
        self.running = False
        self.socket: Optional[socket.socket] = None
        self.thread: Optional[threading.Thread] = None
        self.bound = False
        self.last_error: Optional[str] = None
        self.replies_sent = 0

    @property
    def status(self) -> dict:
        return {
            "enabled": True,
            "bound": self.bound,
            "port": self.port,
            "device_id": self.device_id,
            "base_url": self.base_url,
            "replies_sent": self.replies_sent,
            "last_error": self.last_error,
        }

    def start(self) -> bool:
        if self.running:
            return self.bound
        self.running = True
        self.thread = threading.Thread(
            target=self._run, name="hdhr-discover-65001", daemon=True
        )
        self.thread.start()
        return True

    def stop(self) -> None:
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except OSError:
                pass
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)

    def _run(self) -> None:
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.bind_host, self.port))
            self.socket.settimeout(1.0)
            self.bound = True
            logger.info(
                "HDHomeRun native discovery listening on UDP %s:%s "
                "(DeviceID=%s)",
                self.bind_host,
                self.port,
                self.device_id,
            )
        except OSError as exc:
            self.bound = False
            self.last_error = str(exc)
            logger.warning(
                "HDHomeRun discovery port %s unavailable: %s "
                "(SSDP/manual add still work)",
                self.port,
                exc,
            )
            self.running = False
            return

        reply = build_discover_reply(
            self.device_id, self.base_url, self.tuner_count
        )
        while self.running:
            try:
                data, addr = self.socket.recvfrom(2048)
            except socket.timeout:
                continue
            except OSError:
                if self.running:
                    logger.debug("HDHR discovery socket closed")
                break
            if len(data) < 4:
                continue
            msg_type = struct.unpack(">H", data[:2])[0]
            if msg_type != _TYPE_DISCOVER_REQ:
                continue
            try:
                self.socket.sendto(reply, addr)
                self.replies_sent += 1
                logger.debug("HDHR discover reply → %s", addr)
            except OSError as exc:
                self.last_error = str(exc)
                logger.warning("HDHR discover reply failed: %s", exc)
