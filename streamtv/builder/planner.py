"""Template planner/compiler ported from fixtures reference/ref_plan.py (§5.0, §5.4).

With enrich_metadata=False and guide_title_style=\"slot\", output is byte-identical
to the eight template example channels.
"""

from __future__ import annotations

import copy
import re
from typing import Any

import yaml

from streamtv.builder.source_meta import compose_guide_description

STYLE = {
    "kids_2026": dict(
        date_before_slot=False,
        slot_without_date="{title} ({net})",
        break_notes="Commercial/bumper break reel. Page: {page}",
        id_notes="Station holiday promo / ID. Page: {page}",
    ),
    "prime_2026": dict(
        date_before_slot=True,
        slot_without_date="{title} ({net}, {year})",
        break_notes="Commercial break reel. Page: {page}",
        id_notes="Station holiday promo / ID. Page: {page}",
    ),
}


def dur(seconds: int) -> str:
    s = int(seconds)
    h, m, sec = s // 3600, (s % 3600) // 60, s % 60
    if not s:
        return "PT1S"
    return (
        "PT"
        + (f"{h}H" if h else "")
        + (f"{m}M" if m else "")
        + (f"{sec}S" if sec else "")
    )


def short_network(net: str) -> str:
    return net.split(" /")[0].split(" (")[0]


def compile_streams(
    spec: dict[str, Any],
    cands: list[dict[str, Any]],
    *,
    enrich_metadata: bool = False,
    guide_title_style: str = "slot",
) -> list[dict[str, Any]]:
    st = STYLE[spec["style"]]
    prefix = spec["collection_prefix"]
    out: list[dict[str, Any]] = []
    for c in cands:
        sid = c["id"]
        if c["role"] in ("program", "marathon"):
            if c.get("date"):
                slot = f"{c['title']} ({c['network']}, {c['date']})"
            else:
                slot = st["slot_without_date"].format(
                    title=c["title"], net=c["network"], year=c["year"]
                )
            stream: dict[str, Any] = {
                "id": sid,
                "collection": (
                    f"{prefix} - {c['title']} ({short_network(c['network'])} "
                    f"{c['year']}) [{sid}]"
                ),
                "type": "event",
                "year": c["year"],
            }
            if st["date_before_slot"]:
                stream["broadcast_date"] = c["date"]
            stream.update(
                slot=slot,
                network=c["network"],
                runtime=dur(c["seconds"]),
                source=c["source"],
                url=c["url"],
                notes=(
                    f"Tier {c['tier']}; commercials: {c['commercials']}. "
                    f"{c['note']} Page: {c['page']}"
                ),
            )
            if not st["date_before_slot"] and c.get("date"):
                stream["broadcast_date"] = c["date"]
        else:
            tmpl = st["id_notes"] if c["role"] == "station_id" else st["break_notes"]
            stream = {
                "id": sid,
                "collection": f"{prefix} - Break - {c['title']} [{sid}]",
                "type": "commercial",
                "slot": c["title"],
                "network": c["network"],
                "runtime": dur(c["seconds"]),
                "source": c["source"],
                "url": c["url"],
                "notes": tmpl.format(page=c["page"]),
            }
            if c.get("date"):
                stream["broadcast_date"] = c["date"]
                stream["year"] = int(str(c["date"])[:4])

        if enrich_metadata:
            air = c.get("date")
            quality = "exact" if air else "unknown"
            stream["description"] = compose_guide_description(
                air_date=air,
                air_date_quality=quality,
                network=c.get("network"),
                source_description=str(
                    c.get("source_description") or c.get("note") or ""
                ),
                commercials_label=str(c.get("commercials") or "unverified"),
            )
            if c.get("thumbnail"):
                stream["thumbnail"] = c["thumbnail"]
            cats = c.get("categories") or []
            if cats:
                stream["categories"] = list(cats)
            if c.get("source_metadata"):
                stream["source_metadata"] = c["source_metadata"]

        c["_slot"] = stream["slot"]
        c["_coll"] = stream["collection"]
        if guide_title_style == "clean" and c["role"] in ("program", "marathon"):
            c["_guide_title"] = c["title"]
        else:
            c["_guide_title"] = stream["slot"]
        out.append(stream)
    return out


