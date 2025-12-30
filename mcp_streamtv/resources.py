"""StreamTV documentation and example resources for MCP server"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def get_project_root() -> Path:
    """Get project root directory"""
    # Assuming this file is in mcp-streamtv/, go up to project root
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


async def get_streamtv_api_docs() -> Dict[str, Any]:
    """Get StreamTV API documentation"""
    content = load_resource("docs/API.md")
    if content:
        return {
            "name": "StreamTV API Documentation",
            "content": content,
            "mimeType": "text/markdown"
        }
    return {
        "name": "StreamTV API Documentation",
        "content": "Documentation not found",
        "mimeType": "text/plain"
    }


async def get_streamtv_config_example() -> Dict[str, Any]:
    """Get StreamTV configuration example"""
    content = load_resource("config.example.yaml")
    if content:
        return {
            "name": "StreamTV Configuration Example",
            "content": content,
            "mimeType": "text/yaml"
        }
    return {
        "name": "StreamTV Configuration Example",
        "content": "Configuration example not found",
        "mimeType": "text/plain"
    }


async def get_streamtv_schedule_example(schedule_name: str = "80") -> Dict[str, Any]:
    """Get a StreamTV schedule YAML example
    
    Args:
        schedule_name: Schedule file name without extension (default: "80")
    """
    content = load_resource(f"schedules/{schedule_name}.yml")
    if content:
        return {
            "name": f"StreamTV Schedule Example: {schedule_name}",
            "content": content,
            "mimeType": "text/yaml"
        }
    return {
        "name": f"StreamTV Schedule Example: {schedule_name}",
        "content": f"Schedule example {schedule_name}.yml not found",
        "mimeType": "text/plain"
    }


async def get_streamtv_installation_guide() -> Dict[str, Any]:
    """Get StreamTV installation guide"""
    content = load_resource("docs/INSTALLATION.md")
    if content:
        return {
            "name": "StreamTV Installation Guide",
            "content": content,
            "mimeType": "text/markdown"
        }
    return {
        "name": "StreamTV Installation Guide",
        "content": "Installation guide not found",
        "mimeType": "text/plain"
    }


async def get_streamtv_quickstart() -> Dict[str, Any]:
    """Get StreamTV quick start guide"""
    content = load_resource("docs/QUICKSTART.md")
    if content:
        return {
            "name": "StreamTV Quick Start Guide",
            "content": content,
            "mimeType": "text/markdown"
        }
    return {
        "name": "StreamTV Quick Start Guide",
        "content": "Quick start guide not found",
        "mimeType": "text/plain"
    }


async def get_streamtv_schedules_guide() -> Dict[str, Any]:
    """Get StreamTV schedules guide"""
    content = load_resource("docs/SCHEDULES.md")
    if content:
        return {
            "name": "StreamTV Schedules Guide",
            "content": content,
            "mimeType": "text/markdown"
        }
    return {
        "name": "StreamTV Schedules Guide",
        "content": "Schedules guide not found",
        "mimeType": "text/plain"
    }


# Resource registry
RESOURCES = {
    "streamtv://docs/api": get_streamtv_api_docs,
    "streamtv://docs/config-example": get_streamtv_config_example,
    "streamtv://docs/installation": get_streamtv_installation_guide,
    "streamtv://docs/quickstart": get_streamtv_quickstart,
    "streamtv://docs/schedules": get_streamtv_schedules_guide,
    "streamtv://examples/schedule/80": lambda: get_streamtv_schedule_example("80"),
    "streamtv://examples/schedule/magnum-pi": lambda: get_streamtv_schedule_example("magnum-pi-schedule"),
}


async def list_resources() -> list:
    """List all available StreamTV resources"""
    return [
        {
            "uri": uri,
            "name": uri.split("://")[-1].replace("/", " ").title(),
            "description": f"StreamTV {uri.split('://')[-1]}"
        }
        for uri in RESOURCES.keys()
    ]


async def get_resource(uri: str) -> Optional[Dict[str, Any]]:
    """Get a resource by URI"""
    if uri in RESOURCES:
        return await RESOURCES[uri]()
    return None

