#!/bin/bash
# Install StreamTV app icon into macOS AppIcon.appiconset (+ optional .icns / favicons).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BRAND="${ROOT}/branding/app-icon"
MASTER="${BRAND}/StreamTV-app-icon-1024.png"
ICONSET="${ROOT}/StreamTVMac/StreamTV/Assets.xcassets/AppIcon.appiconset"

usage() {
  cat <<'EOF'
Usage: install_app_icon.sh [--master PATH]

Rasterizes branding/app-icon/StreamTV-app-icon-1024.png into:
  - StreamTVMac AppIcon.appiconset (all mac sizes)
  - StreamTVApp AppIcon mirrors (if present)
  - branding/app-icon/StreamTV.icns
  - branding/app-icon favicon / apple-touch assets
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --master) MASTER="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERROR: unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ -f "${MASTER}" ]] || { echo "ERROR: missing master icon: ${MASTER}" >&2; exit 2; }
[[ -d "${ICONSET}" ]] || { echo "ERROR: missing AppIcon.appiconset: ${ICONSET}" >&2; exit 2; }

PYTHON="${ROOT}/venv/bin/python"
[[ -x "${PYTHON}" ]] || PYTHON="python3"

"${PYTHON}" - "${MASTER}" "${ICONSET}" "${BRAND}" "${ROOT}" <<'PY'
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover
    raise SystemExit("ERROR: Pillow required (pip install Pillow)") from exc

master_path = Path(sys.argv[1])
iconset = Path(sys.argv[2])
brand = Path(sys.argv[3])
root = Path(sys.argv[4])

master = Image.open(master_path).convert("RGBA")
# Build "@2x" names via concatenation — avoids tooling that mangles "@" in literals.
_at2x = "@" + "2x.png"
sizes = {
    "icon_16x16.png": 16,
    "icon_16x16" + _at2x: 32,
    "icon_32x32.png": 32,
    "icon_32x32" + _at2x: 64,
    "icon_128x128.png": 128,
    "icon_128x128" + _at2x: 256,
    "icon_256x256.png": 256,
    "icon_256x256" + _at2x: 512,
    "icon_512x512.png": 512,
    "icon_512x512" + _at2x: 1024,
}
for name, px in sizes.items():
    master.resize((px, px), Image.Resampling.LANCZOS).save(iconset / name, format="PNG")
    print(f"  wrote {iconset.name}/{name} ({px}px)")

mirrors = [
    root / "StreamTVApp/Assets.xcassets/AppIcon.appiconset",
    root / "StreamTVApp/StreamTV/StreamTV/Assets.xcassets/AppIcon.appiconset",
]
contents = iconset / "Contents.json"
for dest in mirrors:
    if not dest.is_dir():
        continue
    for name in sizes:
        shutil.copy2(iconset / name, dest / name)
    if contents.is_file():
        shutil.copy2(contents, dest / "Contents.json")
    print(f"  mirrored → {dest.relative_to(root)}")

brand.mkdir(parents=True, exist_ok=True)
master.resize((180, 180), Image.Resampling.LANCZOS).save(brand / "apple-touch-icon.png")
master.resize((32, 32), Image.Resampling.LANCZOS).save(brand / "favicon-32.png")
master.resize((16, 16), Image.Resampling.LANCZOS).save(brand / "favicon-16.png")
master.save(brand / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
if master_path.resolve() != (brand / "StreamTV-app-icon-1024.png").resolve():
    shutil.copy2(master_path, brand / "StreamTV-app-icon-1024.png")

with tempfile.TemporaryDirectory() as tmp:
    tmp_iconset = Path(tmp) / "AppIcon.iconset"
    tmp_iconset.mkdir()
    for name in sizes:
        shutil.copy2(iconset / name, tmp_iconset / name)
    icns = brand / "StreamTV.icns"
    subprocess.run(["iconutil", "-c", "icns", str(tmp_iconset), "-o", str(icns)], check=True)
    print(f"  wrote {icns.relative_to(root)}")

static = root / "streamtv" / "static" / "branding"
static.mkdir(parents=True, exist_ok=True)
for name in ("favicon.ico", "favicon-32.png", "apple-touch-icon.png", "StreamTV-app-icon-1024.png"):
    shutil.copy2(brand / name, static / name)
    print(f"  wrote static/branding/{name}")
PY

echo "App icon install complete."
