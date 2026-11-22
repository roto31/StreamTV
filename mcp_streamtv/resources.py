"""StreamTV documentation and example resources for MCP server"""

from pathlib import Path
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Minimal examples for NL agents (not full fleet YAML)
_MINIMAL_YOUTUBE_EXAMPLE = """# Minimal YouTube unified channel (illustrative)
config_revision: 1
channel:
  number: "1986"
  name: Example Music
  group: Music
  playout_mode: continuous
  epg_sync_class: A
streams:
  - id: dQw4w9WgXcQ
    collection: Example Music
    type: music_video
    source: youtube
    url: https://www.youtube.com/watch?v=dQw4w9WgXcQ
    title: Example Video
    runtime: PT3M33S
schedule:
  name: Example Music
  content:
    - key: main
      collection: Example Music
      order: chronological
  sequence:
    - key: main-playlist
      items:
        - all: main
  playout:
    - sequence: main-playlist
    - repeat: true
"""

_MINIMAL_ARCHIVE_EXAMPLE = """# Minimal Archive.org unified channel (illustrative)
channel:
  number: "1954"
  name: Example Anthology
  group: Classic TV
  playout_mode: continuous
  epg_sync_class: C
streams:
  - id: example_archive_0001
    collection: Example Anthology
    type: episode
    source: archive_org
    url: https://archive.org/download/example-id/example.mp4
    title: Example Episode
    runtime: PT59M0S
schedule:
  name: Example Anthology
  media:
    preferred_extension: mp4
    mp4_only: true
  content:
    - key: main
      collection: Example Anthology
      order: chronological
  sequence:
    - key: main-playlist
      items:
        - all: main
  playout:
    - sequence: main-playlist
    - repeat: true
"""

_STREAM_ID_RULES = """# Stream id uniqueness (Issues 18–21)

Every stream `id` in inventory YAML must be **globally unique** across all `data/*.yaml` files.

- YouTube: 11-char video id is usually fine
- Archive.org: use a semantic unique slug (never bare collection id alone for multi-file items)
- Duplicates → wrong cache `.part` BUFFER HIT / Plex stop

Before import of hand-edited YAML:

```bash
./venv/bin/python scripts/ensure_unique_yaml_stream_ids.py --audit-only
```

Channel Builder assigns ids during resolve/build — prefer Builder for new channels.

# Archive.org URLs — never `.ia.mp4` (Issue 24)

- **Forbidden:** `*.ia.mp4` Internet Archive **derivative** URLs (bad/unusable Plex tunes).
- **Required:** canonical `https://archive.org/download/<id>/<file>.mp4` from item metadata.
- MCP `builder_add_links` and `playout_guards.validate_archive_stream_urls` both reject `.ia.mp4`.
- See `LESSONS_LEARNED.md` Issue 24.
"""


def get_project_root() -> Path:
    """Get project root directory"""
    current = Path(__file__).resolve().parent
    # mcp_streamtv/ → repo root
    if (current.parent / "streamtv").is_dir():
        return current.parent
    while current.name != "StreamTV" and current.parent != current:
        current = current.parent
        if (current / "streamtv").is_dir():
            return current
    return current


def load_resource(path: str) -> Optional[str]:
    """Load a resource file as text"""
    try:
        full_path = get_project_root() / path
        if full_path.exists():
            return full_path.read_text(encoding="utf-8")
        # Also try package-relative prompts
        pkg_path = Path(__file__).resolve().parent / path
        if pkg_path.exists():
            return pkg_path.read_text(encoding="utf-8")
        return None
    except Exception as e:
        logger.error(f"Error loading resource {path}: {e}")
        return None


def _intake_prompt_text() -> str:
    content = load_resource("prompts/channel_intake.md")
    if content:
        return content
    return (
        "Ask: search Archive.org and/or YouTube, or paste links? "
        "Then Builder draft → links → resolve → confirm → build."
    )


CHANNEL_INTAKE_PROMPT = _intake_prompt_text()


async def get_streamtv_api_docs() -> Dict[str, Any]:
    content = load_resource("docs/API.md")
    return {
        "name": "StreamTV API Documentation",
        "content": content or "Documentation not found",
        "mimeType": "text/markdown",
    }


async def get_streamtv_config_example() -> Dict[str, Any]:
    content = load_resource("config.example.yaml")
    return {
        "name": "StreamTV Configuration Example",
        "content": content or "Configuration example not found",
        "mimeType": "text/yaml",
    }


async def get_streamtv_schedule_example(schedule_name: str = "80") -> Dict[str, Any]:
    content = load_resource(f"schedules/{schedule_name}.yml")
    return {
        "name": f"StreamTV Schedule Example: {schedule_name}",
        "content": content or f"Schedule example {schedule_name}.yml not found",
        "mimeType": "text/yaml",
    }


async def get_streamtv_installation_guide() -> Dict[str, Any]:
    content = load_resource("docs/INSTALLATION.md")
    return {
        "name": "StreamTV Installation Guide",
        "content": content or "Installation guide not found",
        "mimeType": "text/markdown",
    }


