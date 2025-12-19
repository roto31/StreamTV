"""API endpoints for importing channels from YAML"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pathlib import Path
import tempfile
import shutil
from typing import List, Optional
import yaml
import logging
try:
    import magic
except ImportError:
    magic = None  # Optional dependency; handled gracefully
import os

logger = logging.getLogger(__name__)

from ..database import get_db
from ..importers import import_channels_from_yaml
from ..api.schemas import ChannelResponse
from ..validation import YAMLValidator, ValidationError
from ..utils.yaml_to_json import yaml_to_json

router = APIRouter(prefix="/import", tags=["Import"])

# Maximum file size: 5 MB
MAX_FILE_SIZE = 5 * 1024 * 1024

# Allowed MIME types for YAML files
ALLOWED_MIME_TYPES = {
    'text/yaml',
    'text/x-yaml',
    'application/x-yaml',
    'application/yaml',
    'text/plain'  # Some systems report YAML as text/plain
}

# Allowed file extensions
ALLOWED_EXTENSIONS = {'.yaml', '.yml'}


def validate_file_upload(file: UploadFile) -> None:
    """Validate uploaded file for security."""
    # Check filename
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    
    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed extensions: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Check for path traversal attempts
    if '..' in file.filename or '/' in file.filename or '\\' in file.filename:
        raise HTTPException(status_code=400, detail="Invalid filename: path traversal detected")
    
    # Check content type if provided
    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        logger.warning(f"Unexpected content type: {file.content_type} for file {file.filename}")


def validate_file_content(file_path: Path) -> None:
    """Validate file content for security."""
    # Check file size
    file_size = file_path.stat().st_size
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large: {file_size} bytes (max {MAX_FILE_SIZE} bytes)"
        )
    
    if file_size == 0:
        raise HTTPException(status_code=400, detail="File is empty")
    
    # Try to detect MIME type using python-magic if available
    try:
        import magic
        mime_type = magic.from_file(str(file_path), mime=True)
        if mime_type not in ALLOWED_MIME_TYPES:
            logger.warning(f"File MIME type mismatch: {mime_type} for {file_path}")
    except ImportError:
        # python-magic not available, skip MIME type check
        pass
    except Exception as e:
        logger.debug(f"Could not detect MIME type: {e}")
    
    # Validate YAML syntax and safety
    try:
        content = file_path.read_text(encoding='utf-8')
        # Check for potentially dangerous YAML tags
        if '!!python' in content or '!!python/object' in content:
            raise HTTPException(
                status_code=400,
                detail="YAML file contains unsafe Python object tags"
            )
        
        # Parse with safe loader
        yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML syntax: {e}")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File encoding error: file must be UTF-8 encoded")


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
    
    Security: File is validated for type, size, and content before processing.
    """
    # Validate file upload
    validate_file_upload(yaml_file)
    
    # Save uploaded file temporarily
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.yaml') as tmp_file:
            # Read file in chunks to prevent memory issues
            chunk_size = 8192
            total_size = 0
            while True:
                chunk = await yaml_file.read(chunk_size)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > MAX_FILE_SIZE:
                    tmp_file.close()
                    os.unlink(tmp_file.name)
                    raise HTTPException(
                        status_code=400,
                        detail=f"File too large (max {MAX_FILE_SIZE} bytes)"
                    )
                tmp_file.write(chunk)
        tmp_path = Path(tmp_file.name)
    
        # Validate file content
        validate_file_content(tmp_path)
    
        # Validate if requested
        if validate:
            try:
                validator = YAMLValidator()
                result = validator.validate_channel_file(tmp_path)
                if not result.get('valid', False):
                    errors = result.get('errors', [])
                    error_detail = f"Validation failed: {', '.join(errors[:5])}"  # Show first 5 errors
                    if len(errors) > 5:
                        error_detail += f" (and {len(errors) - 5} more errors)"
                    raise HTTPException(
                        status_code=400,
                        detail=error_detail
                    )
            except ValidationError as e:
                # Include detailed errors in the response
                error_detail = e.message
                if hasattr(e, 'errors') and e.errors:
                    error_detail += "\n\nDetailed errors:\n" + "\n".join(f"  - {err}" for err in e.errors[:10])  # Limit to first 10 errors
                raise HTTPException(
                    status_code=400,
                    detail=error_detail
                )
        
        # Import channels
        channels = await import_channels_from_yaml(tmp_path, validate=validate)
        
        logger.info(f"Successfully imported {len(channels)} channels from {yaml_file.filename}")
        return channels
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing channels from {yaml_file.filename}: {e}", exc_info=True)
        raise HTTPException(
            status_code=400,
            detail=f"Error importing channels: {str(e)}"
        )
    finally:
        # Clean up temporary file securely
        if tmp_path and tmp_path.exists():
            try:
                # Overwrite file before deletion (security best practice)
                with open(tmp_path, 'wb') as f:
                    f.write(b'\x00' * min(tmp_path.stat().st_size, 1024))  # Overwrite first KB
                tmp_path.unlink()
            except Exception as e:
                logger.warning(f"Could not securely delete temporary file {tmp_path}: {e}")


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
    
    # Enforce size limit (5 MB) for path-based imports
    if yaml_path.stat().st_size > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="YAML file too large (max 5 MB)")

    # Basic YAML safety check to reject non-safe tags
    try:
        yaml.safe_load(yaml_path.read_text())
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {e}")

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
        channels = await import_channels_from_yaml(yaml_path, validate=validate)
        
        return channels
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error importing channels: {str(e)}"
        )

