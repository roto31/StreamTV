"""ErrorFixer must not rewrite frozen streaming bedrock paths."""

from __future__ import annotations

from pathlib import Path

import pytest

from streamtv.utils.error_fixer import ErrorFixer, is_frozen_fixer_target


@pytest.mark.parametrize(
    "target,expected",
    [
        ("streamtv/streaming/mpegts_streamer.py", True),
        ("streamtv/streaming/stream_manager.py", True),
        ("streamtv/hdhomerun/device.py", True),
        ("streamtv/cache/playback_buffer.py", True),
        ("streamtv/ffmpeg/constants.py", True),
        ("streamtv/scheduling/playout_timeline.py", True),
        ("streamtv/api/iptv.py", True),
        ("./streamtv/streaming/foo.py", True),
        ("config.yaml", False),
        ("streamtv/utils/auto_healer.py", False),
        ("streamtv/api/channels.py", False),
    ],
)
def test_is_frozen_fixer_target(target: str, expected: bool) -> None:
    assert is_frozen_fixer_target(target) is expected


@pytest.mark.asyncio
async def test_ffmpeg_timeout_does_not_write_mpegts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Registry ffmpeg_timeout is operator guidance — never touches mpegts_streamer."""
    root = tmp_path
    mpegts = root / "streamtv" / "streaming" / "mpegts_streamer.py"
    mpegts.parent.mkdir(parents=True)
    original = "first_chunk_timeout = 5.0\n"
    mpegts.write_text(original, encoding="utf-8")

    writes: list[str] = []
    real_open = open

    def tracking_open(path, *args, **kwargs):  # type: ignore[no-untyped-def]
        mode = args[0] if args else kwargs.get("mode", "r")
        if "w" in str(mode):
            writes.append(str(path))
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr("builtins.open", tracking_open)

    fixer = ErrorFixer(root, dry_run=False, max_fix_attempts=3)
    result = await fixer.apply_fix("ffmpeg_timeout")

    assert result["success"] is True
    assert result["fixes_applied"]
    assert all(f.get("requires_review") for f in result["fixes_applied"])
    assert mpegts.read_text(encoding="utf-8") == original
    assert not any("mpegts_streamer" in w for w in writes)


@pytest.mark.asyncio
async def test_frozen_prefix_blocked_even_if_registry_lied(tmp_path: Path) -> None:
    """Direct registered-style apply against bedrock must refuse."""
    root = tmp_path
    target = "streamtv/streaming/mpegts_streamer.py"
    path = root / target
    path.parent.mkdir(parents=True)
    path.write_text("KEEP = 1\n", encoding="utf-8")

    fixer = ErrorFixer(root, dry_run=False)
    # Temporarily inject a hostile registry entry
    fixer.FIX_REGISTRY = {
        **ErrorFixer.FIX_REGISTRY,
        "hostile_bedrock": {
            "type": "code",
            "target": target,
            "fixes": [
                {
                    "description": "should be refused",
                    "search": r"KEEP\s*=\s*1",
                    "replace": lambda m: "KEEP = 2",
                }
            ],
        },
    }
    result = await fixer.apply_fix("hostile_bedrock")
    assert result["success"] is False
    assert result["fixes_failed"]
    assert result["fixes_failed"][0].get("frozen_target") is True
    assert path.read_text(encoding="utf-8") == "KEEP = 1\n"


@pytest.mark.asyncio
async def test_max_fix_attempts_skips_fourth_apply(tmp_path: Path) -> None:
    root = tmp_path
    (root / "config.yaml").write_text(
        "streaming:\n  timeout: 10\n  max_retries: 1\n",
        encoding="utf-8",
    )
    fixer = ErrorFixer(root, dry_run=True, max_fix_attempts=3)

    for _ in range(3):
        r = await fixer.apply_fix("connection_refused")
        assert r["success"] is True
        assert not r.get("skipped_max_attempts")

    fourth = await fixer.apply_fix("connection_refused")
    assert fourth["success"] is False
    assert fourth.get("skipped_max_attempts") is True
    assert "max_fix_attempts" in fourth.get("message", "")
