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


def _fake_video_packet(pid: int = 0x0100, *, pusi: bool = False) -> bytes:
    pkt = bytearray(188)
    pkt[0] = 0x47
    pkt[1] = (pid >> 8) & 0x1F
    if pusi:
        pkt[1] |= 0x40
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


@pytest.mark.asyncio
async def test_video_hold_min_splice_bytes_buffers_thin_burst(
    hold_mod, tmp_path: Path
) -> None:
    """Archive wait-phase: thin first burst must not splice until floor is met."""
    hold = tmp_path / "hold.ts"
    hold_pkt = _fake_video_packet(0x0100)
    hold.write_bytes(hold_pkt * 40)
    thin = _fake_video_packet(0x0200) * 2  # 376 bytes
    fat = _fake_video_packet(0x0200) * 400  # 75200 bytes

    async def upstream():
        yield thin
        await asyncio.sleep(0.25)  # hold should keep looping through this gap
        yield fat

    chunks: list[bytes] = []
    saw_hold_after_thin = False
    spliced = False
    async for chunk in hold_mod.video_hold_mux(
        upstream(),
        hold_path=hold,
        silence_sec=2.0,
        rehold_on_silence=False,
        min_splice_bytes=8_000,
    ):
        chunks.append(chunk)
        cleaned = hold_mod.strip_null_packets(chunk)
        if not cleaned:
            continue
        pid = hold_mod.pid_of_packet(cleaned[:188])
        if not spliced and pid == 0x0100:
            saw_hold_after_thin = True
        if pid == 0x0200:
            spliced = True
            break
        if len(chunks) > 80:
            break

    assert saw_hold_after_thin, "must keep emitting hold through thin burst"
    assert spliced, "must splice once buffered bytes meet the floor"


@pytest.mark.asyncio
async def test_hold_reassembles_8192_straddle(hold_mod, tmp_path: Path) -> None:
    """8192-byte reads split a TS packet; the splice must not drop it."""
    hold = tmp_path / "hold.ts"
    hold.write_bytes(_fake_video_packet(0x00FF) * 4)
    packet = _fake_video_packet(0x0200, pusi=True)
    raw = packet * 50  # 9400 bytes, not a multiple of 8192
    assert len(raw) > 8192

    async def upstream():
        yield raw[:8192]
        yield raw[8192:]

    out = b""
    async for chunk in hold_mod.video_hold_mux(
        upstream(),
        hold_path=hold,
        silence_sec=2.0,
        rehold_on_silence=False,
    ):
        out += chunk
    got = 0
    aligned = len(out) - (len(out) % 188)
    for i in range(0, aligned, 188):
        if out[i] != 0x47:
            continue
        if hold_mod.pid_of_packet(out[i : i + 188]) == 0x0200:
            got += 1
    assert got == 50


def test_discontinuity_skips_sdt_truncation(hold_mod) -> None:
    """Hold→program splice must not truncate SDT/PAT when stuffing discontinuity."""
    sdt = _fake_video_packet(0x0011)
    video = _fake_video_packet(0x0100, pusi=True)
    chunk = sdt + video
    out = hold_mod.discontinuity_flag_media_chunk(chunk)
    # SDT payload-only bytes preserved (no adaptation stuffed into SDT)
    assert out[:188] == sdt
    assert hold_mod.pid_of_packet(out[188:376]) == 0x0100
    assert out[188 + 3] & 0x30 == 0x30  # adaptation + payload on video
    assert out[188 + 5] & 0x80  # discontinuity_indicator


@pytest.mark.asyncio
async def test_archive_splice_waits_for_video_pusi(hold_mod, tmp_path: Path) -> None:
    hold = tmp_path / "hold.ts"
    hold_pkt = _fake_video_packet(0x00FF)  # distinct hold PID
    hold.write_bytes(hold_pkt * 40)
    fat_no_pusi = _fake_video_packet(0x0100, pusi=False) * 400
    with_pusi = _fake_video_packet(0x0100, pusi=True) * 10

    async def upstream():
        yield fat_no_pusi
        await asyncio.sleep(0.2)
        yield with_pusi

    saw_hold = False
    saw_pusi_upstream = False
    n = 0
    async for chunk in hold_mod.video_hold_mux(
        upstream(),
        hold_path=hold,
        silence_sec=2.0,
        rehold_on_silence=False,
        min_splice_bytes=8_000,
        require_video_pusi=True,
    ):
        n += 1
        pid = hold_mod.pid_of_packet(chunk[:188]) if len(chunk) >= 188 else -1
        if pid == 0x00FF:
            saw_hold = True
        if hold_mod.pending_has_video_pusi([chunk]):
            saw_pusi_upstream = True
            break
        if n > 120:
            break
    assert saw_hold, "must keep hold while upstream lacks video PUSI"
    assert saw_pusi_upstream, "must splice once a video PUSI arrives"


def test_youtube_wait_hold_env_default_on(hold_mod, monkeypatch) -> None:
    monkeypatch.delenv("STREAMTV_PLEX_VIDEO_HOLD_YOUTUBE", raising=False)
    assert hold_mod.youtube_wait_hold_env_enabled() is False
    monkeypatch.setenv("STREAMTV_PLEX_VIDEO_HOLD_YOUTUBE", "1")
    assert hold_mod.youtube_wait_hold_env_enabled() is True


def _streaming_response():
    from starlette.responses import StreamingResponse

    async def body():
        yield _KEEPALIVE

    return StreamingResponse(body(), media_type="video/mp2t")


