"""Resolution API endpoints"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db, Resolution
from ..api.schemas import ResolutionCreate, ResolutionUpdate, ResolutionResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resolutions", tags=["Resolutions"])


@router.get("", response_model=List[ResolutionResponse])
def get_all_resolutions(db: Session = Depends(get_db)):
    """Get all resolutions"""
    return db.query(Resolution).order_by(Resolution.width, Resolution.height).all()


@router.get("/{resolution_id}", response_model=ResolutionResponse)
def get_resolution(resolution_id: int, db: Session = Depends(get_db)):
    """Get resolution by ID"""
    resolution = db.query(Resolution).filter(Resolution.id == resolution_id).first()
    if not resolution:
        raise HTTPException(status_code=404, detail="Resolution not found")
    return resolution


@router.post("", response_model=ResolutionResponse, status_code=status.HTTP_201_CREATED)
def create_resolution(resolution: ResolutionCreate, db: Session = Depends(get_db)):
    """Create a new resolution"""
    # Check if resolution with same name exists
    existing = db.query(Resolution).filter(Resolution.name == resolution.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Resolution with this name already exists")
    
    db_resolution = Resolution(**resolution.dict())
    db.add(db_resolution)
    db.commit()
    db.refresh(db_resolution)
    return db_resolution


@router.put("/{resolution_id}", response_model=ResolutionResponse)
def update_resolution(resolution_id: int, resolution_update: ResolutionUpdate, db: Session = Depends(get_db)):
    """Update a resolution"""
    resolution = db.query(Resolution).filter(Resolution.id == resolution_id).first()
    if not resolution:
        raise HTTPException(status_code=404, detail="Resolution not found")
    
    # Check if name is being changed and conflicts with another resolution
    if resolution_update.name and resolution_update.name != resolution.name:
        existing = db.query(Resolution).filter(Resolution.name == resolution_update.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Resolution with this name already exists")
    
    # Update fields
    for field, value in resolution_update.dict(exclude_unset=True).items():
        setattr(resolution, field, value)
    
    db.commit()
    db.refresh(resolution)
    return resolution


@router.delete("/{resolution_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resolution(resolution_id: int, db: Session = Depends(get_db)):
    """Delete a resolution"""
    resolution = db.query(Resolution).filter(Resolution.id == resolution_id).first()
    if not resolution:
        raise HTTPException(status_code=404, detail="Resolution not found")
    
    # Check if resolution is used by any FFmpeg profiles
    from ..database.models import FFmpegProfile
    profiles_using = db.query(FFmpegProfile).filter(FFmpegProfile.resolution_id == resolution_id).count()
    if profiles_using > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete resolution: it is used by {profiles_using} FFmpeg profile(s)"
        )
    
    # Don't allow deleting built-in resolutions
    if not resolution.is_custom:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete built-in resolution"
        )
    
    db.delete(resolution)
    db.commit()
    return None

