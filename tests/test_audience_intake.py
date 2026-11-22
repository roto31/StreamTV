"""Audience intake steers templates and discovery queries."""

from __future__ import annotations

from streamtv.builder.discovery.audience import (
    AUDIENCE_QUESTION,
    apply_audience_to_requirements,
    normalize_audience,
    passes_audience_filter,
)
from streamtv.builder.discovery.archive import build_archive_queries
from streamtv.builder.discovery.youtube import build_youtube_queries
from streamtv.builder.models import ChannelRequirements


def test_normalize_and_template_suggestion() -> None:
    assert normalize_audience("Children") == "kids"
    assert normalize_audience("prime time") == "adults"
    req = ChannelRequirements(audience="kids", theme="Christmas")
    assert req.suggested_template() == "kids_specials"
    assert "audience" not in req.missing_fields()
    empty = ChannelRequirements(theme="Christmas")
    assert "audience" in empty.missing_fields()


def test_audience_biases_queries() -> None:
    kids_q = build_archive_queries(
        {"theme": "christmas", "audience": "kids", "networks": ["CBS"]}
    )
    assert any("cartoon" in q or "animated" in q or "kids" in q for q in kids_q)
    adults_q = build_archive_queries(
        {"theme": "christmas", "audience": "adults", "networks": ["CBS"]}
    )
    assert any("Sunday Movie" in q or "Hallmark" in q for q in adults_q)

    yt = build_youtube_queries(
        {"theme": "Christmas", "audience": "kids", "networks": ["ABC"]}
    )
    assert any("cartoon" in q or "animated" in q for q in yt)


def test_audience_denylist() -> None:
    assert not passes_audience_filter(
        "Adult Film Christmas XXX", "", audience="kids"
    )
    assert passes_audience_filter(
        "Peanuts Christmas special", "", audience="kids"
    )


def test_apply_audience_fills_template() -> None:
    out = apply_audience_to_requirements(
        {"audience": "family", "theme": "Easter", "template": "custom"}
    )
    assert out["audience"] == "family"
    assert out["template"] == "holiday_family"
    assert "Who is this channel for" in AUDIENCE_QUESTION
