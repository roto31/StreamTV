from streamtv.builder.sources.types import BuilderSourceSpec

SPEC = BuilderSourceSpec(
    id="archive_org",
    label="Archive.org",
    status="active",
    hosts=["archive.org"],
    auth_methods=["password", "cookies"],
    url_placeholder=(
        "https://archive.org/details/...\n"
        "https://archive.org/download/identifier/file.mp4"
    ),
    supports_expand=True,
    playout_ready=True,
    resolver_source="archive_org",
    docs_anchor="archive-org",
)
