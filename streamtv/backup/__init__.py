"""Portable configuration backup and restore (format_version 1)."""

from .paths import (
    RESTORE_PENDING_MARKER,
    RESTORE_PENDING_ZIP,
    backup_root,
    project_root,
)
from .restore import apply_pending_restore, restore_from_zip, validate_backup_zip
from .scheduler import BackupScheduler, get_scheduler, schedule_backup
from .snapshot import create_snapshot, snapshot_status

__all__ = [
    "RESTORE_PENDING_MARKER",
    "RESTORE_PENDING_ZIP",
    "BackupScheduler",
    "apply_pending_restore",
    "backup_root",
    "create_snapshot",
    "get_scheduler",
    "project_root",
    "restore_from_zip",
    "schedule_backup",
    "snapshot_status",
    "validate_backup_zip",
]
