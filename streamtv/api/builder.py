"""Channel Builder REST API."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from streamtv.builder.auth_service import (
    apply_archive_credentials,
    apply_tvdb_api_key,
    apply_tvmaze_credentials,
    apply_youtube_cookies,
    auth_status,
)
from streamtv.builder.compiler import _next_channel_number, build_channel_from_draft
from streamtv.builder.cookie_io import (
    cookies_path_for_scope,
    write_netscape_cookies,
)
from streamtv.builder.jobs import job_store
from streamtv.builder.models import (
    ArchiveLoginRequest,
    AuthCheckRequest,
    AuthCheckResponse,
    AuthScopeStatus,
    BuilderDraft,
    BuilderJob,
    BuilderSourceResponse,
    ChannelInfo,
    DraftCreateRequest,
    DraftPatchRequest,
    FillerCollection,
    FillerCreateRequest,
    FillerLink,
    LinkItem,
    LinkStatus,
    LinksBatchRequest,
    PlaywrightLoginRequest,
    TvdbKeyRequest,
    TvmazeCredentialsRequest,
)
from streamtv.builder.playwright_auth import (
    capture_cookies_generic,
    capture_cookies_youtube,
)
from streamtv.builder.resolver import detect_url_kind, expand_url, resolve_url_async
from streamtv.builder.sources import get_source, list_sources, reload_sources
from streamtv.builder.store import DraftStore, FillerStore
from streamtv.config import config
from streamtv.database import Channel, get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/builder", tags=["Channel Builder"])

draft_store = DraftStore()

_RETIRED_BUILDER_SOURCES = frozenset({"pbs", "plex", "vimeo"})


def _assert_source_allowed(source_id: Optional[str]) -> None:
    if not source_id:
        return
    if source_id in _RETIRED_BUILDER_SOURCES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Source '{source_id}' is retired from Channel Builder. "
                "Choose archive.org or youtube."
            ),
        )
filler_store = FillerStore()

ROOT = Path(__file__).resolve().parents[2]
CUSTOM_SOURCES_PDF = ROOT / "frontend" / "builder" / "public" / "custom-sources-guide.pdf"
CUSTOM_SOURCES_HTML = ROOT / "frontend" / "builder" / "public" / "custom-sources-guide.html"


def _existing_channel_numbers(db: Session) -> set[str]:
    return {str(ch.number) for ch in db.query(Channel.number).all()}


def _source_to_response(spec) -> BuilderSourceResponse:
    return BuilderSourceResponse(
        id=spec.id,
        label=spec.label,
        status=spec.status,
        hosts=spec.hosts,
        auth_methods=spec.auth_methods,
        url_placeholder=spec.url_placeholder,
        supports_expand=spec.supports_expand,
        playout_ready=spec.playout_ready,
        docs_anchor=spec.docs_anchor,
    )


def _assert_playout_ready(draft: BuilderDraft) -> None:
    if draft.selected_source:
        spec = get_source(draft.selected_source)
        if spec and not spec.playout_ready:
            raise ValueError(
                "Selected source is not enabled for playout. "
                "See the Custom Sources guide on the Builder page."
            )
    for link in draft.links:
        if link.status != LinkStatus.OK:
            continue
        for spec in list_sources():
            if spec.resolver_source == link.source and not spec.playout_ready:
                raise ValueError(
                    f"Source '{spec.label}' is not enabled for playout. "
                    "See the Custom Sources guide."
                )


async def _resolve_draft_links(job: BuilderJob) -> None:
    draft = draft_store.get(job.draft_id)
    if not draft:
        job.status = "failed"
        job.errors.append("Draft not found")
        job_store.save(job)
        return

    pending = [link for link in draft.links if link.status in (LinkStatus.PENDING, LinkStatus.ERROR)]
    job.total = len(pending)
    job.completed = 0
    job_store.save(job)

    for link in pending:
        link.status = LinkStatus.RESOLVING
        draft_store.save(draft)
        try:
            expanded = await resolve_url_async(link.url, draft=draft)
            if len(expanded) == 1:
                item = expanded[0]
                link.status = LinkStatus.OK
                link.source = item.get("source")
                link.title = item.get("title")
                link.duration = item.get("duration")
                link.upload_date = item.get("upload_date")
                link.thumbnail = item.get("thumbnail")
                link.stream_id = item.get("stream_id")
                link.error = None
            else:
                idx = draft.links.index(link)
                draft.links.pop(idx)
                new_links: list[LinkItem] = []
                for item in expanded:
                    new_links.append(
                        LinkItem(
                            url=item["url"],
                            status=LinkStatus.OK,
                            source=item.get("source"),
                            title=item.get("title"),
                            duration=item.get("duration"),
                            upload_date=item.get("upload_date"),
                            thumbnail=item.get("thumbnail"),
                            stream_id=item.get("stream_id"),
                            expanded_from=link.url,
                        )
                    )
                draft.links[idx:idx] = new_links
        except Exception as exc:
            link.status = LinkStatus.ERROR
            link.error = str(exc)
        job.completed += 1
        job_store.save(job)
        draft_store.save(draft)

    job.result = {"resolved": sum(1 for link in draft.links if link.status == LinkStatus.OK)}
    job_store.save(job)


async def _run_playwright_login(job: BuilderJob, scope: str, email: str, password: str) -> None:
    try:
        if scope == "youtube":
            path = await capture_cookies_youtube(email, password)
            apply_youtube_cookies(path)
        else:
            spec = get_source(scope)
            if not spec or not spec.auth.login_url:
                raise ValueError(f"Playwright login not configured for {scope}")
            await capture_cookies_generic(
                spec.auth.login_url,
                email,
                password,
                spec.auth.cookies_domain or spec.hosts[0],
                scope.replace("community:", ""),
            )
        job.result = {"scope": scope, "configured": True}
        job_store.save(job)
    except Exception as exc:
        job.status = "failed"
        job.errors.append(str(exc))
        job_store.save(job)


@router.get("/sources", response_model=list[BuilderSourceResponse])
async def get_sources() -> list[BuilderSourceResponse]:
    return [_source_to_response(spec) for spec in list_sources()]


@router.post("/sources/reload", response_model=list[BuilderSourceResponse])
async def reload_source_registry() -> list[BuilderSourceResponse]:
    return [_source_to_response(spec) for spec in reload_sources()]


@router.get("/docs/custom-sources.pdf")
async def download_custom_sources_pdf() -> FileResponse:
    if CUSTOM_SOURCES_PDF.exists():
        return FileResponse(
            CUSTOM_SOURCES_PDF,
            media_type="application/pdf",
            filename="custom-sources-guide.pdf",
        )
    if CUSTOM_SOURCES_HTML.exists():
        return FileResponse(
            CUSTOM_SOURCES_HTML,
            media_type="text/html",
            filename="custom-sources-guide.html",
        )
    raise HTTPException(
        status_code=404,
        detail="Guide not built. Run: bash scripts/generate_builder_custom_sources_pdf.sh",
    )


@router.get("/auth/status")
async def builder_auth_status() -> dict:
    return auth_status()


@router.post("/auth/archive")
async def builder_auth_archive(body: ArchiveLoginRequest) -> dict:
    return apply_archive_credentials(body.username, body.password)


@router.post("/auth/youtube/login", response_model=BuilderJob)
async def builder_auth_youtube(body: PlaywrightLoginRequest) -> BuilderJob:
    job = BuilderJob(draft_id="__auth__", job_type="auth_login", total=1)

    async def _run(j: BuilderJob) -> None:
        await _run_playwright_login(j, "youtube", body.email, body.password)

    job_store.start_background(job, _run)
    return job


@router.post("/auth/pbs/login", response_model=BuilderJob)
async def builder_auth_pbs_retired(body: PlaywrightLoginRequest) -> BuilderJob:
    raise HTTPException(
        status_code=410,
        detail=(
            "PBS Builder auth is retired. First-party Builder sources are "
            "Archive.org and YouTube only."
        ),
    )



@router.post("/auth/tvdb")
async def builder_auth_tvdb(body: TvdbKeyRequest) -> dict:
    try:
        return apply_tvdb_api_key(body.api_key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/auth/tvmaze")
async def builder_auth_tvmaze(body: TvmazeCredentialsRequest) -> dict:
    try:
        return apply_tvmaze_credentials(body.username, body.api_key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc



@router.post("/auth/{scope}/cookies")
async def builder_auth_cookies(scope: str, file: UploadFile = File(...)) -> dict:
    scope_key = scope.replace("community:", "")
    path = cookies_path_for_scope(scope_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = await file.read()
    path.write_bytes(content)
    if scope == "youtube":
        apply_youtube_cookies(path)
    return {"status": "success", "scope": scope, "cookies_file": str(path)}


@router.post("/drafts", response_model=BuilderDraft)
async def create_draft(
    body: DraftCreateRequest,
    db: Session = Depends(get_db),
) -> BuilderDraft:
    existing = _existing_channel_numbers(db)
    number = body.channel_number or _next_channel_number(existing)
    if number in existing:
        raise HTTPException(status_code=409, detail=f"Channel number {number} already exists")
    draft = BuilderDraft(
        channel=ChannelInfo(
            number=number,
            name=body.channel_name or f"Channel {number}",
        )
    )
    return draft_store.save(draft)


@router.get("/drafts", response_model=list[BuilderDraft])
async def list_drafts() -> list[BuilderDraft]:
    drafts: list[BuilderDraft] = []
    for draft_id in draft_store.list_ids():
        draft = draft_store.get(draft_id)
        if draft:
            drafts.append(draft)
    return drafts


@router.get("/drafts/{draft_id}", response_model=BuilderDraft)
async def get_draft(draft_id: str) -> BuilderDraft:
    draft = draft_store.get(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@router.patch("/drafts/{draft_id}", response_model=BuilderDraft)
async def patch_draft(draft_id: str, body: DraftPatchRequest) -> BuilderDraft:
    draft = draft_store.get(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    if body.selected_source is not None:
        _assert_source_allowed(body.selected_source)
        spec = get_source(body.selected_source)
        if not spec:
            raise HTTPException(status_code=400, detail=f"Unknown source: {body.selected_source}")
        if spec.status == "coming_soon":
            raise HTTPException(status_code=400, detail=f"{spec.label} is not available yet")
        draft.selected_source = body.selected_source
    if body.ordering is not None:
        draft.ordering = body.ordering
    if body.channel is not None:
        draft.channel = body.channel
    if body.filler_attachments is not None:
        draft.filler_attachments = body.filler_attachments
    if body.pbs_filter_full_episodes is not None:
        draft.pbs_filter_full_episodes = body.pbs_filter_full_episodes
    if body.pbs_min_episode_seconds is not None:
        draft.pbs_min_episode_seconds = body.pbs_min_episode_seconds
    # Channel Creator v2 fields (§4.2 / §7.2)
    for attr in (
        "requirements",
        "template",
        "enrich_metadata",
        "guide_title_style",
        "channel_number",
        "channel_name",
        "slug",
        "collection_prefix",
        "group",
        "break_plan",
        "style",
        "no_repeat_scope",
        "no_repeat_against",
        "explain_level",
        "kept_candidate_indexes",
        "candidates",
    ):
        val = getattr(body, attr, None)
        if val is not None:
            setattr(draft, attr, val)
            if attr == "channel_number" and val:
                draft.channel.number = str(val)
            if attr == "channel_name" and val:
                draft.channel.name = str(val)
            if attr == "group" and val:
                draft.channel.group = str(val)
    return draft_store.save(draft)


@router.delete("/drafts/{draft_id}")
async def delete_draft(draft_id: str) -> dict:
    if not draft_store.delete(draft_id):
        raise HTTPException(status_code=404, detail="Draft not found")
    return {"status": "deleted", "id": draft_id}


@router.post("/drafts/{draft_id}/links", response_model=BuilderDraft)
async def add_links(draft_id: str, body: LinksBatchRequest) -> BuilderDraft:
    draft = draft_store.get(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    seen = {link.url.strip() for link in draft.links}
    for raw in body.urls:
        url = raw.strip()
        if not url or url in seen:
            continue
        seen.add(url)
        draft.links.append(LinkItem(url=url))
    return draft_store.save(draft)


@router.post("/drafts/{draft_id}/resolve", response_model=BuilderJob)
async def start_resolve(draft_id: str) -> BuilderJob:
    draft = draft_store.get(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    job = BuilderJob(draft_id=draft_id, job_type="resolve")
    job_store.start_background(job, _resolve_draft_links)
    return job


@router.get("/jobs/{job_id}", response_model=BuilderJob)
async def get_job(job_id: str) -> BuilderJob:
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/filler-collections", response_model=list[FillerCollection])
async def list_filler_collections() -> list[FillerCollection]:
    return filler_store.list_all()


@router.post("/filler-collections", response_model=FillerCollection)
async def create_filler_collection(body: FillerCreateRequest) -> FillerCollection:
    filler = FillerCollection(name=body.name, description=body.description)
    for url in body.urls:
        url = url.strip()
        if not url:
            continue
        try:
            items = expand_url(url)
            for item in items:
                filler.links.append(
                    FillerLink(
                        url=item["url"],
                        title=item.get("title"),
                        clip_type=body.clip_type,
                        duration=item.get("duration"),
                        source=item.get("source"),
                        stream_id=item.get("stream_id"),
                    )
                )
        except Exception as exc:
            filler.links.append(
                FillerLink(url=url, clip_type=body.clip_type, title=str(exc)[:80])
            )
    return filler_store.save(filler)


@router.get("/filler-collections/{filler_id}", response_model=FillerCollection)
async def get_filler_collection(filler_id: str) -> FillerCollection:
    filler = filler_store.get(filler_id)
    if not filler:
        raise HTTPException(status_code=404, detail="Filler collection not found")
    return filler


@router.delete("/filler-collections/{filler_id}")
async def delete_filler_collection(filler_id: str) -> dict:
    if not filler_store.delete(filler_id):
        raise HTTPException(status_code=404, detail="Filler collection not found")
    return {"status": "deleted", "id": filler_id}


@router.post("/auth-check", response_model=AuthCheckResponse)
async def auth_check(body: AuthCheckRequest) -> AuthCheckResponse:
    status = auth_status()
    requires_archive = False
    requires_youtube = False
    requires_pbs = False
    requires_plex = False
    for url in body.urls:
        kind = detect_url_kind(url)
        if kind in ("archive", "archive_collection"):
            requires_archive = True
        elif kind in ("youtube", "youtube_playlist"):
            requires_youtube = True
        elif kind in ("pbs", "pbs_show"):
            requires_pbs = True
        elif kind == "plex":
            requires_plex = True

    scopes = [
        AuthScopeStatus(scope="archive_org", **status["archive_org"]),
        AuthScopeStatus(scope="youtube", **status["youtube"]),
        AuthScopeStatus(scope="pbs", **status["pbs"]),
        AuthScopeStatus(scope="plex", **status["plex"]),
    ]
    return AuthCheckResponse(
        scopes=scopes,
        requires_archive=requires_archive,
        requires_youtube=requires_youtube,
        requires_pbs=requires_pbs,
        requires_plex=requires_plex,
    )


async def _build_draft_job(job: BuilderJob, request: Request) -> None:
    from streamtv.database.session import SessionLocal

    draft = draft_store.get(job.draft_id)
    if not draft:
        raise ValueError("Draft not found")
    if not draft.channel.number:
        raise ValueError("Channel number required")
    if not any(link.status == LinkStatus.OK for link in draft.links):
        raise ValueError("No resolved links — run resolve first")
    _assert_playout_ready(draft)

    db = SessionLocal()
    try:
        result = await build_channel_from_draft(draft, db, filler_store=filler_store)
        draft.built = True
        draft.built_channel_number = result["channel_number"]
        draft_store.save(draft)

        from streamtv.api.channels import reset_continuous_playout_by_number

        await reset_continuous_playout_by_number(
            result["channel_number"],
            request,
            None,
            db,
        )

        enrichment_summary: dict = {}
        warnings = list(result.get("warnings") or [])
        if draft.channel.enrich_metadata:
            try:
                from streamtv.builder.enrichment import enrich_built_draft

                enrichment_summary = await enrich_built_draft(draft)
                if enrichment_summary.get("warning"):
                    warnings.append(str(enrichment_summary["warning"]))
            except Exception as enrich_exc:
                logger.exception(
                    "Post-build enrichment failed for channel %s",
                    result["channel_number"],
                )
                enrichment_summary = {
                    "skipped_enrichment": True,
                    "warning": f"Enrichment error: {enrich_exc}",
                    "updated": 0,
                    "failed": 0,
                    "total": 0,
                    "skipped": 0,
                }
                warnings.append(enrichment_summary["warning"])

        result["enrichment"] = enrichment_summary
        result["warnings"] = warnings
        job.result = result
        job_store.save(job)
    finally:
        db.close()


@router.post("/drafts/{draft_id}/build", response_model=BuilderJob)
async def build_draft(
    draft_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> BuilderJob:
    draft = draft_store.get(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    _assert_source_allowed(draft.selected_source)

    job = BuilderJob(draft_id=draft_id, job_type="build", total=1)

    async def _run(j: BuilderJob) -> None:
        await _build_draft_job(j, request)

    job_store.start_background(job, _run)
    return job


# ---------------------------------------------------------------------------
# Channel Creator v2 routes (§5.2–§5.8 / detail tools §7.2)
# ---------------------------------------------------------------------------


from pydantic import BaseModel, Field  # noqa: E402


class DiscoverRequest(BaseModel):
    sources: list[str] = Field(default_factory=lambda: ["archive", "youtube"])
    max_per_query: int = 25
    extra_queries: list[str] = Field(default_factory=list)


class InspectRequest(BaseModel):
    candidate_ids: list[str] = Field(default_factory=list)


class CandidateIdsRequest(BaseModel):
    candidate_ids: list[str] = Field(default_factory=list)
    role: str = "program"
    station_group: Optional[str] = None


class ExclusionItem(BaseModel):
    url: Optional[str] = None
    title: Optional[str] = None
    reason: str = ""


class ExclusionsRequest(BaseModel):
    exclusions: list[ExclusionItem] = Field(default_factory=list)


class ValidateRequest(BaseModel):
    skip_availability: bool = False


class NewchannelBuildRequest(BaseModel):
    plan_token: str = ""
    confirm: str = ""
    skip_availability: bool = False
    enrich_metadata: bool = True
    guide_title_style: str = "slot"
    import_channel: bool = True
    force_fail_gate: Optional[str] = None
    dry_run: bool = False


class ArchiveDiscoverRequest(BaseModel):
    query: str
    rows: int = 100


class ArchiveInspectRequest(BaseModel):
    identifier: str


class YoutubeDiscoverRequest(BaseModel):
    query: str
    max_results: int = 20


class YoutubeInspectRequest(BaseModel):
    video_id: str


def _draft_or_404(draft_id: str) -> BuilderDraft:
    draft = draft_store.get(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


def _requirements_dict(draft: BuilderDraft) -> dict:
    return draft.requirements.model_dump() if draft.requirements else {}


@router.post("/drafts/{draft_id}/discover")
async def discover_for_draft(draft_id: str, body: DiscoverRequest) -> dict:
    """Run discovery into draft.candidates."""
    draft = _draft_or_404(draft_id)
    from streamtv.builder.discovery import (
        build_archive_queries,
        search_archive,
        search_youtube,
    )
    from streamtv.builder.discovery.youtube import build_youtube_queries

    req = _requirements_dict(draft)
    candidates: list[dict] = list(draft.candidates or [])
    seen = {(c.get("source"), c.get("id")) for c in candidates}

    if "archive" in body.sources:
        queries = build_archive_queries(req) + list(body.extra_queries)
        for q in queries:
            for doc in search_archive(q, rows=body.max_per_query):
                ident = doc.get("identifier")
                key = ("archive", ident)
                if not ident or key in seen:
                    continue
                seen.add(key)
                candidates.append(
                    {
                        "query": q,
                        "source": "archive",
                        "id": ident,
                        "title": doc.get("title"),
                        "date": doc.get("date"),
                        "description": (doc.get("description") or "")[:500],
                    }
                )

    if "youtube" in body.sources:
        try:
            yq = build_youtube_queries(req) + list(body.extra_queries)
        except Exception:  # noqa: BLE001
            yq = list(body.extra_queries) or [req.get("theme") or "christmas"]
        for q in yq:
            for hit in search_youtube(q, n=body.max_per_query):
                vid = hit.get("video_id") or hit.get("id")
                key = ("youtube", vid)
                if not vid or key in seen:
                    continue
                seen.add(key)
                candidates.append(
                    {
                        "query": q,
                        "source": "youtube",
                        "id": vid,
                        "title": hit.get("title"),
                        "channel": hit.get("channel"),
                        "duration": hit.get("duration"),
                    }
                )

    draft.candidates = candidates
    draft_store.save(draft)
    return {
        "draft_id": draft.id,
        "candidate_count": len(candidates),
        "candidates": candidates[:50],
    }


@router.post("/drafts/{draft_id}/inspect")
async def inspect_candidates(draft_id: str, body: InspectRequest) -> dict:
    draft = _draft_or_404(draft_id)
    from streamtv.builder.discovery import inspect_archive_item, inspect_youtube_video

    want = set(body.candidate_ids) if body.candidate_ids else {
        str(c.get("id")) for c in draft.candidates
    }
    out = []
    for c in draft.candidates:
        cid = str(c.get("id") or "")
        if cid not in want:
            continue
        if c.get("source") == "archive":
            detail = inspect_archive_item(cid)
        else:
            detail = inspect_youtube_video(cid)
        c.update(detail)
        out.append(c)
    draft_store.save(draft)
    return {"draft_id": draft.id, "inspected": out}


@router.post("/drafts/{draft_id}/classify")
async def classify_draft(draft_id: str) -> dict:
    draft = _draft_or_404(draft_id)
    from streamtv.builder.evidence import classify_item

    req = _requirements_dict(draft)
    era = req.get("era") or {}
    era_to = era.get("to")
    for c in draft.candidates:
        result = classify_item(
            str(c.get("title") or ""),
            str(c.get("description") or ""),
            runtime_s=c.get("duration") or c.get("duration_exact"),
            era_to=int(era_to) if era_to is not None else None,
            requirements=req,
        )
        c["network"] = result.network
        c["station"] = result.station
        c["air_date"] = result.air_date
        c["air_date_quality"] = result.air_date_quality
        c["commercials"] = result.commercials
        c["commercials_evidence"] = result.commercials_evidence
        c["tier"] = result.tier
        c["exclusion_reason"] = result.exclusion_reason
    draft_store.save(draft)
    return {"draft_id": draft.id, "candidates": draft.candidates}


@router.post("/drafts/{draft_id}/candidates/add")
async def add_candidates(draft_id: str, body: CandidateIdsRequest) -> BuilderDraft:
    draft = _draft_or_404(draft_id)
    by_id = {str(c.get("id")): c for c in draft.candidates}
    kept = list(draft.kept_candidate_indexes or [])
    for cid in body.candidate_ids:
        c = by_id.get(cid)
        if not c:
            continue
        c["role"] = body.role
        if body.station_group:
            c["group"] = body.station_group
            c["station_group"] = body.station_group
        # Track kept indexes for /plan (otherwise plan uses every candidate).
        for idx, raw in enumerate(draft.candidates):
            if str(raw.get("id")) == str(cid) and idx not in kept:
                kept.append(idx)
                break
        url = c.get("url")
        if url and not any(l.url == url for l in draft.links):
            role = (
                body.role
                if body.role in ("program", "marathon", "break", "station_id")
                else "program"
            )
            draft.links.append(
                LinkItem(
                    url=url,
                    title=c.get("title"),
                    source=c.get("source"),
                    status=LinkStatus.OK,
                    role=role,
                    station_group=body.station_group,
                    network=c.get("network"),
                    air_date=c.get("air_date"),
                    commercials=c.get("commercials") or "unverified",
                    tier=c.get("tier"),
                    duration_exact=c.get("duration_exact"),
                    stream_id=c.get("id"),
                )
            )
    draft.kept_candidate_indexes = kept
    return draft_store.save(draft)


@router.post("/drafts/{draft_id}/exclusions")
async def add_exclusions(draft_id: str, body: ExclusionsRequest) -> BuilderDraft:
    from streamtv.builder.models import ExcludedItem

    draft = _draft_or_404(draft_id)
    for ex in body.exclusions:
        draft.excluded.append(
            ExcludedItem(url=ex.url, title=ex.title, reason=ex.reason)
        )
    return draft_store.save(draft)


@router.post("/drafts/{draft_id}/plan")
async def plan_draft(draft_id: str) -> dict:
    draft = _draft_or_404(draft_id)
    import secrets

    from streamtv.builder.planner import build_channel_package, canonical_title
    from streamtv.builder.templates import apply_template_defaults

    number = draft.channel_number or draft.channel.number or ""
    name = draft.channel_name or draft.channel.name or "New Channel"
    if not number:
        raise HTTPException(status_code=400, detail="channel_number required before plan")

    kept = draft.kept_candidate_indexes
    if kept:
        cands = [draft.candidates[i] for i in kept if 0 <= i < len(draft.candidates)]
    else:
        cands = [
            c
            for c in draft.candidates
            if not c.get("exclusion_reason")
        ]

    normalized = []
    for c in cands:
        role = c.get("role") or "program"
        seconds = c.get("seconds") or c.get("duration") or c.get("duration_exact") or 0
        try:
            seconds = int(float(seconds))
        except (TypeError, ValueError):
            seconds = 0
        year_raw = c.get("year") or (c.get("air_date") or c.get("date") or "1990")[:4]
        try:
            year = int(str(year_raw)[:4])
        except ValueError:
            year = 1990
        normalized.append(
            {
                **c,
                "role": role,
                "seconds": seconds,
                "id": c.get("id") or c.get("stream_id"),
                "title": c.get("title") or "Untitled",
                "network": c.get("network") or c.get("station") or "",
                "year": year,
                "date": c.get("date") or c.get("air_date"),
                "source": c.get("source") or "archive",
                "url": c.get("url") or "",
                "page": c.get("page") or c.get("page_url") or c.get("url") or "",
                "tier": c.get("tier") or 2,
                "commercials": c.get("commercials") or "unverified",
                "note": c.get("note") or "",
                "group": c.get("group") or c.get("station_group") or "",
            }
        )

    tmpl_id = draft.template if draft.template != "custom" else "holiday_family"
    spec = apply_template_defaults(
        {
            "number": number,
            "name": name,
            "group": draft.group or draft.channel.group or "Holiday",
            "description": draft.channel.description or f"New channel {number}",
            "collection_prefix": draft.collection_prefix or name,
            "schedule_description": draft.channel.description or name,
            "sequence_key": f"{(draft.slug or name).lower().replace(' ', '-')}-channel",
            "style": draft.style,
            "break_groups": list(draft.break_plan.groups)
            if draft.break_plan.enabled
            else [],
            "rotation": draft.break_plan.rotation,
            "long_reel_seconds": draft.break_plan.long_reel_seconds,
            "station_id_after_each_gap": draft.break_plan.station_id_after_each_gap,
        },
        tmpl_id,
    )
    if not draft.break_plan.enabled:
        spec["break_groups"] = []
        spec["station_id_after_each_gap"] = False

    channel_doc, schedule = build_channel_package(
        spec,
        normalized,
        enrich_metadata=draft.enrich_metadata,
        guide_title_style=draft.guide_title_style,
    )
    token = secrets.token_urlsafe(16)
    draft.plan_token = token
    draft.plan_preview = {
        "channel": channel_doc,
        "schedule": schedule,
        "program_count": sum(
            1 for s in channel_doc["channels"][0]["streams"] if s.get("type") == "event"
        ),
        "canonical_titles": [
            canonical_title(str(c.get("title") or "")) for c in normalized
        ],
    }
    draft_store.save(draft)
    return {
        "draft_id": draft.id,
        "plan_token": token,
        "preview": draft.plan_preview,
        "questions": draft.plan_questions,
    }


@router.post("/drafts/{draft_id}/validate")
async def validate_draft(
    draft_id: str, body: Optional[ValidateRequest] = None
) -> dict:
    draft = _draft_or_404(draft_id)
    body = body or ValidateRequest()
    from streamtv.builder.gates import evaluate_compiled_package, load_inventory_titles
    from streamtv.builder.newchannel import check_number_free
    from streamtv.builder.paths import data_dir

    preview = draft.plan_preview or {}
    channel_doc = preview.get("channel")
    schedule = preview.get("schedule")
    if not channel_doc or not schedule:
        raise HTTPException(status_code=400, detail="Run /plan first")
    inventory = load_inventory_titles(
        data_dir(),
        list(draft.no_repeat_against or []),
    )
    report = evaluate_compiled_package(
        channel_doc,
        schedule,
        inventory_titles=inventory,
        skip_availability=body.skip_availability,
    )
    number = draft.channel_number or draft.channel.number
    if number:
        conflict = check_number_free(str(number))
        report.add(
            "G5",
            conflict.free,
            "number free" if conflict.free else "; ".join(conflict.reasons),
        )
    return report.as_dict()


@router.post("/drafts/{draft_id}/report")
async def report_draft(draft_id: str) -> dict:
    draft = _draft_or_404(draft_id)
    from streamtv.builder.reports import write_channel_package

    preview = draft.plan_preview or {}
    channel_doc = preview.get("channel")
    schedule = preview.get("schedule")
    if not channel_doc or not schedule:
        raise HTTPException(status_code=400, detail="Run /plan first")
    artifacts = write_channel_package(
        draft_id=draft.id,
        channel_doc=channel_doc,
        schedule=schedule,
        candidates=list(draft.candidates or []),
        excluded=[e.model_dump() for e in draft.excluded],
    )
    return {"draft_id": draft.id, "artifacts": artifacts}


@router.post("/drafts/{draft_id}/newchannel-build")
async def newchannel_build_draft(
    draft_id: str,
    body: NewchannelBuildRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Write a NEW channel via ``build_new_channel`` (§5.6). Requires plan_token + confirm=build."""
    draft = _draft_or_404(draft_id)
    if body.confirm != "build":
        raise HTTPException(status_code=400, detail="confirm must be 'build'")
    if not body.plan_token or body.plan_token != (draft.plan_token or ""):
        raise HTTPException(status_code=400, detail="plan_token missing or stale")

    from streamtv.builder.newchannel import build_new_channel, refuse_edit_existing
    from streamtv.builder.paths import repo_root
    from streamtv.builder.templates import apply_template_defaults

    number = str(draft.channel_number or draft.channel.number or "")
    if not number:
        raise HTTPException(status_code=400, detail="channel_number required")

    # Refuse editing template examples / occupied numbers is handled inside build_new_channel
    if draft.no_repeat_against and number in {str(x) for x in draft.no_repeat_against}:
        raise HTTPException(status_code=400, detail=refuse_edit_existing(number))

    kept = draft.kept_candidate_indexes
    if kept:
        cands = [draft.candidates[i] for i in kept if 0 <= i < len(draft.candidates)]
    else:
        cands = [c for c in (draft.candidates or []) if not c.get("exclusion_reason")]

    tmpl_id = draft.template if draft.template != "custom" else "prime_time_station_ids"
    spec = apply_template_defaults(
        {
            "number": number,
            "name": draft.channel_name or draft.channel.name or "New Channel",
            "group": draft.group or draft.channel.group or "Holiday",
            "description": draft.channel.description or f"New channel {number}",
            "collection_prefix": draft.collection_prefix
            or (draft.channel_name or draft.channel.name or "Channel"),
            "schedule_description": draft.channel.description
            or (draft.channel_name or "schedule"),
            "sequence_key": f"{(draft.slug or number).lower().replace(' ', '-')}-channel",
            "style": draft.style or "prime_2026",
            "break_groups": list(draft.break_plan.groups)
            if draft.break_plan.enabled
            else [],
            "rotation": draft.break_plan.rotation,
            "long_reel_seconds": draft.break_plan.long_reel_seconds,
            "station_id_after_each_gap": draft.break_plan.station_id_after_each_gap,
        },
        tmpl_id,
    )

    # Normalize candidate shape for planner
    normalized = []
    for c in cands:
        seconds = c.get("seconds") or c.get("duration") or c.get("duration_exact") or 0
        try:
            seconds = int(float(seconds))
        except (TypeError, ValueError):
            seconds = 0
        year_raw = c.get("year") or (c.get("air_date") or c.get("date") or "1990")[:4]
        try:
            year = int(str(year_raw)[:4])
        except ValueError:
            year = 1990
        row = {
            **c,
            "role": c.get("role") or "program",
            "seconds": seconds,
            "id": c.get("id") or c.get("stream_id"),
            "title": c.get("title") or "Untitled",
            "network": c.get("network") or c.get("station") or "",
            "year": year,
            "date": c.get("date") or c.get("air_date"),
            "source": c.get("source") or "archive",
            "url": c.get("url") or "",
            "page": c.get("page") or c.get("page_url") or c.get("url") or "",
            "tier": c.get("tier") or 2,
            "commercials": c.get("commercials") or "unverified",
            "note": c.get("note") or "",
            "group": c.get("group") or c.get("station_group") or "",
        }
        if body.enrich_metadata and not row.get("categories"):
            row["categories"] = ["Holiday", "Special"]
        if body.enrich_metadata and not row.get("source_description"):
            row["source_description"] = row.get("note") or row.get("title") or ""
        if body.enrich_metadata and not row.get("thumbnail") and row.get("id"):
            row["thumbnail"] = f"/static/thumbnails/{row['id']}.jpg"
        if body.enrich_metadata and not row.get("source_metadata"):
            row["source_metadata"] = {
                "title": row["title"],
                "duration_exact": float(seconds),
                "platform": row.get("source"),
            }
        normalized.append(row)

    report, artifacts, details = build_new_channel(
        spec,
        normalized,
        db=db,
        root=repo_root(),
        enrich_metadata=body.enrich_metadata,
        guide_title_style=body.guide_title_style,
        import_channel=body.import_channel,
        dry_run=body.dry_run,
        skip_availability=body.skip_availability,
        force_fail_gate=body.force_fail_gate,
    )
    out = report.as_dict()
    out["details"] = details
    if artifacts is not None:
        out["artifacts"] = [str(p) for p in artifacts.paths]
        out["channel_row_id"] = artifacts.channel_row_id
    return out


@router.post("/discover/archive")
async def discover_archive_ad_hoc(body: ArchiveDiscoverRequest) -> dict:
    from streamtv.builder.discovery import search_archive

    return {"results": search_archive(body.query, rows=body.rows)}


@router.post("/discover/archive/inspect")
async def inspect_archive_ad_hoc(body: ArchiveInspectRequest) -> dict:
    from streamtv.builder.discovery import inspect_archive_item

    return inspect_archive_item(body.identifier)


@router.post("/discover/youtube")
async def discover_youtube_ad_hoc(body: YoutubeDiscoverRequest) -> dict:
    from streamtv.builder.discovery import search_youtube

    return {"results": search_youtube(body.query, n=body.max_results)}


@router.post("/discover/youtube/inspect")
async def inspect_youtube_ad_hoc(body: YoutubeInspectRequest) -> dict:
    from streamtv.builder.discovery import inspect_youtube_video

    return inspect_youtube_video(body.video_id)
