"""Schedules API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from pathlib import Path
import yaml

from ..database import get_db, Schedule, Channel
from ..api.schemas import ScheduleCreate, ScheduleResponse

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


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(schedule_id: int, db: Session = Depends(get_db)):
    """Delete a schedule"""
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    db.delete(schedule)
    db.commit()
    return None


@router.get("/files", response_model=List[Dict[str, Any]])
def get_schedule_files():
    """Get list of schedule YAML files from the schedules directory"""
    schedules_dir = Path("schedules")
    schedule_files = []
    
    if not schedules_dir.exists():
        return []
    
    for file_path in schedules_dir.glob("*.yml"):
        try:
            with open(file_path, 'r') as f:
                schedule_data = yaml.safe_load(f)
                channel_info = schedule_data.get('channel', {}) if schedule_data else {}
                schedule_files.append({
                    'file': file_path.name,
                    'name': channel_info.get('name', file_path.stem),
                    'channel_number': channel_info.get('number'),
                    'path': str(file_path)
                })
        except Exception as e:
            # If we can't parse the file, still include it in the list
            schedule_files.append({
                'file': file_path.name,
                'name': file_path.stem,
                'channel_number': None,
                'path': str(file_path)
            })
    
    # Also check for .yaml files
    for file_path in schedules_dir.glob("*.yaml"):
        try:
            with open(file_path, 'r') as f:
                schedule_data = yaml.safe_load(f)
                channel_info = schedule_data.get('channel', {}) if schedule_data else {}
                schedule_files.append({
                    'file': file_path.name,
                    'name': channel_info.get('name', file_path.stem),
                    'channel_number': channel_info.get('number'),
                    'path': str(file_path)
                })
        except Exception as e:
            schedule_files.append({
                'file': file_path.name,
                'name': file_path.stem,
                'channel_number': None,
                'path': str(file_path)
            })
    
    return schedule_files
