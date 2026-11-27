"""Issue 59 — overlay stdout gaps vs true hang (no live FFmpeg)."""

from __future__ import annotations

from streamtv.streaming.mpegts_streamer import midstream_stall_decision


def test_copy_path_warns_on_first_silence() -> None:
    assert (
        midstream_stall_decision(
            overlay_active=False,
            silence_sec=5.0,
            stall_limit_sec=90.0,
            bytes_yielded=8192,
            first_silence_event=True,
        )
        == "warn"
    )


def test_copy_path_continues_until_limit() -> None:
    assert (
        midstream_stall_decision(
            overlay_active=False,
            silence_sec=40.0,
            stall_limit_sec=90.0,
            bytes_yielded=8192,
            first_silence_event=False,
        )
        == "continue"
    )


def test_copy_path_aborts_at_stall_limit() -> None:
    assert (
        midstream_stall_decision(
            overlay_active=False,
            silence_sec=90.0,
            stall_limit_sec=90.0,
            bytes_yielded=8192,
            first_silence_event=False,
        )
        == "abort"
    )


def test_overlay_growing_ts_does_not_warn() -> None:
    assert (
        midstream_stall_decision(
            overlay_active=True,
            silence_sec=5.0,
            stall_limit_sec=90.0,
            bytes_yielded=39_000_000,
            first_silence_event=True,
        )
        == "continue"
    )


def test_copy_path_aborts_when_trickle_never_goes_silent() -> None:
    """A chunk every few seconds resets consecutive silence; rate still aborts."""
    assert (
        midstream_stall_decision(
            overlay_active=False,
            silence_sec=0.0,
            stall_limit_sec=90.0,
            bytes_yielded=8192,
            first_silence_event=False,
            elapsed_sec=20.0,
        )
        == "abort"
    )


def test_copy_path_rate_ok_does_not_abort() -> None:
    assert (
        midstream_stall_decision(
            overlay_active=False,
            silence_sec=0.0,
            stall_limit_sec=90.0,
            bytes_yielded=2_000_000,
            first_silence_event=False,
            elapsed_sec=20.0,
        )
        == "continue"
    )


def test_overlay_true_hang_still_aborts() -> None:
    assert (
        midstream_stall_decision(
            overlay_active=True,
            silence_sec=90.0,
            stall_limit_sec=90.0,
            bytes_yielded=39_000_000,
            first_silence_event=False,
        )
        == "abort"
    )
