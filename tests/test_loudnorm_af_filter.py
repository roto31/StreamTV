"""LoudNorm anti-spike filter contract for FFmpeg profiles."""

from __future__ import annotations

from streamtv.transcoding.ffmpeg_builder import LOUDNORM_AF_FILTER


def test_loudnorm_filter_has_true_peak_headroom_and_limiter() -> None:
    assert "loudnorm=" in LOUDNORM_AF_FILTER
    assert "TP=-2.0" in LOUDNORM_AF_FILTER
    assert "I=-16" in LOUDNORM_AF_FILTER
    assert "linear=true" in LOUDNORM_AF_FILTER
    assert "alimiter=" in LOUDNORM_AF_FILTER
    assert "limit=0.89" in LOUDNORM_AF_FILTER
