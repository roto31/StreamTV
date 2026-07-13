# YouTube geo-blocks (bulk import)

Some videos are region-locked or removed. Bulk import and channel extension scripts **skip** unavailable entries rather than failing the whole job.

## Operator notes

- Channel **1991** and similar large playlists may log skipped geo-blocked IDs.
- Re-run extension scripts after cookie refresh if skips seem wrong.
- Verify with a direct tune of a single item before blaming playout.

See [Authentication](/docs/authentication) for cookie export.
