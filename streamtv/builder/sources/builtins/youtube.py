from streamtv.builder.sources.types import BuilderSourceSpec

SPEC = BuilderSourceSpec(
    id="youtube",
    label="YouTube",
    status="active",
    hosts=["youtube.com", "youtu.be", "www.youtube.com", "m.youtube.com"],
    auth_methods=["playwright", "cookies"],
    url_placeholder=(
        "https://www.youtube.com/watch?v=...\n"
        "https://www.youtube.com/playlist?list=..."
    ),
    supports_expand=True,
    playout_ready=True,
    resolver_source="youtube",
    docs_anchor="youtube",
)
