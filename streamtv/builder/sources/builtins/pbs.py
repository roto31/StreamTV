from streamtv.builder.sources.types import BuilderSourceSpec

SPEC = BuilderSourceSpec(
    id="pbs",
    label="PBS",
    status="active",
    hosts=["pbs.org", "www.pbs.org"],
    auth_methods=["playwright", "cookies"],
    url_placeholder=(
        "https://www.pbs.org/video/...\n"
        "https://www.pbs.org/show/nature/\n"
        "\n"
        "Show pages expand to full season catalogs (up to 5000 videos). "
        "Full-episode filter skips trailers (≥5 min when duration known). "
        "Long-form PBS builds default to epg_sync_class C."
    ),
    supports_expand=True,
    playout_ready=True,
    resolver_source="pbs",
    docs_anchor="pbs",
)
