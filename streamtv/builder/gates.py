"""Build gate reports for Channel Creator (§5.7)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from streamtv.builder.planner import canonical_title


@dataclass
class GateResult:
    gate: str
    ok: bool
    message: str = ""
    level: str = "ERROR"  # ERROR | WARN | INFO
    diagnostic: str = ""
    repair: str = ""

    def as_dict(self) -> dict[str, Any]:
        status = "PASS" if self.ok else ("WARN" if self.level == "WARN" else "FAIL")
        if self.level == "INFO" and self.ok:
            status = "PASS"
        return {
            "id": self.gate,
            "name": self.gate,
            "status": status,
            "detail": self.message,
            "diagnostic": self.diagnostic,
            "repair": self.repair,
            "level": self.level,
            "ok": self.ok,
            "message": self.message,
        }


@dataclass
class GateReport:
    results: list[GateResult] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    rolled_back: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(
            r.ok or r.level in ("INFO", "WARN") for r in self.results
        )

    @property
    def failed(self) -> list[GateResult]:
        return [r for r in self.results if not r.ok and r.level == "ERROR"]

    def add(
        self,
        gate: str,
        ok: bool,
        message: str = "",
        level: str = "ERROR",
        *,
        diagnostic: str = "",
        repair: str = "",
    ) -> None:
        self.results.append(
            GateResult(
                gate=gate,
                ok=ok,
                message=message,
                level=level,
                diagnostic=diagnostic,
                repair=repair,
            )
        )

    def summary_table(self) -> str:
        lines = [
            "| Gate | Result | Detail |",
            "|---|---|---|",
        ]
        for r in self.results:
            status = "PASS" if r.ok else ("WARN" if r.level == "WARN" else "FAIL")
            detail = (r.message or "").replace("|", "/")
            lines.append(f"| {r.gate} | {status} | {detail} |")
        return "\n".join(lines)

    def as_dict(self) -> dict[str, Any]:
        overall = "PASS" if self.ok and not self.failed else "FAIL"
        return {
            "gates": [r.as_dict() for r in self.results],
            "overall": overall,
            "ok": self.ok,
            "artifacts": list(self.artifacts),
            "rolled_back": list(self.rolled_back),
            "summary_table": self.summary_table(),
            "results": [r.as_dict() for r in self.results],
        }


def check_no_duration_items(schedule: dict[str, Any]) -> GateResult:
    items = []
    for seq in schedule.get("sequence") or []:
        items.extend(seq.get("items") or [])
    bad = [i for i in items if "duration" in i]
    return GateResult(
        "G1",
        ok=not bad,
        message="schema/schedule: no duration: items"
        if not bad
        else f"{len(bad)} duration: items (D1)",
        repair="Emit only all: items from planner/compiler",
    )


def check_unique_ids_in_streams(streams: list[dict[str, Any]]) -> GateResult:
    ids = [str(s.get("id")) for s in streams if s.get("id")]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    ia_mp4 = [
        str(s.get("id"))
        for s in streams
        if ".ia.mp4" in str(s.get("url") or "").lower()
    ]
    ok = not dupes and not ia_mp4
    msg = "unique stream ids"
    if dupes:
        msg = f"duplicate ids: {dupes[:5]}"
    elif ia_mp4:
        msg = f".ia.mp4 URLs: {ia_mp4[:5]}"
    return GateResult(
        "G2",
        ok=ok,
        message=msg,
        repair="Use ids.make_stream_id / builder_id_registry",
    )


def check_content_keys(schedule: dict[str, Any]) -> GateResult:
    keys = {c.get("key") for c in (schedule.get("content") or [])}
    used: set[str] = set()
    for seq in schedule.get("sequence") or []:
        for item in seq.get("items") or []:
            if "all" in item:
                used.add(str(item["all"]))
    orphan = used - keys
    unused = keys - used
    ok = not orphan
    msg = "all sequence keys in content"
    if orphan:
        msg = f"orphan keys: {sorted(orphan)[:5]}"
    elif unused:
        msg = f"content keys unused (info): {sorted(unused)[:5]}"
    return GateResult(
        "G3",
        ok=ok,
        message=msg,
        level="INFO" if ok and unused else "ERROR",
    )


def check_no_repeat(
    streams: list[dict[str, Any]],
    schedule: dict[str, Any],
    *,
    inventory_titles: Optional[set[str]] = None,
) -> GateResult:
    """G4: no repeated program key in loop; optional inventory collision."""
    prog_ids = [
        str(s.get("id"))
        for s in streams
        if s.get("type") == "event" and s.get("id")
    ]
    items = []
    for seq in schedule.get("sequence") or []:
        items.extend(seq.get("items") or [])
    seen: set[str] = set()
    dup_keys: list[str] = []
    for item in items:
        key = item.get("all")
        if not key or key not in prog_ids:
            continue
        if key in seen:
            dup_keys.append(str(key))
        seen.add(str(key))
    inventory = inventory_titles or set()
    collisions: list[str] = []
    for s in streams:
        if s.get("type") != "event":
            continue
        ct = canonical_title(str(s.get("slot") or s.get("id") or ""))
        if ct and ct in inventory:
            collisions.append(ct)
    ok = not dup_keys and not collisions
    msg = "no program repeats"
    if dup_keys:
        msg = f"program key scheduled twice: {dup_keys[:5]}"
    elif collisions:
        msg = f"inventory collision: {collisions[:5]}"
    return GateResult(
        "G4",
        ok=ok,
        message=msg,
        repair="Exclude duplicates or widen no_repeat_against",
    )


def check_runtimes_present(
    streams: list[dict[str, Any]],
    *,
    skip_availability: bool = False,
) -> GateResult:
    if skip_availability:
        return GateResult(
            "G6",
            ok=True,
            message="SKIPPED (skip_availability=true)",
            level="INFO",
        )
    missing = [
        str(s.get("id") or s.get("title"))
        for s in streams
        if s.get("type") != "commercial" and not s.get("runtime")
    ]
    mismatch: list[str] = []
    for s in streams:
        exact = s.get("duration_exact")
        if exact is None:
            meta = s.get("source_metadata") or {}
            if isinstance(meta, dict):
                exact = meta.get("duration_exact")
        if exact is None or not s.get("runtime"):
            continue
        from streamtv.builder.source_meta import parse_archive_length, round_duration_seconds

        # runtime is ISO; compare rounded seconds when duration_exact present
        try:
            rounded = round_duration_seconds(float(exact))
            # Accept ISO matching rounded seconds via notes; soft check abs
            _ = parse_archive_length  # keep import used
            # Store mismatch only when YAML also carries numeric seconds
            if s.get("runtime_seconds") is not None:
                if abs(float(s["runtime_seconds"]) - float(exact)) > 0.5:
                    mismatch.append(str(s.get("id")))
            elif s.get("seconds") is not None:
                if abs(float(s["seconds"]) - float(exact)) > 0.5:
                    mismatch.append(str(s.get("id")))
            else:
                # ISO-only: ensure runtime exists when exact does
                if not s.get("runtime"):
                    missing.append(str(s.get("id")))
        except (TypeError, ValueError):
            pass
    for s in streams:
        src = (s.get("source") or "").lower()
        url = (s.get("url") or "").lower()
        if ("archive" in src or "archive.org" in url) and not s.get("runtime"):
            missing.append(str(s.get("id")))
    missing = sorted(set(missing))
    mismatch = sorted(set(mismatch))
    ok = not missing and not mismatch
    msg = "runtimes present"
    if missing:
        msg = f"missing runtime: {missing[:5]}"
    elif mismatch:
        msg = f"runtime vs duration_exact >0.5s: {mismatch[:5]}"
    return GateResult(
        "G6",
        ok=ok,
        message=msg,
        repair="Inspect source and set duration_exact / runtime",
    )


def evaluate_compiled_package(
    channel_doc: dict[str, Any],
    schedule: dict[str, Any],
    *,
    inventory_titles: Optional[set[str]] = None,
    skip_availability: bool = False,
) -> GateReport:
    report = GateReport()
    channels = channel_doc.get("channels") or []
    streams = (channels[0].get("streams") if channels else []) or []
    report.results.append(check_no_duration_items(schedule))
    report.results.append(check_unique_ids_in_streams(streams))
    report.results.append(check_content_keys(schedule))
    report.results.append(
        check_no_repeat(streams, schedule, inventory_titles=inventory_titles)
    )
    report.results.append(
        check_runtimes_present(streams, skip_availability=skip_availability)
    )
    return report


def check_guide_preview_info(
    streams: list[dict[str, Any]],
) -> GateResult:
    """G10 soft check without live XMLTV (Phase 7 exercises live)."""
    short = [
        str(s.get("id"))
        for s in streams
        if s.get("type") == "commercial"
        and isinstance(s.get("runtime"), str)
        and s["runtime"] in ("PT0S", "PT1S")
    ]
    missing_desc = [
        str(s.get("id"))
        for s in streams
        if s.get("type") == "event" and not s.get("description")
    ]
    if missing_desc:
        return GateResult(
            "G10",
            ok=False,
            message=f"programs missing description: {missing_desc[:5]}",
            level="WARN",
            repair="Rebuild with enrich_metadata=True",
        )
    msg = "guide fields present on streams"
    if short:
        msg += f"; sub-60s INFO candidates: {short[:5]}"
    return GateResult("G10", ok=True, message=msg, level="INFO")


def load_inventory_titles(data_dir: Path, channel_numbers: list[str]) -> set[str]:
    """Canonical titles from existing channel YAML for no-repeat (§5.5)."""
    import yaml

    titles: set[str] = set()
    for num in channel_numbers:
        path = data_dir / f"channels_generated_{num}.yaml"
        if not path.exists():
            # also try any yaml containing the number
            for cand in data_dir.glob("*.yaml"):
                try:
                    data = yaml.safe_load(cand.read_text(encoding="utf-8")) or {}
                except Exception:  # noqa: BLE001
                    continue
                for ch in data.get("channels") or []:
                    if str(ch.get("number")) != str(num):
                        continue
                    for s in ch.get("streams") or []:
                        if s.get("type") == "event":
                            titles.add(
                                canonical_title(str(s.get("slot") or s.get("id") or ""))
                            )
            continue
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception:  # noqa: BLE001
            continue
        for ch in data.get("channels") or []:
            for s in ch.get("streams") or []:
                if s.get("type") == "event":
                    titles.add(canonical_title(str(s.get("slot") or s.get("id") or "")))
    return {t for t in titles if t}