def plan_schedule(
    spec: dict[str, Any],
    cands: list[dict[str, Any]],
    *,
    guide_title_style: str = "slot",
) -> dict[str, Any]:
    """Build schedule dict; never emits duration: items (D1)."""
    progs = [c for c in cands if c["role"] == "program"]
    marathons = [c for c in cands if c["role"] == "marathon"]
    ids = [c for c in cands if c["role"] == "station_id"]
    brk = [c for c in cands if c["role"] == "break"]
    longs = [c for c in brk if c["seconds"] > spec["long_reel_seconds"]]
    groups = {
        g: [c for c in brk if c["group"] == g and c not in longs]
        for g in spec["break_groups"]
    }
    order = sorted(progs, key=lambda c: c["date"] or f"{c['year']}-12-31")
    gaps: list[list[dict[str, Any]]] = [[] for _ in order]

    if spec["rotation"] == "parity_alternate":
        a, b = (groups[g] for g in spec["break_groups"])
        ia = ib = 0
        for i in range(len(order)):
            if i % 2 == 0:
                gaps[i].append(a[ia % len(a)])
                ia += 1
            else:
                gaps[i].append(b[ib % len(b)])
                ib += 1
    else:
        rot: list[dict[str, Any]] = []
        if any(groups.values()):
            for k in range(max(len(v) for v in groups.values())):
                for g in spec["break_groups"]:
                    if k < len(groups[g]):
                        rot.append(groups[g][k])
        if rot and order:
            for k in range(max(len(order), len(rot))):
                gaps[k % len(order)].append(rot[k % len(rot)])

    items: list[dict[str, Any]] = []
    for i, (p, g) in enumerate(zip(order, gaps)):
        title = p["title"] if guide_title_style == "clean" else (
            p.get("_guide_title") or p.get("_slot") or p["title"]
        )
        items.append({"all": p["id"], "custom_title": title})
        for b in g:
            items.append(
                {
                    "all": b["id"],
                    "custom_title": "Station Break: " + b["title"],
                    "filler_kind": "Commercial",
                }
            )
        if spec["station_id_after_each_gap"] and ids:
            pr = ids[i % len(ids)]
            items.append(
                {
                    "all": pr["id"],
                    "custom_title": "Station ID: " + pr["title"],
                    "filler_kind": "Commercial",
                }
            )
    for b in longs:
        items.append(
            {
                "all": b["id"],
                "custom_title": "Commercial Break Marathon: " + b["title"],
                "filler_kind": "Commercial",
            }
        )
    for p in marathons:
        title = p["title"] if guide_title_style == "clean" else (
            p.get("_guide_title") or p.get("_slot") or p["title"]
        )
        items.append({"all": p["id"], "custom_title": title})

    content = [
        {"key": c["id"], "collection": c["_coll"], "order": "chronological"}
        for c in cands
        if c["role"] in ("program", "marathon")
    ]
    content += [
        {"key": c["id"], "collection": c["_coll"], "order": "chronological"}
        for g in spec["break_groups"]
        for c in groups[g]
    ]
    content += [
        {"key": c["id"], "collection": c["_coll"], "order": "chronological"}
        for c in longs + ids
    ]
    key = spec["sequence_key"]
    return {
        "name": f"{spec['number']} {spec['name']}",
        "description": spec["schedule_description"],
        "media": {"preferred_extension": "mp4", "mp4_only": True},
        "content": content,
        "sequence": [{"key": key, "items": items}],
        "playout": [{"sequence": key}, {"repeat": True}],
    }


def build_channel_package(
    channel_spec: dict[str, Any],
    candidates: list[dict[str, Any]],
    *,
    enrich_metadata: bool = False,
    guide_title_style: str = "slot",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (channels_yaml_dict, schedule_yaml_dict)."""
    cands = copy.deepcopy(candidates)
    streams = compile_streams(
        channel_spec,
        cands,
        enrich_metadata=enrich_metadata,
        guide_title_style=guide_title_style,
    )
    channel_doc = {
        "channels": [
            {
                "number": channel_spec["number"],
                "name": channel_spec["name"],
                "group": channel_spec["group"],
                "description": channel_spec["description"],
                "enabled": True,
                "streams": streams,
            }
        ]
    }
    schedule = plan_schedule(
        channel_spec, cands, guide_title_style=guide_title_style
    )
    return channel_doc, schedule


def dump_yaml(data: Any) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=200)


def canonical_title(title: str) -> str:
    """No-repeat key (§5.5)."""
    t = re.sub(r"\s*\([^()]*\)", "", title or "")
    t = t.replace('"', "").replace("\u201c", "").replace("\u201d", "")
    t = t.replace("\u2019", "'")
    t = re.sub(r"\s+", " ", t).strip()
    return t.casefold()
