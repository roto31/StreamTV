"""Archive.org API documentation resources for MCP server"""

from typing import Dict, Any
import logging

from .config import config

logger = logging.getLogger(__name__)


async def get_archive_org_api_docs() -> Dict[str, Any]:
    """Get Archive.org API documentation reference"""
    return {
        "name": "Archive.org API Documentation",
        "content": f"""# Archive.org API Documentation

## Base URLs
- Base URL: {config.base_url}
- Metadata API: {config.metadata_url}
- Search API: {config.search_url}

## Metadata API

Get item metadata:
```
GET {config.metadata_url}/{{identifier}}
```

Returns JSON with:
- metadata: Item metadata (title, creator, date, description, etc.)
- files: List of files with format, size, length
- reviews: User reviews
- server: Server hostname
- dir: Directory path

## Advanced Search API

Search Archive.org:
```
GET {config.search_url}?q={{query}}&output=json&rows={{rows}}&page={{page}}
```

Query examples:
- `collection:tv` - All TV items
- `collection:movies` - All movies
- `title:Magnum` - Items with "Magnum" in title
- `creator:ABC` - Items created by ABC
- `mediatype:movies AND year:[1980 TO 1990]` - Movies from 1980-1990

Fields (fl parameter):
- identifier, title, creator, date, mediatype, description, publicdate, downloads

Sort options:
- `downloads desc` - Most downloaded first
- `date desc` - Newest first
- `publicdate desc` - Most recently published

## Authentication

Optional authentication for restricted content:
- Set ARCHIVE_ORG_USERNAME and ARCHIVE_ORG_PASSWORD environment variables
- Or provide username/password in configuration

## Streaming URLs

Video files can be streamed directly:
```
https://{{server}}{{dir}}/{{filename}}
```

Or via download endpoint:
```
{config.base_url}/download/{{identifier}}/{{filename}}
```

## Rate Limiting

Archive.org has rate limits:
- Be respectful with request frequency
- Use appropriate delays between requests
- Cache results when possible

## Documentation Links

- Official API Docs: https://archive.org/developers/index-apis.html
- Metadata API: https://archive.org/developers/metadata-api.html
- Search API: https://archive.org/developers/search-api.html
""",
        "mimeType": "text/markdown"
    }


async def get_archive_org_search_examples() -> Dict[str, Any]:
    """Get Archive.org search query examples"""
    return {
        "name": "Archive.org Search Examples",
        "content": """# Archive.org Search Query Examples

## Basic Queries

```
collection:tv
collection:movies
mediatype:movies
mediatype:etree
```

## Combined Queries

```
collection:tv AND title:Magnum
collection:movies AND year:[1980 TO 1990]
creator:ABC AND mediatype:movies
```

## Field-Specific Searches

```
title:Magnum P.I.
creator:ABC
subject:"Television Programs"
description:"detective"
```

## Date Ranges

```
year:[1980 TO 1990]
publicdate:[2020-01-01 TO 2020-12-31]
date:[1980 TO 1989]
```

## Popular Collections

- `tv` - Television programs
- `movies` - Movies
- `opensource_movies` - Open source movies
- `etree` - Live music recordings
- `audio` - Audio recordings
- `software` - Software collections

## Advanced Examples

Find TV shows from 1980s:
```
collection:tv AND year:[1980 TO 1989]
```

Find movies by specific creator:
```
collection:movies AND creator:"ABC" AND year:[1980 TO 1990]
```

Find items with specific format:
```
collection:tv AND format:"h.264"
```
""",
        "mimeType": "text/markdown"
    }


# Resource registry
RESOURCES = {
    "archive-org://docs/api": get_archive_org_api_docs,
    "archive-org://docs/search-examples": get_archive_org_search_examples,
}


async def list_resources() -> list:
    """List all available Archive.org resources"""
    return [
        {
            "uri": uri,
            "name": uri.split("://")[-1].replace("/", " ").title(),
            "description": f"Archive.org {uri.split('://')[-1]}"
        }
        for uri in RESOURCES.keys()
    ]


async def get_resource(uri: str) -> Dict[str, Any]:
    """Get a resource by URI"""
    if uri in RESOURCES:
        return await RESOURCES[uri]()
    return {
        "name": "Not Found",
        "content": f"Resource not found: {uri}",
        "mimeType": "text/plain"
    }

