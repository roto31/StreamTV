"""Unit tests for Plex AAC codec verify/install helpers (Issue 72)."""

from __future__ import annotations

from pathlib import Path

from streamtv.setup import plex_codecs as pc


def test_verify_skips_when_plex_absent(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(pc, "PMS_APP_CANDIDATES", (tmp_path / "no-plex.app",))
    monkeypatch.setattr(pc, "find_plex_transcoder", lambda: None)
    home = tmp_path / "home"
    home.mkdir()
    status = pc.verify_aac_codecs(home=home)
    assert status.detected is False
    assert status.ok is True
    assert status.skipped is True


def test_verify_fails_when_plex_support_empty(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(pc, "PMS_APP_CANDIDATES", (tmp_path / "no-plex.app",))
    monkeypatch.setattr(pc, "find_plex_transcoder", lambda: None)
    home = tmp_path / "home"
    support = home / "Library" / "Application Support" / "Plex Media Server"
    support.mkdir(parents=True)
    status = pc.verify_aac_codecs(home=home)
    assert status.detected is True
    assert status.ok is False
    assert "missing" in status.detail.lower() or "libaac" in status.detail.lower()


def test_verify_ok_with_placeholder_decoder(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(pc, "PMS_APP_CANDIDATES", (tmp_path / "no-plex.app",))
    monkeypatch.setattr(pc, "find_plex_transcoder", lambda: None)
    monkeypatch.setattr(pc, "transcoder_build_id", lambda _t=None: "deadbeef-cafebabe")
    home = tmp_path / "home"
    codecs = (
        home
        / "Library"
        / "Application Support"
        / "Plex Media Server"
        / "Codecs"
        / pc.expected_codec_dir_name("deadbeef-cafebabe")
    )
    codecs.mkdir(parents=True)
    (codecs / pc.AAC_DECODER_NAME).write_bytes(b"placeholder")
    status = pc.verify_aac_codecs(home=home)
    assert status.detected is True
    assert status.ok is True
    assert status.decoder_path is not None


def test_copy_codecs_from_donor(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(pc, "transcoder_build_id", lambda _t=None: "aabbcc-ddeeff")
    monkeypatch.setattr(pc, "darwin_arch_suffix", lambda: "darwin-aarch64")
    home = tmp_path / "home"
    donor = tmp_path / "donor"
    build_name = "aabbcc-ddeeff-darwin-aarch64"
    src = donor / build_name
    src.mkdir(parents=True)
    (src / pc.AAC_DECODER_NAME).write_bytes(b"dec")
    (src / pc.AAC_ENCODER_NAME).write_bytes(b"enc")
    eae = donor / "EasyAudioEncoder-xyz-darwin-aarch64"
    eae.mkdir()
    (eae / "marker").write_text("1", encoding="utf-8")

    detail = pc.copy_codecs_from_donor(donor, home=home, require_build="aabbcc-ddeeff")
    dest = (
        home
        / "Library"
        / "Application Support"
        / "Plex Media Server"
        / "Codecs"
        / build_name
        / pc.AAC_DECODER_NAME
    )
    assert dest.is_file()
    assert "copied" in detail
    status = pc.verify_aac_codecs(home=home)
    assert status.ok is True


def test_parse_transcoder_build_id() -> None:
    text = "ffmpeg version a336ba9-16a9aaf440ee9a92b75f070b Copyright (c) 2000-2025"
    assert pc.parse_transcoder_build_id(text) == "a336ba9-16a9aaf440ee9a92b75f070b"


def test_install_skips_when_already_ok(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        pc,
        "verify_aac_codecs",
        lambda home=None: pc.PlexCodecStatus(
            detected=True,
            ok=True,
            detail="already",
            codecs_root="/tmp",
        ),
    )
    status = pc.install_aac_codecs(home=tmp_path)
    assert status.ok is True
    assert status.detail == "already"
