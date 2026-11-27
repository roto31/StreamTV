"""Configuration for Archive.org MCP Server"""

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class ArchiveOrgConfig(BaseSettings):
    """Archive.org API configuration"""
    
    base_url: str = Field(
        default="https://archive.org",
        description="Archive.org base URL"
    )
    metadata_url: str = Field(
        default="https://archive.org/metadata",
        description="Archive.org Metadata API URL"
    )
    search_url: str = Field(
        default="https://archive.org/advancedsearch.php",
        description="Archive.org Advanced Search API URL"
    )
    username: Optional[str] = Field(
        default=None,
        description="Archive.org username for authenticated requests (optional)"
    )
    password: Optional[str] = Field(
        default=None,
        description="Archive.org password for authenticated requests (optional)"
    )
    cookies_file: Optional[str] = Field(
        default=None,
        description="Path to cookies file for authentication (optional)"
    )
    timeout: int = Field(
        default=30,
        description="HTTP request timeout in seconds"
    )
    max_retries: int = Field(
        default=3,
        description="Maximum number of retry attempts for failed requests"
    )
    
    model_config = SettingsConfigDict(env_prefix="ARCHIVE_ORG_", case_sensitive=False)


# Global config instance
config = ArchiveOrgConfig()

