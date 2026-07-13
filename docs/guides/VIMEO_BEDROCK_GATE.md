# Vimeo playout — bedrock gate

Vimeo Builder source is **beta** (`playout_ready: false`). Schema allows `source: vimeo`.

## Blocked without owner approval

Streaming adapter in `streamtv/streaming/` requires:

```
APPROVED: change streamtv/streaming/ — Vimeo adapter for playout
```

## Completed (non-bedrock)

- `schemas/channel.schema.json` — `vimeo` enum
- `streamtv/builder/sources/builtins/vimeo.py` — beta status

## Next steps after approval

1. Add `streamtv/streaming/vimeo_adapter.py`
2. Register in stream manager
3. New golden tests (never regenerate existing snapshots)
4. Set Builder `playout_ready=True`
