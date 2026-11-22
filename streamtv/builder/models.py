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
    AIR_DATE = "air_date"
    SHUFFLE = "shuffle"


class EraRange(BaseModel):
    from_year: Optional[int] = Field(default=None, alias="from")
    to_year: Optional[int] = Field(default=None, alias="to")

    model_config = {"populate_by_name": True}


class ChannelTarget(BaseModel):
    channel_number: Optional[str] = None
    name: Optional[str] = None


class ChannelRequirements(BaseModel):
    """Intake requirement model (§6.2)."""

    content_type: str = "movies_and_specials"
    theme: str = ""
    theme_terms: list[str] = Field(default_factory=list)
    # Who the channel is for — drives discovery queries, template defaults, and filters.
    audience: Literal[
        "",
        "kids",
        "family",
        "teens",
        "adults",
        "general",
    ] = ""
    audience_notes: str = ""  # free-text, e.g. "preschool", "nostalgia for parents"
    networks: list[str] = Field(default_factory=list)
    stations_for_breaks: list[str] = Field(default_factory=list)
    daypart: Literal["any", "daytime", "evening", "late_night"] = "any"
    era: dict[str, int] = Field(default_factory=dict)
    sources: list[str] = Field(default_factory=lambda: ["archive", "youtube"])
    commercials: Literal["required", "preferred", "none", "dont_care"] = "preferred"
    breaks_between_programs: bool = True
    target: ChannelTarget = Field(default_factory=ChannelTarget)
    no_repeat_scope: Literal["channel", "channel_and_others", "off"] = "channel"
    no_repeat_against: list[str] = Field(default_factory=list)
    loop_length_hint_hours: Optional[float] = None
    exclude: list[str] = Field(default_factory=list)
    explain_level: Literal["beginner", "intermediate", "expert"] = "beginner"
    template: Literal[
        "kids_specials", "holiday_family", "prime_time_station_ids", "custom"
    ] = "custom"
    known_titles: list[str] = Field(default_factory=list)
    theme_month: Optional[str] = None

    def missing_fields(self) -> list[str]:
        """Fields the intake should still ask about."""
        missing: list[str] = []
        if not self.audience:
            missing.append("audience")
        if not self.theme:
            missing.append("theme")
        if not self.template or self.template == "custom":
            if not self.audience:
                missing.append("template")
        return missing

    def suggested_template(self) -> str:
        if self.template and self.template != "custom":
            return self.template
        if self.audience == "kids":
            return "kids_specials"
        if self.audience == "family":
            return "holiday_family"
        if self.audience in ("adults", "teens"):
            return "prime_time_station_ids"
        return "custom"


class LinkStatus(str, Enum):
    PENDING = "pending"
    RESOLVING = "resolving"
    OK = "ok"
    ERROR = "error"


class PaddingMode(str, Enum):
    NONE = "none"
    BETWEEN_ITEMS = "between_items"
    DURATION = "duration"


class SourceMetadata(BaseModel):
    """Verbatim archive.org / YouTube metadata (§5.9.2). All fields optional."""

    platform: Optional[str] = None
    identifier: Optional[str] = None
    id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    date: Optional[str] = None
    year: Optional[str] = None
    creator: Optional[str] = None
    uploader: Optional[str] = None
    subject: list[str] = Field(default_factory=list)
    collection: list[str] = Field(default_factory=list)
    language: Optional[str] = None
    publicdate: Optional[str] = None
    licenseurl: Optional[str] = None
    page_url: Optional[str] = None
    name: Optional[str] = None
    format: Optional[str] = None
    size: Optional[str] = None
    length: Optional[str] = None
    duration_exact: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    thumbnail_source: Optional[str] = None
    channel: Optional[str] = None
    channel_id: Optional[str] = None
    uploader_id: Optional[str] = None
    upload_date: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    chapters: list[dict[str, Any]] = Field(default_factory=list)
    view_count: Optional[int] = None
    availability: Optional[str] = None
    webpage_url: Optional[str] = None


class BreakPlan(BaseModel):
    """Break / station-ID rotation (§5.4)."""

    enabled: bool = False
    groups: list[str] = Field(default_factory=list)
    rotation: Literal["interleave_wrap", "parity_alternate"] = "interleave_wrap"
    long_reel_seconds: int = 1200
    station_id_after_each_gap: bool = False


