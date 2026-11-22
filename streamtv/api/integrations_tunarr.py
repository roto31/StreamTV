"""StreamTV Tunarr hybrid status (non-bedrock).

Library browse / smart-collection proxies are parked under
``parked/tunarr-library-proxy/``. Production needs only reachability status
plus the ``/tuners`` HDHR/EPG path (``tuner_manager``).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from ..integrations.tunarr_client import TunarrClient
from ..integrations.tunarr_config import get_tunarr_base_url
from .auth_checker import verify_api_key

router = APIRouter(
    prefix="/integrations/tunarr",
    tags=["Tunarr Integration"],
    dependencies=[Depends(verify_api_key)],
)


@router.get("/status")
async def tunarr_status() -> dict[str, Any]:
    """Reachability and configured upstream URL."""
    base = get_tunarr_base_url()
    if not base:
        return {"configured": False, "reachable": False, "url": None}
    client = TunarrClient(base)
    health = await client.health()
    return {
        "configured": True,
        "url": base,
        "web_url": f"{base}/web",
        **health,
    }
