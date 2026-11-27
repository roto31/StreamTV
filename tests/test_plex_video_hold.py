"""Tests for Plex video hold mux."""

from __future__ import annotations

import asyncio

import pytest

# StreamTV null keepalive (same construction as mpegts_keepalive)
_MPEGTS_NULL = bytes([0x47, 0x1F, 0xFF, 0x10] + [0xFF] * 184)
_KEEPALIVE = (_MPEGTS_NULL * ((8192 // 188) + 1))[:8192]


@pytest.fixture(scope="module")
def hold_mod():
    from streamtv.tuners import video_hold

    return video_hold


def _fake_video_packet(pid: int = 0x0100) -> bytes:
    pkt = bytearray(188)
    pkt[0] = 0x47
    pkt[1] = (pid >> 8) & 0x1F
    pkt[2] = pid & 0xFF
    pkt[3] = 0x10  # payload only, cc=0
    pkt[4:] = b"\x00" * 184
    return bytes(pkt)


def test_keepalive_is_all_null(hold_mod) -> None:
    assert hold_mod.is_all_null_keepalive(_KEEPALIVE)
    assert hold_mod.is_all_null_keepalive(b"")
    assert not hold_mod.is_all_null_keepalive(_fake_video_packet())


def test_strip_null_keeps_video(hold_mod) -> None:
    video = _fake_video_packet()
    mixed = _MPEGTS_NULL + video + _MPEGTS_NULL
    out = hold_mod.strip_null_packets(mixed)
    assert out == video
    assert hold_mod.has_video_payload(mixed)


def test_hold_chunk_not_keepalive_size_only(hold_mod) -> None:
    """Hold file must be real MPEG-TS, not the 8192-byte null keepalive."""
    path = hold_mod.default_hold_path()
    if not path.is_file():
        pytest.skip("data/plex_hold.ts not generated")
    data = path.read_bytes()
    assert len(data) > 8192
    assert not hold_mod.is_all_null_keepalive(data[:8192])
    assert hold_mod.has_video_payload(data[:188 * 40])


@pytest.mark.asyncio
async def test_video_hold_emits_before_slow_upstream(hold_mod, tmp_path: Path) -> None:
    # Tiny synthetic hold: repeating video packets
    hold = tmp_path / "hold.ts"
    hold.write_bytes(_fake_video_packet() * 50)

    async def slow_upstream():
        await asyncio.sleep(0.35)
        yield _fake_video_packet(0x0200) * 10

    chunks: list[bytes] = []
    deadline = asyncio.get_event_loop().time() + 2.0
    async for chunk in hold_mod.video_hold_mux(
        slow_upstream(), hold_path=hold, silence_sec=2.0
    ):
        chunks.append(chunk)
        if asyncio.get_event_loop().time() > deadline:
            break
        if len(chunks) >= 5:
            break

    assert chunks, "expected hold chunks before upstream"
    # First chunk should arrive quickly (hold), not after 0.35s sleep alone
    assert hold_mod.has_video_payload(chunks[0])
    assert not hold_mod.is_all_null_keepalive(chunks[0])


@pytest.mark.asyncio
async def test_video_hold_skips_null_prefix(hold_mod, tmp_path: Path) -> None:
    hold = tmp_path / "hold.ts"
    hold.write_bytes(_fake_video_packet() * 20)
    real = _fake_video_packet(0x0101) * 5

    async def upstream():
        yield _KEEPALIVE
        yield _KEEPALIVE
        yield real

    got_real = False
    async for chunk in hold_mod.video_hold_mux(
        upstream(), hold_path=hold, silence_sec=2.0
    ):
        cleaned = hold_mod.strip_null_packets(chunk)
        if cleaned and cleaned[:3] == real[:3]:
            got_real = True
            break
        if hold_mod.is_all_null_keepalive(chunk):
            pytest.fail("null keepalive must not be forwarded to client")
    assert got_real


@pytest.mark.asyncio
async def test_video_hold_no_rehold_after_splice(hold_mod, tmp_path: Path) -> None:
    """Wait-phase mode: after first real video, silence must not resume hold."""
    hold = tmp_path / "hold.ts"
    hold_pkt = _fake_video_packet(0x0100)
    hold.write_bytes(hold_pkt * 40)
    real = _fake_video_packet(0x0200) * 5

    async def upstream():
        yield _KEEPALIVE
        await asyncio.sleep(0.15)
        yield real
        await asyncio.sleep(0.5)  # silence longer than silence_sec if rehold were on
        yield real

    chunks: list[bytes] = []
    async for chunk in hold_mod.video_hold_mux(
        upstream(),
        hold_path=hold,
        silence_sec=0.2,
        rehold_on_silence=False,
    ):
        chunks.append(chunk)
        if len(chunks) >= 8:
            break

    assert chunks
    # After splice, further chunks must be real PID 0x0200 — not hold PID 0x0100
    spliced = False
    for chunk in chunks:
        cleaned = hold_mod.strip_null_packets(chunk)
        if not cleaned:
            continue
        pid = hold_mod.pid_of_packet(cleaned[:188])
        if pid == 0x0200:
            spliced = True
        elif spliced and pid == 0x0100:
            pytest.fail("rehold must not resume after wait-phase splice")
    assert spliced


def test_youtube_wait_hold_env_default_on(hold_mod, monkeypatch) -> None:
    monkeypatch.delenv("STREAMTV_PLEX_VIDEO_HOLD_YOUTUBE", raising=False)
    assert hold_mod.youtube_wait_hold_env_enabled() is False
    monkeypatch.setenv("STREAMTV_PLEX_VIDEO_HOLD_YOUTUBE", "1")
    assert hold_mod.youtube_wait_hold_env_enabled() is True


def test_hold_chunk_pace(hold_mod) -> None:
    pace = hold_mod.hold_chunk_pace_sec(8192)
    assert 0.02 <= pace <= 0.2
