"""Configuration for StreamTV MCP Server"""

from __future__ import annotations

from typing import Optional

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings  # type: ignore
from pydantic import Field


class StreamTVConfig(BaseSettings):
    """StreamTV API + MCP transport configuration (STREAMTV_* env)."""

    base_url: str = Field(
        default="http://localhost:8410",
        description="StreamTV API base URL",
    )
    api_key: Optional[str] = Field(
        default=None,
        description="StreamTV API access token (optional if api_key_required is False)",
    )
    timeout: int = Field(default=30, description="HTTP request timeout in seconds")
    max_retries: int = Field(
        default=3, description="Maximum number of retry attempts for failed requests"
    )

    # MCP transport (§7A) — CLI flags override these
    mcp_transport: str = Field(default="stdio", description="stdio | http | sse")
    mcp_host: str = Field(default="127.0.0.1")
    mcp_port: int = Field(default=8411)
    mcp_path: str = Field(default="/mcp")
    mcp_profile: str = Field(default="guided")
    mcp_auth: str = Field(
        default="none",
        description="none | bearer | oauth | dual (Access JWT + bearer)",
    )
    mcp_token: str = Field(default="", description="Bearer token (≥32 chars)")
    # OAuth / OIDC resource-server (Auth0, Cloudflare Access as IdP, custom)
    mcp_oauth_provider: str = Field(
        default="custom",
        description="auth0 | cloudflare_access | custom",
    )
    mcp_oauth_domain: str = Field(
        default="",
        description="Auth0 domain or Cloudflare Access team name",
    )
    mcp_oauth_issuer: str = Field(default="")
    mcp_oauth_audience: str = Field(default="streamtv-mcp")
    mcp_oauth_jwks_url: str = Field(default="")
    mcp_oauth_jwks_json: str = Field(default="", description="Inline JWKS JSON for tests")
    # Dual-lock: Cloudflare Access application AUD (can differ from oauth audience)
    mcp_access_audience: str = Field(
        default="",
        description="Cloudflare Access Application Audience (AUD) tag",
    )
    mcp_access_team: str = Field(
        default="",
        description="Cloudflare Access team subdomain (e.g. myteam)",
    )
    mcp_allowed_hosts: str = Field(
        default="127.0.0.1:8411,localhost:8411",
        description="Comma list for DNS-rebinding protection",
    )
    mcp_allowed_origins: str = Field(
        default="http://127.0.0.1:8411,http://localhost:8411",
        description="Comma list of allowed Origin headers",
    )

    class Config:
        env_prefix = "STREAMTV_"
        case_sensitive = False


config = StreamTVConfig()
