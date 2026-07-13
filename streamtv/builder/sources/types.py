"""Builder source registry types."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


SourceStatus = Literal["active", "coming_soon", "community"]
AuthMethod = Literal["playwright", "password", "token", "cookies", "none"]


class SourceAuthSpec(BaseModel):
    method: AuthMethod = "none"
    login_url: Optional[str] = None
    cookies_domain: Optional[str] = None


class BuilderSourceSpec(BaseModel):
    id: str
    label: str
    status: SourceStatus = "active"
    hosts: list[str] = Field(default_factory=list)
    auth_methods: list[AuthMethod] = Field(default_factory=lambda: ["none"])
    url_placeholder: str = ""
    supports_expand: bool = False
    playout_ready: bool = True
    resolver_source: str = ""
    docs_anchor: Optional[str] = None
    auth: SourceAuthSpec = Field(default_factory=SourceAuthSpec)
    module: Optional[str] = None

    def model_post_init(self, __context: object) -> None:
        if not self.resolver_source:
            object.__setattr__(self, "resolver_source", self.id.replace("community:", ""))
