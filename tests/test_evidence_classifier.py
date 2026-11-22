"""Classifier cases from tests/fixtures/channel_creator_v2/classifier_cases.json."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from streamtv.builder.evidence import classify_item

CASES_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "channel_creator_v2"
    / "classifier_cases.json"
)


def _cases() -> list[dict]:
    data = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    return list(data["cases"])


@pytest.mark.parametrize("case", _cases(), ids=lambda c: c["title"][:48])
def test_classifier_case(case: dict) -> None:
    expect = case["expect"]
    result = classify_item(
        case["title"],
        case.get("description") or "",
        runtime_s=case.get("runtime_s"),
        era_to=expect.get("era_to"),
    )
    if "exclusion_reason" in expect:
        assert result.exclusion_reason == expect["exclusion_reason"], result.as_dict()
        return
    if "commercials" in expect:
        assert result.commercials == expect["commercials"], result.as_dict()
    if expect.get("partial"):
        assert result.partial is True, result.as_dict()
    if "network" in expect:
        assert result.network == expect["network"], result.as_dict()
    if "station" in expect:
        assert result.station == expect["station"], result.as_dict()
    if "air_date" in expect:
        assert result.air_date == expect["air_date"], result.as_dict()
    if "air_date_quality" in expect:
        assert result.air_date_quality == expect["air_date_quality"], result.as_dict()
