"""G5 number safety and rollback for newchannel builds (§5.6)."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from streamtv.builder.newchannel import (
    build_new_channel,
    check_number_free,
    refuse_edit_existing,
)


def _mini_spec(number: str) -> tuple[dict, list]:
    spec = {
        "number": number,
        "name": "Probe Channel",
        "slug": "probe-channel",
        "group": "Test",
        "collection_prefix": "Probe",
        "description": "Number safety probe.",
        "schedule_description": "Probe schedule.",
        "sequence_key": "probe-channel",
        "rotation": "interleave_wrap",
        "break_groups": ["mn"],
        "station_id_after_each_gap": False,
        "long_reel_seconds": 1200,
        "style": "prime_2026",
    }
    cands = [
        {
            "id": "probe_prog_1",
            "role": "program",
            "group": None,
            "title": "Probe Show",
            "network": "CBS",
            "date": "1989-12-25",
            "year": 1989,
            "tier": 1,
            "commercials": "yes",
            "note": "test",
            "page": "https://example.com/p",
            "url": "https://www.youtube.com/watch?v=probeprog01",
            "source": "youtube",
            "seconds": 1800,
        },
        {
            "id": "probe_break_1",
            "role": "break",
            "group": "mn",
            "title": "Break",
            "network": "WCCO",
            "date": "1989-12-01",
            "year": 1989,
            "tier": 2,
            "commercials": "yes",
            "note": "break",
            "page": "https://example.com/b",
            "url": "https://www.youtube.com/watch?v=probebreak1",
            "source": "youtube",
            "seconds": 120,
        },
    ]
    return spec, cands


def test_g5_occupied_by_data_yaml(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    (tmp_path / "schedules").mkdir()
    (data / "unified").mkdir()
    payload = {
        "channels": [
            {
                "number": "9555",
                "name": "Taken",
                "streams": [{"id": "x", "url": "https://example.com", "source": "youtube"}],
            }
        ]
    }
    (data / "channels_taken.yaml").write_text(yaml.safe_dump(payload), encoding="utf-8")
    conflict = check_number_free("9555", root=tmp_path)
    assert not conflict.free
    assert any("channels_taken.yaml" in r for r in conflict.reasons)


def test_g5_occupied_by_mn_olympics_schedule(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()
    schedules = tmp_path / "schedules"
    schedules.mkdir()
    (tmp_path / "data" / "unified").mkdir()
    (schedules / "mn-olympics-9556.yml").write_text("name: x\n", encoding="utf-8")
    conflict = check_number_free("9556", root=tmp_path)
    assert not conflict.free
    assert any("mn-olympics-9556.yml" in r for r in conflict.reasons)


def test_g5_template_example_refused() -> None:
    conflict = check_number_free("1225")
    assert not conflict.free
    assert any("template example" in r for r in conflict.reasons)


def test_refuse_edit_message() -> None:
    msg = refuse_edit_existing("2011")
    assert "out of scope" in msg
    assert "2011" in msg


def test_build_onto_occupied_writes_nothing(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    (tmp_path / "schedules").mkdir()
    (data / "unified").mkdir()
    (data / "builder_drafts").mkdir()
    (data / "channels_occupied.yaml").write_text(
        yaml.safe_dump(
            {
                "channels": [
                    {
                        "number": "9557",
                        "name": "Occupied",
                        "streams": [
                            {
                                "id": "occ1",
                                "url": "https://example.com/a",
                                "source": "youtube",
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    spec, cands = _mini_spec("9557")
    report, artifacts, details = build_new_channel(
        spec,
        cands,
        root=tmp_path,
        import_channel=False,
    )
    assert not report.ok
    assert artifacts is None
    assert not (data / "channels_generated_9557.yaml").exists()
    assert not (tmp_path / "schedules" / "9557.yml").exists()
    assert any(r.gate == "G5" and not r.ok for r in report.results)


def test_successful_dry_run_and_write(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    (tmp_path / "schedules").mkdir()
    (data / "unified").mkdir()
    (data / "builder_drafts").mkdir()
    spec, cands = _mini_spec("9558")

    report, artifacts, details = build_new_channel(
        spec, cands, root=tmp_path, import_channel=False, dry_run=True
    )
    assert report.ok
    assert artifacts is None
    assert "channel_yaml" in details

    report2, artifacts2, _ = build_new_channel(
        spec, cands, root=tmp_path, import_channel=False, dry_run=False
    )
    assert report2.ok
    assert artifacts2 is not None
    assert (data / "channels_generated_9558.yaml").exists()
    assert (tmp_path / "schedules" / "9558.yml").exists()
    assert (data / "unified" / "9558.channel.yaml").exists()


def test_forced_failure_rolls_back(tmp_path: Path, monkeypatch) -> None:
    data = tmp_path / "data"
    data.mkdir()
    (tmp_path / "schedules").mkdir()
    (data / "unified").mkdir()
    (data / "builder_drafts").mkdir()
    spec, cands = _mini_spec("9559")

    # Force failure after files would be written by breaking dump mid-flight via import
    def boom(*_a, **_k):
        raise RuntimeError("forced G8 failure")

    monkeypatch.setattr(
        "streamtv.builder.newchannel.evaluate_compiled_package",
        lambda *a, **k: __import__(
            "streamtv.builder.gates", fromlist=["GateReport"]
        ).GateReport(),
    )
    # Patch _write_text to write first file then fail on second
    from streamtv.builder import newchannel as nc

    calls = {"n": 0}
    real_write = nc._write_text

    def flaky(path: Path, text: str) -> None:
        calls["n"] += 1
        if calls["n"] >= 2:
            raise RuntimeError("forced G8 failure")
        real_write(path, text)

    monkeypatch.setattr(nc, "_write_text", flaky)
    report, artifacts, details = build_new_channel(
        spec, cands, root=tmp_path, import_channel=False
    )
    assert artifacts is None
    assert any(r.gate == "G8" and not r.ok for r in report.results)
    assert any(r.gate == "G9" and r.ok for r in report.results)
    # First path may have been written then rolled back
    assert not (data / "channels_generated_9559.yaml").exists()
