#!/usr/bin/env bash
# Install 2-minute stalled-FFmpeg self-heal LaunchAgent (com.streamtv.stalled-ffmpeg-heal).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLIST_LABEL="com.streamtv.stalled-ffmpeg-heal"
PLIST_PATH="${HOME}/Library/LaunchAgents/${PLIST_LABEL}.plist"
LOG_DIR="${HOME}/Library/Logs/StreamTV"
HEAL_SCRIPT="${ROOT}/scripts/heal_stalled_ffmpeg.sh"

verify_step() {
  local step_name="$1"
  local check_command="$2"
  if eval "${check_command}"; then
    echo "  [PASSED] ${step_name}"
  else
    echo "  [FAILED] ${step_name}"
    exit 1
  fi
}

chmod +x "${HEAL_SCRIPT}" \
  "${ROOT}/scripts/heal_stalled_ffmpeg.py" \
  "${ROOT}/scripts/heal_keepalive_tunes.py"
mkdir -p "${LOG_DIR}"

cat >"${PLIST_PATH}" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${PLIST_LABEL}</string>
  <key>WorkingDirectory</key>
  <string>${ROOT}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${HEAL_SCRIPT}</string>
  </array>
  <key>StartInterval</key>
  <integer>120</integer>
  <key>RunAtLoad</key>
  <true/>
  <key>StandardOutPath</key>
  <string>${LOG_DIR}/stalled-ffmpeg-heal.stdout.log</string>
  <key>StandardErrorPath</key>
  <string>${LOG_DIR}/stalled-ffmpeg-heal.stderr.log</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>STREAMTV_STALL_HEAL_MIN_ETIME</key>
    <string>90</string>
    <key>STREAMTV_STALL_HEAL_MAX_PCPU</key>
    <string>0.15</string>
    <key>STREAMTV_BASE_URL</key>
    <string>http://127.0.0.1:8410</string>
    <key>STREAMTV_KEEPALIVE_HEAL_TUNE_SEC</key>
    <string>30</string>
    <key>STREAMTV_KEEPALIVE_HEAL_MIN_FAILS</key>
    <string>2</string>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>
</dict>
</plist>
PLIST

launchctl bootout "gui/$(id -u)/${PLIST_LABEL}" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "${PLIST_PATH}"

verify_step "plist installed" "[[ -f \"${PLIST_PATH}\" ]]"
verify_step "heal script executable" "[[ -x \"${HEAL_SCRIPT}\" ]]"
verify_step "label loaded" "launchctl print gui/$(id -u)/${PLIST_LABEL} >/dev/null"

echo ""
echo "Installed ${PLIST_LABEL}"
echo "  Schedule: every 120s + RunAtLoad"
echo "  Script:   ${HEAL_SCRIPT}"
echo "  Log:      ${LOG_DIR}/stalled-ffmpeg-heal.log"
echo "  Criteria: archive.org ffmpeg, etime>=90s, pcpu<=0.15"
