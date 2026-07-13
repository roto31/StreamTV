"""Schedule Items API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from ..database import get_db, ScheduleItem, Schedule, Collection, MediaItem, Playlist
from ..api.schemas import ScheduleItemCreate, ScheduleItemUpdate, ScheduleItemResponse

router = APIRouter(prefix="/schedule-items", tags=["Schedule Items"])


@router.get("", response_model=List[ScheduleItemResponse])
def get_all_schedule_items(
    schedule_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get all schedule items, optionally filtered by schedule_id"""
    query = db.query(ScheduleItem)
    if schedule_id:
        query = query.filter(ScheduleItem.schedule_id == schedule_id)
    items = query.order_by(ScheduleItem.index).all()
    return items


@router.get("/{item_id}", response_model=ScheduleItemResponse)
def get_schedule_item(item_id: int, db: Session = Depends(get_db)):
    """Get schedule item by ID"""
    item = db.query(ScheduleItem).filter(ScheduleItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Schedule item not found")
    return item


@router.post("", response_model=ScheduleItemResponse, status_code=status.HTTP_201_CREATED)
def create_schedule_item(item: ScheduleItemCreate, db: Session = Depends(get_db)):
    """Create a new schedule item"""
    # Validate schedule exists
    schedule = db.query(Schedule).filter(Schedule.id == item.schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    # Validate collection/media/playlist references based on collection_type
    if item.collection_type == "collection" and item.collection_id:
        collection = db.query(Collection).filter(Collection.id == item.collection_id).first()
        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")
    elif item.collection_type == "media_item" and item.media_item_id:
        media = db.query(MediaItem).filter(MediaItem.id == item.media_item_id).first()
        if not media:
            raise HTTPException(status_code=404, detail="Media item not found")
    elif item.collection_type == "playlist" and item.playlist_id:
        playlist = db.query(Playlist).filter(Playlist.id == item.playlist_id).first()
        if not playlist:
            raise HTTPException(status_code=404, detail="Playlist not found")
    
    # If no index specified, add to end
    if item.index is None:
        max_index = db.query(ScheduleItem).filter(
            ScheduleItem.schedule_id == item.schedule_id
        ).order_by(ScheduleItem.index.desc()).first()
        item.index = (max_index.index + 1) if max_index else 0
    
    db_item = ScheduleItem(**item.dict(exclude_unset=True))
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.put("/{item_id}", response_model=ScheduleItemResponse)
def update_schedule_item(item_id: int, item: ScheduleItemUpdate, db: Session = Depends(get_db)):
    """Update a schedule item"""
    db_item = db.query(ScheduleItem).filter(ScheduleItem.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Schedule item not found")
    
    # Validate references if changed
    update_data = item.dict(exclude_unset=True)
    if "collection_id" in update_data and update_data["collection_id"]:
        collection = db.query(Collection).filter(Collection.id == update_data["collection_id"]).first()
        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")
    if "media_item_id" in update_data and update_data["media_item_id"]:
        media = db.query(MediaItem).filter(MediaItem.id == update_data["media_item_id"]).first()
        if not media:
            raise HTTPException(status_code=404, detail="Media item not found")
    if "playlist_id" in update_data and update_data["playlist_id"]:
        playlist = db.query(Playlist).filter(Playlist.id == update_data["playlist_id"]).first()
        if not playlist:
            raise HTTPException(status_code=404, detail="Playlist not found")
    
    for key, value in update_data.items():
        setattr(db_item, key, value)
    
    db_item.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_item)
    return db_item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule_item(item_id: int, db: Session = Depends(get_db)):
    """Delete a schedule item"""
    item = db.query(ScheduleItem).filter(ScheduleItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Schedule item not found")
    
    schedule_id = item.schedule_id
    item_index = item.index
    
    db.delete(item)
    db.commit()
    
    # Reorder remaining items
    remaining_items = db.query(ScheduleItem).filter(
        ScheduleItem.schedule_id == schedule_id,
        ScheduleItem.index > item_index
    ).all()
    for remaining_item in remaining_items:
        remaining_item.index -= 1
    db.commit()
    
    return None


@router.post("/{item_id}/move", response_model=ScheduleItemResponse)
def move_schedule_item(
    item_id: int,
    direction: str = Query(..., description="Direction to move: 'up' or 'down'"),
    db: Session = Depends(get_db)
):
    """Move a schedule item up or down in the order"""
    """Move a schedule item up or down in the order"""
    item = db.query(ScheduleItem).filter(ScheduleItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Schedule item not found")
    
    if direction == "up":
        if item.index == 0:
            raise HTTPException(status_code=400, detail="Item is already at the top")
        other_item = db.query(ScheduleItem).filter(
            ScheduleItem.schedule_id == item.schedule_id,
            ScheduleItem.index == item.index - 1
        ).first()
        if other_item:
            item.index, other_item.index = other_item.index, item.index
    elif direction == "down":
        max_index = db.query(ScheduleItem).filter(
            ScheduleItem.schedule_id == item.schedule_id
        ).order_by(ScheduleItem.index.desc()).first()
        if item.index >= max_index.index:
            raise HTTPException(status_code=400, detail="Item is already at the bottom")
        other_item = db.query(ScheduleItem).filter(
            ScheduleItem.schedule_id == item.schedule_id,
            ScheduleItem.index == item.index + 1
        ).first()
        if other_item:
            item.index, other_item.index = other_item.index, item.index
    else:
        raise HTTPException(status_code=400, detail="Direction must be 'up' or 'down'")
    
    db.commit()
    db.refresh(item)
    return item

