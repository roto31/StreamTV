"""FFmpeg command builder from profiles"""

import logging
from typing import List, Optional, Dict, Any
from pathlib import Path

from ..config import config
from ..database.models import (
    FFmpegProfile, Watermark, Resolution,
    HardwareAccelerationKind, VideoFormat, AudioFormat
)

logger = logging.getLogger(__name__)

# One-pass loudnorm for live MPEG-TS + peak limiter (anti-spike / anti-oversat).
# TP=-2.0 gives more true-peak headroom than -1.5; alimiter ~-1 dBFS hard ceiling.
LOUDNORM_AF_FILTER = (
    "loudnorm=I=-16:TP=-2.0:LRA=11:linear=true,"
    "alimiter=limit=0.89:attack=5:release=50"
)


def detach_ffmpeg_profile(db, profile: FFmpegProfile) -> FFmpegProfile:
    """Expunge profile (+ resolution) for use after the Session is closed.

    Continuous playout closes the channel DB session after bind; without an
    eager load, build_ffmpeg_command hits DetachedInstanceError on
    ``profile.resolution`` and falls back to legacy (no LoudNorm).
    """
    from sqlalchemy.orm import joinedload

    # Re-fetch with joinedload when possible so resolution is present.
    pid = getattr(profile, "id", None)
    if pid is not None:
        loaded = (
            db.query(FFmpegProfile)
            .options(joinedload(FFmpegProfile.resolution))
            .filter(FFmpegProfile.id == pid)
            .first()
        )
        if loaded is not None:
            profile = loaded

    # Touch attributes used by build_ffmpeg_command while still bound.
    _ = (
        profile.name,
        profile.thread_count,
        profile.hardware_acceleration,
        profile.vaapi_driver,
        profile.vaapi_device,
        profile.qsv_extra_hardware_frames,
        profile.scaling_behavior,
        profile.video_format,
        profile.video_profile,
        profile.video_preset,
        profile.allow_b_frames,
        profile.bit_depth,
        profile.video_bitrate,
        profile.video_buffer_size,
        profile.audio_format,
        profile.audio_bitrate,
        profile.normalize_loudness_mode,
        profile.audio_channels,
        profile.audio_sample_rate,
        profile.normalize_framerate,
        profile.deinterlace_video,
    )
    res = profile.resolution
    if res is not None:
        _ = (res.width, res.height, res.name)
        db.expunge(res)
    db.expunge(profile)
    return profile


def load_ffmpeg_profile_for_playout(db, profile_id: int) -> Optional[FFmpegProfile]:
    """Load and detach an FFmpeg profile for continuous / HDHomeRun playout."""
    from sqlalchemy.orm import joinedload

    profile = (
        db.query(FFmpegProfile)
        .options(joinedload(FFmpegProfile.resolution))
        .filter(FFmpegProfile.id == profile_id)
        .first()
    )
    if profile is None:
        return None
    return detach_ffmpeg_profile(db, profile)


