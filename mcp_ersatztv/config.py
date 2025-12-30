"""Configuration for ErsatzTV MCP Server"""

import os
from pathlib import Path
from typing import Optional
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings
from pydantic import Field


class ErsatzTVConfig(BaseSettings):
    """ErsatzTV documentation configuration"""
    
    docs_path: Optional[str] = Field(
        default=None,
        description="Path to local ErsatzTV documentation (defaults to workspace docs/ and ersatztv-reference/)"
    )
    github_url: str = Field(
        default="https://github.com/ErsatzTV/ErsatzTV",
        description="ErsatzTV GitHub repository URL"
    )
    wiki_url: str = Field(
        default="https://ersatztv.org/docs/",
        description="ErsatzTV wiki documentation URL"
    )
    
    class Config:
        env_prefix = "ERSATZTV_"
        case_sensitive = False


# Global config instance
config = ErsatzTVConfig()

