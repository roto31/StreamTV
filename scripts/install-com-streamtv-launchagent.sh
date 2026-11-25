#!/usr/bin/env bash
# Install universal com.streamtv LaunchAgent (no Studio-specific EnvironmentVariables).
# Usage:
#   bash scripts/install-com-streamtv-launchagent.sh
#   bash scripts/install-com-streamtv-launchagent.sh --workdir "/path/to/repo"
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEFAULT_WORKDIR="${HOME}/Library/Application Support/StreamTV"
WORKDIR=""
PLIST_LABEL="com.streamtv"
PLIST_PATH="${HOME}/Library/LaunchAgents/${PLIST_LABEL}.plist"
LOG_DIR="${HOME}/Library/Logs/StreamTV"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workdir)
      WORKDIR="${2:-}"
      shift 2
      ;;
    --help|-h)
      echo "Usage: $0 [--workdir PATH]"
      echo "Default workdir: ${DEFAULT_WORKDIR}"
      exit 0
      ;;
    *)
      echo "ERROR: unknown arg: $1" >&2
      exit 2
      ;;
  esac
done

if [[ -z "${WORKDIR}" ]]; then
  WORKDIR="${DEFAULT_WORKDIR}"
fi
WORKDIR="$(cd "${WORKDIR}" 2>/dev/null && pwd || true)"
if [[ -z "${WORKDIR}" || ! -d "${WORKDIR}" ]]; then
  echo "ERROR: workdir does not exist: ${WORKDIR:-unset}" >&2
  exit 2
fi

PYTHON="${WORKDIR}/venv/bin/python3"
if [[ ! -x "${PYTHON}" ]]; then
  PYTHON="${WORKDIR}/venv/bin/python"
fi
if [[ ! -x "${PYTHON}" ]]; then
  echo "ERROR: missing venv python under ${WORKDIR}/venv — create venv and pip install -r requirements.txt first" >&2
  exit 2
fi

# Prefer package import from workdir (repo or Application Support with streamtv/)
if ! (
  cd "${WORKDIR}"
  "${PYTHON}" -c "import streamtv" 2>/dev/null
); then
  echo "ERROR: cannot import streamtv from ${WORKDIR}" >&2
  exit 2
fi

mkdir -p "${LOG_DIR}" "${HOME}/Library/LaunchAgents"

cat >"${PLIST_PATH}" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${PLIST_LABEL}</string>
  <key>WorkingDirectory</key>
  <string>${WORKDIR}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${PYTHON}</string>
    <string>-m</string>
    <string>streamtv.main</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>${LOG_DIR}/streamtv.stdout.log</string>
  <key>StandardErrorPath</key>
  <string>${LOG_DIR}/streamtv.stderr.log</string>
</dict>
</plist>
PLIST

launchctl bootout "gui/$(id -u)/${PLIST_LABEL}" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "${PLIST_PATH}"
launchctl enable "gui/$(id -u)/${PLIST_LABEL}" 2>/dev/null || true
launchctl kickstart -k "gui/$(id -u)/${PLIST_LABEL}" 2>/dev/null || true

echo "Installed ${PLIST_LABEL}"
echo "  WorkingDirectory: ${WORKDIR}"
echo "  Python:           ${PYTHON}"
echo "  Plist:            ${PLIST_PATH}"
echo "  Logs:             ${LOG_DIR}/streamtv.*.log"
echo "Verify: launchctl print gui/\$(id -u)/${PLIST_LABEL} | head"
