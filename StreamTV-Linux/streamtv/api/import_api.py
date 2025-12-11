"""API endpoints for importing channels from YAML"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pathlib import Path
import tempfile
import shutil
from typing import List, Optional

from ..database import get_db
from ..importers import import_channels_from_yaml
from ..api.schemas import ChannelResponse
from ..validation import YAMLValidator, ValidationError
from ..utils.yaml_to_json import yaml_to_json

router = APIRouter(prefix="/import", tags=["Import"])


@router.post("/channels/yaml", response_model=List[ChannelResponse])
async def import_channels_yaml(
    yaml_file: UploadFile = File(...),
    validate: bool = Query(True, description="Validate YAML against JSON schema"),
    db: Session = Depends(get_db)
):
    """
    Import channels from uploaded YAML file.
    
    Creates channels, collections, playlists, and media items from YAML configuration.
    Optionally validates the YAML file against JSON schema before import.
    """
    if not yaml_file.filename.endswith(('.yaml', '.yml')):
        raise HTTPException(
            status_code=400,
            detail="File must be a YAML file (.yaml or .yml)"
        )
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix='.yaml') as tmp_file:
        shutil.copyfileobj(yaml_file.file, tmp_file)
        tmp_path = Path(tmp_file.name)
    
    try:
        # Validate if requested
        if validate:
            try:
                validator = YAMLValidator()
                result = validator.validate_channel_file(tmp_path)
                if not result.get('valid', False):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Validation failed: {', '.join(result.get('errors', []))}"
                    )
            except ValidationError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Validation error: {e.message}"
                )
        
        # Import channels
        channels = import_channels_from_yaml(tmp_path, validate=validate)
        
        return channels
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error importing channels: {str(e)}"
        )
    finally:
        # Clean up temporary file
        if tmp_path.exists():
            tmp_path.unlink()


@router.post("/channels/yaml/path", response_model=List[ChannelResponse])
async def import_channels_yaml_path(
    file_path: str,
    validate: bool = Query(True, description="Validate YAML against JSON schema"),
    db: Session = Depends(get_db)
):
    """
    Import channels from YAML file path.
    
    Creates channels, collections, playlists, and media items from YAML configuration.
    Optionally validates the YAML file against JSON schema before import.
    """
    yaml_path = Path(file_path)
    
    if not yaml_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"YAML file not found: {file_path}"
        )
    
    if not yaml_path.suffix in ('.yaml', '.yml'):
        raise HTTPException(
            status_code=400,
            detail="File must be a YAML file (.yaml or .yml)"
        )
    
    try:
        # Validate if requested
        if validate:
            try:
                validator = YAMLValidator()
                result = validator.validate_channel_file(yaml_path)
                if not result.get('valid', False):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Validation failed: {', '.join(result.get('errors', []))}"
                    )
            except ValidationError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Validation error: {e.message}"
                )
        
        # Import channels
        channels = import_channels_from_yaml(yaml_path, validate=validate)
        
        return channels
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error importing channels: {str(e)}"
        )

