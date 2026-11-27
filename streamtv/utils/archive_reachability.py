"""Archive.org reachability evidence (Issue 75).

Unauthenticated CDN **401** (or a probe that never sent Archive login cookies)
is **not** proof an item is dead. Adult/inappropriate-gated IA items return 401
to anonymous clients and **200** once `logged-in-user` / `logged-in-sig` are
attached — the same cookies production FFmpeg uses.

Metadata edge cases that must **not** become false purges:
- Metadata HTTP timeout/error → UNCERTAIN (keep)
- Filename case / punctuation mismatch → FILENAME_MISMATCH (keep or --fix-urls)
- CDN node unreachable while files[] is non-empty (Issue 32) → do not prune
- Item later restored on IA → historical prune was correct then; restore from
  YAML backup / re-add — never treat one prune as forever

Use these helpers before pruning YAML, shrinking schedules, or deleting DB
playlist rows. Prefer IA metadata file lists and cookie-authenticated probes
over bare curl HEAD.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional


class ArchiveReachability(str, Enum):
    """How to treat an Archive download URL for library/schedule edits."""

    REACHABLE = "reachable"
    """Authenticated or public probe succeeded (2xx)."""

    DEAD_NOT_IN_METADATA = "dead_not_in_metadata"
    """IA metadata lists files and this filename is truly absent after mismatch checks."""

    EMPTY_ITEM = "empty_item"
    """IA metadata returned successfully with zero files — safe prune candidate."""

    AUTH_REQUIRED_OR_GATED = "auth_required_or_gated"
    """401/403 without (or despite incomplete) cookies — keep in library."""

    FILENAME_MISMATCH = "filename_mismatch"
    """Case/punctuation/.ia.mp4 mismatch vs metadata — keep; use --fix-urls."""

    CDN_UNREACHABLE = "cdn_unreachable"
    """Metadata has files but storage/CDN fails (Issue 32) — keep; ops/IA problem."""

    UNCERTAIN = "uncertain"
    """Metadata/network failure or inconclusive probe — keep; do not purge."""


def classify_download_http_status(
    status_code: Optional[int],
    *,
    used_archive_auth_cookies: bool,
) -> ArchiveReachability:
    """Classify a download/CDN HTTP status for purge decisions.

    Bare 401/403 without cookies must never drive stream removal (Issue 75).
    5xx / timeouts with files still in metadata are CDN issues (Issue 32), not
    empties — callers that already know files[] is non-empty should use
    CDN_UNREACHABLE instead of this helper alone.
    """
    if status_code is None:
        return ArchiveReachability.UNCERTAIN
    if 200 <= status_code < 300:
        return ArchiveReachability.REACHABLE
    if status_code in (401, 403):
        # Gated whether or not cookies were sent — never "missing file".
        return ArchiveReachability.AUTH_REQUIRED_OR_GATED
    if status_code == 404:
        return ArchiveReachability.UNCERTAIN  # confirm via metadata before prune
    if status_code >= 500:
        return ArchiveReachability.CDN_UNREACHABLE
    return ArchiveReachability.UNCERTAIN


def classify_metadata_outcome(
    *,
    metadata_fetched: bool,
    file_count: Optional[int] = None,
    filename_in_listing: Optional[bool] = None,
    filename_mismatch_only: bool = False,
) -> ArchiveReachability:
    """Classify IA metadata results for purge decisions (Issue 75 edge cases)."""
    if not metadata_fetched:
        return ArchiveReachability.UNCERTAIN
    if file_count is None:
        return ArchiveReachability.UNCERTAIN
    if file_count == 0:
        return ArchiveReachability.EMPTY_ITEM
    if filename_mismatch_only:
        return ArchiveReachability.FILENAME_MISMATCH
    if filename_in_listing is True:
        return ArchiveReachability.REACHABLE
    if filename_in_listing is False:
        return ArchiveReachability.DEAD_NOT_IN_METADATA
    return ArchiveReachability.UNCERTAIN


def may_remove_from_library(classification: ArchiveReachability) -> bool:
    """True only for evidence that will not falsely empty a user's schedule."""
    return classification in (
        ArchiveReachability.DEAD_NOT_IN_METADATA,
        ArchiveReachability.EMPTY_ITEM,
    )


def false_dead_evidence_message(
    *,
    status_code: Optional[int] = None,
    used_archive_auth_cookies: bool = False,
    detail: str = "",
) -> str:
    """Operator-facing explanation when a probe looks dead but must not purge."""
    bits = [
        "Do not remove Archive streams from YAML/DB/schedule on this evidence.",
        "Unauthenticated or gated CDN 401/403 is not a missing file "
        "(inappropriate-content / login gate). Retry with "
        "data/cookies/archive.org_cookies.txt (same as FFmpeg) or confirm via "
        "archive.org/metadata/<identifier> file list.",
        "Metadata timeout ≠ empty item; filename case/punctuation mismatch ≠ "
        "absent (use --fix-urls); CDN 5xx with files in metadata is Issue 32 "
        "(unreachable node), not a prune.",
    ]
    if status_code is not None:
        bits.append(f"http_status={status_code}")
    bits.append(f"used_archive_auth_cookies={used_archive_auth_cookies}")
    if detail:
        bits.append(detail)
    return " ".join(bits)
