"""Watermark API endpoints"""

import logging
import shutil
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from pathlib import Path

from ..database import get_db, Watermark
from ..api.schemas import (
    WatermarkCreate, WatermarkUpdate, WatermarkResponse
)
from ..config import config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/watermarks", tags=["Watermarks"])

# Directory for storing watermark images
# Use absolute path relative to project root
WATERMARKS_DIR = Path(__file__).parent.parent.parent / "data" / "watermarks"
WATERMARKS_DIR.mkdir(parents=True, exist_ok=True)


@router.get("", response_model=List[WatermarkResponse])
def get_all_watermarks(db: Session = Depends(get_db)):
    """Get all watermarks"""
    return db.query(Watermark).order_by(Watermark.name).all()


@router.get("/{watermark_id}", response_model=WatermarkResponse)
def get_watermark(watermark_id: int, db: Session = Depends(get_db)):
    """Get watermark by ID"""
    watermark = db.query(Watermark).filter(Watermark.id == watermark_id).first()
    if not watermark:
        raise HTTPException(status_code=404, detail="Watermark not found")
    return watermark


@router.post("", response_model=WatermarkResponse, status_code=status.HTTP_201_CREATED)
def create_watermark(watermark: WatermarkCreate, db: Session = Depends(get_db)):
    """Create a new watermark"""
    # Check if watermark with same name exists
    existing = db.query(Watermark).filter(Watermark.name == watermark.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Watermark with this name already exists")
    
    db_watermark = Watermark(**watermark.dict(exclude={"image"}))
    db.add(db_watermark)
    db.commit()
    db.refresh(db_watermark)
    return db_watermark


@router.put("/{watermark_id}", response_model=WatermarkResponse)
def update_watermark(watermark_id: int, watermark_update: WatermarkUpdate, db: Session = Depends(get_db)):
    """Update a watermark"""
    watermark = db.query(Watermark).filter(Watermark.id == watermark_id).first()
    if not watermark:
        raise HTTPException(status_code=404, detail="Watermark not found")
    
    # Check if name is being changed and conflicts with another watermark
    if watermark_update.name and watermark_update.name != watermark.name:
        existing = db.query(Watermark).filter(Watermark.name == watermark_update.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Watermark with this name already exists")
    
    # Update fields
    for field, value in watermark_update.dict(exclude_unset=True, exclude={"image"}).items():
        setattr(watermark, field, value)
    
    db.commit()
    db.refresh(watermark)
    return watermark


@router.delete("/{watermark_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_watermark(watermark_id: int, db: Session = Depends(get_db)):
    """Delete a watermark"""
    watermark = db.query(Watermark).filter(Watermark.id == watermark_id).first()
    if not watermark:
        raise HTTPException(status_code=404, detail="Watermark not found")
    
    # Check if watermark is used by any channels
    from ..database.models import Channel
    channels_using = db.query(Channel).filter(Channel.watermark_id == watermark_id).count()
    if channels_using > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete watermark: it is used by {channels_using} channel(s)"
        )
    
    # Delete image file if it exists
    if watermark.image:
        image_path = WATERMARKS_DIR / watermark.image
        if image_path.exists():
            try:
                image_path.unlink()
                logger.info(f"Deleted watermark image: {image_path}")
            except Exception as e:
                logger.warning(f"Failed to delete watermark image {image_path}: {e}")
    
    db.delete(watermark)
    db.commit()
    return None


@router.post("/{watermark_id}/image", response_model=WatermarkResponse)
async def upload_watermark_image(
    watermark_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload or update watermark image"""
    watermark = db.query(Watermark).filter(Watermark.id == watermark_id).first()
    if not watermark:
        raise HTTPException(status_code=404, detail="Watermark not found")
    
    # Validate file type
    allowed_types = ["image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: {', '.join(allowed_types)}"
        )
    
    # Generate filename
    file_ext = Path(file.filename).suffix if file.filename else ".png"
    if not file_ext:
        file_ext = ".png"
    filename = f"watermark_{watermark_id}{file_ext}"
    file_path = WATERMARKS_DIR / filename
    
    # Delete old image if it exists
    if watermark.image:
        old_path = WATERMARKS_DIR / watermark.image
        if old_path.exists() and old_path != file_path:
            try:
                old_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete old watermark image: {e}")
    
    # Save new image
    try:
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # Update watermark record
        watermark.image = filename
        watermark.original_content_type = file.content_type
        db.commit()
        db.refresh(watermark)
        
        logger.info(f"Uploaded watermark image: {file_path}")
        return watermark
        
    except Exception as e:
        logger.error(f"Failed to save watermark image: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save image: {str(e)}")


@router.delete("/{watermark_id}/image", response_model=WatermarkResponse)
def delete_watermark_image(watermark_id: int, db: Session = Depends(get_db)):
    """Delete watermark image"""
    watermark = db.query(Watermark).filter(Watermark.id == watermark_id).first()
    if not watermark:
        raise HTTPException(status_code=404, detail="Watermark not found")
    
    if not watermark.image:
        raise HTTPException(status_code=400, detail="Watermark has no image")
    
    # Delete image file
    image_path = WATERMARKS_DIR / watermark.image
    if image_path.exists():
        try:
            image_path.unlink()
            logger.info(f"Deleted watermark image: {image_path}")
        except Exception as e:
            logger.warning(f"Failed to delete watermark image {image_path}: {e}")
    
    # Update watermark record
    watermark.image = None
    watermark.original_content_type = None
    db.commit()
    db.refresh(watermark)
    
    return watermark

