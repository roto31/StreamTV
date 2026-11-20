# Public release sanitization policy

StreamTV-source is private. The public [StreamTV](https://github.com/roto31/StreamTV) repository receives **sanitized** docs and, when explicitly released, culled source trees.

## Never publish

- API keys, tokens, passwords, or `secrets.env`
- Cookie jars and browser cookie exports
- Lab or home network addresses (`192.168.*`, `10.*`, Tailscale `100.*`)
- Operator-specific paths (`/home/streamtv/`, internal hostnames)
- Channel YAML, schedules, signing keys, or release CI secrets

## Tooling

| Script | Purpose |
|--------|---------|
| `scripts/verify_public_sanitization.sh` | Fail-closed scan before any public push |
| `scripts/public_sanitize.lib.sh` | Shared scrub + scan patterns |
| `scripts/sync_public_code.sh` | Culled code release (`--dry-run` / `--apply --confirm`) |
| `scripts/sync_public_docs.sh` | Docs-only sync (runs verification gate) |
| `config/public_release_manifest.yaml` | Include/exclude lists for code releases |

## Workflow

**Standing rule:** after platform changes land on private `StreamTV-source`
`main`, update the public `StreamTV` repo in the same task (see Cursor rule
`streamtv-public-repo-sync`).

1. Refresh `docs/public-repo/CHANGELOG.md` with sanitized user-facing notes.
2. Run `bash scripts/sync_public_code.sh --dry-run` and review the tree.
3. Fix violations in source or manifest exclusions.
4. `bash scripts/verify_public_sanitization.sh /path/to/tree` must print **PASSED**.
5. `bash scripts/sync_public_code.sh --apply --confirm`.
6. `bash scripts/sync_public_docs.sh --apply` (add `--wiki` when `docs/wiki/` changed).

Docs sync (`sync_public_docs.sh`) always runs verification before push.
