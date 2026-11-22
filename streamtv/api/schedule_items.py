"""Schedule Items API endpoints (legacy DB; YAML is playout authority)."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..api.schemas import ScheduleItemCreate, ScheduleItemResponse, ScheduleItemUpdate
from ..database import ScheduleItem, get_db

router = APIRouter(prefix="/schedule-items", tags=["Schedule Items"])

_MUTATE_DISABLED = (
    "Web/API schedule-item mutation is disabled. "
    "Edit schedules/{channel}.yml on disk (continuous playout + XMLTV authority)."
)


@router.get("", response_model=List[ScheduleItemResponse])
def get_all_schedule_items(
    schedule_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Get all schedule items, optionally filtered by schedule_id (legacy DB)."""
    query = db.query(ScheduleItem)
    if schedule_id:
        query = query.filter(ScheduleItem.schedule_id == schedule_id)
    return query.order_by(ScheduleItem.index).all()


@router.get("/{item_id}", response_model=ScheduleItemResponse)
def get_schedule_item(item_id: int, db: Session = Depends(get_db)):
    """Get schedule item by ID (legacy DB)."""
    item = db.query(ScheduleItem).filter(ScheduleItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Schedule item not found")
    return item


@router.post("", response_model=ScheduleItemResponse, status_code=status.HTTP_201_CREATED)
def create_schedule_item(item: ScheduleItemCreate, db: Session = Depends(get_db)):
    """Disabled — continuous playout uses schedules/{n}.yml only."""
    raise HTTPException(status_code=status.HTTP_410_GONE, detail=_MUTATE_DISABLED)


@router.put("/{item_id}", response_model=ScheduleItemResponse)
def update_schedule_item(
    item_id: int,
    item: ScheduleItemUpdate,
    db: Session = Depends(get_db),
):
    """Disabled — edit schedules/{n}.yml on disk instead."""
    raise HTTPException(status_code=status.HTTP_410_GONE, detail=_MUTATE_DISABLED)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule_item(item_id: int, db: Session = Depends(get_db)):
    """Disabled — edit schedules/{n}.yml on disk instead."""
    raise HTTPException(status_code=status.HTTP_410_GONE, detail=_MUTATE_DISABLED)


@router.post("/{item_id}/move", response_model=ScheduleItemResponse)
def move_schedule_item(
    item_id: int,
    direction: str = Query(..., description="Direction to move: 'up' or 'down'"),
    db: Session = Depends(get_db),
):
    """Disabled — edit schedules/{n}.yml on disk instead."""
    raise HTTPException(status_code=status.HTTP_410_GONE, detail=_MUTATE_DISABLED)
