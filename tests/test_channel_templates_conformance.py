"""Template conformance: 8 example channels byte-equal with enrichment off (§5.0/§5.4)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from streamtv.builder.planner import build_channel_package, dump_yaml

FIXTURES = (
    Path(__file__).resolve().parent / "fixtures" / "channel_creator_v2" / "new_channels"
)
EXPECTED = FIXTURES / "expected"

SEQUENCE_COUNTS = {
    "101": 25,
    "214": 13,
    "401": 26,
    "704": 17,
    "1031": 28,
    "1128": 145,
    "1224": 96,
    "1225": 99,
}

EXAMPLE_SLUGS = {
    "101": "vintage-new-years",
    "214": "vintage-kids-valentines",
    "401": "vintage-kids-easter",
    "704": "vintage-fourth-of-july",
    "1031": "vintage-kids-halloween",
    "1128": "vintage-kids-thanksgiving",
    "1224": "vintage-prime-time-christmas",
    "1225": "vintage-kids-christmas",
}


def _load_candidates(number: str) -> tuple[dict, list]:
    data = json.loads((FIXTURES / f"candidates_{number}.json").read_text(encoding="utf-8"))
    return data["channel"], data["candidates"]


@pytest.mark.parametrize("number", sorted(SEQUENCE_COUNTS.keys()))
def test_template_conformance_byte_equal(number: str, tmp_path: Path) -> None:
    spec, cands = _load_candidates(number)
    channel_doc, schedule = build_channel_package(
        spec, cands, enrich_metadata=False, guide_title_style="slot"
    )

    got_channel = dump_yaml(channel_doc)
    got_sched = dump_yaml(schedule)

    slug = EXAMPLE_SLUGS[number]
    exp_channel = (EXPECTED / f"channel-{number}-{slug}.yaml").read_text(encoding="utf-8")
    exp_sched = (EXPECTED / f"{number}.yml").read_text(encoding="utf-8")

    assert got_channel == exp_channel, f"channel {number} YAML drift"
    assert got_sched == exp_sched, f"schedule {number} YAML drift"

    items = schedule["sequence"][0]["items"]
    assert len(items) == SEQUENCE_COUNTS[number]
    assert not any("duration" in i for i in items)
    ids = [s["id"] for s in channel_doc["channels"][0]["streams"]]
    assert len(ids) == len(set(ids))
    keys = {c["key"] for c in schedule["content"]}
    used = {i["all"] for i in items if "all" in i}
    assert used <= keys


@pytest.mark.parametrize("number", ["101", "1224"])
def test_enrichment_adds_fields_without_changing_core(number: str) -> None:
    spec, cands = _load_candidates(number)
    # Attach enrichment inputs on a copy of first program
    enriched_cands = json.loads(json.dumps(cands))
    for c in enriched_cands:
        if c["role"] == "program":
            c["categories"] = ["Holiday", "Special"]
            c["thumbnail"] = f"/static/thumbnails/{c['id']}.jpg"
            c["source_metadata"] = {"title": c["title"], "platform": "test"}
            c["source_description"] = "Probe description."
            break

    base_ch, base_sch = build_channel_package(
        spec, cands, enrich_metadata=False, guide_title_style="slot"
    )
    enr_ch, enr_sch = build_channel_package(
        spec, enriched_cands, enrich_metadata=True, guide_title_style="slot"
    )

    # Schedule structure unchanged when guide_title_style stays slot
    assert dump_yaml(base_sch) == dump_yaml(enr_sch)

    base_streams = base_ch["channels"][0]["streams"]
    enr_streams = enr_ch["channels"][0]["streams"]
    assert len(base_streams) == len(enr_streams)

    # Find enriched program
    enriched = next(
        s for s in enr_streams if s.get("description") and s.get("type") == "event"
    )
    assert "Original air date:" in enriched["description"] or "Air date:" in enriched[
        "description"
    ]
    assert enriched.get("categories") == ["Holiday", "Special"]
    assert enriched.get("thumbnail", "").startswith("/static/thumbnails/")
    assert enriched.get("source_metadata", {}).get("platform") == "test"

    # Core keys from base still match for that id
    base = next(s for s in base_streams if s["id"] == enriched["id"])
    for key in ("id", "collection", "type", "runtime", "url", "notes", "slot", "network"):
        assert base.get(key) == enriched.get(key)