def build_ffmpeg_command(
    profile: FFmpegProfile,
    input_url: str,
    watermark: Optional[Watermark] = None,
    subtitle_path: Optional[str] = None,
    codec_info: Optional[Dict[str, Any]] = None
) -> List[str]:
    """
    Build FFmpeg command from profile with hardware acceleration, watermarks, and subtitles.
    
    Args:
        profile: FFmpeg profile to use
        input_url: Input stream URL
        watermark: Optional watermark to overlay
        subtitle_path: Optional path to subtitle file
        codec_info: Optional codec information from probe
    
    Returns:
        List of FFmpeg command arguments
    """
    cmd = [config.ffmpeg.ffmpeg_path]
    
    # Global options
    log_level = config.ffmpeg.log_level or "info"
    cmd.extend(["-loglevel", log_level])
    
    # Hardware acceleration (must come before input)
    if profile.hardware_acceleration != HardwareAccelerationKind.NONE:
        hwaccel = profile.hardware_acceleration.value
        cmd.extend(["-hwaccel", hwaccel])
        
        # Platform-specific hardware acceleration options
        if profile.hardware_acceleration == HardwareAccelerationKind.VAAPI:
            if profile.vaapi_device:
                cmd.extend(["-hwaccel_device", profile.vaapi_device])
            if profile.vaapi_driver:
                # VAAPI driver is typically set via environment, but we can note it
                logger.debug(f"Using VAAPI driver: {profile.vaapi_driver}")
        elif profile.hardware_acceleration == HardwareAccelerationKind.QSV:
            if profile.qsv_extra_hardware_frames:
                cmd.extend(["-qsv_device", str(profile.qsv_extra_hardware_frames)])
        elif profile.hardware_acceleration == HardwareAccelerationKind.NVENC:
            # NVENC uses CUDA
            cmd.extend(["-hwaccel", "cuda"])
            if config.ffmpeg.hwaccel_device:
                cmd.extend(["-hwaccel_device", config.ffmpeg.hwaccel_device])
    
    # Input options for HTTP streams
    if input_url.startswith("http"):
        # Archive.org VOD must terminate at EOF (same as YouTube) so playout advances.
        http_opts = [
            "-timeout", "10000000",  # 10 second timeout
            "-user_agent", "Mozilla/5.0 (compatible; StreamTV/1.0)",
            "-reconnect", "1",
        ]
        if "archive.org" not in input_url.lower():
            http_opts.extend(["-reconnect_at_eof", "1"])
        http_opts.extend([
            "-reconnect_streamed", "1",
            "-reconnect_delay_max", "2",
        ])
        cmd.extend(http_opts)
    
    # Input flags
    cmd.extend([
        "-fflags", "+genpts+discardcorrupt+fastseek",
        "-flags", "+low_delay",
        "-strict", "experimental",
        "-probesize", "1000000",
        "-analyzeduration", "2000000",
        "-i", input_url,
    ])
    
    # Threads
    if profile.thread_count > 0:
        cmd.extend(["-threads", str(profile.thread_count)])
    elif config.ffmpeg.threads > 0:
        cmd.extend(["-threads", str(config.ffmpeg.threads)])
    
    # Add watermark image as second input if needed
    watermark_input_added = False
    if watermark and watermark.image:
        # Use absolute path relative to project root
        watermark_path = Path(__file__).parent.parent.parent / "data" / "watermarks" / watermark.image
        if watermark_path.exists():
            cmd.extend(["-i", str(watermark_path)])
            watermark_input_added = True
    
    # Video filters (scaling, watermark, subtitles)
    video_filters = []
    
    # Resolution scaling
    resolution = profile.resolution
    if resolution:
        scale_filter = _build_scale_filter(resolution, profile.scaling_behavior)
        if scale_filter:
            video_filters.append(scale_filter)
    
    # Watermark overlay (requires second input)
    if watermark_input_added:
        watermark_filter = _build_watermark_filter(watermark, resolution)
        if watermark_filter:
            video_filters.append(watermark_filter)
    
    # Subtitle overlay
    if subtitle_path and Path(subtitle_path).exists():
        subtitle_filter = f"subtitles={subtitle_path}"
        video_filters.append(subtitle_filter)
    
    # Apply video filters
    if video_filters:
        cmd.extend(["-vf", ",".join(video_filters)])
    
    # Video codec
    if profile.video_format == VideoFormat.COPY:
        cmd.extend(["-c:v", "copy"])
    else:
        encoder = _get_video_encoder(profile)
        cmd.extend(["-c:v", encoder])
        
        # Video codec options
        if profile.video_format == VideoFormat.H264:
            if profile.video_profile:
                cmd.extend(["-profile:v", profile.video_profile])
            if profile.allow_b_frames:
                cmd.extend(["-bf", "2"])
            else:
                cmd.extend(["-bf", "0"])
        
        if profile.video_preset:
            if profile.hardware_acceleration == HardwareAccelerationKind.NVENC:
                cmd.extend(["-preset", profile.video_preset])
            elif profile.hardware_acceleration == HardwareAccelerationKind.QSV:
                cmd.extend(["-preset", profile.video_preset])
            else:
                cmd.extend(["-preset", profile.video_preset])
        
        # Bitrate
        cmd.extend(["-b:v", f"{profile.video_bitrate}k"])
        cmd.extend(["-maxrate", f"{profile.video_bitrate}k"])
        cmd.extend(["-bufsize", f"{profile.video_buffer_size}k"])
        
        # Pixel format
        if profile.bit_depth.value == "10bit":
            if profile.video_format == VideoFormat.H264:
                cmd.extend(["-pix_fmt", "yuv420p10le"])
            elif profile.video_format == VideoFormat.HEVC:
                cmd.extend(["-pix_fmt", "yuv420p10le"])
        else:
            cmd.extend(["-pix_fmt", "yuv420p"])
        
        # Deinterlace
        if profile.deinterlace_video is True:
            cmd.extend(["-deinterlace"])
        elif profile.deinterlace_video is False:
            # Explicitly disable deinterlacing
            pass
    
    # Audio codec
    if profile.audio_format == AudioFormat.COPY:
        cmd.extend(["-c:a", "copy"])
    else:
        encoder = _get_audio_encoder(profile)
        cmd.extend(["-c:a", encoder])
        
        # Audio options
        cmd.extend(["-b:a", f"{profile.audio_bitrate}k"])
        cmd.extend(["-ar", str(profile.audio_sample_rate)])
        cmd.extend(["-ac", str(profile.audio_channels)])
        
        # Normalize loudness (streaming one-pass + hard ceiling to avoid TP overs).
        # I=-16 streaming target; TP=-2.0 headroom; alimiter ~-1 dBFS catches residual spikes.
        if profile.normalize_loudness_mode.value == "loudnorm":
            cmd.extend(["-af", LOUDNORM_AF_FILTER])
    
    # Normalize framerate
    if profile.normalize_framerate:
        cmd.extend(["-r", "30"])  # Default to 30fps
    
    # Output format: MPEG-TS
    cmd.extend([
        "-f", "mpegts",
        "-muxrate", f"{profile.video_bitrate + profile.audio_bitrate}k",
        "-"
    ])
    
    return cmd


