"""Unit tests for download failure classification."""

from __future__ import annotations

from datetime import timedelta

from streamtv.utils.clock import utc_now_naive

from streamtv.utils.download_errors import (
    TERMINAL_CLASSES,
    classify_download_error,
    is_terminal_failure,
    may_auto_requeue,
)


def test_rate_limited_from_429_text() -> None:
    c = classify_download_error("ERROR: HTTP Error 429: Too Many Requests")
    assert c.failure_class == "rate_limited"
    assert c.is_retryable
    assert c.retry_after is not None


def test_rate_limited_from_http_status() -> None:
    c = classify_download_error("throttled", http_status=429, rate_limit_cooldown_seconds=90)
    assert c.failure_class == "rate_limited"
    assert c.retry_after is not None


def test_auth_required_sign_in() -> None:
    c = classify_download_error("ERROR: [youtube] abc: Sign in to confirm your age")
    assert c.failure_class == "auth_required"
    assert c.is_terminal


def test_auth_required_http_403() -> None:
    c = classify_download_error("forbidden", http_status=403)
    assert c.failure_class == "auth_required"


def test_unavailable_private() -> None:
    c = classify_download_error("ERROR: [youtube] xyz: Private video")
    assert c.failure_class == "unavailable"
    assert is_terminal_failure(c.failure_class)


def test_no_playable_file_archive() -> None:
    c = classify_download_error("No matching mp4 file for BigBuckBunny")
    assert c.failure_class == "no_playable_file"


def test_transient_default() -> None:
    c = classify_download_error("connection reset by peer")
    assert c.failure_class == "transient"
    assert c.is_retryable


def test_may_auto_requeue_respects_retry_after() -> None:
    future = utc_now_naive() + timedelta(minutes=5)
    assert not may_auto_requeue("rate_limited", future)
    past = utc_now_naive() - timedelta(seconds=1)
    assert may_auto_requeue("rate_limited", past)
    assert not may_auto_requeue("unavailable", past)
    assert not may_auto_requeue(None, None)


def test_terminal_set_complete() -> None:
    assert "auth_required" in TERMINAL_CLASSES
    assert "unavailable" in TERMINAL_CLASSES
    assert "no_playable_file" in TERMINAL_CLASSES
    assert "rate_limited" not in TERMINAL_CLASSES
