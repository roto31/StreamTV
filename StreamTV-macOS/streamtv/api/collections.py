"""Collections API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db, Collection, CollectionItem, MediaItem
from ..api.schemas import CollectionCreate, CollectionResponse

router = APIRouter(prefix="/collections", tags=["Collections"])


@router.get("", response_model=List[CollectionResponse])
def get_all_collections(db: Session = Depends(get_db)):
    """Get all collections"""
    collections = db.query(Collection).all()
    return collections


@router.get("/{collection_id}", response_model=CollectionResponse)
def get_collection(collection_id: int, db: Session = Depends(get_db)):
    """Get collection by ID"""
    collection = db.query(Collection).filter(Collection.id == collection_id).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


@router.post("", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
def create_collection(collection: CollectionCreate, db: Session = Depends(get_db)):
    """Create a new collection"""
    # Check if name already exists
    existing = db.query(Collection).filter(Collection.name == collection.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Collection name already exists")
    
    db_collection = Collection(**collection.dict())
    db.add(db_collection)
    db.commit()
    db.refresh(db_collection)
    return db_collection


@router.post("/{collection_id}/items/{media_id}", status_code=status.HTTP_201_CREATED)
def add_item_to_collection(collection_id: int, media_id: int, db: Session = Depends(get_db)):
    """Add media item to collection"""
    collection = db.query(Collection).filter(Collection.id == collection_id).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    media_item = db.query(MediaItem).filter(MediaItem.id == media_id).first()
    if not media_item:
        raise HTTPException(status_code=404, detail="Media item not found")
    
    # Check if already in collection
    existing = db.query(CollectionItem).filter(
        CollectionItem.collection_id == collection_id,
        CollectionItem.media_item_id == media_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Item already in collection")
    
    # Get max order
    max_order = db.query(CollectionItem).filter(
        CollectionItem.collection_id == collection_id
    ).count()
    
    collection_item = CollectionItem(
        collection_id=collection_id,
        media_item_id=media_id,
        order=max_order
    )
    db.add(collection_item)
    db.commit()
    return {"message": "Item added to collection"}


@router.delete("/{collection_id}/items/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_item_from_collection(collection_id: int, media_id: int, db: Session = Depends(get_db)):
    """Remove media item from collection"""
    collection_item = db.query(CollectionItem).filter(
        CollectionItem.collection_id == collection_id,
        CollectionItem.media_item_id == media_id
    ).first()
    if not collection_item:
        raise HTTPException(status_code=404, detail="Item not found in collection")
    
    db.delete(collection_item)
    db.commit()
    return None


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection(collection_id: int, db: Session = Depends(get_db)):
    """Delete a collection"""
    collection = db.query(Collection).filter(Collection.id == collection_id).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    db.delete(collection)
    db.commit()
    return None