def _build_scale_filter(resolution: Resolution, scaling_behavior) -> Optional[str]:
    """Build scale filter for resolution"""
    if scaling_behavior.value == "scale_and_pad":
        return f"scale={resolution.width}:{resolution.height}:force_original_aspect_ratio=decrease,pad={resolution.width}:{resolution.height}:(ow-iw)/2:(oh-ih)/2"
    elif scaling_behavior.value == "stretch":
        return f"scale={resolution.width}:{resolution.height}"
    elif scaling_behavior.value == "crop":
        return f"scale={resolution.width}:{resolution.height}:force_original_aspect_ratio=increase,crop={resolution.width}:{resolution.height}"
    return None


def _build_watermark_filter(watermark: Watermark, resolution: Optional[Resolution]) -> Optional[str]:
    """Build watermark overlay filter (watermark is second input [1:v])"""
    # Calculate position
    x_expr = _get_watermark_x_position(watermark)
    y_expr = _get_watermark_y_position(watermark)
    
    # Calculate size
    size_expr = _get_watermark_size(watermark, resolution)
    
    # Opacity
    opacity = watermark.opacity / 100.0 if watermark.opacity else 1.0
    
    # Scale and apply opacity to watermark (second input [1:v])
    watermark_filters = [f"scale={size_expr}"]
    if opacity < 1.0:
        watermark_filters.append(f"format=yuva420p,colorchannelmixer=aa={opacity}")
    
    # Build overlay filter
    if watermark.mode.value == "intermittent" and watermark.duration_seconds > 0:
        # Intermittent mode with duration
        overlay_expr = f"overlay={x_expr}:{y_expr}:enable='between(t,0,{watermark.duration_seconds})'"
    else:
        # Permanent mode
        overlay_expr = f"overlay={x_expr}:{y_expr}"
    
    # Full filter chain: process watermark, then overlay on main video
    # [0:v] is main video, [1:v] is watermark image
    return f"[1:v]{','.join(watermark_filters)}[wm];[0:v][wm]{overlay_expr}"


