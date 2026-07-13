from streamtv.builder.sources.types import BuilderSourceSpec

SPEC = BuilderSourceSpec(
    id="pbs",
    label="PBS",
    status="active",
    hosts=["pbs.org", "www.pbs.org"],
    auth_methods=["playwright", "cookies"],
    url_placeholder=(
        "https://www.pbs.org/video/...\n"
        "https://www.pbs.org/show/nature/"
    ),
    supports_expand=True,
    playout_ready=True,
    resolver_source="pbs",
    docs_anchor="pbs",
)
