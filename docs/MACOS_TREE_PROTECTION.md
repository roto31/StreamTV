# macOS tree protection

StreamTV-source is the **canonical macOS repository**. Core runtime trees are
mechanically locked so accidental edits to frozen / packaging trees fail
pre-commit and PR CI.

StreamTV ships **macOS only**. There is **no Linux product** and **no maintained
Linux fork** (`StreamTV-linux` retired).

## Forbidden paths

Any staged change or PR diff touching these paths **fails** pre-commit and CI
(except owner push to `main` with explicit intent — see rules):

| Path | Reason |
|------|--------|
| `streamtv/` | Canonical Python runtime (streaming bedrock frozen) |
| `StreamTVMac/` | macOS SwiftUI app |
| `packaging/macos/` | macOS packaging |
| `tests/test_ffmpeg_command_golden.py` | Frozen golden FFmpeg commands |
| `tests/test_youtube_ffmpeg_path.py` | Frozen YouTube FFmpeg path |
| `tests/test_epg_live_air_position.py` | Frozen EPG/playout tests |
| `tests/test_playout_reset_anchor.py` | Frozen playout anchor tests |
| `tests/test_youtube_ydl_opts.py` | Frozen yt-dlp options tests |

## One-time setup (every clone)

```bash
bash scripts/install_git_hooks.sh
```

This sets `core.hooksPath` to `.githooks` and runs `scripts/verify_forbidden_paths.sh --staged` on every commit.

## Verification commands

```bash
# Pre-commit equivalent (staged files)
bash scripts/verify_forbidden_paths.sh --staged

# CI equivalent (diff vs main)
bash scripts/verify_forbidden_paths.sh --ci --base origin/main

# Locked trees match config/macos_tree_lock.json
bash scripts/verify_forbidden_paths.sh --assert-clean
```

Output is `[PASSED]` or `[FAILED]` with the exact file list.

## Lock file

[`config/macos_tree_lock.json`](../config/macos_tree_lock.json) records:

- `locked_ref` — full git SHA when trees were last certified clean
- `tree_paths` — directories compared in `--assert-clean` mode

Update only during an explicit owner lock ceremony (`protect_macos_tree.sh` +
`--assert-clean`), not for a Linux export (removed).

## CI

| Workflow | Runner | Purpose |
|----------|--------|---------|
| `forbidden-paths.yml` | `ubuntu-latest` | Fail **PRs** if forbidden paths change; **push to main is allowed** (owner macOS runtime) |
| `pr-path-report.yml` | `ubuntu-latest` | PR comment: forbidden vs allowed paths; still fails the PR job |
| `ci.yml` (first step) | M4 self-hosted | Same: fail on PR, skip fail on push |

## Related

- [CONTRIBUTING.md](../CONTRIBUTING.md) — macOS contributions only
- [PACKAGING.md](../PACKAGING.md) — macOS packaging only
- [STREAMING_BEDROCK_FROZEN.md](STREAMING_BEDROCK_FROZEN.md) — bedrock freeze policy
