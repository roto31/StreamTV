#!/usr/bin/env bash
# Self-heal stalled Archive.org FFmpeg (keepalive-only HDHomeRun wedge).
# Lesson 41 — see LESSONS_LEARNED.md / skill heal-stalled-ffmpeg-keepalive.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}"
PYTHON="${ROOT}/venv/bin/python3"
LOG_DIR="${HOME}/Library/Logs/StreamTV"
LOGFILE="${LOG_DIR}/stalled-ffmpeg-heal.log"

mkdir -p "${LOG_DIR}"
exec >>"${LOGFILE}" 2>&1

echo "=== stalled ffmpeg heal $(date '+%Y-%m-%d %H:%M:%S') ==="

if [[ ! -x "${PYTHON}" ]]; then
  echo "ERROR: missing ${PYTHON}"
  exit 2
fi

# Always exit 0 so launchd KeepAlive/interval stays healthy
set +e
"${PYTHON}" "${ROOT}/scripts/heal_stalled_ffmpeg.py" --apply
rc=$?
set -e
if [[ "${rc}" -ne 0 ]]; then
  echo "WARN: heal_stalled_ffmpeg.py exit ${rc}"
else
  echo "[PASSED] stalled ffmpeg heal"
fi

# Keepalive-only HDHR sample → kill stalled archive ffmpeg + soft-restart channel
set +e
"${PYTHON}" "${ROOT}/scripts/heal_keepalive_tunes.py" --apply
krc=$?
set -e
if [[ "${krc}" -ne 0 ]]; then
  echo "WARN: heal_keepalive_tunes.py exit ${krc}"
else
  echo "[PASSED] keepalive tune heal"
fi
exit 0
