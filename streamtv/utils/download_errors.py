"""Classify cache-download failures so terminal errors are not re-queued forever.

Mirrors TunarrTube's split of 429 / sign-in-required / unavailable vs transient.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

# Sticky until operator POST /api/cache/items/{id}/retry
TERMINAL_CLASSES = frozenset({"auth_required", "unavailable", "no_playable_file"})
# May auto-requeue after retry_after
RETRYABLE_CLASSES = frozenset({"rate_limited", "transient"})

FAILURE_CLASSES = TERMINAL_CLASSES | RETRYABLE_CLASSES

_RATE_LIMIT = re.compile(
    r"HTTP\s*Error\s*429|429\s*Client\s*Error|Too\s*Many\s*Requests|"
    r"rate[\s_-]?limit|HTTP\s*429",
    re.I,
)
_SIGN_IN = re.compile(
    r"sign\s+in\s+to\s+confirm|login\s+required|"
    r"Use\s+--cookies|cookiefile|cookies?\s+(file|are)\s+required",
    re.I,
)
_AUTH_HTTP = re.compile(r"\bHTTP\s*(401|403)\b|status[_\s]*(401|403)|unauthorized|forbidden", re.I)
_UNAVAILABLE = re.compile(
    r"\bprivate\b|\bunavailable\b|\bdeleted\b|\bremoved\b|"
    r"Video unavailable|This video is not available|has been removed",
    re.I,
)
_NO_FILE = re.compile(
    r"No video files|No matching .* file|no playable|Download returned no file|"
    r"Could not parse Archive\.org|Cannot extract video ID",
    re.I,
)


@dataclass(frozen=True)
class ClassifiedDownloadError:
    """Structured download failure for cache manifest persistence."""

    failure_class: str
    message: str
    retry_after: Optional[datetime] = None

    @property
    def is_terminal(self) -> bool:
        return self.failure_class in TERMINAL_CLASSES

    @property
    def is_retryable(self) -> bool:
        return self.failure_class in RETRYABLE_CLASSES


class DownloadFailure(Exception):
    """Raised by downloaders when a classified failure should stick on the manifest."""

    def __init__(self, classified: ClassifiedDownloadError) -> None:
        self.classified = classified
        super().__init__(classified.message)


def classify_download_error(
    message: str,
    *,
    source: Optional[str] = None,
    http_status: Optional[int] = None,
    rate_limit_cooldown_seconds: float = 3600.0,
) -> ClassifiedDownloadError:
    """Map stderr / exception text to a failure class.

    ``source`` is informational (youtube / archive_org); classification is
    primarily string- and status-based so both downloaders share one path.
    """
    text = (message or "").strip() or "Download failed"
    now = datetime.utcnow()

    if http_status == 429 or _RATE_LIMIT.search(text):
        return ClassifiedDownloadError(
            failure_class="rate_limited",
            message=text[:1024],
            retry_after=now + timedelta(seconds=max(1.0, rate_limit_cooldown_seconds)),
        )
    if http_status in (401, 403) or _AUTH_HTTP.search(text):
        # Prefer auth over generic "cookies" in yt-dlp hints when status is clear
        return ClassifiedDownloadError(
            failure_class="auth_required",
            message=text[:1024],
        )
    if _SIGN_IN.search(text) and not _RATE_LIMIT.search(text):
        return ClassifiedDownloadError(
            failure_class="auth_required",
            message=text[:1024],
        )
    if _UNAVAILABLE.search(text):
        return ClassifiedDownloadError(
            failure_class="unavailable",
            message=text[:1024],
        )
    if _NO_FILE.search(text):
        return ClassifiedDownloadError(
            failure_class="no_playable_file",
            message=text[:1024],
        )
    if http_status is not None and http_status >= 500:
        return ClassifiedDownloadError(
            failure_class="transient",
            message=text[:1024],
            retry_after=now + timedelta(seconds=60),
        )
    return ClassifiedDownloadError(
        failure_class="transient",
        message=text[:1024],
        retry_after=now + timedelta(seconds=120),
    )


def is_terminal_failure(failure_class: Optional[str]) -> bool:
    return bool(failure_class) and failure_class in TERMINAL_CLASSES


def may_auto_requeue(
    failure_class: Optional[str],
    retry_after: Optional[datetime],
    *,
    now: Optional[datetime] = None,
) -> bool:
    """True when a FAILED row may be moved back to QUEUED without operator retry."""
    if not failure_class or failure_class not in RETRYABLE_CLASSES:
        return False
    clock = now or datetime.utcnow()
    if retry_after is not None and retry_after > clock:
        return False
    return True
