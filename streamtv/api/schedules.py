"""Schedules API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from ..database import get_db, Schedule, Channel
from ..api.schemas import ScheduleCreate, ScheduleResponse, ScheduleUpdate
from ..config import config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/schedules", tags=["Schedules"])


@router.get("", response_model=List[ScheduleResponse])
def get_all_schedules(
    channel_id: int = None,
    db: Session = Depends(get_db)
):
    """Get all schedules"""
    query = db.query(Schedule)
    if channel_id:
        query = query.filter(Schedule.channel_id == channel_id)
    schedules = query.all()
    return schedules


@router.get("/{schedule_id}", response_model=ScheduleResponse)
def get_schedule(schedule_id: int, db: Session = Depends(get_db)):
    """Get schedule by ID"""
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
def create_schedule(schedule: ScheduleCreate, db: Session = Depends(get_db)):
    """Create a new schedule"""
    # Validate channel exists
    channel = db.query(Channel).filter(Channel.id == schedule.channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    db_schedule = Schedule(**schedule.dict())
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    return db_schedule


@router.put("/{schedule_id}", response_model=ScheduleResponse)
def update_schedule(schedule_id: int, schedule: ScheduleUpdate, db: Session = Depends(get_db)):
    """Update a schedule"""
    db_schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not db_schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    # Validate channel exists if changed
    update_data = schedule.dict(exclude_unset=True)
    if "channel_id" in update_data and update_data["channel_id"] != db_schedule.channel_id:
        channel = db.query(Channel).filter(Channel.id == update_data["channel_id"]).first()
        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found")
    
    for key, value in update_data.items():
        setattr(db_schedule, key, value)
    
    db.commit()
    db.refresh(db_schedule)
    return db_schedule


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(schedule_id: int, db: Session = Depends(get_db)):
    """Delete a schedule"""
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    db.delete(schedule)
    db.commit()
    return None
