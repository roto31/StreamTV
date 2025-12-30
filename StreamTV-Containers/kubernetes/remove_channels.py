#!/usr/bin/env python3
"""
Utility to remove one or more channels (and associated schedules/playlists)
from the current StreamTV database, even when the live schema has drifted
from the current ORM models (e.g., older SQLite without new columns).

Usage:
    python3 remove_channels.py 1939 1940 1850
    python3 remove_channels.py --dry-run 1939

By default, nothing is removed unless channel numbers are provided. When not
in dry-run mode the script will:
- Delete ChannelPlaybackPosition rows for the given numbers
- Delete the Channel row (which cascades to schedules and playlists)
- Commit the transaction
"""

from __future__ import annotations

import argparse
from typing import Iterable, List, Sequence, Tuple

from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from streamtv.database.session import engine


def normalize(numbers: Iterable[str]) -> List[str]:
    cleaned: List[str] = []
    for num in numbers:
        if num is None:
            continue
        val = str(num).strip()
        if not val:
            continue
        cleaned.append(val)
    return cleaned


def _safe_exec(conn, sql: str, params: dict) -> None:
    try:
        conn.execute(text(sql), params)
    except OperationalError as exc:
        print(f"[WARN] Skipping step due to schema mismatch: {exc}")


def remove_channels(numbers: List[str], *, dry_run: bool) -> None:
    if not numbers:
        print("No channel numbers provided; nothing to do.")
        return

    with engine.begin() as conn:
        # Resolve channel ids first using minimal columns (id/number)
        placeholders = ", ".join([f":n{i}" for i in range(len(numbers))])
        params = {f"n{i}": num for i, num in enumerate(numbers)}
        rows = list(conn.execute(text(f"SELECT id, number FROM channels WHERE number IN ({placeholders})"), params))
        if not rows:
            print("No matching channels found.")
            return

        channel_ids = [row[0] for row in rows]
        print(f"[INFO] Removing channels: {', '.join(str(r[1]) for r in rows)} (ids: {channel_ids})")

        # Gather dependent ids with minimal selects to avoid missing columns
        schedule_rows: Sequence[Tuple[int]] = []
        if channel_ids:
            placeholders = ",".join(str(cid) for cid in channel_ids)
            schedule_rows = conn.execute(
                text(f"SELECT id FROM schedules WHERE channel_id IN ({placeholders})")
            ).fetchall()
        schedule_ids = [r[0] for r in schedule_rows]

        playlist_rows: Sequence[Tuple[int]] = []
        if channel_ids:
            placeholders = ",".join(str(cid) for cid in channel_ids)
            playlist_rows = conn.execute(
                text(f"SELECT id FROM playlists WHERE channel_id IN ({placeholders})")
            ).fetchall()
        playlist_ids = [r[0] for r in playlist_rows]

        if dry_run:
            print(f"[DRY-RUN] Would delete playback positions for channel_ids={channel_ids}")
            print(f"[DRY-RUN] Would delete schedule_items for schedule_ids={schedule_ids}")
            print(f"[DRY-RUN] Would delete schedules for channel_ids={channel_ids}")
            print(f"[DRY-RUN] Would delete playlist_items for playlist_ids={playlist_ids}")
            print(f"[DRY-RUN] Would delete playlists for channel_ids={channel_ids}")
            print(f"[DRY-RUN] Would delete channels for ids={channel_ids}")
            return

        # Dependent deletes (order matters)
        # Build simple IN lists using string interpolation (safe for integers we constructed)
        cids_str = ",".join(str(cid) for cid in channel_ids)
        sids_str = ",".join(str(sid) for sid in schedule_ids) if schedule_ids else ""
        pids_str = ",".join(str(pid) for pid in playlist_ids) if playlist_ids else ""

        _safe_exec(conn, f"DELETE FROM channel_playback_positions WHERE channel_id IN ({cids_str})", {})
        if schedule_ids:
            _safe_exec(conn, f"DELETE FROM schedule_items WHERE schedule_id IN ({sids_str})", {})
        _safe_exec(conn, f"DELETE FROM schedules WHERE channel_id IN ({cids_str})", {})
        if playlist_ids:
            _safe_exec(conn, f"DELETE FROM playlist_items WHERE playlist_id IN ({pids_str})", {})
        _safe_exec(conn, f"DELETE FROM playlists WHERE channel_id IN ({cids_str})", {})
        _safe_exec(conn, f"DELETE FROM channels WHERE id IN ({cids_str})", {})

        print("Removal complete.")


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("channels", nargs="*", help="Channel numbers to remove")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be removed without committing changes.",
    )

    args = parser.parse_args(argv)
    numbers = normalize(args.channels)
    remove_channels(numbers, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
