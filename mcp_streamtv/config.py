"""Configuration for StreamTV MCP Server"""

import os
from typing import Optional
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings
from pydantic import Field


class StreamTVConfig(BaseSettings):
    """StreamTV API configuration"""
    
    base_url: str = Field(
        default="http://localhost:8410",
        description="StreamTV API base URL"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="StreamTV API access token (optional if api_key_required is False)"
    )
    timeout: int = Field(
        default=30,
        description="HTTP request timeout in seconds"
    )
    max_retries: int = Field(
        default=3,
        description="Maximum number of retry attempts for failed requests"
    )
    
    class Config:
        env_prefix = "STREAMTV_"
        case_sensitive = False


# Global config instance
config = StreamTVConfig()

