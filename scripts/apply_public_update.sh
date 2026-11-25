#!/usr/bin/env bash
# Apply latest public StreamTV release tree into this install (repo or app mode).
# Does not touch frozen bedrock semantics beyond replacing shipped public code.
set -euo pipefail

MODE="repo"
BACKUP_DIR=""
PUBLIC_REPO="${STREAMTV_PUBLIC_REPO:-roto31/StreamTV}"

usage() {
  echo "Usage: $(basename "$0") [--mode repo|app] [--backup-dir DIR]" >&2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode) MODE="${2:-}"; shift 2 ;;
    --backup-dir) BACKUP_DIR="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERROR: unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}"

echo "apply_public_update: mode=${MODE} root=${ROOT}"

if [[ -n "${BACKUP_DIR}" ]]; then
  mkdir -p "${BACKUP_DIR}"
  echo "backup dir: ${BACKUP_DIR}"
fi

# Fetch latest release tag via GitHub API
TAG="$(curl -fsSL -H 'Accept: application/vnd.github+json' -H 'User-Agent: StreamTV-Updates' \
  "https://api.github.com/repos/${PUBLIC_REPO}/releases/latest" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin).get("tag_name") or "")')"

if [[ -z "${TAG}" ]]; then
  echo "ERROR: could not resolve latest release tag" >&2
  exit 1
fi

echo "latest tag: ${TAG}"
TMP="$(mktemp -d /tmp/streamtv-update.XXXXXX)"
cleanup() { rm -rf "${TMP}"; }
trap cleanup EXIT

ARCHIVE="${TMP}/source.tgz"
curl -fsSL -L -o "${ARCHIVE}" \
  "https://github.com/${PUBLIC_REPO}/archive/refs/tags/${TAG}.tar.gz"

mkdir -p "${TMP}/extract"
tar -xzf "${ARCHIVE}" -C "${TMP}/extract"
SRC_DIR="$(find "${TMP}/extract" -mindepth 1 -maxdepth 1 -type d | head -1)"
if [[ -z "${SRC_DIR}" || ! -d "${SRC_DIR}/streamtv" ]]; then
  echo "ERROR: extracted archive missing streamtv/" >&2
  exit 1
fi

# Preserve local operator files
PRESERVE=(config.yaml streamtv.db .streamtv-setup-done data/cookies)
for item in "${PRESERVE[@]}"; do
  if [[ -e "${ROOT}/${item}" && -n "${BACKUP_DIR}" ]]; then
    mkdir -p "${BACKUP_DIR}/preserve"
    cp -R "${ROOT}/${item}" "${BACKUP_DIR}/preserve/" 2>/dev/null || true
  fi
done

# Sync public package code (rsync if available)
if command -v rsync >/dev/null 2>&1; then
  rsync -a --delete \
    --exclude 'config.yaml' \
    --exclude 'streamtv.db' \
    --exclude 'venv/' \
    --exclude '.git/' \
    --exclude 'data/cookies/' \
    "${SRC_DIR}/streamtv/" "${ROOT}/streamtv/"
  if [[ -f "${SRC_DIR}/requirements.txt" ]]; then
    cp "${SRC_DIR}/requirements.txt" "${ROOT}/requirements.txt"
  fi
  if [[ -f "${SRC_DIR}/VERSION" ]]; then
    cp "${SRC_DIR}/VERSION" "${ROOT}/VERSION"
  fi
else
  rm -rf "${ROOT}/streamtv"
  cp -R "${SRC_DIR}/streamtv" "${ROOT}/streamtv"
  cp "${SRC_DIR}/requirements.txt" "${ROOT}/requirements.txt" 2>/dev/null || true
  cp "${SRC_DIR}/VERSION" "${ROOT}/VERSION" 2>/dev/null || true
fi

# Refresh shipped operator scripts (LaunchAgent installers, yt-dlp upgrade, heal).
if [[ -d "${SRC_DIR}/scripts" ]]; then
  mkdir -p "${ROOT}/scripts"
  for script in install-com-streamtv-launchagent.sh install-yt-dlp-upgrade-launchagent.sh \
      upgrade-yt-dlp-production.sh install-tunarr-ram-heal-launchagent.sh heal_tunarr_ram.sh \
      apply_public_update.sh check_core_dependency_freshness.py; do
    if [[ -f "${SRC_DIR}/scripts/${script}" ]]; then
      cp "${SRC_DIR}/scripts/${script}" "${ROOT}/scripts/${script}"
      chmod +x "${ROOT}/scripts/${script}" 2>/dev/null || true
    fi
  done
fi

# Starter channel packs (optional setup picker reads data/starter_packs).
if [[ -d "${SRC_DIR}/data/starter_packs" ]]; then
  mkdir -p "${ROOT}/data/starter_packs"
  rsync -a "${SRC_DIR}/data/starter_packs/" "${ROOT}/data/starter_packs/" 2>/dev/null \
    || cp -R "${SRC_DIR}/data/starter_packs/." "${ROOT}/data/starter_packs/"
fi

if [[ -x "${ROOT}/venv/bin/pip" ]]; then
  "${ROOT}/venv/bin/pip" install -r "${ROOT}/requirements.txt" --upgrade
elif [[ -x "${HOME}/Library/Application Support/StreamTV/venv/bin/pip" ]]; then
  "${HOME}/Library/Application Support/StreamTV/venv/bin/pip" install -r "${ROOT}/requirements.txt" --upgrade
fi

echo "apply_public_update: OK (${TAG})"
