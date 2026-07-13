"""Single-instance enforcement via pidfile + listen-port check.

Prevents the Errno 48 / mid-stream Connection refused class of failures
where a second StreamTV process binds 8410 (or fails to) while FFmpeg is
still reading the first instance's /cache/files HTTP URLs.
"""

from __future__ import annotations

import atexit
import logging
import os
import socket
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_PIDFILE = Path(".streamtv.pid")


class InstanceLockError(RuntimeError):
    """Raised when another StreamTV instance already owns the runtime."""


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _port_in_use(host: str, port: int) -> bool:
    bind_host = "0.0.0.0" if host in ("0.0.0.0", "::", "") else host
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((bind_host, port))
        return False
    except OSError:
        return True
    finally:
        sock.close()


def acquire_instance_lock(
    pidfile: Path = DEFAULT_PIDFILE,
    host: str = "0.0.0.0",
    port: int = 8410,
) -> Path:
    """Refuse to start if another live StreamTV owns the pidfile or port."""
    if pidfile.exists():
        try:
            existing = int(pidfile.read_text().strip() or "0")
        except ValueError:
            existing = 0
        if existing and existing != os.getpid() and _pid_alive(existing):
            raise InstanceLockError(
                f"StreamTV already running (pid {existing}, pidfile {pidfile}). "
                f"Stop it before starting another instance."
            )
        logger.warning(f"Removing stale pidfile {pidfile} (pid {existing})")
        try:
            pidfile.unlink()
        except OSError:
            pass

    if _port_in_use(host, port):
        raise InstanceLockError(
            f"Port {port} is already bound — another StreamTV (or process) "
            f"is listening. Refusing to start a second instance."
        )

    pidfile.write_text(f"{os.getpid()}\n")
    atexit.register(_release_instance_lock, pidfile)
    logger.info(f"Acquired instance lock: {pidfile} (pid {os.getpid()})")
    return pidfile


def _release_instance_lock(pidfile: Path) -> None:
    try:
        if pidfile.exists():
            current = int(pidfile.read_text().strip() or "0")
            if current == os.getpid():
                pidfile.unlink()
                logger.info(f"Released instance lock: {pidfile}")
    except Exception as exc:
        logger.debug(f"Pidfile cleanup skipped: {exc}")
