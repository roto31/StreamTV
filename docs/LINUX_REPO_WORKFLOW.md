# Linux repository workflow

StreamTV Linux porting happens in a **separate git repository** (`StreamTV-linux`). There is **no merge history** and **no backports** between macOS and Linux codebases.

## Repositories

| Repo | Visibility | Purpose |
|------|------------|---------|
| [StreamTV-source](https://github.com/roto31/StreamTV-source) | Private | macOS canonical code, CI, guards |
| [StreamTV-linux](https://github.com/roto31/StreamTV-linux) | Private | Linux refactor, packaging, CI |
| [StreamTV](https://github.com/roto31/StreamTV) | Public | Docs, wiki, sanitized releases |

## Rules

1. **Never** open PRs from StreamTV-linux into StreamTV-source.
2. **Never** import Linux commits into `streamtv/` in StreamTV-source.
3. Refresh Linux from macOS only via **one-way export** (`scripts/export_linux_repo_snapshot.sh`).
4. `macos-source` remote in StreamTV-linux is **fetch-only** for audit diffs — not for merge.

## macOS → Linux export (operator)

From StreamTV-source:

```bash
bash scripts/install_git_hooks.sh
bash scripts/protect_macos_tree.sh --readonly   # optional
bash scripts/export_linux_repo_snapshot.sh --update-lock
bash scripts/verify_forbidden_paths.sh --assert-clean
bash scripts/protect_macos_tree.sh --writable   # optional
```

Artifacts:

- `exports/linux/streamtv-linux-snapshot.tar.gz` (gitignored)
- `exports/linux/latest-manifest.json` (source SHA + file hashes)

## Linux developer setup

```bash
git clone https://github.com/roto31/StreamTV-linux.git
cd StreamTV-linux
bash scripts/install_git_hooks.sh   # after bootstrap adds hooks
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp config.example.yaml config.yaml
pytest -q   # smoke after bootstrap
```

### Optional audit against macOS snapshot

```bash
git remote add macos-source https://github.com/roto31/StreamTV-source.git
git fetch macos-source
# Compare manifest source_sha in exports/linux/latest-manifest.json
```

## Linux repo guards

StreamTV-linux uses **allowlist-only** changes:

- `scripts/verify_linux_allowlist.sh` — only permitted top-level paths may change
- Forbidden: `StreamTVMac/`, `packaging/macos/`, macOS-only tooling
- CI: `ubuntu-latest` + pytest + allowlist check

Allowed top-level paths include: `streamtv/`, `tests/`, `packaging/`, `docs/`, `scripts/`, `requirements*.txt`, `pytest.ini`, `LICENSE`, `README.md`, `CHANGELOG.md`, etc.

## Worktree workflow

```bash
# macOS machine — edit Linux only in separate clone
cd ~/src/StreamTV-linux
git checkout -b linux/platform-paths
# ... Linux-specific changes (XDG logs, credentials, videotoolbox defaults, etc.)
```

Do **not** create `streamtv_linux/` or Linux branches inside StreamTV-source.

## Verification gates

| Gate | Command | Pass |
|------|---------|------|
| G1 | Touch `README.md` only, `--staged` | PASS |
| G2 | Stage change under `streamtv/` | FAIL |
| G3 | CI `forbidden-paths` on PR | PASS/FAIL per diff |
| G4 | `git diff streamtv/` after export | empty |
| G5 | Linux clone + `pytest` smoke | PASS (post-bootstrap) |

## Related

- [MACOS_TREE_PROTECTION.md](MACOS_TREE_PROTECTION.md) — macOS forbidden-path policy
- [CONTRIBUTING.md](../CONTRIBUTING.md)
