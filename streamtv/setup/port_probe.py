"""Port availability probe and suggested alternatives."""

from __future__ import annotations

import socket
from dataclasses import dataclass
from typing import List


DEFAULT_SUGGESTIONS = (8411, 8412, 8500, 9000)


@dataclass
class PortProbeResult:
    port: int
    available: bool
    suggestions: List[int]
    message: str


def _can_bind(port: int, host: str = "0.0.0.0") -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def suggested_ports(preferred: int = 8410, limit: int = 4) -> List[int]:
    out: List[int] = []
    for candidate in DEFAULT_SUGGESTIONS:
        if candidate == preferred:
            continue
        if _can_bind(candidate):
            out.append(candidate)
        if len(out) >= limit:
            break
    # Fall back to scanning nearby ports
    if len(out) < limit:
        for candidate in range(preferred + 1, preferred + 50):
            if candidate in out or candidate == preferred:
                continue
            if _can_bind(candidate):
                out.append(candidate)
            if len(out) >= limit:
                break
    return out


def probe_port(port: int) -> PortProbeResult:
    available = _can_bind(port)
    suggestions = suggested_ports(preferred=port) if not available else []
    if available:
        message = f"Port {port} is available."
    else:
        message = (
            f"Port {port} is in use. Choose another port "
            f"(suggested: {', '.join(str(p) for p in suggestions) or 'none'})."
        )
    return PortProbeResult(
        port=port,
        available=available,
        suggestions=suggestions,
        message=message,
    )
