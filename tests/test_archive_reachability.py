"""Issue 75: unauthenticated Archive 401 must not authorize library purges."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from streamtv.utils.archive_reachability import (
    ArchiveReachability,
    classify_download_http_status,
    classify_metadata_outcome,
    false_dead_evidence_message,
    may_remove_from_library,
)
from streamtv.validation.playout_guards import warn_library_shrink

_ROOT = Path(__file__).resolve().parents[1]
_PRUNE_PATH = _ROOT / "scripts" / "prune_dead_archive_urls.py"


def _load_prune():
    spec = importlib.util.spec_from_file_location("prune_dead_archive_urls", _PRUNE_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_unauthenticated_401_is_gated_not_dead() -> None:
    c = classify_download_http_status(401, used_archive_auth_cookies=False)
    assert c == ArchiveReachability.AUTH_REQUIRED_OR_GATED
    assert not may_remove_from_library(c)


def test_authenticated_401_still_keeps_library() -> None:
    c = classify_download_http_status(401, used_archive_auth_cookies=True)
    assert c == ArchiveReachability.AUTH_REQUIRED_OR_GATED
    assert not may_remove_from_library(c)


def test_200_is_reachable() -> None:
    c = classify_download_http_status(200, used_archive_auth_cookies=True)
    assert c == ArchiveReachability.REACHABLE
    assert not may_remove_from_library(c)


def test_5xx_is_cdn_unreachable_not_dead() -> None:
    c = classify_download_http_status(503, used_archive_auth_cookies=True)
    assert c == ArchiveReachability.CDN_UNREACHABLE
    assert not may_remove_from_library(c)


def test_only_metadata_proof_allows_removal() -> None:
    assert may_remove_from_library(ArchiveReachability.EMPTY_ITEM)
    assert may_remove_from_library(ArchiveReachability.DEAD_NOT_IN_METADATA)
    assert not may_remove_from_library(ArchiveReachability.UNCERTAIN)
    assert not may_remove_from_library(ArchiveReachability.FILENAME_MISMATCH)
    assert not may_remove_from_library(ArchiveReachability.CDN_UNREACHABLE)


def test_failed_metadata_fetch_is_uncertain_not_empty() -> None:
    """Main trap: metadata timeout must never look like EMPTY_ITEM."""
    c = classify_metadata_outcome(metadata_fetched=False)
    assert c == ArchiveReachability.UNCERTAIN
    assert not may_remove_from_library(c)
    empty = classify_metadata_outcome(metadata_fetched=True, file_count=0)
    assert empty == ArchiveReachability.EMPTY_ITEM
    assert may_remove_from_library(empty)


def test_filename_mismatch_keeps_library() -> None:
    c = classify_metadata_outcome(
        metadata_fetched=True,
        file_count=3,
        filename_mismatch_only=True,
    )
    assert c == ArchiveReachability.FILENAME_MISMATCH
    assert not may_remove_from_library(c)


def test_true_absence_after_mismatch_checks_may_remove() -> None:
    c = classify_metadata_outcome(
        metadata_fetched=True,
        file_count=3,
        filename_in_listing=False,
    )
    assert c == ArchiveReachability.DEAD_NOT_IN_METADATA
    assert may_remove_from_library(c)


def test_false_dead_message_mentions_cookies_and_traps() -> None:
    msg = false_dead_evidence_message(status_code=401, used_archive_auth_cookies=False)
    assert "401" in msg
    assert "cookies" in msg.lower()
    assert "Do not remove" in msg
    assert "Metadata timeout" in msg
    assert "Issue 32" in msg


def test_warn_library_shrink_on_large_drop() -> None:
    report = warn_library_shrink(
        before_count=1186, after_count=362, channel_label="123"
    )
    assert report.warnings
    assert any("Issue 75" in w for w in report.warnings)
    assert any("401" in w for w in report.warnings)


def test_warn_library_shrink_skips_small_drop() -> None:
    report = warn_library_shrink(before_count=100, after_count=96, channel_label="80")
    assert not report.warnings


def test_resolve_fuzzy_mismatch_kept_without_fix_urls() -> None:
    prune = _load_prune()
    files = {"Sesame Street - S40E01.mp4"}
    lower = {n.rsplit("/", 1)[-1].lower(): n for n in files}
    status, detail, fixed = prune.resolve_filename(
        "ident",
        "Sesame_Street_-_S40E01.mp4",
        files,
        lower,
        fix_urls=False,
    )
    assert status == "mismatch_fuzzy"
    assert fixed is None
    assert detail == "Sesame Street - S40E01.mp4"
    assert not prune._removal_allowed(status)


def test_resolve_fuzzy_rewrites_with_fix_urls() -> None:
    prune = _load_prune()
    files = {"Sesame Street - S40E01.mp4"}
    lower = {n.rsplit("/", 1)[-1].lower(): n for n in files}
    status, detail, fixed = prune.resolve_filename(
        "ident",
        "Sesame_Street_-_S40E01.mp4",
        files,
        lower,
        fix_urls=True,
    )
    assert status == "fixed_fuzzy"
    assert fixed is not None
    assert "Sesame%20Street" in fixed or "Sesame Street" in fixed


def test_resolve_true_absence_is_dead_file() -> None:
    prune = _load_prune()
    files = {"other.mp4"}
    lower = {"other.mp4": "other.mp4"}
    status, _detail, fixed = prune.resolve_filename(
        "ident",
        "gone.mp4",
        files,
        lower,
        fix_urls=False,
    )
    assert status == "dead_file"
    assert fixed is None
    assert prune._removal_allowed(status)


def test_uncertain_meta_never_removal_allowed() -> None:
    prune = _load_prune()
    assert not prune._removal_allowed("uncertain_meta")
    assert not prune._removal_allowed("mismatch_ia")
    assert not prune._removal_allowed("mismatch_fuzzy")
