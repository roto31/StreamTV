# Import vs Channel Builder

| Scenario | Tool |
|----------|------|
| New channel from YouTube / Archive.org / PBS URLs | [Channel Builder](/builder) |
| Migrate `channels_generated_*.yaml` from another server | [Import](/import) |
| Re-import after `scripts/compile_unified_channel.py` | Import |
| Operator-edited `data/unified/*.channel.yaml` | Compile script, then Import |

Import remains required for migration and compiled artifacts. Builder does not replace it.

See also: [Channel Builder](/docs/channel_builder)