def _get_watermark_x_position(watermark: Watermark) -> str:
    """Get X position expression for watermark"""
    if watermark.location.value == "top_left" or watermark.location.value == "bottom_left":
        margin = f"W*{watermark.horizontal_margin_percent/100}"
        return margin
    elif watermark.location.value == "top_right" or watermark.location.value == "bottom_right":
        return f"W-w-{watermark.horizontal_margin_percent/100}*W"
    else:  # center
        return "(W-w)/2"


def _get_watermark_y_position(watermark: Watermark) -> str:
    """Get Y position expression for watermark"""
    if watermark.location.value == "top_left" or watermark.location.value == "top_right":
        margin = f"H*{watermark.vertical_margin_percent/100}"
        return margin
    elif watermark.location.value == "bottom_left" or watermark.location.value == "bottom_right":
        return f"H-h-{watermark.vertical_margin_percent/100}*H"
    else:  # center
        return "(H-h)/2"


def _get_watermark_size(watermark: Watermark, resolution: Optional[Resolution]) -> str:
    """Get size expression for watermark"""
    if watermark.size.value == "small":
        return "iw*0.05:-1"  # 5% of input width
    elif watermark.size.value == "medium":
        return "iw*0.1:-1"  # 10% of input width
    elif watermark.size.value == "large":
        return "iw*0.2:-1"  # 20% of input width
    else:  # custom
        width_pct = watermark.width_percent / 100.0
        return f"iw*{width_pct}:-1"


def _get_video_encoder(profile: FFmpegProfile) -> str:
    """Get video encoder name based on profile"""
    if profile.video_format == VideoFormat.H264:
        if profile.hardware_acceleration == HardwareAccelerationKind.NVENC:
            return "h264_nvenc"
        elif profile.hardware_acceleration == HardwareAccelerationKind.QSV:
            return "h264_qsv"
        elif profile.hardware_acceleration == HardwareAccelerationKind.VAAPI:
            return "h264_vaapi"
        elif profile.hardware_acceleration == HardwareAccelerationKind.VIDEOTOOLBOX:
            return "h264_videotoolbox"
        elif profile.hardware_acceleration == HardwareAccelerationKind.AMF:
            return "h264_amf"
        else:
            return "libx264"
    elif profile.video_format == VideoFormat.HEVC:
        if profile.hardware_acceleration == HardwareAccelerationKind.NVENC:
            return "hevc_nvenc"
        elif profile.hardware_acceleration == HardwareAccelerationKind.QSV:
            return "hevc_qsv"
        elif profile.hardware_acceleration == HardwareAccelerationKind.VAAPI:
            return "hevc_vaapi"
        elif profile.hardware_acceleration == HardwareAccelerationKind.VIDEOTOOLBOX:
            return "hevc_videotoolbox"
        elif profile.hardware_acceleration == HardwareAccelerationKind.AMF:
            return "hevc_amf"
        else:
            return "libx265"
    elif profile.video_format == VideoFormat.MPEG2VIDEO:
        return "mpeg2video"
    elif profile.video_format == VideoFormat.AV1:
        if profile.hardware_acceleration == HardwareAccelerationKind.NVENC:
            return "av1_nvenc"
        elif profile.hardware_acceleration == HardwareAccelerationKind.QSV:
            return "av1_qsv"
        else:
            return "libaom-av1"
    else:
        return "libx264"


def _get_audio_encoder(profile: FFmpegProfile) -> str:
    """Get audio encoder name based on profile"""
    if profile.audio_format == AudioFormat.AAC:
        return "aac"
    elif profile.audio_format == AudioFormat.AC3:
        return "ac3"
    elif profile.audio_format == AudioFormat.AACLATM:
        return "aac"
    else:
        return "aac"

