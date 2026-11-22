"""§5.8 package writer smoke test."""

from __future__ import annotations

from pathlib import Path

from streamtv.builder.reports import write_channel_package


def test_write_channel_package_creates_artifacts(tmp_path: Path) -> None:
    channel_doc = {
        "channels": [
            {
                "number": "9224",
                "name": "Test Package Channel",
                "group": "Holiday",
                "description": "probe",
                "enabled": True,
                "streams": [
                    {
                        "id": "demo_stream",
                        "type": "event",
                        "network": "CBS",
                        "broadcast_date": "1989-12-01",
                        "runtime": "PT1H",
                        "url": "https://archive.org/download/x/y.mp4",
                        "source_metadata": {"platform": "archive", "title": "Demo"},
                    }
                ],
            }
        ]
    }
    schedule = {
        "name": "9224 Test",
        "content": [{"key": "demo_stream", "collection": "c", "order": "chronological"}],
        "sequence": [{"key": "loop", "items": [{"all": "demo_stream"}]}],
        "playout": [{"sequence": "loop"}, {"repeat": True}],
    }
    artifacts = write_channel_package(
        draft_id="draft_test_pkg",
        channel_doc=channel_doc,
        schedule=schedule,
        candidates=[
            {
                "id": "demo_stream",
                "role": "program",
                "title": "Demo",
                "source": "archive",
                "tier": 1,
                "network": "CBS",
                "date": "1989-12-01",
                "commercials": "yes",
                "page": "https://archive.org/details/x",
            }
        ],
        root=tmp_path,
        excluded=[{"title": "Skip Me", "reason": "duplicate"}],
    )
    out = Path(artifacts["dir"])
    assert (out / "SOURCES.md").exists()
    assert (out / "urls.tsv").exists()
    assert (out / "README.md").exists()
    assert Path(artifacts["install_script"]).exists()
    assert "9224" in Path(artifacts["install_script"]).read_text(encoding="utf-8")
    assert (out / "metadata" / "demo_stream.json").exists()
