"""Cache management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..database.models import CachedMedia, CacheStatus, MediaItem

router = APIRouter(prefix="/cache")


def _get_cache_manager(request: Request):
    mgr = getattr(request.app.state, "cache_manager", None)
    if mgr is None:
        raise HTTPException(status_code=503, detail="Cache not enabled or not initialized")
    return mgr


def _get_download_queue(request: Request):
    q = getattr(request.app.state, "download_queue", None)
    if q is None:
        raise HTTPException(status_code=503, detail="Download queue not initialized")
    return q


def _get_download_scheduler(request: Request):
    s = getattr(request.app.state, "download_scheduler", None)
    if s is None:
        raise HTTPException(status_code=503, detail="Download scheduler not initialized")
    return s


@router.get("/stats")
async def cache_stats(request: Request):
    """Return cache usage statistics."""
    cache_manager = _get_cache_manager(request)
    return cache_manager.stats()


@router.get("/items")
async def list_cache_items(
    request: Request,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """List cached media items, optionally filtered by status."""
    query = db.query(CachedMedia)
    if status:
        try:
            status_enum = CacheStatus(status)
            query = query.filter(CachedMedia.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    total = query.count()
    items = (
        query.order_by(CachedMedia.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [
            {
                "id": item.id,
                "source_id": item.source_id,
                "source": item.source.value if item.source else None,
                "media_item_id": item.media_item_id,
                "local_path": item.local_path,
                "size_bytes": item.size_bytes,
                "status": item.status.value if item.status else None,
                "error_message": item.error_message,
                "expires_at": item.expires_at.isoformat() if item.expires_at else None,
                "accessed_at": item.accessed_at.isoformat() if item.accessed_at else None,
                "hit_count": item.hit_count,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in items
        ],
    }


@router.delete("/items/{source_id}")
async def evict_cache_item(source_id: str, request: Request, db: Session = Depends(get_db)):
    """Manually evict a specific cached item."""
    item = db.query(CachedMedia).filter(CachedMedia.source_id == source_id).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"Cache entry not found: {source_id}")

    from pathlib import Path
    path = Path(item.local_path)
    if path.exists():
        try:
            if path.is_dir():
                import shutil
                shutil.rmtree(path)
            else:
                path.unlink()
        except OSError as exc:
            raise HTTPException(status_code=500, detail=f"Failed to delete file: {exc}")

    db.delete(item)
    db.commit()
    return {"deleted": source_id}


@router.post("/download")
async def enqueue_download(
    request: Request,
    media_item_id: int,
    db: Session = Depends(get_db),
):
    """Manually enqueue a media item for background download."""
    media_item = db.query(MediaItem).filter(MediaItem.id == media_item_id).first()
    if not media_item:
        raise HTTPException(status_code=404, detail=f"MediaItem {media_item_id} not found")

    download_queue = _get_download_queue(request)
    await download_queue.enqueue(media_item)
    return {"queued": media_item_id, "source_id": media_item.source_id}


@router.post("/evict-expired")
async def evict_expired(request: Request):
    """Trigger manual eviction of all expired cache entries."""
    cache_manager = _get_cache_manager(request)
    count = cache_manager.evict_expired()
    return {"evicted": count}


@router.post("/reconcile")
async def reconcile(request: Request):
    """Reconcile the cache manifest against files on disk."""
    cache_manager = _get_cache_manager(request)
    cache_manager.reconcile()
    return {"status": "reconciled"}


@router.get("/scheduler/jobs")
async def list_scheduler_jobs(request: Request):
    """List all scheduled download jobs."""
    scheduler = _get_download_scheduler(request)
    return {"jobs": scheduler.list_jobs()}


@router.post("/scheduler/jobs/{job_id}/trigger")
async def trigger_scheduler_job(job_id: str, request: Request):
    """Trigger an immediate run of a scheduled job."""
    scheduler = _get_download_scheduler(request)
    ok = await scheduler.trigger_now(job_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return {"triggered": job_id}
