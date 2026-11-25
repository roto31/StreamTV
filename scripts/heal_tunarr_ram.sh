#!/usr/bin/env bash
# Keep TunarrRAM from filling (Errno 28 kills playout).
#
# Universal volume watchdog — not tied to any tuned channel/station.
# Runs on a fixed LaunchAgent interval whether or not anyone is watching.
#
# Policy (2026-09-20):
#   Purge when ANY of:
#     used% >= STREAMTV_TUNARRAM_MAX_USED_PCT (default 45)          — early
#     used GiB >= STREAMTV_TUNARRAM_MAX_USED_GB (default 1.7)     — hard ceiling
#     free MiB < STREAMTV_TUNARRAM_MIN_FREE_MB (default 300)
#   Deletes cache files EXCEPT those open by ffmpeg/StreamTV (+ .part siblings).
#   Also removes orphan /Volumes/TunarrRAM/stream_* HLS dirs when not open.
#
# Usage:
#   bash scripts/heal_tunarr_ram.sh
#   DRY_RUN=1 bash scripts/heal_tunarr_ram.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CACHE="${STREAMTV_CACHE_DIR:-/Volumes/TunarrRAM/streamtv-cache}"
MAX_USED_PCT="${STREAMTV_TUNARRAM_MAX_USED_PCT:-45}"
MAX_USED_GB="${STREAMTV_TUNARRAM_MAX_USED_GB:-1.7}"
MIN_FREE_MB="${STREAMTV_TUNARRAM_MIN_FREE_MB:-300}"
DRY_RUN="${DRY_RUN:-0}"
PYTHON="${ROOT}/venv/bin/python3"
if [[ ! -x "${PYTHON}" ]]; then
  PYTHON="$(command -v python3)"
fi
PURGE="${ROOT}/scripts/heal_tunarr_ram_purge.py"

if [[ ! -d "${CACHE}" ]]; then
  echo "WARN: cache dir missing: ${CACHE}"
  exit 0
fi

export STREAMTV_CACHE_DIR="${CACHE}"
export STREAMTV_TUNARRAM_MAX_USED_PCT="${MAX_USED_PCT}"
export STREAMTV_TUNARRAM_MAX_USED_GB="${MAX_USED_GB}"
export STREAMTV_TUNARRAM_MIN_FREE_MB="${MIN_FREE_MB}"

echo "TunarrRAM heal cache=${CACHE} max_used_pct=${MAX_USED_PCT} max_used_gb=${MAX_USED_GB} min_free_mb=${MIN_FREE_MB} dry_run=${DRY_RUN}"

ARGS=(
  --cache-dir "${CACHE}"
  --max-used-pct "${MAX_USED_PCT}"
  --max-used-gb "${MAX_USED_GB}"
  --min-free-mb "${MIN_FREE_MB}"
)
if [[ "${DRY_RUN}" == "1" ]]; then
  ARGS+=(--dry-run)
else
  ARGS+=(--apply)
fi

"${PYTHON}" "${PURGE}" "${ARGS[@]}"

# Orphan Tunarr HLS session dirs on the RAM volume (legacy path before SSD transcode)
VOLUME_ROOT="$(dirname "${CACHE}")"
if [[ "${VOLUME_ROOT}" == /Volumes/TunarrRAM ]]; then
  OPEN_TMP="$(mktemp)"
  lsof +D "${VOLUME_ROOT}" 2>/dev/null | awk 'NR>1{print $NF}' >"${OPEN_TMP}" || true
  for d in "${VOLUME_ROOT}"/stream_*; do
    [[ -d "${d}" ]] || continue
    if grep -qF "${d}" "${OPEN_TMP}" 2>/dev/null; then
      echo "keep open Tunarr HLS dir: ${d}"
      continue
    fi
    if [[ "${DRY_RUN}" == "1" ]]; then
      echo "dry-run would remove orphan Tunarr HLS: ${d}"
    else
      rm -rf "${d}"
      echo "removed orphan Tunarr HLS: ${d}"
    fi
  done
  rm -f "${OPEN_TMP}"
fi

exit 0