class LinkItem(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    url: str
    status: LinkStatus = LinkStatus.PENDING
    source: Optional[str] = None
    title: Optional[str] = None
    duration: Optional[int] = None
    upload_date: Optional[str] = None
    air_date: Optional[str] = None
    air_date_quality: Literal[
        "exact", "month", "year", "placeholder", "unknown"
    ] = "unknown"
    thumbnail: Optional[str] = None
    stream_id: Optional[str] = None
    error: Optional[str] = None
    expanded_from: Optional[str] = None
    existing_id: Optional[str] = None
    # Channel Creator v2 (§4.1)
    role: Literal["program", "marathon", "break", "station_id"] = "program"
    station_group: Optional[str] = None
    network: Optional[str] = None
    commercials: Literal[
        "yes", "label-only", "inferred", "unverified", "no"
    ] = "unverified"
    commercials_evidence: Optional[str] = None
    tier: Optional[int] = None
    contains: list[str] = Field(default_factory=list)
    canonical_title: Optional[str] = None
    uploader: Optional[str] = None
    page_url: Optional[str] = None
    notes: Optional[str] = None
    duration_exact: Optional[float] = None
    source_metadata: Optional[SourceMetadata] = None
    thumbnail_local: Optional[str] = None
    categories: list[str] = Field(default_factory=list)
    playable: Optional[bool] = None
    checked_at: Optional[str] = None


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
    # Post-build TVDB/TVMaze/TMDB enrichment (see streamtv.builder.enrichment)
    enrich_metadata: bool = True
    enrichment_type: Literal["series", "movie"] = "series"
    # Series providers: free TVMaze, keyed TVDB, or both (merge / longest plot)
    enrichment_series_provider: Literal["tvmaze", "tvdb", "both"] = "tvmaze"
    enrichment_series_name: Optional[str] = None
    enrichment_year: Optional[int] = None


class ExcludedItem(BaseModel):
    url: Optional[str] = None
    title: Optional[str] = None
    reason: str = ""


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
    built: bool = False
    built_channel_number: Optional[str] = None
    requirements: ChannelRequirements = Field(default_factory=ChannelRequirements)
    template: Literal[
        "kids_specials", "holiday_family", "prime_time_station_ids", "custom"
    ] = "custom"
    # §5.9 guide enrichment (distinct from ChannelInfo.enrich_metadata = TVDB/TVMaze)
    enrich_metadata: bool = True
    guide_title_style: Literal["clean", "slot"] = "clean"
    channel_number: str = ""
    channel_name: str = ""
    slug: str = ""
    collection_prefix: str = ""
    group: str = "Holiday"
    break_plan: BreakPlan = Field(default_factory=BreakPlan)
    style: Literal["prime_2026", "kids_2026"] = "prime_2026"
    no_repeat_scope: Literal["channel", "channel_and_others", "off"] = "channel"
    no_repeat_against: list[str] = Field(default_factory=list)
    excluded: list[ExcludedItem] = Field(default_factory=list)
    explain_level: Literal["beginner", "intermediate", "expert"] = "beginner"
    # Channel Creator v2 working state (discovery → plan → build)
    candidates: list[dict[str, Any]] = Field(default_factory=list)
    kept_candidate_indexes: list[int] = Field(default_factory=list)
    plan_token: Optional[str] = None
    plan_preview: Optional[dict[str, Any]] = None
    plan_questions: list[dict[str, Any]] = Field(default_factory=list)
    find_job_id: Optional[str] = None


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
    requirements: Optional[ChannelRequirements] = None
    template: Optional[
        Literal["kids_specials", "holiday_family", "prime_time_station_ids", "custom"]
    ] = None
    enrich_metadata: Optional[bool] = None
    guide_title_style: Optional[Literal["clean", "slot"]] = None
    channel_number: Optional[str] = None
    channel_name: Optional[str] = None
    slug: Optional[str] = None
    collection_prefix: Optional[str] = None
    group: Optional[str] = None
    break_plan: Optional[BreakPlan] = None
    style: Optional[Literal["prime_2026", "kids_2026"]] = None
    no_repeat_scope: Optional[Literal["channel", "channel_and_others", "off"]] = None
    no_repeat_against: Optional[list[str]] = None
    explain_level: Optional[Literal["beginner", "intermediate", "expert"]] = None


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


class TvdbKeyRequest(BaseModel):
    api_key: str


class TvmazeCredentialsRequest(BaseModel):
    username: str
    api_key: str


class CommunityCookieLoginRequest(BaseModel):
    source_id: str


class BuildResult(BaseModel):
    channel_number: str
    unified_path: str
    inventory_path: str
    schedule_path: str
    stream_count: int
    warnings: list[str] = Field(default_factory=list)
