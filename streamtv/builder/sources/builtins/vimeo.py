from streamtv.builder.sources.types import BuilderSourceSpec

SPEC = BuilderSourceSpec(
    id="vimeo",
    label="Vimeo",
    status="active",
    hosts=["vimeo.com", "player.vimeo.com", "www.vimeo.com"],
    auth_methods=["playwright", "cookies"],
    url_placeholder="https://vimeo.com/... (resolve only; playout pending bedrock)",
    supports_expand=False,
    playout_ready=False,
    resolver_source="vimeo",
    docs_anchor="vimeo-bedrock-pending",
)
