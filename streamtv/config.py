"""Configuration management for StreamTV"""

from pathlib import Path
from typing import Optional, Dict, Type, List
import os
import logging
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings
from pydantic import Field
import yaml

logger = logging.getLogger(__name__)


class ServerConfig(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8410
    base_url: str = "http://localhost:8410"


class DatabaseConfig(BaseSettings):
    url: str = "sqlite:///./streamtv.db"


class StreamingConfig(BaseSettings):
    buffer_size: int = 8192
    chunk_size: int = 1024
    timeout: int = 30
    max_retries: int = 3


class YouTubeConfig(BaseSettings):
    enabled: bool = True
    quality: str = "best"
    extract_audio: bool = False
    cookies_file: Optional[str] = None  # Path to cookies.txt file for authentication
    cookies_json_file: Optional[str] = None  # Browser JSON export; synced to cookies_file
    use_authentication: bool = False  # Enable YouTube authentication
    api_key: Optional[str] = None  # Can be set via STREAMTV_YOUTUBE_API_KEY env var
    oauth_client_id: Optional[str] = None  # Can be set via STREAMTV_YOUTUBE_OAUTH_CLIENT_ID env var
    oauth_client_secret: Optional[str] = None  # Can be set via STREAMTV_YOUTUBE_OAUTH_CLIENT_SECRET env var
    oauth_refresh_token: Optional[str] = None  # Can be set via STREAMTV_YOUTUBE_OAUTH_REFRESH_TOKEN env var
    request_delay: float = 5.0
    rate_limit_backoff_min: float = 300.0
    rate_limit_backoff_max: float = 3600.0
    rate_limit_backoff_multiplier: float = 2.0
    enable_request_queue: bool = True
    js_runtime: Optional[str] = None
    remote_components: Optional[str] = None

    class Config:
        env_prefix = "STREAMTV_YOUTUBE_"
        case_sensitive = False


class ArchiveOrgConfig(BaseSettings):
    enabled: bool = True
    preferred_format: str = "h264"
    mp4_only: bool = True  # Skip non-MP4 archive.org files (AVI/MKV demux errors)
    username: Optional[str] = None
    password: Optional[str] = None
    use_authentication: bool = False
    cookies_file: Optional[str] = None  # Path to cookies.txt file for authentication (preferred)
    s3_access_key: Optional[str] = None
    s3_secret_key: Optional[str] = None


class PBSConfig(BaseSettings):
    enabled: bool = True
    username: Optional[str] = None
    password: Optional[str] = None
    use_authentication: bool = False
    cookies_file: Optional[str] = None  # Path to cookies.txt file for authentication (preferred)
    use_headless_browser: bool = True  # Use headless browser for JavaScript-rendered pages (requires Playwright)
    show_max_videos: int = 5000  # PBS show expand cap (Nature and similar catalogs)
    cookies_import_path: Optional[str] = None  # default ~/Downloads/cookies.txt for Builder import
    # Common PBS stations - can be extended
    stations: Optional[Dict[str, str]] = None


class SecurityConfig(BaseSettings):
    api_key_required: bool = True  # Enable by default for security
    access_token: Optional[str] = None  # Can be set via STREAMTV_SECURITY_ACCESS_TOKEN env var
    allow_local_path_import: bool = False  # POST /api/import/channels/yaml/path (operator-only)

    class Config:
        env_prefix = "STREAMTV_SECURITY_"
        case_sensitive = False


class LoggingConfig(BaseSettings):
    level: str = "INFO"
    file: Optional[str] = "streamtv.log"


class HDHomeRunConfig(BaseSettings):
    enabled: bool = True
    device_id: str = "FFFFFFFF"
    friendly_name: str = "StreamTV HDHomeRun"
    tuner_count: int = 2
    enable_ssdp: bool = True  # Enable SSDP discovery (requires port 1900)


class FFmpegConfig(BaseSettings):
    ffmpeg_path: str = "/usr/local/bin/ffmpeg"
    ffprobe_path: str = "/usr/local/bin/ffprobe"
    log_level: str = "info"
    threads: int = 0
    hwaccel: Optional[str] = None
    hwaccel_device: Optional[str] = None
    extra_flags: Optional[str] = None
    # Per-source overrides (optional)
    youtube_hwaccel: Optional[str] = None
    archive_org_hwaccel: Optional[str] = None
    pbs_hwaccel: Optional[str] = None
    plex_hwaccel: Optional[str] = None
    youtube_video_encoder: Optional[str] = None
    archive_org_video_encoder: Optional[str] = None
    pbs_video_encoder: Optional[str] = None
    plex_video_encoder: Optional[str] = None


class PlayoutConfig(BaseSettings):
    build_days: int = 1  # Number of days ahead to build playout schedules (default: 1 day = 24 hours)
    archive_tune_seek: bool = False  # Archive.org tune-in intra-episode seek (-ss); default off
    youtube_only_boot_defer: List[str] = Field(
        default_factory=lambda: ["1988", "1991", "1994"]
    )
    hybrid_boot_defer: List[str] = Field(default_factory=lambda: ["1984"])
    # EPG sync taxonomy — see docs/guides/EPG_SYNC_CLASSES.md
    epg_sync_classes: Dict[str, Dict[str, object]] = Field(
        default_factory=lambda: {
            "A": {
                "playout_authoritative_epg": True,
                "epg_pad_seconds": 5,
                "prefetch_at_boundary": 1,
                "reload_on_item_boundary": True,
            },
            "B": {"archive_tune_seek": True},
            "C": {},
        }
    )
    epg_sync_class_fallback: Dict[str, str] = Field(default_factory=dict)

    class Config:
        env_prefix = "STREAMTV_PLAYOUT_"
        case_sensitive = False


class PlexConfig(BaseSettings):
    enabled: bool = False  # Enable Plex API integration for EPG
    base_url: Optional[str] = None  # Plex Media Server URL (e.g., "http://192.0.2.1:32400")
    token: Optional[str] = Field(
        default=None,
        description="Plex authentication token. Can be set via STREAMTV_PLEX_TOKEN environment variable for security."
    )
    use_for_epg: bool = False  # Use Plex API for EPG metadata enhancement
    auto_reload_guide: bool = True  # POST livetv/dvrs/{id}/reloadGuide when playout lags wall-clock
    reload_on_item_boundary: bool = True  # Class-A item advance → reloadGuide (per-channel cooldown)
    item_boundary_cooldown_s: int = 90
    global_reload_cooldown_s: int = 900  # Tune-connect lag reload cooldown
    dvr_id: Optional[str] = None  # Plex DVR key; auto-discovered when unset
    logs_path: Optional[str] = None  # Path to Plex Media Server logs directory (auto-detected if not set)
    
    class Config:
        env_prefix = "STREAMTV_PLEX_"
        case_sensitive = False


class MetadataConfig(BaseSettings):
    enabled: bool = False  # Enable metadata enrichment
    auto_enrich: bool = False  # Automatically enrich on import
    tvdb_api_key: Optional[str] = None  # Can be set via STREAMTV_METADATA_TVDB_API_KEY env var
    tvdb_pin: Optional[str] = None
    tvdb_read_token: Optional[str] = None  # Can be set via STREAMTV_METADATA_TVDB_READ_TOKEN env var
    tmdb_api_key: Optional[str] = None  # Can be set via STREAMTV_METADATA_TMDB_API_KEY env var
    enable_tvdb: bool = True  # Use TVDB (primary for TV)
    enable_tvmaze: bool = True  # Use TVMaze (fallback, free)
    enable_tmdb: bool = True  # Use TMDB (for movies)
    cache_duration: int = 86400  # Cache duration in seconds (24 hours)
    
    class Config:
        env_prefix = "STREAMTV_METADATA_"
        case_sensitive = False


class AutoHealerConfig(BaseSettings):
    enabled: bool = False  # Enable auto-healing system
    enable_ai: bool = True  # Use Ollama AI for analysis
    ollama_url: str = "http://localhost:11434"  # Ollama API URL
    ollama_model: str = "llama3.2:latest"  # Ollama model to use
    check_interval: int = 30  # Minutes between health checks
    apply_fixes: bool = False  # Auto-apply fixes (False = dry-run only)
    max_fix_attempts: int = 3  # Max attempts to fix same error


class DownloadStrategyConfig(BaseSettings):
    """Controls how and when content is downloaded to local cache."""
    enabled: bool = False
    format_preference: str = "mp4"
    max_concurrent_downloads: int = 2
    youtube_rate_limit_seconds: float = 30.0
    youtube_rate_limit_cooldown_seconds: float = 3600.0
    scheduled_downloads: list = []

    class Config:
        env_prefix = "STREAMTV_DOWNLOAD_"
        case_sensitive = False


class CacheConfig(BaseSettings):
    """Local media cache configuration."""
    enabled: bool = False
    # direct — CDN stream only; no background downloads (Tunarr-style, lowest disk use)
    # buffer — direct stream + optional read-ahead prefetch into capped cache (RAM disk)
    # full   — download-first; wait for cache/buffer before playout (legacy default)
    playback_mode: str = "full"
    cache_directory: str = "data/cache"
    max_size_gb: float = 10.0
    default_ttl_hours: int = 72
    queue_poll_interval_seconds: int = 15
    download_timeout_seconds: int = 3600
    prefetch_count: int = 3
    # Start playback from a partial download once this many MB are on disk (.part file).
    stream_buffer_mb: float = 32.0
    # Minimum seconds of media buffered before FFmpeg starts (buffer/full modes).
    stream_buffer_seconds: float = 30.0
    # Tune-only ring buffer: write at most this many MB per item (not a full download).
    stream_buffer_max_mb: float = 48.0
    # Max seconds to block a live tuner before starting CDN (Plex tune timeout).
    # Keep low — Plex aborts after ~few seconds of keepalive-only MPEG-TS.
    tune_buffer_max_wait_seconds: float = 5.0
    # Buffer mode: only use RAM when Plex/tuner is connected (Tunarr-style).
    tune_only_buffer: bool = True
    # Stream from archive.org CDN while background download fills cache (no full file required).
    archive_org_stream_while_caching: bool = True
    # Buffer mode only: download YouTube VOD to RAM/disk cache instead of CDN direct
    # (eliminates googlevideo 403 mid-song pauses). Archive.org stays CDN-first.
    youtube_full_cache: bool = False
    # Max seconds to wait for a YouTube cache file before CDN fallback (playout/tune).
    youtube_cache_wait_seconds: float = 120.0
    # Tunarr-style RAM disk: delete cache file when an item finishes playing.
    evict_after_play: bool = True
    # Drop READY cache entries not in the upcoming prefetch window (long-form friendly).
    evict_off_schedule: bool = True
    download_strategy: DownloadStrategyConfig = DownloadStrategyConfig()

    class Config:
        env_prefix = "STREAMTV_CACHE_"
        case_sensitive = False


class TunerEndpointConfig(BaseSettings):
    """One upstream HDHomeRun-compatible tuner to normalize for Plex."""

    name: str = "tunarr"
    url: str = "http://192.0.2.1:8000"
    force_device_id: Optional[str] = None
    force_base_url: Optional[str] = None
    xmltv_url: Optional[str] = None
    role: str = "proxy"


class TunerManagerConfig(BaseSettings):
    """Proxy Tunarr (and similar) so Plex GUI Add Device accepts a hex DeviceID."""

    enabled: bool = True
    listen_path_prefix: str = "/tuners"
    merged_guide: bool = True
    tuners: list = []

    class Config:
        env_prefix = "STREAMTV_TUNER_MANAGER_"
        case_sensitive = False


def _load_secrets_env() -> None:
    """Load secrets from an out-of-repo env file into the process environment.

    Looked up at ``$STREAMTV_SECRETS_FILE`` or ``~/.streamtv/secrets.env``.
    Values already present in the environment are never overwritten, so
    launchd/shell-provided variables keep precedence.
    """
    candidate = os.getenv("STREAMTV_SECRETS_FILE") or str(
        Path.home() / ".streamtv" / "secrets.env"
    )
    path = Path(candidate)
    if not path.is_file():
        return
    try:
        for raw in path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("'\"")
            if key and key not in os.environ:
                os.environ[key] = value
    except OSError as exc:
        logger.warning(f"Could not read secrets file {path}: {exc}")


class Config:
    def __init__(self, config_path: Optional[Path] = None):
        _load_secrets_env()

        if config_path is None:
            config_path = Path("config.yaml")
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
        else:
            config_data = {}
        
        self._config_path = config_path
        self._config_data = config_data
        self._section_classes: Dict[str, Type[BaseSettings]] = {
            "server": ServerConfig,
            "database": DatabaseConfig,
            "streaming": StreamingConfig,
            "youtube": YouTubeConfig,
            "archive_org": ArchiveOrgConfig,
            "pbs": PBSConfig,
            "security": SecurityConfig,
            "logging": LoggingConfig,
            "hdhomerun": HDHomeRunConfig,
            "ffmpeg": FFmpegConfig,
            "playout": PlayoutConfig,
            "plex": PlexConfig,
            "metadata": MetadataConfig,
            "auto_healer": AutoHealerConfig,
            "cache": CacheConfig,
            "tuner_manager": TunerManagerConfig,
        }
        
        # Store OAuth state temporarily (in production, use proper session storage)
        self._oauth_states = {}
        
        # Initialize config sections - BaseSettings will automatically read from environment variables
        # Environment variables take precedence over YAML values
        self.server = ServerConfig(**config_data.get("server", {}))
        self.database = DatabaseConfig(**config_data.get("database", {}))
        self.streaming = StreamingConfig(**config_data.get("streaming", {}))
        self.youtube = YouTubeConfig(**config_data.get("youtube", {}))
        self.archive_org = ArchiveOrgConfig(**config_data.get("archive_org", {}))
        self.pbs = PBSConfig(**config_data.get("pbs", {}))
        self.security = SecurityConfig(**config_data.get("security", {}))
        self.logging = LoggingConfig(**config_data.get("logging", {}))
        self.hdhomerun = HDHomeRunConfig(**config_data.get("hdhomerun", {}))
        self.ffmpeg = FFmpegConfig(**config_data.get("ffmpeg", {}))
        self.playout = PlayoutConfig(**config_data.get("playout", {}))
        self.plex = PlexConfig(**config_data.get("plex", {}))
        self.metadata = MetadataConfig(**config_data.get("metadata", {}))
        self.auto_healer = AutoHealerConfig(**config_data.get("auto_healer", {}))

        cache_data = dict(config_data.get("cache", {}) or {})
        ds_data = cache_data.pop("download_strategy", {}) or {}
        self.cache = CacheConfig(
            download_strategy=DownloadStrategyConfig(**ds_data),
            **cache_data,
        )

        tm_data = dict(config_data.get("tuner_manager", {}) or {})
        raw_tuners = tm_data.pop("tuners", None)
        if raw_tuners is None:
            # Sensible default: proxy local Tunarr for Plex GUI add
            raw_tuners = [
                {
                    "name": "tunarr",
                    "url": "http://192.0.2.1:8000",
                    "xmltv_url": "http://192.0.2.1:8000/api/xmltv.xml",
                    "role": "proxy",
                }
            ]
        parsed_tuners = [
            TunerEndpointConfig(**t) if isinstance(t, dict) else t
            for t in (raw_tuners or [])
        ]
        self.tuner_manager = TunerManagerConfig(
            tuners=parsed_tuners,
            **tm_data,
        )
        if os.getenv("STREAMTV_TUNER_MANAGER_ENABLED") is not None:
            self.tuner_manager.enabled = (
                os.getenv("STREAMTV_TUNER_MANAGER_ENABLED", "").lower()
                in ("1", "true", "yes", "on")
            )

        # Security: Override sensitive values from environment variables if set
        # This ensures env vars take precedence even if they're in YAML
        if os.getenv("STREAMTV_SECURITY_ACCESS_TOKEN"):
            self.security.access_token = os.getenv("STREAMTV_SECURITY_ACCESS_TOKEN")
        if os.getenv("STREAMTV_PLEX_TOKEN"):
            self.plex.token = os.getenv("STREAMTV_PLEX_TOKEN")
        if os.getenv("STREAMTV_YOUTUBE_API_KEY"):
            self.youtube.api_key = os.getenv("STREAMTV_YOUTUBE_API_KEY")
        if os.getenv("STREAMTV_YOUTUBE_OAUTH_CLIENT_ID"):
            self.youtube.oauth_client_id = os.getenv("STREAMTV_YOUTUBE_OAUTH_CLIENT_ID")
        if os.getenv("STREAMTV_YOUTUBE_OAUTH_CLIENT_SECRET"):
            self.youtube.oauth_client_secret = os.getenv("STREAMTV_YOUTUBE_OAUTH_CLIENT_SECRET")
        if os.getenv("STREAMTV_YOUTUBE_OAUTH_REFRESH_TOKEN"):
            self.youtube.oauth_refresh_token = os.getenv("STREAMTV_YOUTUBE_OAUTH_REFRESH_TOKEN")
        if os.getenv("STREAMTV_METADATA_TVDB_API_KEY"):
            self.metadata.tvdb_api_key = os.getenv("STREAMTV_METADATA_TVDB_API_KEY")
        if os.getenv("STREAMTV_METADATA_TVDB_READ_TOKEN"):
            self.metadata.tvdb_read_token = os.getenv("STREAMTV_METADATA_TVDB_READ_TOKEN")
        if os.getenv("STREAMTV_METADATA_TMDB_API_KEY"):
            self.metadata.tmdb_api_key = os.getenv("STREAMTV_METADATA_TMDB_API_KEY")
        if os.getenv("STREAMTV_ARCHIVE_ORG_USERNAME"):
            self.archive_org.username = os.getenv("STREAMTV_ARCHIVE_ORG_USERNAME")
        if os.getenv("STREAMTV_ARCHIVE_ORG_PASSWORD"):
            self.archive_org.password = os.getenv("STREAMTV_ARCHIVE_ORG_PASSWORD")
        if os.getenv("STREAMTV_ARCHIVE_ORG_S3_ACCESS_KEY"):
            self.archive_org.s3_access_key = os.getenv("STREAMTV_ARCHIVE_ORG_S3_ACCESS_KEY")
        if os.getenv("STREAMTV_ARCHIVE_ORG_S3_SECRET_KEY"):
            self.archive_org.s3_secret_key = os.getenv("STREAMTV_ARCHIVE_ORG_S3_SECRET_KEY")
        if os.getenv("STREAMTV_METADATA_TVDB_PIN"):
            self.metadata.tvdb_pin = os.getenv("STREAMTV_METADATA_TVDB_PIN")
        if os.getenv("STREAMTV_PBS_USERNAME"):
            self.pbs.username = os.getenv("STREAMTV_PBS_USERNAME")
        if os.getenv("STREAMTV_PBS_PASSWORD"):
            self.pbs.password = os.getenv("STREAMTV_PBS_PASSWORD")
        
        # Security: Warn if secrets are found in config file
        self._warn_secrets_in_config(config_data)

    def _warn_secrets_in_config(self, config_data: Dict) -> None:
        """Warn if sensitive values are found in config file instead of environment variables."""
        secrets_found = []
        
        # Check for secrets in config file
        security_data = config_data.get("security", {})
        if security_data.get("access_token") and not os.getenv("STREAMTV_SECURITY_ACCESS_TOKEN"):
            secrets_found.append("security.access_token")
        
        plex_data = config_data.get("plex", {})
        if plex_data.get("token") and not os.getenv("STREAMTV_PLEX_TOKEN"):
            secrets_found.append("plex.token")
        
        youtube_data = config_data.get("youtube", {})
        if youtube_data.get("api_key") and not os.getenv("STREAMTV_YOUTUBE_API_KEY"):
            secrets_found.append("youtube.api_key")
        if youtube_data.get("oauth_client_secret") and not os.getenv("STREAMTV_YOUTUBE_OAUTH_CLIENT_SECRET"):
            secrets_found.append("youtube.oauth_client_secret")
        if youtube_data.get("oauth_refresh_token") and not os.getenv("STREAMTV_YOUTUBE_OAUTH_REFRESH_TOKEN"):
            secrets_found.append("youtube.oauth_refresh_token")
        
        archive_org_data = config_data.get("archive_org", {})
        if archive_org_data.get("password") and not os.getenv("STREAMTV_ARCHIVE_ORG_PASSWORD"):
            secrets_found.append("archive_org.password")
        
        pbs_data = config_data.get("pbs", {})
        if pbs_data.get("password") and not os.getenv("STREAMTV_PBS_PASSWORD"):
            secrets_found.append("pbs.password")
        
        metadata_data = config_data.get("metadata", {})
        if metadata_data.get("tvdb_api_key") and not os.getenv("STREAMTV_METADATA_TVDB_API_KEY"):
            secrets_found.append("metadata.tvdb_api_key")
        if metadata_data.get("tvdb_read_token") and not os.getenv("STREAMTV_METADATA_TVDB_READ_TOKEN"):
            secrets_found.append("metadata.tvdb_read_token")
        if metadata_data.get("tmdb_api_key") and not os.getenv("STREAMTV_METADATA_TMDB_API_KEY"):
            secrets_found.append("metadata.tmdb_api_key")
        
        if secrets_found:
            logger.warning(
                "SECURITY WARNING: Sensitive values found in config file. "
                "For better security, use environment variables instead:"
            )
            for secret in secrets_found:
                env_var = secret.upper().replace(".", "_").replace("-", "_")
                logger.warning(f"  - {secret} -> Set STREAMTV_{env_var} environment variable")
            logger.warning(
                "See .env.example for a template of all environment variables."
            )
    
    def update_section(self, section: str, values: Dict) -> None:
        """Update a config section, persist to disk, and refresh in-memory settings."""
        if section not in self._section_classes:
            raise ValueError(f"Unsupported config section: {section}")
        
        section_data = self._config_data.setdefault(section, {})
        # Update with new values, but don't set None values (keep existing or remove)
        for key, value in values.items():
            if value is None:
                section_data.pop(key, None)
            else:
                section_data[key] = value
        
        with open(self._config_path, "w") as f:
            yaml.safe_dump(self._config_data, f, sort_keys=False, default_flow_style=False, allow_unicode=True)
        
        section_class = self._section_classes[section]
        setattr(self, section, section_class(**section_data))


# Global config instance (override path: STREAMTV_CONFIG=config.pilot-cache.yaml)
_config_path = Path(os.getenv("STREAMTV_CONFIG", "config.yaml"))
config = Config(_config_path)