ARCHIVE_URL = "https://archive.org/download/tape-1/Tape%201.mp4"


@pytest.fixture
def archive_env(hold_mod, monkeypatch, tmp_path):
    """Allowlist 1984.2, isolate sidecars, write both hold assets, fix on-air URL."""
    from streamtv.utils import archive_probe_cache

    root = tmp_path / "probe_cache"
    monkeypatch.setattr(
        archive_probe_cache,
        "sidecar_path",
        lambda identifier, filename: root / identifier / f"{filename}.probe.json",
    )
    hold_480 = tmp_path / "plex_hold_480.ts"
    hold_720 = tmp_path / "plex_hold.ts"
    for path in (hold_480, hold_720):
        path.write_bytes(_fake_video_packet() * 20)
    monkeypatch.setenv("STREAMTV_PLEX_HOLD_ARCHIVE_TS", str(hold_480))
    monkeypatch.setenv("STREAMTV_PLEX_HOLD_TS", str(hold_720))
    monkeypatch.setenv("STREAMTV_PLEX_VIDEO_HOLD_ARCHIVE_CHANNELS", "80, 1984.2")
    monkeypatch.setattr(hold_mod, "on_air_media_url", lambda channel, db: ARCHIVE_URL)
    return {"cache": archive_probe_cache, "hold_480": hold_480, "hold_720": hold_720}


def _save_sidecar(cache, width=None, height=None) -> None:
    info = {"video_codec": "h264", "audio_codec": "aac", "can_copy_video": True}
    if width is not None:
        info.update(width=width, height=height)
    assert cache.save(ARCHIVE_URL, info)


def _wrapped_hold_path(hold_mod, monkeypatch, channel: str = "1984.2"):
    """Return the hold_path the Archive wrap passed to maybe_wrap_mpegts_hold, or None."""
    seen: dict = {}

    def fake_wrap(response, **kwargs):
        seen.update(kwargs)
        return object()

    monkeypatch.setattr(hold_mod, "maybe_wrap_mpegts_hold", fake_wrap)
    resp = _streaming_response()
    out = hold_mod.maybe_wrap_archive_wait_hold(resp, channel, db=None)
    return None if out is resp else seen["hold_path"]


def test_archive_wait_hold_480_item_uses_480_hold(hold_mod, archive_env, monkeypatch) -> None:
    _save_sidecar(archive_env["cache"], 640, 480)
    assert _wrapped_hold_path(hold_mod, monkeypatch) == archive_env["hold_480"]


def test_archive_wait_hold_720_item_uses_720_hold(hold_mod, archive_env, monkeypatch) -> None:
    _save_sidecar(archive_env["cache"], 1280, 720)
    assert _wrapped_hold_path(hold_mod, monkeypatch) == archive_env["hold_720"]


def test_archive_wait_hold_other_geometry_skips(hold_mod, archive_env, monkeypatch) -> None:
    _save_sidecar(archive_env["cache"], 1920, 1080)
    assert _wrapped_hold_path(hold_mod, monkeypatch) is None


def test_archive_wait_hold_missing_geometry_skips(hold_mod, archive_env, monkeypatch) -> None:
    _save_sidecar(archive_env["cache"])
    assert _wrapped_hold_path(hold_mod, monkeypatch) is None


def test_archive_wait_hold_no_sidecar_skips(hold_mod, archive_env, monkeypatch) -> None:
    assert _wrapped_hold_path(hold_mod, monkeypatch) is None


def test_archive_wait_hold_missing_hold_file_skips(hold_mod, archive_env, monkeypatch) -> None:
    _save_sidecar(archive_env["cache"], 640, 480)
    archive_env["hold_480"].unlink()
    assert _wrapped_hold_path(hold_mod, monkeypatch) is None


def test_archive_wait_hold_skips_unlisted(hold_mod, archive_env, monkeypatch) -> None:
    _save_sidecar(archive_env["cache"], 640, 480)
    assert _wrapped_hold_path(hold_mod, monkeypatch, channel="1984") is None


def test_archive_wait_hold_empty_env_wraps_nothing(hold_mod, archive_env, monkeypatch) -> None:
    _save_sidecar(archive_env["cache"], 640, 480)
    monkeypatch.delenv("STREAMTV_PLEX_VIDEO_HOLD_ARCHIVE_CHANNELS", raising=False)
    assert hold_mod.archive_wait_hold_channels() == frozenset()
    assert _wrapped_hold_path(hold_mod, monkeypatch) is None


def test_archive_wait_hold_real_wrap_returns_new_response(hold_mod, archive_env) -> None:
    _save_sidecar(archive_env["cache"], 640, 480)
    resp = _streaming_response()
    assert hold_mod.maybe_wrap_archive_wait_hold(resp, "1984.2", db=None) is not resp


def test_youtube_wait_hold_uses_default_720_hold(hold_mod, archive_env, monkeypatch) -> None:
    seen: dict = {}
    monkeypatch.setattr(hold_mod, "channel_needs_youtube_wait_hold", lambda channel, db: True)
    monkeypatch.setattr(
        hold_mod, "maybe_wrap_mpegts_hold", lambda response, **kw: seen.update(kw) or object()
    )
    hold_mod.maybe_wrap_youtube_wait_hold(_streaming_response(), "1985", db=None)
    assert seen.get("hold_path") is None
    assert hold_mod.default_hold_path() == archive_env["hold_720"]


def test_hold_chunk_pace(hold_mod) -> None:
    pace = hold_mod.hold_chunk_pace_sec(8192)
    assert 0.02 <= pace <= 0.2
