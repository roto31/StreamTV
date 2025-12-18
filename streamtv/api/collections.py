"""Collections API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Optional

from ..database import get_db, Collection, CollectionItem, MediaItem, Schedule
from ..api.schemas import CollectionCreate, CollectionResponse

router = APIRouter(prefix="/collections", tags=["Collections"])


def _extract_olympics_key(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    import re
    m = re.match(r"^(?:mn\s+)?(\d{4}\s+Winter\s+Olympics)", name, re.IGNORECASE)
    if not m:
        return None
    return " ".join(m.group(1).split()).strip()


def _extract_day_number(name: Optional[str]) -> int:
    if not name:
        return 0
    import re
    m = re.search(r"Day\s*(\d{1,2})", name, re.IGNORECASE)
    return int(m.group(1)) if m else 0


def _extract_base_olympics_name(name: Optional[str]) -> Optional[str]:
    """Extract base Olympics name (e.g., '1980 Winter Olympics' from '1980 Winter Olympics - Day 1')"""
    if not name:
        return None
    import re
    # Match patterns like "1980 Winter Olympics - Day 1" or "MN 1980 Winter Olympics - Day 1"
    match = re.match(r"^(?:mn\s+)?(\d{4}\s+Winter\s+Olympics)(?:\s*-\s*Day\s*\d+)?", name, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


@router.get("", response_model=List[CollectionResponse])
def get_all_collections(db: Session = Depends(get_db)):
    """Get all collections, including consolidated virtual Winter Olympics groups"""
    import logging
    logger = logging.getLogger(__name__)
    
    orm_collections: List[Collection] = db.query(Collection).all()
    logger.info(f"Found {len(orm_collections)} collections in database")
    
    # Log collection types for debugging
    for col in orm_collections:
        collection_type_value = col.collection_type.value if hasattr(col.collection_type, 'value') else str(col.collection_type)
        logger.debug(f"Collection: id={col.id}, name={col.name}, collection_type={collection_type_value}, search_query={col.search_query}")

    # Group potential Olympics day collections
    olympics_groups: Dict[str, Dict] = {}
    passthrough: List[Collection] = []

    for col in orm_collections:
        key = _extract_olympics_key(col.name)
        if not key:
            passthrough.append(col)
            continue
        group = olympics_groups.get(key)
        if not group:
            group = {
                "key": key,
                "collections": [],
                "items": [],
                "earliest_created": col.created_at,
                "latest_updated": col.updated_at,
            }
            olympics_groups[key] = group

        group["collections"].append(col)
        if col.created_at and (group["earliest_created"] is None or col.created_at < group["earliest_created"]):
            group["earliest_created"] = col.created_at
        if col.updated_at and (group["latest_updated"] is None or col.updated_at > group["latest_updated"]):
            group["latest_updated"] = col.updated_at

        day_num = _extract_day_number(col.name)
        for item in (col.items or []):
            group["items"].append({
                "item": item,
                "day": day_num,
                "source": col.name,
            })

    consolidated: List[CollectionResponse] = []
    for key, group in olympics_groups.items():
        if len(group["collections"]) <= 1:
            # Not actually multiple day collections; pass through the single ORM collection
            passthrough.append(group["collections"][0])
            continue

        # Sort items by day then original order
        sorted_items = sorted(group["items"], key=lambda x: (x["day"], getattr(x["item"], "order", 0)))

        # Build pydantic CollectionItemResponse list from ORM items but with new sequential order
        consolidated_items = []
        for idx, wrapped in enumerate(sorted_items):
            itm: CollectionItem = wrapped["item"]
            # Ensure media_item relationship is loaded
            _ = itm.media_item
            consolidated_items.append(
                CollectionItem(
                    id=itm.id,
                    collection_id=0,  # virtual
                    media_item_id=itm.media_item_id,
                    order=idx,
                )
            )

        # Convert the temp CollectionItem ORM objects to Pydantic via response model
        items_response = []
        for citem in consolidated_items:
            # Attach media_item for serialization
            citem.media_item = db.query(MediaItem).filter(MediaItem.id == citem.media_item_id).first()
            items_response.append(citem)

        virtual = Collection(
            id=0,
            name=key,
            description=f"{len(group['collections'])} day collections consolidated into a single view",
            created_at=group["earliest_created"],
            updated_at=group["latest_updated"],
        )
        virtual.items = items_response  # type: ignore

        # Create pydantic response with virtual flags
        resp = CollectionResponse(
            id=virtual.id,
            name=virtual.name,
            description=virtual.description,
            created_at=virtual.created_at,
            updated_at=virtual.updated_at,
            items=[
                # Convert ORM CollectionItem to Pydantic by leveraging Config.from_attributes
                # FastAPI will handle conversion, but we pre-materialize media_item
                {
                    "id": i.id,
                    "media_item_id": i.media_item_id,
                    "order": i.order,
                    "media_item": i.media_item,
                }
                for i in items_response
            ],
            is_virtual=True,
            source_collections=[c.name for c in group["collections"]],
        )
        consolidated.append(resp)

    # Combine consolidated virtual groups with passthrough real collections
    final_list: List[CollectionResponse] = consolidated + orm_collections_to_responses(passthrough)
    final_list.sort(key=lambda c: c.name or "")
    return final_list


def orm_collections_to_responses(cols: List[Collection]) -> List[CollectionResponse]:
    import logging
    logger = logging.getLogger(__name__)
    responses: List[CollectionResponse] = []
    for col in cols:
        # Ensure media_item is loaded for each item
        for it in (col.items or []):
            _ = it.media_item
        
        # Log collection type for debugging
        collection_type_value = col.collection_type.value if hasattr(col.collection_type, 'value') else str(col.collection_type)
        logger.debug(f"Serializing collection: id={col.id}, name={col.name}, collection_type={collection_type_value}")
        
        # FastAPI/Pydantic will automatically convert ORM to response model
        # The enum should be serialized to its string value automatically
        responses.append(col)
    return responses


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
    import logging
    logger = logging.getLogger(__name__)
    
    # Check if name already exists
    existing = db.query(Collection).filter(Collection.name == collection.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Collection name already exists")
    
    # Log the incoming collection data
    logger.info(f"Creating collection: name={collection.name}, collection_type={collection.collection_type}, search_query={collection.search_query}")
    
    # Convert collection_type string to enum if needed
    collection_dict = collection.dict()
    if collection_dict.get('collection_type'):
        # Ensure collection_type is lowercase to match enum values
        collection_type_str = collection_dict['collection_type'].lower()
        from ..database.models import CollectionTypeEnum
        try:
            # Convert string to enum
            collection_dict['collection_type'] = CollectionTypeEnum(collection_type_str)
        except ValueError:
            logger.warning(f"Invalid collection_type '{collection_type_str}', defaulting to MANUAL")
            collection_dict['collection_type'] = CollectionTypeEnum.MANUAL
    
    db_collection = Collection(**collection_dict)
    db.add(db_collection)
    db.commit()
    db.refresh(db_collection)
    
    # Log the created collection
    collection_type_value = db_collection.collection_type.value if hasattr(db_collection.collection_type, 'value') else str(db_collection.collection_type)
    logger.info(f"Created collection: id={db_collection.id}, name={db_collection.name}, collection_type={db_collection.collection_type}, collection_type_value={collection_type_value}")
    
    # Verify the collection_type is set correctly
    if collection_type_value != collection_dict.get('collection_type', '').lower() if isinstance(collection_dict.get('collection_type'), str) else collection_type_value:
        logger.warning(f"Collection type mismatch! Expected: {collection_dict.get('collection_type')}, Got: {collection_type_value}")
    
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


@router.post("/consolidate", status_code=status.HTTP_200_OK)
def consolidate_collections(db: Session = Depends(get_db)):
    """
    Consolidate single-item collections that belong to the same channel.
    Groups collections by name pattern (e.g., "1980 Winter Olympics - Day 1", "1980 Winter Olympics - Day 2")
    and merges them into a single consolidated collection.
    """
    from sqlalchemy import func
    
    # Get all collections with their item counts
    collections_with_counts = db.query(
        Collection,
        func.count(CollectionItem.id).label('item_count')
    ).outerjoin(CollectionItem).group_by(Collection.id).all()
    
    # Find single-item collections
    single_item_collections = [
        col for col, count in collections_with_counts 
        if count == 1
    ]
    
    if not single_item_collections:
        return {"message": "No single-item collections found to consolidate", "consolidated": 0, "groups": []}
    
    # Group collections by name pattern (e.g., "1980 Winter Olympics - Day 1", "1980 Winter Olympics - Day 2")
    name_pattern_groups = {}
    for collection in single_item_collections:
        # Extract base name (e.g., "1980 Winter Olympics" from "1980 Winter Olympics - Day 1")
        base_name = _extract_base_olympics_name(collection.name)
        if base_name:
            if base_name not in name_pattern_groups:
                name_pattern_groups[base_name] = []
            name_pattern_groups[base_name].append(collection)
    
    consolidated_count = 0
    consolidated_groups = []
    
    # Process name pattern groups
    for base_name, collections in name_pattern_groups.items():
        if len(collections) <= 1:
            continue
        
        # Get all items from these collections, sorted by day number
        all_items = []
        for collection in collections:
            items = db.query(CollectionItem).filter(
                CollectionItem.collection_id == collection.id
            ).all()
            for item in items:
                day_num = _extract_day_number(collection.name)
                all_items.append({
                    'item': item,
                    'day': day_num,
                    'collection_name': collection.name
                })
        
        # Sort by day number
        all_items.sort(key=lambda x: (x['day'], x['item'].order))
        
        # Check if consolidated collection already exists
        existing = db.query(Collection).filter(Collection.name == base_name).first()
        
        if existing:
            # Add items to existing collection
            target_collection = existing
            max_order_result = db.query(func.max(CollectionItem.order)).filter(
                CollectionItem.collection_id == existing.id
            ).scalar()
            max_order = max_order_result if max_order_result is not None else 0
        else:
            # Create new consolidated collection
            target_collection = Collection(
                name=base_name,
                description=f"Consolidated from {len(collections)} day collections"
            )
            db.add(target_collection)
            db.flush()  # Get the ID
            max_order = 0
        
        # Move items to consolidated collection
        for idx, wrapped_item in enumerate(all_items):
            item = wrapped_item['item']
            new_item = CollectionItem(
                collection_id=target_collection.id,
                media_item_id=item.media_item_id,
                order=max_order + idx
            )
            db.add(new_item)
        
        # Update schedules to point to consolidated collection
        for collection in collections:
            schedules = db.query(Schedule).filter(
                Schedule.collection_id == collection.id
            ).all()
            for schedule in schedules:
                schedule.collection_id = target_collection.id
        
        # Delete old collections
        for collection in collections:
            db.delete(collection)
        
        consolidated_count += len(collections)
        consolidated_groups.append({
            'base_name': base_name,
            'merged_collections': [c.name for c in collections],
            'items_count': len(all_items)
        })
    
    db.commit()
    
    return {
        "message": f"Consolidated {consolidated_count} collections into {len(consolidated_groups)} groups",
        "consolidated": consolidated_count,
        "groups": consolidated_groups
    }
