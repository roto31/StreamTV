"""ErsatzTV documentation resources for MCP server"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

from .config import config

logger = logging.getLogger(__name__)


def get_project_root() -> Path:
    """Get project root directory"""
    # Assuming this file is in mcp-ersatztv/, go up to project root
    current = Path(__file__).parent
    while current.name != "StreamTV" and current.parent != current:
        current = current.parent
    return current


def load_resource(path: str) -> Optional[str]:
    """Load a resource file as text"""
    try:
        project_root = get_project_root()
        full_path = project_root / path
        if full_path.exists():
            return full_path.read_text(encoding="utf-8")
        return None
    except Exception as e:
        logger.error(f"Error loading resource {path}: {e}")
        return None


async def get_ersatztv_integration_guide() -> Dict[str, Any]:
    """Get ErsatzTV integration guide"""
    content = load_resource("docs/ERSATZTV_INTEGRATION.md")
    if content:
        return {
            "name": "ErsatzTV Integration Guide",
            "content": content,
            "mimeType": "text/markdown"
        }
    return {
        "name": "ErsatzTV Integration Guide",
        "content": "Integration guide not found",
        "mimeType": "text/plain"
    }


async def get_ersatztv_comparison() -> Dict[str, Any]:
    """Get ErsatzTV comparison document"""
    content = load_resource("docs/COMPARISON.md")
    if content:
        return {
            "name": "StreamTV vs ErsatzTV Comparison",
            "content": content,
            "mimeType": "text/markdown"
        }
    return {
        "name": "StreamTV vs ErsatzTV Comparison",
        "content": "Comparison document not found",
        "mimeType": "text/plain"
    }


async def get_ersatztv_complete_integration() -> Dict[str, Any]:
    """Get ErsatzTV complete integration document"""
    content = load_resource("docs/ERSATZTV_COMPLETE_INTEGRATION.md")
    if content:
        return {
            "name": "ErsatzTV Complete Integration",
            "content": content,
            "mimeType": "text/markdown"
        }
    return {
        "name": "ErsatzTV Complete Integration",
        "content": "Complete integration document not found",
        "mimeType": "text/plain"
    }


async def get_ersatztv_schedules_guide() -> Dict[str, Any]:
    """Get ErsatzTV schedules guide"""
    content = load_resource("docs/SCHEDULES.md")
    if content:
        return {
            "name": "ErsatzTV Schedules Guide",
            "content": content,
            "mimeType": "text/markdown"
        }
    return {
        "name": "ErsatzTV Schedules Guide",
        "content": "Schedules guide not found",
        "mimeType": "text/plain"
    }


async def get_ersatztv_github_reference() -> Dict[str, Any]:
    """Get ErsatzTV GitHub repository reference"""
    return {
        "name": "ErsatzTV GitHub Repository",
        "content": f"ErsatzTV GitHub Repository: {config.github_url}\n\n"
                   f"Documentation: {config.wiki_url}\n\n"
                   f"ErsatzTV is a .NET/C# application for creating custom TV channels from local media.\n"
                   f"StreamTV provides similar functionality but streams directly from online sources.",
        "mimeType": "text/plain"
    }


async def get_ersatztv_wiki_reference() -> Dict[str, Any]:
    """Get ErsatzTV wiki reference"""
    return {
        "name": "ErsatzTV Wiki Documentation",
        "content": f"ErsatzTV Wiki: {config.wiki_url}\n\n"
                   f"The ErsatzTV wiki contains comprehensive documentation on:\n"
                   f"- API endpoints\n"
                   f"- Schedule configuration\n"
                   f"- Media library management\n"
                   f"- Playout settings\n"
                   f"- Integration with Plex, Emby, and Jellyfin",
        "mimeType": "text/plain"
    }


# Resource registry
RESOURCES = {
    "ersatztv://docs/integration": get_ersatztv_integration_guide,
    "ersatztv://docs/comparison": get_ersatztv_comparison,
    "ersatztv://docs/complete-integration": get_ersatztv_complete_integration,
    "ersatztv://docs/schedules": get_ersatztv_schedules_guide,
    "ersatztv://reference/github": get_ersatztv_github_reference,
    "ersatztv://reference/wiki": get_ersatztv_wiki_reference,
}


async def list_resources() -> list:
    """List all available ErsatzTV resources"""
    return [
        {
            "uri": uri,
            "name": uri.split("://")[-1].replace("/", " ").title(),
            "description": f"ErsatzTV {uri.split('://')[-1]}"
        }
        for uri in RESOURCES.keys()
    ]


async def get_resource(uri: str) -> Optional[Dict[str, Any]]:
    """Get a resource by URI"""
    if uri in RESOURCES:
        return await RESOURCES[uri]()
    return None

