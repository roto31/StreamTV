"""First-run setup helpers (SetupDone marker, port, MCP offer)."""

from .first_run_state import (
    SETUP_DONE_FILENAME,
    clear_setup_done,
    is_setup_done,
    read_setup_done,
    setup_done_paths,
    write_setup_done,
)
from .port_probe import PortProbeResult, probe_port, suggested_ports

__all__ = [
    "SETUP_DONE_FILENAME",
    "PortProbeResult",
    "clear_setup_done",
    "is_setup_done",
    "probe_port",
    "read_setup_done",
    "setup_done_paths",
    "suggested_ports",
    "write_setup_done",
]
