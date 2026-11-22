"""Build gate reports for Channel Creator (§5.7)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class GateResult:
    gate: str
    ok: bool
    message: str = ""
    level: str = "ERROR"  # ERROR | WARN | INFO

    def as_dict(self) -> dict[str, Any]:
        return {
            "gate": self.gate,
            "ok": self.ok,
            "message": self.message,
            "level": self.level,
        }


@dataclass
class GateReport:
    results: list[GateResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(r.ok or r.level == "INFO" for r in self.results if r.level != "WARN")

    @property
    def failed(self) -> list[GateResult]:
        return [r for r in self.results if not r.ok and r.level == "ERROR"]

    def add(self, gate: str, ok: bool, message: str = "", level: str = "ERROR") -> None:
        self.results.append(GateResult(gate=gate, ok=ok, message=message, level=level))

    def summary_table(self) -> str:
        lines = [f"{'GATE':<6} {'RESULT':<6} MESSAGE", "-" * 60]
        for r in self.results:
            status = "PASS" if r.ok else ("WARN" if r.level == "WARN" else "FAIL")
            lines.append(f"{r.gate:<6} {status:<6} {r.message}")
        return "\n".join(lines)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
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
        message="no duration: items" if not bad else f"{len(bad)} duration: items (D1)",
    )


def check_unique_ids_in_streams(streams: list[dict[str, Any]]) -> GateResult:
    ids = [str(s.get("id")) for s in streams if s.get("id")]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    return GateResult(
        "G2",
        ok=not dupes,
        message="unique stream ids" if not dupes else f"duplicate ids: {dupes[:5]}",
    )


def check_runtimes_present(streams: list[dict[str, Any]]) -> GateResult:
    missing = [
        str(s.get("id") or s.get("title"))
        for s in streams
        if s.get("type") != "commercial" and not s.get("runtime")
    ]
    # Also require archive streams always have runtime
    for s in streams:
        src = (s.get("source") or "").lower()
        url = (s.get("url") or "").lower()
        if ("archive" in src or "archive.org" in url) and not s.get("runtime"):
            missing.append(str(s.get("id")))
    missing = sorted(set(missing))
    return GateResult(
        "G6",
        ok=not missing,
        message="runtimes present" if not missing else f"missing runtime: {missing[:5]}",
    )


def evaluate_compiled_package(
    channel_doc: dict[str, Any],
    schedule: dict[str, Any],
) -> GateReport:
    report = GateReport()
    channels = channel_doc.get("channels") or []
    streams = (channels[0].get("streams") if channels else []) or []
    report.results.append(check_no_duration_items(schedule))
    report.results.append(check_unique_ids_in_streams(streams))
    report.results.append(check_runtimes_present(streams))
    # Content keys used
    keys = {c.get("key") for c in (schedule.get("content") or [])}
    used: set[str] = set()
    for seq in schedule.get("sequence") or []:
        for item in seq.get("items") or []:
            if "all" in item:
                used.add(str(item["all"]))
    orphan = used - keys
    report.add(
        "G3",
        ok=not orphan,
        message="all sequence keys in content" if not orphan else f"orphan keys: {sorted(orphan)[:5]}",
    )
    return report
