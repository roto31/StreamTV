"""Playlists API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db, Playlist, PlaylistItem, MediaItem
from ..api.schemas import PlaylistCreate, PlaylistResponse

router = APIRouter(prefix="/playlists", tags=["Playlists"])


@router.get("", response_model=List[PlaylistResponse])
def get_all_playlists(db: Session = Depends(get_db)):
    """Get all playlists"""
    playlists = db.query(Playlist).all()
    return playlists


@router.get("/{playlist_id}", response_model=PlaylistResponse)
def get_playlist(playlist_id: int, db: Session = Depends(get_db)):
    """Get playlist by ID"""
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    return playlist


@router.post("", response_model=PlaylistResponse, status_code=status.HTTP_201_CREATED)
def create_playlist(playlist: PlaylistCreate, db: Session = Depends(get_db)):
    """Create a new playlist"""
    db_playlist = Playlist(**playlist.dict())
    db.add(db_playlist)
    db.commit()
    db.refresh(db_playlist)
    return db_playlist


@router.post("/{playlist_id}/items/{media_id}", status_code=status.HTTP_201_CREATED)
def add_item_to_playlist(playlist_id: int, media_id: int, db: Session = Depends(get_db)):
    """Add media item to playlist"""
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    media_item = db.query(MediaItem).filter(MediaItem.id == media_id).first()
    if not media_item:
        raise HTTPException(status_code=404, detail="Media item not found")
    
    # Get max order
    max_order = db.query(PlaylistItem).filter(
        PlaylistItem.playlist_id == playlist_id
    ).count()
    
    playlist_item = PlaylistItem(
        playlist_id=playlist_id,
        media_item_id=media_id,
        order=max_order
    )
    db.add(playlist_item)
    db.commit()
    return {"message": "Item added to playlist"}


@router.delete("/{playlist_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_item_from_playlist(playlist_id: int, item_id: int, db: Session = Depends(get_db)):
    """Remove item from playlist"""
    playlist_item = db.query(PlaylistItem).filter(
        PlaylistItem.id == item_id,
        PlaylistItem.playlist_id == playlist_id
    ).first()
    if not playlist_item:
        raise HTTPException(status_code=404, detail="Item not found in playlist")
    
    db.delete(playlist_item)
    db.commit()
    return None


@router.delete("/{playlist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_playlist(playlist_id: int, db: Session = Depends(get_db)):
    """Delete a playlist"""
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    db.delete(playlist)
    db.commit()
    return None
