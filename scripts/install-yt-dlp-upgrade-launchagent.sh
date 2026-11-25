#!/usr/bin/env bash
# Install weekly yt-dlp upgrade LaunchAgent for production StreamTV (com.streamtv).
# Does not modify streaming code; restarts production daemon after upgrade.
# Re-run after editing upgrade-yt-dlp-production.sh (Issue 45 / 73).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${ROOT}/venv/bin/python3"
PLIST_LABEL="com.streamtv.ytdlp-upgrade"
PLIST_PATH="${HOME}/Library/LaunchAgents/${PLIST_LABEL}.plist"
LOG_DIR="${HOME}/Library/Logs/StreamTV"
UPGRADE_SCRIPT="${ROOT}/scripts/upgrade-yt-dlp-production.sh"

verify_step() {
  local step_name="$1"
  local check_command="$2"
  if eval "$check_command"; then
    echo "  [PASSED] $step_name"
  else
    echo "  [FAILED] $step_name"
    exit 1
  fi
}

# Ensure upgrade script is executable (source of truth lives in-repo; do not
# regenerate it here — floor is read from YTDLP_MIN_VERSION at runtime).
if [[ ! -f "${UPGRADE_SCRIPT}" ]]; then
  echo "ERROR: missing ${UPGRADE_SCRIPT}"
  exit 2
fi
chmod +x "${UPGRADE_SCRIPT}"

mkdir -p "${LOG_DIR}"

cat >"${PLIST_PATH}" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${PLIST_LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${UPGRADE_SCRIPT}</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Weekday</key>
    <integer>0</integer>
    <key>Hour</key>
    <integer>4</integer>
    <key>Minute</key>
    <integer>15</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>${LOG_DIR}/ytdlp-upgrade.stdout.log</string>
  <key>StandardErrorPath</key>
  <string>${LOG_DIR}/ytdlp-upgrade.stderr.log</string>
</dict>
</plist>
PLIST

launchctl bootout "gui/$(id -u)/${PLIST_LABEL}" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "${PLIST_PATH}"

verify_step "plist installed" "[[ -f \"${PLIST_PATH}\" ]]"
verify_step "upgrade script executable" "[[ -x \"${UPGRADE_SCRIPT}\" ]]"
verify_step "python can read YTDLP_MIN_VERSION" "\"${PYTHON}\" -c 'from streamtv.ffmpeg.constants import YTDLP_MIN_VERSION; print(YTDLP_MIN_VERSION)'"

echo ""
echo "Installed ${PLIST_LABEL}"
echo "  Schedule: Sundays 04:15"
echo "  Script:   ${UPGRADE_SCRIPT}"
echo "  Logs:     ${LOG_DIR}/ytdlp-upgrade*.log"
echo "Dry-run now: bash ${UPGRADE_SCRIPT}"
echo "Freshness:  ${PYTHON} ${ROOT}/scripts/check_core_dependency_freshness.py"
