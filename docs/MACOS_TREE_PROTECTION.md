# macOS tree protection

StreamTV-source is the **canonical macOS repository**. Core runtime trees are mechanically locked so Linux port work cannot accidentally modify macOS code.

## Forbidden paths

Any staged change or PR diff touching these paths **fails** pre-commit and CI:

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

Linux development belongs in the separate **[StreamTV-linux](https://github.com/roto31/StreamTV-linux)** repository. See [LINUX_REPO_WORKFLOW.md](LINUX_REPO_WORKFLOW.md).

## One-time setup (every clone)

```bash
bash scripts/install_git_hooks.sh
```

This sets `core.hooksPath` to `.githooks` and runs `scripts/verify_forbidden_paths.sh --staged` on every commit.

**Do not** use `git commit --no-verify` for Linux work.

## Verification commands

```bash
# Pre-commit equivalent (staged files)
bash scripts/verify_forbidden_paths.sh --staged

# CI equivalent (diff vs main)
bash scripts/verify_forbidden_paths.sh --ci --base origin/main

# Post-export: locked trees match config/macos_tree_lock.json
bash scripts/verify_forbidden_paths.sh --assert-clean
```

Output is `[PASSED]` or `[FAILED]` with the exact file list.

## Lock file

[`config/macos_tree_lock.json`](../config/macos_tree_lock.json) records:

- `locked_ref` — full git SHA when trees were last certified clean
- `tree_paths` — directories compared in `--assert-clean` mode

Updated only during an explicit owner export ceremony (`export_linux_repo_snapshot.sh --update-lock`).

## Optional read-only ceremony (export)

Before exporting a Linux snapshot:

```bash
bash scripts/protect_macos_tree.sh --readonly
bash scripts/export_linux_repo_snapshot.sh --update-lock
bash scripts/verify_forbidden_paths.sh --assert-clean
bash scripts/protect_macos_tree.sh --writable
```

`protect_macos_tree.sh` uses `chmod -R a-w` / `u+w` (portable fallback; no bind mounts required).

## CI

| Workflow | Runner | Purpose |
|----------|--------|---------|
| `forbidden-paths.yml` | `ubuntu-latest` | Fail PR/push if forbidden paths change |
| `pr-path-report.yml` | `ubuntu-latest` | PR comment: forbidden vs allowed paths |
| `ci.yml` (first step) | M4 self-hosted | Defense in depth before pytest/Swift |

## GitHub branch protection (optional — not on Free private repos)

GitHub **branch protection rules** for private repositories require **GitHub Pro**, **Team**, or **Enterprise**, or making the repo public. If your plan does not include branch protection, **skip this step** — the controls below still enforce the policy.

### Compensating controls (use these instead)

| Layer | What it does |
|-------|----------------|
| **Local pre-commit** | `bash scripts/install_git_hooks.sh` — blocks commits that touch forbidden paths |
| **`forbidden-paths.yml`** | Runs on every PR and push to `main`; job fails if forbidden paths change |
| **`pr-path-report.yml`** | PR comment listing forbidden vs allowed path touches |
| **`ci.yml` (M4, first step)** | Same guard before pytest/Swift on self-hosted runner |
| **Process** | Merge via PR only; review diffs for `streamtv/`, `StreamTVMac/`, `packaging/macos/` |

### If you upgrade or go public later

On `main` in **StreamTV-source** → Settings → Branches:

1. Require status check **Forbidden paths** (`forbidden-paths` job)
2. Require PR review before merge
3. Do not allow bypassing required checks for Linux work

## Related

- [CONTRIBUTING.md](../CONTRIBUTING.md) — macOS contributions only in this repo
- [LINUX_REPO_WORKFLOW.md](LINUX_REPO_WORKFLOW.md) — separate Linux repo workflow
- [STREAMING_BEDROCK_FROZEN.md](STREAMING_BEDROCK_FROZEN.md) — bedrock freeze policy
