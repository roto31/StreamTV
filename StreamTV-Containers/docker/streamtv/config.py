"""Configuration management for StreamTV"""

from pathlib import Path
from typing import Optional, Dict, Type
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings
from pydantic import Field
import yaml


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
    use_authentication: bool = False  # Enable YouTube authentication
    api_key: Optional[str] = None  # YouTube Data API v3 key (recommended for better reliability)
    oauth_client_id: Optional[str] = None  # Google OAuth client ID
    oauth_client_secret: Optional[str] = None  # Google OAuth client secret
    oauth_refresh_token: Optional[str] = None  # OAuth refresh token (stored after first auth)


class ArchiveOrgConfig(BaseSettings):
    enabled: bool = True
    preferred_format: str = "h264"
    username: Optional[str] = None
    password: Optional[str] = None
    use_authentication: bool = False
    cookies_file: Optional[str] = None  # Path to cookies.txt file for authentication (preferred)


class PBSConfig(BaseSettings):
    enabled: bool = True
    username: Optional[str] = None
    password: Optional[str] = None
    use_authentication: bool = False
    cookies_file: Optional[str] = None  # Path to cookies.txt file for authentication (preferred)
    use_headless_browser: bool = True  # Use headless browser for JavaScript-rendered pages (requires Playwright)
    # Common PBS stations - can be extended
    stations: Optional[Dict[str, str]] = None


class SecurityConfig(BaseSettings):
    api_key_required: bool = True  # Enable by default for security
    access_token: Optional[str] = None


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


class PlayoutConfig(BaseSettings):
    build_days: int = 1  # Number of days ahead to build playout schedules (default: 1 day = 24 hours)


class PlexConfig(BaseSettings):
    enabled: bool = False  # Enable Plex API integration for EPG
    base_url: Optional[str] = None  # Plex Media Server URL (e.g., "http://192.168.1.100:32400")
    token: Optional[str] = None  # Plex authentication token
    use_for_epg: bool = False  # Use Plex API for EPG metadata enhancement
    logs_path: Optional[str] = None  # Path to Plex Media Server logs directory (auto-detected if not set)


class MetadataConfig(BaseSettings):
    enabled: bool = False  # Enable metadata enrichment
    auto_enrich: bool = False  # Automatically enrich on import
    tvdb_api_key: Optional[str] = None  # TVDB API key
    tvdb_read_token: Optional[str] = None  # TVDB v4 read access token (preferred)
    tmdb_api_key: Optional[str] = None  # TMDB API key
    enable_tvdb: bool = True  # Use TVDB (primary for TV)
    enable_tvmaze: bool = True  # Use TVMaze (fallback, free)
    enable_tmdb: bool = True  # Use TMDB (for movies)
    cache_duration: int = 86400  # Cache duration in seconds (24 hours)


class AutoHealerConfig(BaseSettings):
    enabled: bool = False  # Enable auto-healing system
    enable_ai: bool = True  # Use Ollama AI for analysis
    ollama_url: str = "http://localhost:11434"  # Ollama API URL
    ollama_model: str = "llama3.2:latest"  # Ollama model to use
    check_interval: int = 30  # Minutes between health checks
    apply_fixes: bool = False  # Auto-apply fixes (False = dry-run only)
    max_fix_attempts: int = 3  # Max attempts to fix same error


class Config:
    def __init__(self, config_path: Optional[Path] = None):
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
        }
        
        # Store OAuth state temporarily (in production, use proper session storage)
        self._oauth_states = {}
        
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


# Global config instance
config = Config()
