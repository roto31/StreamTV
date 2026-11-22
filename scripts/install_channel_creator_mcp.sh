#!/bin/bash
# Bootstrap Channel Creator MCP from the public GitHub repo.
# Designed for curl|bash; prompts use /dev/tty when stdin is the pipe.
#
# One-liner:
#   curl -fsSL https://raw.githubusercontent.com/roto31/StreamTV/main/scripts/install_channel_creator_mcp.sh | bash
#
# With flags (non-interactive):
#   curl -fsSL https://raw.githubusercontent.com/roto31/StreamTV/main/scripts/install_channel_creator_mcp.sh | bash -s -- --platform cursor --apply --no-smoke
#
# Env:
#   STREAMTV_INSTALL_DIR   Clone/checkout path (default: ./StreamTV or $PWD if already a checkout)
#   STREAMTV_GIT_URL       Override clone URL (default: https://github.com/roto31/StreamTV.git)
#   STREAMTV_GIT_REF       Branch/tag (default: main)
set -euo pipefail

GIT_URL="${STREAMTV_GIT_URL:-https://github.com/roto31/StreamTV.git}"
GIT_REF="${STREAMTV_GIT_REF:-main}"
INSTALL_DIR="${STREAMTV_INSTALL_DIR:-}"
SETUP_ARGS=()

usage() {
  cat <<'EOF'
Usage: install_channel_creator_mcp.sh [setup options…]

Clones (or reuses) the public StreamTV repo, ensures a venv + MCP deps,
then runs scripts/setup_channel_creator_mcp.sh.

One-liner:
  curl -fsSL https://raw.githubusercontent.com/roto31/StreamTV/main/scripts/install_channel_creator_mcp.sh | bash

Non-interactive example:
  curl -fsSL https://raw.githubusercontent.com/roto31/StreamTV/main/scripts/install_channel_creator_mcp.sh \
    | bash -s -- --platform cursor --apply --install-deps --no-smoke

Env: STREAMTV_INSTALL_DIR, STREAMTV_GIT_URL, STREAMTV_GIT_REF

All flags after this script’s own options are passed to setup_channel_creator_mcp.sh
(--platform, --apply, --emit-only, --profile, …). See that script’s --help.
EOF
}

err() { echo "ERROR: $*" >&2; }
info() { echo "$*"; }

# When piped via curl|bash, stdin is not a TTY — open /dev/tty for setup prompts.
ensure_tty_stdin() {
  if [[ ! -t 0 ]] && [[ -r /dev/tty ]]; then
    exec </dev/tty
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --install-dir)
      INSTALL_DIR="${2:-}"
      shift 2
      ;;
    --git-url)
      GIT_URL="${2:-}"
      shift 2
      ;;
    --git-ref)
      GIT_REF="${2:-}"
      shift 2
      ;;
    *)
      SETUP_ARGS+=("$1")
      shift
      ;;
  esac
done

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    err "missing required command: $1"
    exit 3
  }
}

need_cmd git
need_cmd python3
need_cmd curl

is_streamtv_checkout() {
  local root="$1"
  [[ -d "${root}/mcp_streamtv" && -f "${root}/scripts/setup_channel_creator_mcp.sh" ]]
}

resolve_install_dir() {
  if [[ -n "${INSTALL_DIR}" ]]; then
    echo "${INSTALL_DIR}"
    return 0
  fi
  if is_streamtv_checkout "$(pwd)"; then
    pwd
    return 0
  fi
  if [[ -d "$(pwd)/StreamTV" ]] && is_streamtv_checkout "$(pwd)/StreamTV"; then
    echo "$(pwd)/StreamTV"
    return 0
  fi
  echo "$(pwd)/StreamTV"
}

REPO_ROOT="$(resolve_install_dir)"
info "Install / checkout: ${REPO_ROOT}"
info "Git: ${GIT_URL} @ ${GIT_REF}"

if is_streamtv_checkout "${REPO_ROOT}"; then
  info "Existing StreamTV checkout detected — skip clone."
  if [[ -d "${REPO_ROOT}/.git" ]]; then
    git -C "${REPO_ROOT}" fetch --depth 1 origin "${GIT_REF}" 2>/dev/null || true
    git -C "${REPO_ROOT}" checkout "${GIT_REF}" 2>/dev/null || true
    git -C "${REPO_ROOT}" pull --ff-only origin "${GIT_REF}" 2>/dev/null || \
      info "Could not fast-forward (ok if you have local edits)."
  fi
else
  info "Cloning ${GIT_URL} (${GIT_REF}) → ${REPO_ROOT}"
  mkdir -p "$(dirname "${REPO_ROOT}")"
  git clone --depth 1 --branch "${GIT_REF}" "${GIT_URL}" "${REPO_ROOT}"
fi

if ! is_streamtv_checkout "${REPO_ROOT}"; then
  err "checkout incomplete — mcp_streamtv / setup script missing under ${REPO_ROOT}"
  exit 1
fi

cd "${REPO_ROOT}"

if [[ ! -x "${REPO_ROOT}/venv/bin/python" ]]; then
  info "Creating venv…"
  python3 -m venv "${REPO_ROOT}/venv"
fi
PYTHON_BIN="${REPO_ROOT}/venv/bin/python"

info "Installing Channel Creator MCP Python deps…"
"${PYTHON_BIN}" -m pip install -q --upgrade pip
"${PYTHON_BIN}" -m pip install -q -r "${REPO_ROOT}/requirements-mcp-streamtv.txt"

# Default: interactive prompts for platform/mode; skip smoke until StreamTV is up
if [[ ${#SETUP_ARGS[@]} -eq 0 ]]; then
  SETUP_ARGS=(--install-deps --no-smoke)
fi

# Prefer explicit python + repo for setup
SETUP_ARGS=(--repo-root "${REPO_ROOT}" --python "${PYTHON_BIN}" "${SETUP_ARGS[@]}")

info ""
info "Running setup_channel_creator_mcp.sh ${SETUP_ARGS[*]}"
info ""

ensure_tty_stdin
bash "${REPO_ROOT}/scripts/setup_channel_creator_mcp.sh" "${SETUP_ARGS[@]}"

info ""
info "Bootstrap complete."
info "Wiki: https://github.com/roto31/StreamTV/wiki/Channel-Creator-MCP-Host-Wiring"
