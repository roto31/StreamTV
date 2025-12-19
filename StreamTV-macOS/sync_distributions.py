#!/usr/bin/env python3
"""
Synchronize the canonical StreamTV source tree into every distribution package.

The script discovers files that have been added or modified on the current
branch (relative to origin/main as well as untracked files) and mirrors those
paths into each distribution variant:
- StreamTV-Linux
- StreamTV-macOS
- StreamTV-Windows
- StreamTV-Containers/{docker,docker-compose,kubernetes,podman}

Usage:
    python3 sync_distributions.py            # copies detected changes
    python3 sync_distributions.py --dry-run  # show what would change
    python3 sync_distributions.py path/to/file another/path

Extra positional paths are always copied, even if they are not detected as
changes. This is useful when you want to force-sync a file or directory.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Set

ROOT = Path(__file__).resolve().parent

TARGET_DIRECTORIES: List[Path] = [
    ROOT / "StreamTV-Linux",
    ROOT / "StreamTV-macOS",
    ROOT / "StreamTV-Windows",
    ROOT / "StreamTV-Containers" / "docker",
    ROOT / "StreamTV-Containers" / "docker-compose",
    ROOT / "StreamTV-Containers" / "kubernetes",
    ROOT / "StreamTV-Containers" / "podman",
]

# Paths rooted at the canonical platform that are allowed to be synced. Anything
# outside this allow-list is assumed to be environment-specific and will be
# ignored unless explicitly provided on the command line.
ALLOWED_ROOTS: Set[str] = {
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "README.md",
    "SECURITY.md",
    "config.example.yaml",
    "create-wiki.sh",
    "data",
    "push-distributions.sh",
    "requirements-secure.txt",
    "requirements.txt",
    "requirements.txt.backup",
    "sbom.json",
    "setup.py",
    "start_server.sh",
    "sync_distributions.py",
    "streamtv",
    "update-dependencies.sh",
}

EXCLUDED_PREFIXES: tuple[str, ...] = (
    "StreamTV-Linux/",
    "StreamTV-macOS/",
    "StreamTV-Windows/",
    "StreamTV-Containers/",
    ".git/",
)


class SyncError(RuntimeError):
    """Raised when git commands fail."""


def run_git_command(args: Iterable[str]) -> str:
    result = subprocess.run(
        list(args),
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SyncError(result.stderr.strip() or "Git command failed")
    return result.stdout


def normalize_path(raw_path: str) -> str:
    path = raw_path.strip()
    if " -> " in path:
        path = path.split(" -> ", 1)[1]
    return path.strip()


def is_allowed(path: str) -> bool:
    if not path:
        return False
    if any(path.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
        return False
    first_component = path.split("/", 1)[0]
    return first_component in ALLOWED_ROOTS


def gather_changed_paths() -> Set[str]:
    paths: Set[str] = set()

    try:
        diff_output = run_git_command(["git", "diff", "--name-only", "origin/main...HEAD"])
    except SyncError:
        diff_output = ""

    for line in diff_output.splitlines():
        line = line.strip()
        if not line:
            continue
        if is_allowed(line):
            paths.add(line)

    status_output = run_git_command(["git", "status", "--porcelain"])
    for line in status_output.splitlines():
        if not line:
            continue
        if len(line) < 4:
            continue
        candidate = normalize_path(line[3:])
        if is_allowed(candidate):
            paths.add(candidate)

    return paths


def normalize_manual_paths(raw_paths: Iterable[str]) -> Set[str]:
    normalized: Set[str] = set()
    for raw in raw_paths:
        raw = raw.strip()
        if not raw:
            continue
        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = (ROOT / candidate).resolve()
        else:
            candidate = candidate.resolve()
        try:
            relative = candidate.relative_to(ROOT)
        except ValueError:
            print(f"[WARN] Skipping path outside repository root: {raw}")
            continue
        cleaned = relative.as_posix()
        if cleaned:
            normalized.add(cleaned)
    return normalized


def copy_path(relative_path: str, *, dry_run: bool, verbose: bool) -> None:
    src = ROOT / relative_path
    if not src.exists():
        print(f"[WARN] Skipping missing path: {relative_path}")
        return

    for target_root in TARGET_DIRECTORIES:
        dest = target_root / relative_path
        action = "COPY" if not dry_run else "DRY-RUN"
        if verbose or dry_run:
            print(f"[{action}] {src} -> {dest}")

        if dry_run:
            continue

        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dest)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        help="Extra files or directories to sync regardless of git status.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be copied without modifying any files.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print each copy operation as it occurs.",
    )

    args = parser.parse_args(argv)

    if any(not target.exists() for target in TARGET_DIRECTORIES):
        missing = [str(target) for target in TARGET_DIRECTORIES if not target.exists()]
        print("[ERROR] Missing target directories:\n - " + "\n - ".join(missing))
        return 1

    changed_paths = gather_changed_paths()
    requested_paths = normalize_manual_paths(args.paths)
    all_paths = sorted(changed_paths | requested_paths)

    if not all_paths:
        print("No eligible changes detected. Use --verbose to see filtering details or pass paths explicitly.")
        return 0

    for relative in all_paths:
        copy_path(relative, dry_run=args.dry_run, verbose=args.verbose)

    print(f"Synced {len(all_paths)} path(s) to {len(TARGET_DIRECTORIES)} distributions.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