async def get_streamtv_quickstart() -> Dict[str, Any]:
    content = load_resource("docs/QUICKSTART.md")
    return {
        "name": "StreamTV Quick Start Guide",
        "content": content or "Quick start guide not found",
        "mimeType": "text/markdown",
    }


async def get_streamtv_schedules_guide() -> Dict[str, Any]:
    content = load_resource("docs/SCHEDULES.md")
    return {
        "name": "StreamTV Schedules Guide",
        "content": content or "Schedules guide not found",
        "mimeType": "text/markdown",
    }


async def get_channel_builder_docs() -> Dict[str, Any]:
    content = load_resource("docs/channel-builder.md")
    return {
        "name": "Channel Builder Guide",
        "content": content or "channel-builder.md not found",
        "mimeType": "text/markdown",
    }


async def get_import_vs_builder() -> Dict[str, Any]:
    content = load_resource("docs/guides/IMPORT_VS_BUILDER.md")
    return {
        "name": "Import vs Channel Builder",
        "content": content or "IMPORT_VS_BUILDER.md not found",
        "mimeType": "text/markdown",
    }


async def get_unified_channel_schema() -> Dict[str, Any]:
    content = load_resource("schemas/unified_channel.schema.json")
    return {
        "name": "Unified Channel JSON Schema",
        "content": content or "unified_channel.schema.json not found",
        "mimeType": "application/json",
    }


async def get_channel_intake_prompt() -> Dict[str, Any]:
    return {
        "name": "Channel Creator Intake Prompt",
        "content": CHANNEL_INTAKE_PROMPT,
        "mimeType": "text/markdown",
    }


async def get_minimal_youtube_example() -> Dict[str, Any]:
    return {
        "name": "Minimal YouTube Unified Channel Example",
        "content": _MINIMAL_YOUTUBE_EXAMPLE,
        "mimeType": "text/yaml",
    }


async def get_minimal_archive_example() -> Dict[str, Any]:
    return {
        "name": "Minimal Archive.org Unified Channel Example",
        "content": _MINIMAL_ARCHIVE_EXAMPLE,
        "mimeType": "text/yaml",
    }


async def get_stream_id_rules() -> Dict[str, Any]:
    return {
        "name": "Stream ID Uniqueness Rules",
        "content": _STREAM_ID_RULES,
        "mimeType": "text/markdown",
    }


async def get_channel_creator_mcp_guide() -> Dict[str, Any]:
    content = load_resource("docs/guides/CHANNEL_CREATOR_MCP.md")
    return {
        "name": "Channel Creator MCP Host Guide",
        "content": content or "CHANNEL_CREATOR_MCP.md not found",
        "mimeType": "text/markdown",
    }


# Resource registry
RESOURCES = {
    "streamtv://docs/api": get_streamtv_api_docs,
    "streamtv://docs/config-example": get_streamtv_config_example,
    "streamtv://docs/installation": get_streamtv_installation_guide,
    "streamtv://docs/quickstart": get_streamtv_quickstart,
    "streamtv://docs/schedules": get_streamtv_schedules_guide,
    "streamtv://docs/channel-builder": get_channel_builder_docs,
    "streamtv://docs/import-vs-builder": get_import_vs_builder,
    "streamtv://docs/channel-creator-mcp": get_channel_creator_mcp_guide,
    "streamtv://schema/unified-channel": get_unified_channel_schema,
    "streamtv://prompts/channel-intake": get_channel_intake_prompt,
    "streamtv://examples/unified/youtube-minimal": get_minimal_youtube_example,
    "streamtv://examples/unified/archive-minimal": get_minimal_archive_example,
    "streamtv://rules/stream-ids": get_stream_id_rules,
    "streamtv://examples/schedule/80": lambda: get_streamtv_schedule_example("80"),
    "streamtv://examples/schedule/magnum-pi": lambda: get_streamtv_schedule_example(
        "magnum-pi-schedule"
    ),
}


async def list_resources() -> list:
    """List all available StreamTV resources"""
    descriptions = {
        "streamtv://prompts/channel-intake": "Search vs paste-links intake prompt for NL channel creation",
        "streamtv://schema/unified-channel": "JSON Schema for data/unified/{N}.channel.yaml",
        "streamtv://docs/channel-builder": "Channel Builder operator guide",
        "streamtv://docs/channel-creator-mcp": "Host wiring for Cursor, Claude Desktop, local models",
        "streamtv://rules/stream-ids": "Global stream id uniqueness rules",
    }
    out = []
    for uri in RESOURCES.keys():
        mime = "text/markdown"
        if "schema" in uri:
            mime = "application/json"
        elif "example" in uri or "config" in uri:
            mime = "text/yaml" if "schedule" in uri or "unified" in uri or "config" in uri else mime
        out.append(
            {
                "uri": uri,
                "name": uri.split("://")[-1].replace("/", " ").title(),
                "description": descriptions.get(
                    uri, f"StreamTV {uri.split('://')[-1]}"
                ),
                "mimeType": mime,
            }
        )
    return out


async def get_resource(uri: str) -> Optional[Dict[str, Any]]:
    """Get a resource by URI"""
    if uri in RESOURCES:
        return await RESOURCES[uri]()
    return None
