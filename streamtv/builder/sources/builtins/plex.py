from streamtv.builder.sources.types import BuilderSourceSpec

SPEC = BuilderSourceSpec(
    id="plex",
    label="Plex",
    status="active",
    hosts=["plex://"],
    auth_methods=["token"],
    url_placeholder="plex://server/library/metadata/12345",
    supports_expand=False,
    playout_ready=True,
    resolver_source="plex",
    docs_anchor="plex",
)
