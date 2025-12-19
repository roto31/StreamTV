"""Media API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from ..database import get_db, MediaItem, StreamSource
from ..api.schemas import MediaItemCreate, MediaItemResponse
from ..streaming import StreamManager


class PlexRatingKeyRequest(BaseModel):
    rating_key: str

router = APIRouter(prefix="/media", tags=["Media"])

stream_manager = StreamManager()


@router.get("", response_model=List[MediaItemResponse])
def get_all_media(
    source: Optional[StreamSource] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all media items"""
    query = db.query(MediaItem)
    if source:
        query = query.filter(MediaItem.source == source)
    media_items = query.offset(skip).limit(limit).all()
    return media_items


@router.get("/{media_id}", response_model=MediaItemResponse)
def get_media(media_id: int, db: Session = Depends(get_db)):
    """Get media item by ID"""
    media_item = db.query(MediaItem).filter(MediaItem.id == media_id).first()
    if not media_item:
        raise HTTPException(status_code=404, detail="Media item not found")
    return media_item


@router.post("", response_model=MediaItemResponse, status_code=status.HTTP_201_CREATED)
async def create_media(media: MediaItemCreate, db: Session = Depends(get_db)):
    """Add a new media item from URL"""
    # Check if URL already exists
    existing = db.query(MediaItem).filter(MediaItem.url == media.url).first()
    if existing:
        return existing
    
    # Detect source and get media info
    source = stream_manager.detect_source(media.url)
    if source.value == "unknown":
        raise HTTPException(status_code=400, detail="Unsupported media source")
    
    try:
        # Get media information
        media_info = await stream_manager.get_media_info(media.url, source)
        
        # Extract source ID
        source_id = media.url
        if source.value == "youtube" and stream_manager.youtube_adapter:
            source_id = stream_manager.youtube_adapter.extract_video_id(media.url) or media.url
        elif source.value == "archive_org" and stream_manager.archive_org_adapter:
            source_id = stream_manager.archive_org_adapter.extract_identifier(media.url) or media.url
        elif source.value == "pbs":
            # For PBS, use the URL as source_id (live streams don't have separate IDs)
            source_id = media.url
        
        # Create media item
        db_media = MediaItem(
            source=StreamSource(source.value),
            source_id=source_id or "",
            url=media.url,
            title=media_info.get('title', media.title),
            description=media_info.get('description', media.description),
            duration=media_info.get('duration', media.duration),
            thumbnail=media_info.get('thumbnail', media.thumbnail),
            uploader=media_info.get('uploader') or media_info.get('creator'),
            upload_date=media_info.get('upload_date') or media_info.get('date'),
            view_count=media_info.get('view_count'),
        )
        
        db.add(db_media)
        db.commit()
        db.refresh(db_media)
        return db_media
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error adding media: {str(e)}")


@router.post("/plex/from-rating-key", response_model=MediaItemResponse, status_code=status.HTTP_201_CREATED)
async def create_media_from_plex_rating_key(
    request: PlexRatingKeyRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Create a MediaItem from a Plex rating key"""
    from ..config import config
    
    rating_key = request.rating_key
    
    if not config.plex.enabled or not config.plex.base_url:
        raise HTTPException(status_code=400, detail="Plex not configured")
    
    # Check if MediaItem already exists for this rating key
    existing = db.query(MediaItem).filter(
        MediaItem.source == StreamSource.PLEX,
        MediaItem.source_id == rating_key
    ).first()
    if existing:
        return existing
    
    try:
        # Get media info from Plex
        plex_url = f"plex://{config.plex.base_url.replace('http://', '').replace('https://', '')}/library/metadata/{rating_key}"
        plex_info = await stream_manager.plex_adapter.get_media_info(plex_url)
        
        if not plex_info:
            raise HTTPException(status_code=404, detail="Plex media not found")
        
        # Format thumbnail URL
        thumbnail = None
        if plex_info.get('thumb'):
            thumb_path = plex_info['thumb']
            if thumb_path.startswith('/'):
                thumbnail = f"{config.plex.base_url}{thumb_path}?X-Plex-Token={config.plex.token or ''}"
            elif thumb_path.startswith('http'):
                thumbnail = thumb_path
            else:
                thumbnail = f"{config.plex.base_url}/{thumb_path}?X-Plex-Token={config.plex.token or ''}"
        
        # Create media item
        db_media = MediaItem(
            source=StreamSource.PLEX,
            source_id=rating_key,
            url=plex_url,
            title=plex_info.get('title', 'Untitled'),
            description=plex_info.get('summary', ''),
            duration=plex_info.get('duration'),
            thumbnail=thumbnail
        )
        
        db.add(db_media)
        db.commit()
        db.refresh(db_media)
        return db_media
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating media from Plex: {str(e)}")


@router.delete("/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_media(media_id: int, db: Session = Depends(get_db)):
    """Delete a media item"""
    media_item = db.query(MediaItem).filter(MediaItem.id == media_id).first()
    if not media_item:
        raise HTTPException(status_code=404, detail="Media item not found")
    
    db.delete(media_item)
    db.commit()
    return None
