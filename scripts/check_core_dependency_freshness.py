#!/usr/bin/env python3
"""Check StreamTV core dependencies for floor / PyPI / banned YouTube clients.

Exit codes:
  0  all findings ok (warnings allowed unless --strict)
  1  one or more fail findings (below floor, banned clients, missing yt-dlp)
  2  usage / import error

Examples:
  ./venv/bin/python scripts/check_core_dependency_freshness.py
  ./venv/bin/python scripts/check_core_dependency_freshness.py --json
  ./venv/bin/python scripts/check_core_dependency_freshness.py --no-pypi --strict
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="StreamTV core dependency freshness (yt-dlp, clients, ffmpeg)",
    )
    parser.add_argument(
        "--no-pypi",
        action="store_true",
        help="Skip PyPI latest-version lookup (floor + clients only)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warn findings as failure (exit 1)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON report",
    )
    args = parser.parse_args()

    try:
        from streamtv.utils.dependency_freshness import run_freshness_checks
    except ImportError as exc:
        print(f"ERROR: cannot import freshness module: {exc}", file=sys.stderr)
        return 2

    report = run_freshness_checks(check_pypi=not args.no_pypi)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        for finding in report.findings:
            mark = {"ok": "OK", "warn": "WARN", "fail": "FAIL"}[finding.status]
            print(f"[{mark}] {finding.component}: {finding.detail}")
        if report.ok and not (args.strict and report.has_warnings):
            print("dependency freshness: PASSED")
        else:
            print("dependency freshness: FAILED", file=sys.stderr)

    if not report.ok:
        return 1
    if args.strict and report.has_warnings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
