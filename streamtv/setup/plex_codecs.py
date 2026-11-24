"""Plex AAC codec pack verify / install (Issue 72).

Codecs live only under PMS Application Support. StreamTV never vendors Plex
dylibs into the repo or DMG. Install tries PMS on-demand download first, then
optional donor-directory copy (same Transcoder build id).
"""

from __future__ import annotations

import logging
import os
import platform
import re
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

CODEC_ROOT_REL = Path("Library/Application Support/Plex Media Server/Codecs")
PMS_SUPPORT_REL = Path("Library/Application Support/Plex Media Server")
AAC_DECODER_NAME = "libaac_decoder.dylib"
AAC_ENCODER_NAME = "libaac_encoder.dylib"

TRANSCCODER_CANDIDATES = (
    Path("/Applications/Plex Media Server.app/Contents/MacOS/Plex Transcoder"),
    Path("/Applications/Plex.app/Contents/MacOS/Plex Transcoder"),
)

PMS_APP_CANDIDATES = (
    Path("/Applications/Plex Media Server.app"),
    Path("/Applications/Plex.app"),
)

_VERSION_RE = re.compile(
    r"ffmpeg version\s+([0-9a-f]+-[0-9a-f]+)",
    re.IGNORECASE,
)


@dataclass
class PlexCodecStatus:
    detected: bool
    ok: bool
    detail: str
    codecs_root: str
    build_hint: Optional[str] = None
    decoder_path: Optional[str] = None
    transcoder_path: Optional[str] = None
    skipped: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_codecs_root(*, home: Optional[Path] = None) -> Path:
    base = home or Path.home()
    return base / CODEC_ROOT_REL


def default_pms_support(*, home: Optional[Path] = None) -> Path:
    base = home or Path.home()
    return base / PMS_SUPPORT_REL


def darwin_arch_suffix() -> str:
    machine = platform.machine().lower()
    if machine in {"arm64", "aarch64"}:
        return "darwin-aarch64"
    return "darwin-x86_64"


def find_plex_transcoder() -> Optional[Path]:
    for path in TRANSCCODER_CANDIDATES:
        if path.is_file():
            return path
    which = shutil.which("Plex Transcoder")
    if which:
        return Path(which)
    return None


def plex_detected(*, home: Optional[Path] = None) -> bool:
    if any(app.is_dir() for app in PMS_APP_CANDIDATES):
        return True
    support = default_pms_support(home=home)
    if support.is_dir():
        return True
    return find_plex_transcoder() is not None


def parse_transcoder_build_id(version_text: str) -> Optional[str]:
    match = _VERSION_RE.search(version_text)
    if not match:
        return None
    return match.group(1)


