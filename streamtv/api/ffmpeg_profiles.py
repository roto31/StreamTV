"""FFmpeg Profile API endpoints"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db, FFmpegProfile, Resolution
from ..api.schemas import (
    FFmpegProfileCreate, FFmpegProfileUpdate, FFmpegProfileResponse,
    HardwareAccelerationResponse
)
from ..transcoding.hardware import get_available_hardware_acceleration

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ffmpeg-profiles", tags=["FFmpeg Profiles"])


@router.get("", response_model=List[FFmpegProfileResponse])
def get_all_ffmpeg_profiles(db: Session = Depends(get_db)):
    """Get all FFmpeg profiles"""
    return db.query(FFmpegProfile).order_by(FFmpegProfile.name).all()


@router.get("/{profile_id}", response_model=FFmpegProfileResponse)
def get_ffmpeg_profile(profile_id: int, db: Session = Depends(get_db)):
    """Get FFmpeg profile by ID"""
    profile = db.query(FFmpegProfile).filter(FFmpegProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="FFmpeg profile not found")
    return profile


def _default_resolution_id(db: Session) -> int:
    """Seeded 1080p row when present; otherwise first resolution. Scale UI retired."""
    row = db.query(Resolution).filter(Resolution.name == "1080p").first()
    if row:
        return int(row.id)
    row = db.query(Resolution).order_by(Resolution.id).first()
    if not row:
        raise HTTPException(status_code=400, detail="No resolution seed rows in database")
    return int(row.id)


@router.post("", response_model=FFmpegProfileResponse, status_code=status.HTTP_201_CREATED)
def create_ffmpeg_profile(profile: FFmpegProfileCreate, db: Session = Depends(get_db)):
    """Create a new FFmpeg profile"""
    # Check if profile with same name exists
    existing = db.query(FFmpegProfile).filter(FFmpegProfile.name == profile.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="FFmpeg profile with this name already exists")

    data = profile.model_dump()
    resolution = db.query(Resolution).filter(Resolution.id == data.get("resolution_id")).first()
    if not resolution:
        data["resolution_id"] = _default_resolution_id(db)

    db_profile = FFmpegProfile(**data)
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    return db_profile


@router.put("/{profile_id}", response_model=FFmpegProfileResponse)
def update_ffmpeg_profile(profile_id: int, profile_update: FFmpegProfileUpdate, db: Session = Depends(get_db)):
    """Update an FFmpeg profile"""
    profile = db.query(FFmpegProfile).filter(FFmpegProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="FFmpeg profile not found")
    
    # Check if name is being changed and conflicts with another profile
    if profile_update.name and profile_update.name != profile.name:
        existing = db.query(FFmpegProfile).filter(FFmpegProfile.name == profile_update.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="FFmpeg profile with this name already exists")
    
    # Verify resolution if being changed
    if profile_update.resolution_id and profile_update.resolution_id != profile.resolution_id:
        resolution = db.query(Resolution).filter(Resolution.id == profile_update.resolution_id).first()
        if not resolution:
            raise HTTPException(status_code=400, detail="Resolution not found")
    
    # Update fields
    for field, value in profile_update.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    
    db.commit()
    db.refresh(profile)
    return profile


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ffmpeg_profile(profile_id: int, db: Session = Depends(get_db)):
    """Delete an FFmpeg profile"""
    profile = db.query(FFmpegProfile).filter(FFmpegProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="FFmpeg profile not found")
    
    # Check if profile is used by any channels
    from ..database.models import Channel
    channels_using = db.query(Channel).filter(Channel.ffmpeg_profile_id == profile_id).count()
    if channels_using > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete FFmpeg profile: it is used by {channels_using} channel(s)"
        )
    
    db.delete(profile)
    db.commit()
    return None


@router.get("/hardware-acceleration/available", response_model=HardwareAccelerationResponse)
def get_available_hardware_acceleration_types():
    """Get list of available hardware acceleration types"""
    available = get_available_hardware_acceleration()
    return HardwareAccelerationResponse(available=available)

