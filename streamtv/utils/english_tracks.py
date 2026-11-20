"""Offline English-audio / bitmap-subtitle classification for Archive.org titles.

Used by operator scripts only. Does not run on the live MPEG-TS tune path.
English audio on any track always wins over subtitle burn.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Sequence

BITMAP_SUBTITLE_CODECS = frozenset(
    {
        "dvd_subtitle",
        "dvdsub",
        "dvb_subtitle",
        "hdmv_pgs_subtitle",
        "pgssub",
        "xsub",
    }
)

TEXT_SUBTITLE_CODECS = frozenset(
    {
        "subrip",
        "srt",
        "ass",
        "ssa",
        "mov_text",
        "webvtt",
        "text",
    }
)

ENGLISH_LANG_KEYS = frozenset({"eng", "en", "english"})

_US_HARDCODED_HINTS = re.compile(
    r"\b(us\s*version|u\.s\.|criterion|english\s*version|american\s*version)\b",
    re.IGNORECASE,
)


def normalize_media_lang(code: Optional[str]) -> str:
    """Map ISO 639-1/2 / English names to a short compare key (eng/jpn/…)."""
    if not code:
        return ""
    base = str(code).strip().lower().replace("_", "-").split("-", 1)[0]
    if base in ENGLISH_LANG_KEYS:
        return "eng"
    if base in ("ja", "jpn", "jp", "japanese"):
        return "jpn"
    if base in ("und", "unknown", "null", "none"):
        return ""
    return base


def is_english_lang(code: Optional[str]) -> bool:
    return normalize_media_lang(code) == "eng"


@dataclass
class StreamTrack:
    index: int
    codec: str
    language: str


@dataclass
class ProbeResult:
    path_or_url: str
    audio_tracks: list[StreamTrack] = field(default_factory=list)
    subtitle_tracks: list[StreamTrack] = field(default_factory=list)
    video_codec: Optional[str] = None
    error: Optional[str] = None

    @property
    def audio_languages(self) -> list[str]:
        return [t.language for t in self.audio_tracks]

    @property
    def has_english_audio(self) -> bool:
        return any(is_english_lang(t.language) for t in self.audio_tracks)

    @property
    def has_any_audio_language_tag(self) -> bool:
        return any(bool(normalize_media_lang(t.language)) for t in self.audio_tracks)

    @property
    def english_bitmap_index(self) -> Optional[int]:
        """0-based subtitle stream index among subtitle streams only."""
        for i, sub in enumerate(self.subtitle_tracks):
            if sub.codec.lower() not in BITMAP_SUBTITLE_CODECS:
                continue
            if is_english_lang(sub.language):
                return i
        return None

    @property
    def has_english_bitmap(self) -> bool:
        return self.english_bitmap_index is not None

    @property
    def has_english_text_sub(self) -> bool:
        return any(
            is_english_lang(t.language) and t.codec.lower() in TEXT_SUBTITLE_CODECS
            for t in self.subtitle_tracks
        )

    @property
    def dual_audio_english_not_first(self) -> bool:
        if not self.has_english_audio or len(self.audio_tracks) < 2:
            return False
        return not is_english_lang(self.audio_tracks[0].language)


def looks_like_us_or_hardcoded_title(title: str, stream_id: str = "") -> bool:
    blob = f"{title} {stream_id}"
    return bool(_US_HARDCODED_HINTS.search(blob))


def classify_title(
    probe: ProbeResult,
    *,
    title: str = "",
    stream_id: str = "",
    source: str = "archive_org",
) -> str:
    """Return inventory action string per platform English-tracks plan."""
    src = (source or "").strip().lower()
    if src in {"youtube", "pbs"}:
        return f"n/a_{src}" if src else "n/a"
    if probe.error:
        return "probe_error"
    if probe.has_english_audio:
        if probe.dual_audio_english_not_first:
            return "dual_audio_needs_map"
        return "has_english_audio"
    if looks_like_us_or_hardcoded_title(title, stream_id) and not probe.has_any_audio_language_tag:
        return "skip_hardcoded"
    if not probe.has_any_audio_language_tag:
        if probe.has_english_bitmap:
            return "unlabeled_needs_review"
        return "unlabeled_needs_review"
    if probe.has_english_bitmap:
        return "offline_burn"
    if probe.has_english_text_sub:
        return "text_sub_needs_bedrock"
    return "no_english"


def ffprobe_tracks(
    path_or_url: str,
    *,
    ffprobe_path: str = "ffprobe",
    timeout: float = 120.0,
    headers: Optional[Sequence[str]] = None,
) -> ProbeResult:
    """ffprobe all audio/subtitle streams (language tags on every track)."""
    cmd = [
        ffprobe_path,
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_streams",
        "-show_format",
        "-probesize",
        "10000000",
        "-analyzeduration",
        "10000000",
    ]
    if path_or_url.startswith("http"):
        cmd.extend(
            [
                "-timeout",
                "30000000",
                "-user_agent",
                "Mozilla/5.0 (compatible; StreamTV/1.0)",
            ]
        )
        if headers:
            for h in headers:
                cmd.extend(["-headers", h])
    cmd.append(path_or_url)
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return ProbeResult(path_or_url=path_or_url, error=str(exc))
    if proc.returncode != 0 or not proc.stdout:
        err = (proc.stderr or "").strip()[:240] or f"ffprobe exit {proc.returncode}"
        return ProbeResult(path_or_url=path_or_url, error=err)
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return ProbeResult(path_or_url=path_or_url, error=str(exc))
    return parse_ffprobe_json(data, path_or_url)


def parse_ffprobe_json(data: dict[str, Any], path_or_url: str = "") -> ProbeResult:
    result = ProbeResult(path_or_url=path_or_url)
    for stream in data.get("streams") or []:
        codec_type = stream.get("codec_type")
        codec = str(stream.get("codec_name") or "").lower()
        tags = stream.get("tags") or {}
        lang = str(tags.get("language") or tags.get("LANGUAGE") or "")
        idx = int(stream.get("index") or 0)
        if codec_type == "video" and result.video_codec is None:
            # Prefer non-mjpeg (cover art) when possible
            if codec != "mjpeg" or result.video_codec is None:
                if codec != "mjpeg":
                    result.video_codec = codec
                elif result.video_codec is None:
                    result.video_codec = codec
        elif codec_type == "audio":
            result.audio_tracks.append(
                StreamTrack(index=idx, codec=codec, language=lang)
            )
        elif codec_type == "subtitle":
            result.subtitle_tracks.append(
                StreamTrack(index=idx, codec=codec, language=lang)
            )
    return result


def burned_output_path(burned_dir: Path, source_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9._\-]+", "_", source_id).strip("_")
    if not safe.lower().endswith(".mp4"):
        safe = f"{safe}.mp4"
    return burned_dir / safe


def hdhr_port_in_use(port: int = 65001) -> bool:
    """True if an active HDHomeRun *client* tune is in progress.

    Mere LISTEN on discovery port 65001 is normal while com.streamtv runs and
    must NOT block offline burns. We treat ESTABLISHED/TCP connections on the
    HTTP HDHomeRun tune port (8410) or non-LISTEN activity on ``port`` as busy.
    """
    # Active client on MPEG-TS HTTP tune port
    try:
        proc = subprocess.run(
            ["lsof", "-nP", "-iTCP:8410"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return True
    for line in (proc.stdout or "").splitlines():
        if "ESTABLISHED" in line and (
            "v1954" in line
            or "/auto/" in line
            or "hdhomerun" in line.lower()
            or ":8410->" in line
            or "->127.0.0.1:8410" in line
            or "->192.168." in line and ":8410" in line
        ):
            return True
        # Any ESTABLISHED to :8410 from a remote/local client (not just LISTEN)
        if "ESTABLISHED" in line and ":8410" in line:
            return True
    # Optional: ESTABLISHED on UDP/TCP discovery (rare)
    try:
        proc2 = subprocess.run(
            ["lsof", "-nP", f"-iUDP:{port}", f"-iTCP:{port}"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    for line in (proc2.stdout or "").splitlines():
        if "ESTABLISHED" in line:
            return True
    return False
