"""Pydantic models for Channel Builder drafts and jobs."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class OrderingMode(str, Enum):
    AS_ADDED = "as_added"
    CHRONOLOGICAL = "chronological"
    SHUFFLE = "shuffle"


class LinkStatus(str, Enum):
    PENDING = "pending"
    RESOLVING = "resolving"
    OK = "ok"
    ERROR = "error"


class PaddingMode(str, Enum):
    NONE = "none"
    BETWEEN_ITEMS = "between_items"
    DURATION = "duration"


class LinkItem(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    url: str
    status: LinkStatus = LinkStatus.PENDING
    source: Optional[str] = None
    title: Optional[str] = None
    duration: Optional[int] = None
    upload_date: Optional[str] = None
    thumbnail: Optional[str] = None
    stream_id: Optional[str] = None
    error: Optional[str] = None
    expanded_from: Optional[str] = None


class FillerAttachment(BaseModel):
    filler_id: str
    padding_mode: PaddingMode = PaddingMode.BETWEEN_ITEMS
    break_duration_seconds: int = 120


class ChannelInfo(BaseModel):
    number: str = ""
    name: str = ""
    group: Optional[str] = "Custom"
    description: Optional[str] = None
    playout_mode: Literal["continuous", "on_demand"] = "continuous"
    primary_collection: Optional[str] = None
    epg_sync_class: Optional[Literal["A", "B", "C"]] = None


class BuilderDraft(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    selected_source: Optional[str] = None
    links: list[LinkItem] = Field(default_factory=list)
    ordering: OrderingMode = OrderingMode.AS_ADDED
    channel: ChannelInfo = Field(default_factory=ChannelInfo)
    filler_attachments: list[FillerAttachment] = Field(default_factory=list)
    pbs_filter_full_episodes: bool = True
    pbs_min_episode_seconds: int = 300
    pbs_exclude_passport_drm: bool = True
    built: bool = False
    built_channel_number: Optional[str] = None


class BuilderJob(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    draft_id: str
    job_type: Literal["resolve", "build", "auth_login"] = "resolve"
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    total: int = 0
    completed: int = 0
    errors: list[str] = Field(default_factory=list)
    result: Optional[dict[str, Any]] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class FillerLink(BaseModel):
    url: str
    title: Optional[str] = None
    clip_type: Literal["bumper", "commercial", "filler"] = "filler"
    duration: Optional[int] = None
    source: Optional[str] = None
    stream_id: Optional[str] = None


class FillerCollection(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    name: str
    description: Optional[str] = None
    links: list[FillerLink] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DraftCreateRequest(BaseModel):
    channel_number: Optional[str] = None
    channel_name: Optional[str] = None


class DraftPatchRequest(BaseModel):
    selected_source: Optional[str] = None
    ordering: Optional[OrderingMode] = None
    channel: Optional[ChannelInfo] = None
    filler_attachments: Optional[list[FillerAttachment]] = None
    pbs_filter_full_episodes: Optional[bool] = None
    pbs_min_episode_seconds: Optional[int] = Field(default=None, ge=0, le=7200)
    pbs_exclude_passport_drm: Optional[bool] = None


class LinksBatchRequest(BaseModel):
    urls: list[str] = Field(..., min_length=1, max_length=500)


class FillerCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    urls: list[str] = Field(default_factory=list)
    clip_type: Literal["bumper", "commercial", "filler"] = "filler"


class AuthCheckRequest(BaseModel):
    urls: list[str] = Field(default_factory=list)


class AuthScopeStatus(BaseModel):
    scope: str
    configured: bool
    method: Optional[str] = None


class AuthCheckResponse(BaseModel):
    scopes: list[AuthScopeStatus]
    requires_archive: bool = False
    requires_youtube: bool = False
    requires_pbs: bool = False
    requires_plex: bool = False


class BuilderSourceResponse(BaseModel):
    id: str
    label: str
    status: str
    hosts: list[str]
    auth_methods: list[str]
    url_placeholder: str
    supports_expand: bool
    playout_ready: bool
    docs_anchor: Optional[str] = None


class ArchiveLoginRequest(BaseModel):
    username: str
    password: str


class PlaywrightLoginRequest(BaseModel):
    email: str
    password: str


class PlexLoginRequest(BaseModel):
    base_url: str
    token: str


class CommunityCookieLoginRequest(BaseModel):
    source_id: str


class BuildResult(BaseModel):
    channel_number: str
    unified_path: str
    inventory_path: str
    schedule_path: str
    stream_count: int
    warnings: list[str] = Field(default_factory=list)
