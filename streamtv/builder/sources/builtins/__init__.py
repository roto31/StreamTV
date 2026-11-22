"""Built-in Channel Builder sources (first-party)."""

from streamtv.builder.sources.builtins.archive_org import SPEC as ARCHIVE_ORG
from streamtv.builder.sources.builtins.youtube import SPEC as YOUTUBE

# PBS / Plex / Vimeo parked under parked/builder-sources/builtins/
BUILTIN_SPECS = [ARCHIVE_ORG, YOUTUBE]

__all__ = ["BUILTIN_SPECS", "ARCHIVE_ORG", "YOUTUBE"]
