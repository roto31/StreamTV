"""API authentication checker for StreamTV"""

from fastapi import Depends, HTTPException, Header, status
from typing import Optional
from ..config import config

async def verify_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """
    Verify API key for protected endpoints.
    
    Usage:
        @router.post("/endpoint", dependencies=[Depends(verify_api_key)])
    """
    if config.security.api_key_required:
        if not config.security.access_token:
            # If API key required but not configured, allow access with warning
            # In production, this should be an error
            return True
        
        if not x_api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required. Provide X-API-Key header.",
                headers={"WWW-Authenticate": "ApiKey"},
            )
        
        if x_api_key != config.security.access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "ApiKey"},
            )
    
    return True
