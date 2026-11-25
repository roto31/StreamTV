#!/usr/bin/env bash
# Install TunarrRAM volume watchdog LaunchAgent (always-on; not per-channel).
# Default: every 60s; purge at 45% OR used>=1.7 GiB OR free<300 MiB.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLIST_LABEL="com.streamtv.tunarr-ram-heal"
PLIST_PATH="${HOME}/Library/LaunchAgents/${PLIST_LABEL}.plist"
LOG_DIR="${HOME}/Library/Logs/StreamTV"
HEAL_SCRIPT="${ROOT}/scripts/heal_tunarr_ram.sh"
CACHE_DIR="${STREAMTV_CACHE_DIR:-/Volumes/TunarrRAM/streamtv-cache}"
MAX_USED_PCT="${STREAMTV_TUNARRAM_MAX_USED_PCT:-45}"
MAX_USED_GB="${STREAMTV_TUNARRAM_MAX_USED_GB:-1.7}"
MIN_FREE_MB="${STREAMTV_TUNARRAM_MIN_FREE_MB:-300}"
START_INTERVAL="${STREAMTV_TUNARRAM_HEAL_INTERVAL_SEC:-60}"

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

mkdir -p "${LOG_DIR}"
chmod +x "${HEAL_SCRIPT}" "${ROOT}/scripts/heal_tunarr_ram_purge.py"

cat >"${PLIST_PATH}" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${PLIST_LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${HEAL_SCRIPT}</string>
  </array>
  <key>WorkingDirectory</key>
  <string>${ROOT}</string>
  <key>StartInterval</key>
  <integer>${START_INTERVAL}</integer>
  <key>RunAtLoad</key>
  <true/>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    <key>STREAMTV_CACHE_DIR</key>
    <string>${CACHE_DIR}</string>
    <key>STREAMTV_TUNARRAM_MAX_USED_PCT</key>
    <string>${MAX_USED_PCT}</string>
    <key>STREAMTV_TUNARRAM_MAX_USED_GB</key>
    <string>${MAX_USED_GB}</string>
    <key>STREAMTV_TUNARRAM_MIN_FREE_MB</key>
    <string>${MIN_FREE_MB}</string>
  </dict>
  <key>StandardOutPath</key>
  <string>${LOG_DIR}/tunarr-ram-heal.stdout.log</string>
  <key>StandardErrorPath</key>
  <string>${LOG_DIR}/tunarr-ram-heal.stderr.log</string>
</dict>
</plist>
PLIST

launchctl bootout "gui/$(id -u)/${PLIST_LABEL}" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "${PLIST_PATH}"

verify_step "plist installed" "[[ -f \"${PLIST_PATH}\" ]]"
verify_step "heal script executable" "[[ -x \"${HEAL_SCRIPT}\" ]]"
verify_step "purge helper present" "[[ -f \"${ROOT}/scripts/heal_tunarr_ram_purge.py\" ]]"

echo ""
echo "Installed ${PLIST_LABEL} (universal volume watchdog — not per-channel)"
echo "  Interval: every ${START_INTERVAL}s (RunAtLoad + StartInterval)"
echo "  max_used_pct=${MAX_USED_PCT}  max_used_gb=${MAX_USED_GB}  min_free_mb=${MIN_FREE_MB}"
echo "  Dry-run:  DRY_RUN=1 bash ${HEAL_SCRIPT}"
echo "  Apply:    bash ${HEAL_SCRIPT}"
