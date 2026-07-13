"""FFmpeg flag constants — single source of truth.

Any FFmpeg flag string used in more than one place, or whose exact value was
the subject of a past bug, MUST be defined here and imported. Never inline
these literals. See .cursor/rules/streamtv-safety.mdc.
"""

# Input fflags for network streams (YouTube path).
# +genpts: synthesize missing PTS; +discardcorrupt: drop corrupt packets;
# +igndts: ignore broken DTS from CDN segment boundaries.
# NEVER add +fastseek (local-file optimization) or use -flags +low_delay
# (breaks decoder reordering on HLS) on network inputs.
FFLAGS_NETWORK_STREAMING = "+genpts+discardcorrupt+igndts"

# Pace direct YouTube VOD inputs by media timestamps. Without this input flag,
# FFmpeg consumes multi-hour VODs in minutes and reaches CDN EOF prematurely.
INPUT_FLAG_REALTIME = "-re"

# H.264 bitstream filters for stream-copy into MPEG-TS.
# h264_mp4toannexb converts AVCC (length-prefixed, MP4/MOV/MKV containers) to
# Annex B (start-code prefixed) as required by MPEG-TS. It must NOT be forced
# onto sources that are already Annex B (HLS .m3u8, .ts). dump_extra re-injects
# SPS/PPS at keyframes and is safe for both.
BSF_H264_MP4TOANNEXB = "h264_mp4toannexb"
BSF_H264_DUMP_EXTRA = "dump_extra"

# Container format_name substrings (from ffprobe) that indicate AVCC packaging
# and therefore require h264_mp4toannexb when copying into MPEG-TS.
AVCC_CONTAINER_HINTS = ("mp4", "mov", "m4a", "3gp", "matroska", "webm")

# YouTube signed CDN URLs are valid ~6 minutes. Cache resolved URLs for less.
YOUTUBE_URL_TTL_VOD_SECONDS = 240
YOUTUBE_URL_TTL_LIVE_SECONDS = 25

# yt-dlp client policy (verified against yt-dlp PO Token Guide, 2026-07).
# YouTube enforces Proof-of-Origin (PO) Tokens per client:
#   web        -> SABR-only, GVS PO Token required   (unusable without plugin)
#   android/ios-> GVS or Player PO Token required    (unusable without plugin)
#   tv         -> formats DRM'd without account cookies
#   web_safari -> HLS (m3u8) formats require NO PO Token   <- primary
#   android_vr -> no PO Token ("made for kids" videos unavailable) <- fallback
#   web_embedded -> no PO Token (embeddable videos only)   <- last resort
# HLS live streams require no PO Token on any client except ios.
YOUTUBE_PLAYER_CLIENTS = ["web_safari", "android_vr", "web_embedded"]

# Extractor args dict to merge into every yt-dlp options dict for YouTube.
YOUTUBE_EXTRACTOR_ARGS = {"youtube": {"player_client": YOUTUBE_PLAYER_CLIENTS}}

# Minimum acceptable yt-dlp version; warn loudly at startup if older.
# YouTube extractor breakage in stale yt-dlp is the #1 fleet-wide failure mode.
YTDLP_MIN_VERSION = "2026.07.04"

# STREAMING selector (Track B, single- or dual-URL consumption by FFmpeg):
# prefer muxed H.264+AAC (incl. HLS variants), then split avc1+mp4a pairs
# (returned as info['requested_formats'] -> dual-input FFmpeg), then anything.
def youtube_stream_selector(max_height: int = 1080) -> str:
    h = int(max_height)
    return (
        f"best[vcodec^=avc1][acodec^=mp4a][height<={h}]"
        f"/bestvideo[vcodec^=avc1][height<={h}]+bestaudio[acodec^=mp4a]"
        f"/best[height<={h}]/best"
    )

# DOWNLOAD selector (Track A): yt-dlp merges split streams itself via FFmpeg,
# so a merged selector is safe here and yields H.264+AAC MP4 for direct-play.
def youtube_format_selector(max_height: int = 1080) -> str:
    h = int(max_height)
    return (
        f"bestvideo[vcodec^=avc1][height<={h}]+bestaudio[acodec^=mp4a]"
        f"/bestvideo[vcodec^=avc][height<={h}]+bestaudio[acodec^=mp4a]"
        f"/best[ext=mp4][height<={h}]"
        f"/best[height<={h}]"
    )
