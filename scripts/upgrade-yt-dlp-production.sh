#!/usr/bin/env bash
# Upgrade yt-dlp in the production venv. Kickstart com.streamtv only when pip
# actually installed a newer wheel (not when "Requirement already satisfied").
# Floor comes from YTDLP_MIN_VERSION in streamtv/ffmpeg/constants.py (Issue 73).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${ROOT}/venv/bin/python3"
LOG_DIR="${HOME}/Library/Logs/StreamTV"
mkdir -p "${LOG_DIR}"
exec >>"${LOG_DIR}/ytdlp-upgrade.log" 2>&1
echo "=== yt-dlp upgrade $(date) ==="

if [[ ! -x "${PYTHON}" ]]; then
  echo "ERROR: missing interpreter ${PYTHON}"
  exit 3
fi

FLOOR="$("${PYTHON}" -c "from streamtv.ffmpeg.constants import YTDLP_MIN_VERSION; print(YTDLP_MIN_VERSION)")"
echo "floor yt-dlp>=${FLOOR} (from YTDLP_MIN_VERSION)"

BEFORE="$("${PYTHON}" -c "import yt_dlp; print(yt_dlp.version.__version__)" 2>/dev/null || echo "none")"
PIP_OUT="$("${PYTHON}" -m pip install -U "yt-dlp>=${FLOOR}" 2>&1)" || {
  echo "${PIP_OUT}"
  echo "ERROR: pip install failed"
  exit 1
}
echo "${PIP_OUT}"
AFTER="$("${PYTHON}" -c "import yt_dlp; print(yt_dlp.version.__version__)")"
echo "yt-dlp before=${BEFORE} after=${AFTER}"

UPGRADED=0
if echo "${PIP_OUT}" | grep -qiE 'Successfully installed yt-dlp|Installing collected packages:.*yt-dlp'; then
  UPGRADED=1
elif [[ "${BEFORE}" != "${AFTER}" ]]; then
  UPGRADED=1
fi

if [[ "${UPGRADED}" -eq 1 ]]; then
  echo "wheel upgraded — kickstarting com.streamtv"
  launchctl kickstart -k "gui/$(id -u)/com.streamtv" || true
else
  echo "already satisfied (before=${BEFORE}) — skip kickstart"
fi

# Best-effort freshness report (never fails the upgrade job).
"${PYTHON}" "${ROOT}/scripts/check_core_dependency_freshness.py" --no-pypi || true

echo "=== done ==="
