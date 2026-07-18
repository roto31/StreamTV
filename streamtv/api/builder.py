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
    apply_pbs_cookies,
    apply_plex_credentials,
    apply_youtube_cookies,
    auth_status,
)
from streamtv.builder.compiler import _next_channel_number, build_channel_from_draft
from streamtv.builder.cookie_io import (
    cookies_path_for_scope,
    default_pbs_cookies_import_path,
    ensure_pbs_cookies_for_builder,
    import_pbs_cookies_from_downloads,
    write_netscape_cookies,
)
from streamtv.builder.pbs_defaults import apply_pbs_source_defaults
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
    PlexLoginRequest,
)
from streamtv.builder.playwright_auth import (
    capture_cookies_generic,
    capture_cookies_pbs,
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

    if draft.selected_source == "pbs":
        imported = ensure_pbs_cookies_for_builder(auto_import_downloads=True)
        if imported:
            logger.info("PBS cookies ready for resolve: %s", imported)

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
        elif scope == "pbs":
            path = await capture_cookies_pbs(email, password)
            apply_pbs_cookies(path)
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
async def builder_auth_pbs(body: PlaywrightLoginRequest) -> BuilderJob:
    job = BuilderJob(draft_id="__auth__", job_type="auth_login", total=1)

    async def _run(j: BuilderJob) -> None:
        await _run_playwright_login(j, "pbs", body.email, body.password)

    job_store.start_background(job, _run)
    return job


@router.post("/auth/plex")
async def builder_auth_plex(body: PlexLoginRequest) -> dict:
    return apply_plex_credentials(body.base_url, body.token)


@router.post("/auth/pbs/cookies/import")
async def builder_auth_pbs_import_downloads() -> dict:
    """Import PBS cookies from ~/Downloads/cookies.txt (or pbs.cookies_import_path)."""
    try:
        path = import_pbs_cookies_from_downloads()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    apply_pbs_cookies(path)
    return {
        "status": "success",
        "scope": "pbs",
        "cookies_file": str(path),
        "import_source": str(default_pbs_cookies_import_path()),
    }


@router.post("/auth/{scope}/cookies")
async def builder_auth_cookies(scope: str, file: UploadFile = File(...)) -> dict:
    scope_key = scope.replace("community:", "")
    path = cookies_path_for_scope(scope_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = await file.read()
    path.write_bytes(content)
    if scope == "youtube":
        apply_youtube_cookies(path)
    elif scope == "pbs":
        apply_pbs_cookies(path)
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
        spec = get_source(body.selected_source)
        if not spec:
            raise HTTPException(status_code=400, detail=f"Unknown source: {body.selected_source}")
        if spec.status == "coming_soon":
            raise HTTPException(status_code=400, detail=f"{spec.label} is not available yet")
        draft.selected_source = body.selected_source
        if body.selected_source == "pbs":
            draft = apply_pbs_source_defaults(draft)
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
    if body.pbs_exclude_passport_drm is not None:
        draft.pbs_exclude_passport_drm = body.pbs_exclude_passport_drm
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

    job = BuilderJob(draft_id=draft_id, job_type="build", total=1)

    async def _run(j: BuilderJob) -> None:
        await _build_draft_job(j, request)

    job_store.start_background(job, _run)
    return job