def transcoder_build_id(transcoder: Optional[Path] = None) -> Optional[str]:
    binary = transcoder or find_plex_transcoder()
    if binary is None:
        return None
    try:
        proc = subprocess.run(
            [str(binary), "-version"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("Plex Transcoder -version failed: %s", exc)
        return None
    text = (proc.stdout or "") + "\n" + (proc.stderr or "")
    return parse_transcoder_build_id(text)


def expected_codec_dir_name(build_id: str) -> str:
    return f"{build_id}-{darwin_arch_suffix()}"


def find_aac_decoder(codecs_root: Path, *, prefer_build: Optional[str] = None) -> Optional[Path]:
    if not codecs_root.is_dir():
        return None
    if prefer_build:
        preferred = codecs_root / expected_codec_dir_name(prefer_build) / AAC_DECODER_NAME
        if preferred.is_file():
            return preferred
    matches = sorted(codecs_root.rglob(AAC_DECODER_NAME))
    return matches[0] if matches else None


def verify_aac_codecs(*, home: Optional[Path] = None) -> PlexCodecStatus:
    codecs_root = default_codecs_root(home=home)
    transcoder = find_plex_transcoder()
    build = transcoder_build_id(transcoder) if transcoder else None
    detected = plex_detected(home=home)

    if not detected:
        return PlexCodecStatus(
            detected=False,
            ok=True,
            detail="Plex not installed — AAC codec gate skipped",
            codecs_root=str(codecs_root),
            build_hint=build,
            transcoder_path=str(transcoder) if transcoder else None,
            skipped=True,
        )

    decoder = find_aac_decoder(codecs_root, prefer_build=build)
    if decoder is not None:
        return PlexCodecStatus(
            detected=True,
            ok=True,
            detail=f"AAC decoder present: {decoder}",
            codecs_root=str(codecs_root),
            build_hint=build,
            decoder_path=str(decoder),
            transcoder_path=str(transcoder) if transcoder else None,
        )

    hint = (
        f"missing {AAC_DECODER_NAME} under {codecs_root}"
        + (f" (expected dir {expected_codec_dir_name(build)})" if build else "")
    )
    return PlexCodecStatus(
        detected=True,
        ok=False,
        detail=hint,
        codecs_root=str(codecs_root),
        build_hint=build,
        transcoder_path=str(transcoder) if transcoder else None,
    )


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _plex_hold_ts() -> Optional[Path]:
    candidate = _repo_root() / "data" / "plex_hold.ts"
    if candidate.is_file():
        return candidate
    # App bundle / Application Support may not ship data/; allow env override.
    env = os.environ.get("STREAMTV_PLEX_HOLD_TS")
    if env:
        path = Path(env).expanduser()
        if path.is_file():
            return path
    return None


def trigger_pms_codec_download(*, home: Optional[Path] = None, timeout_sec: float = 45.0) -> str:
    """Exercise Plex Transcoder remux so PMS may fetch missing AAC packs.

    Does not ship dylibs — only runs the local Transcoder against a tiny AAC TS.
    """
    transcoder = find_plex_transcoder()
    if transcoder is None:
        return "no Plex Transcoder binary found"

    build = transcoder_build_id(transcoder)
    codecs_root = default_codecs_root(home=home)
    codecs_root.mkdir(parents=True, exist_ok=True)

    if build:
        version_dir = codecs_root / expected_codec_dir_name(build)
        version_dir.mkdir(parents=True, exist_ok=True)
        external_libs = str(version_dir)
    else:
        # Point at Codecs root; PMS often creates the version dir on first use.
        external_libs = str(codecs_root)

    hold = _plex_hold_ts()
    if hold is None:
        return (
            "plex_hold.ts not found — play any library AAC item in Plex, or set "
            "STREAMTV_PLEX_HOLD_TS / use --from-dir donor copy"
        )

    env = os.environ.copy()
    env["FFMPEG_EXTERNAL_LIBS"] = external_libs

    with tempfile.TemporaryDirectory(prefix="streamtv-plex-codec-") as tmp:
        out_pattern = str(Path(tmp) / "media-%05d.ts")
        cmd = [
            str(transcoder),
            "-hide_banner",
            "-loglevel",
            "warning",
            "-i",
            str(hold),
            "-c",
            "copy",
            "-f",
            "ssegment",
            "-segment_time",
            "2",
            "-segment_format",
            "mpegts",
            out_pattern,
        ]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                check=False,
                env=env,
            )
        except subprocess.TimeoutExpired:
            return f"Plex Transcoder remux timed out after {timeout_sec}s (codec download may still be in progress)"
        except OSError as exc:
            return f"Plex Transcoder remux failed to start: {exc}"

        err = (proc.stderr or proc.stdout or "").strip()
        snippet = err[-400:] if err else f"exit {proc.returncode}"
        return f"triggered remux via {transcoder.name} (libs={external_libs}): {snippet}"


def _build_id_from_dir_name(name: str) -> Optional[str]:
    # a336ba9-16a9aaf440ee9a92b75f070b-darwin-aarch64
    suffix = f"-{darwin_arch_suffix()}"
    if name.endswith(suffix):
        return name[: -len(suffix)]
    # Accept either arch suffix
    for arch in ("darwin-aarch64", "darwin-x86_64"):
        tail = f"-{arch}"
        if name.endswith(tail):
            return name[: -len(tail)]
    return None


def copy_codecs_from_donor(
    donor: Path,
    *,
    home: Optional[Path] = None,
    require_build: Optional[str] = None,
) -> str:
    """Copy matching build-id + EasyAudioEncoder trees into default Codecs root."""
    donor = donor.expanduser().resolve()
    if not donor.is_dir():
        raise FileNotFoundError(f"donor Codecs dir not found: {donor}")

    codecs_root = default_codecs_root(home=home)
    codecs_root.mkdir(parents=True, exist_ok=True)

    build = require_build or transcoder_build_id()
    decoder = find_aac_decoder(donor, prefer_build=build)
    if decoder is None:
        raise FileNotFoundError(
            f"donor {donor} has no {AAC_DECODER_NAME}"
            + (f" for build {build}" if build else "")
        )

    build_dir = decoder.parent
    donor_build = _build_id_from_dir_name(build_dir.name)
    if build and donor_build and donor_build != build:
        raise ValueError(
            f"donor build {donor_build} does not match local Transcoder {build} — refuse cross-build copy"
        )

    dest_build = codecs_root / build_dir.name
    if dest_build.exists():
        shutil.rmtree(dest_build)
    shutil.copytree(build_dir, dest_build)

    # EasyAudioEncoder sibling trees
    copied_eae: list[str] = []
    for eae in donor.glob("EasyAudioEncoder-*-darwin-*"):
        if not eae.is_dir():
            continue
        dest_eae = codecs_root / eae.name
        if dest_eae.exists():
            shutil.rmtree(dest_eae)
        shutil.copytree(eae, dest_eae)
        copied_eae.append(eae.name)

    # Ensure encoder present if donor has it next to decoder
    enc = build_dir / AAC_ENCODER_NAME
    if enc.is_file():
        shutil.copy2(enc, dest_build / AAC_ENCODER_NAME)

    detail = f"copied {build_dir.name} → {dest_build}"
    if copied_eae:
        detail += f"; EasyAudioEncoder={','.join(copied_eae)}"
    return detail


def install_aac_codecs(
    *,
    home: Optional[Path] = None,
    from_dir: Optional[str] = None,
    trigger_download: bool = True,
) -> PlexCodecStatus:
    """Install path C: PMS trigger, then optional donor copy; always re-verify."""
    status = verify_aac_codecs(home=home)
    if not status.detected:
        return status
    if status.ok:
        return status

    notes: list[str] = []

    if trigger_download:
        notes.append(trigger_pms_codec_download(home=home))
        status = verify_aac_codecs(home=home)
        if status.ok:
            status.detail = f"{status.detail} (after PMS trigger: {notes[-1][:120]})"
            return status

    donor = from_dir or os.environ.get("STREAMTV_PLEX_CODEC_SOURCE")
    if donor:
        try:
            copy_detail = copy_codecs_from_donor(
                Path(donor),
                home=home,
                require_build=status.build_hint,
            )
            notes.append(copy_detail)
        except (OSError, ValueError, FileNotFoundError) as exc:
            notes.append(f"donor copy failed: {exc}")
        status = verify_aac_codecs(home=home)
        if status.ok:
            status.detail = f"{status.detail} (after donor: {notes[-1]})"
            return status

    # Still missing
    guidance = (
        "AAC codecs still missing. Retry after Plex is signed in, play a library "
        "AAC item, or re-run with --from-dir pointing at a healthy host's "
        "…/Plex Media Server/Codecs (same Transcoder build id). "
        f"Notes: {' | '.join(notes) if notes else 'no install steps ran'}"
    )
    status.detail = guidance
    status.ok = False
    return status


def ensure_codecs_for_setup_complete(*, home: Optional[Path] = None) -> PlexCodecStatus:
    """Gate helper for POST /api/setup/complete."""
    return verify_aac_codecs(home=home)
