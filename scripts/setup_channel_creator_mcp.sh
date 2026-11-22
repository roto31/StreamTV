#!/bin/bash
# All-in-one Channel Creator MCP host wiring setup.
# Interactive: platform menu → mode menu → shared prompts → run that path.
# Optional flags skip menus for automation.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
HELPER_DIR="${SCRIPT_DIR}/channel-creator-mcp"
TEMPLATE_DIR="${HELPER_DIR}/templates"
GENERATED_DIR="${HELPER_DIR}/generated"
INTAKE_SRC="${DEFAULT_REPO_ROOT}/mcp_streamtv/prompts/channel_intake.md"

PLATFORM=""
MODE=""
REPO_ROOT=""
PYTHON_BIN=""
BASE_URL=""
WITH_ARCHIVE=""
INSTALL_DEPS=""
API_KEY=""
LOCAL_CLIENT=""

usage() {
  cat <<'EOF'
Usage: setup_channel_creator_mcp.sh [options]

Prefer the gated Phase-6 script for new wiring:
  zsh scripts/channel_creator_mcp_hosts.zsh --host all --mode emit --profile guided

All-in-one Channel Creator MCP wiring. With no flags, prompts for:
  1) Platform  2) Mode (apply / dry-run / emit-only)  3) Shared entries

Options:
  --platform cursor|vscode-continue|vscode-cline|claude|local|chatgpt
  --apply              Merge live host config where supported
  --dry-run            Print actions only; write nothing
  --emit-only          Write snippets under scripts/channel-creator-mcp/generated/
  --repo-root PATH     StreamTV checkout (default: detect from script)
  --python PATH        Python interpreter
  --base-url URL       STREAMTV_BASE_URL (default: http://127.0.0.1:8410)
  --with-archive       Include mcp_archive_org server block
  --no-archive         Skip Archive.org MCP
  --install-deps       pip install StreamTV + Archive MCP requirements
  --no-install-deps    Skip pip install
  -h, --help           Show this help

Exit codes: 0 success, 1 runtime failure, 2 usage/config error
EOF
}

err() { echo "ERROR: $*" >&2; }
warn() { echo "WARN: $*" >&2; }
info() { echo "$*"; }

prompt_default() {
  local prompt="$1"
  local default="$2"
  local reply=""
  if [[ -n "${default}" ]]; then
    read -r -p "${prompt} [${default}]: " reply || true
    echo "${reply:-${default}}"
  else
    read -r -p "${prompt}: " reply || true
    echo "${reply}"
  fi
}

prompt_yn() {
  local prompt="$1"
  local default="$2"
  local reply=""
  local hint="y/N"
  [[ "${default}" == "y" ]] && hint="Y/n"
  read -r -p "${prompt} (${hint}): " reply || true
  reply="$(echo "${reply}" | tr '[:upper:]' '[:lower:]')"
  if [[ -z "${reply}" ]]; then
    [[ "${default}" == "y" ]]
    return $?
  fi
  [[ "${reply}" == "y" || "${reply}" == "yes" ]]
}

prompt_secret() {
  local prompt="$1"
  local reply=""
  read -r -s -p "${prompt} (blank to skip): " reply || true
  echo >&2
  echo "${reply}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --platform)
      PLATFORM="${2:-}"
      shift 2
      ;;
    --apply)
      MODE="apply"
      shift
      ;;
    --dry-run)
      MODE="dry-run"
      shift
      ;;
    --emit-only)
      MODE="emit-only"
      shift
      ;;
    --repo-root)
      REPO_ROOT="${2:-}"
      shift 2
      ;;
    --python)
      PYTHON_BIN="${2:-}"
      shift 2
      ;;
    --base-url)
      BASE_URL="${2:-}"
      shift 2
      ;;
    --with-archive)
      WITH_ARCHIVE="y"
      shift
      ;;
    --no-archive)
      WITH_ARCHIVE="n"
      shift
      ;;
    --install-deps)
      INSTALL_DEPS="y"
      shift
      ;;
    --no-install-deps)
      INSTALL_DEPS="n"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      err "unknown option: $1"
      usage >&2
      exit 2
      ;;
  esac
done

prompt_platform() {
  cat <<'EOF'

Which platform are you setting up?
  1) Cursor
  2) VS Code — Continue
  3) VS Code — Cline
  4) Claude Desktop
  5) Local model (Ollama / LM Studio + Continue or Cline)
  6) ChatGPT (deferred — checklist only)
EOF
  local choice
  read -r -p "Select [1-6]: " choice || true
  case "${choice}" in
    1) PLATFORM="cursor" ;;
    2) PLATFORM="vscode-continue" ;;
    3) PLATFORM="vscode-cline" ;;
    4) PLATFORM="claude" ;;
    5) PLATFORM="local" ;;
    6) PLATFORM="chatgpt" ;;
    *)
      err "invalid platform choice: ${choice}"
      exit 2
      ;;
  esac
}

prompt_mode() {
  cat <<'EOF'

Mode?
  1) Apply — write/merge live host config (with .bak backup where supported)
  2) Dry-run — print what would happen; write nothing
  3) Emit only — write snippets under scripts/channel-creator-mcp/generated/
EOF
  local choice
  read -r -p "Select [1-3]: " choice || true
  case "${choice}" in
    1) MODE="apply" ;;
    2) MODE="dry-run" ;;
    3) MODE="emit-only" ;;
    *)
      err "invalid mode choice: ${choice}"
      exit 2
      ;;
  esac
}

validate_platform() {
  case "${PLATFORM}" in
    cursor|vscode-continue|vscode-cline|claude|local|chatgpt) ;;
    *)
      err "invalid --platform: ${PLATFORM}"
      exit 2
      ;;
  esac
}

[[ -z "${PLATFORM}" ]] && prompt_platform
validate_platform
[[ -z "${MODE}" ]] && prompt_mode
case "${MODE}" in
  apply|dry-run|emit-only) ;;
  *)
    err "invalid mode: ${MODE}"
    exit 2
    ;;
esac

if [[ -z "${REPO_ROOT}" ]]; then
  REPO_ROOT="$(prompt_default "StreamTV repo root" "${DEFAULT_REPO_ROOT}")"
fi
REPO_ROOT="$(cd "${REPO_ROOT}" && pwd)" || {
  err "repo root not found: ${REPO_ROOT}"
  exit 2
}

if [[ ! -d "${REPO_ROOT}/mcp_streamtv" ]]; then
  err "mcp_streamtv not found under ${REPO_ROOT}"
  exit 2
fi

INTAKE_SRC="${REPO_ROOT}/mcp_streamtv/prompts/channel_intake.md"
HELPER_DIR="${REPO_ROOT}/scripts/channel-creator-mcp"
TEMPLATE_DIR="${HELPER_DIR}/templates"
GENERATED_DIR="${HELPER_DIR}/generated"

if [[ -z "${PYTHON_BIN}" ]]; then
  local_default="python3"
  if [[ -x "${REPO_ROOT}/venv/bin/python" ]]; then
    local_default="${REPO_ROOT}/venv/bin/python"
  fi
  PYTHON_BIN="$(prompt_default "Python binary" "${local_default}")"
fi

if [[ -z "${BASE_URL}" ]]; then
  BASE_URL="$(prompt_default "STREAMTV_BASE_URL" "http://127.0.0.1:8410")"
fi

if [[ -z "${WITH_ARCHIVE}" ]]; then
  if prompt_yn "Include Archive.org MCP (mcp_archive_org)?" "n"; then
    WITH_ARCHIVE="y"
  else
    WITH_ARCHIVE="n"
  fi
fi

if [[ -z "${INSTALL_DEPS}" ]]; then
  if [[ "${MODE}" == "dry-run" ]]; then
    INSTALL_DEPS="n"
  elif prompt_yn "Install MCP pip deps now (streamtv + archive reqs only)?" "n"; then
    INSTALL_DEPS="y"
  else
    INSTALL_DEPS="n"
  fi
fi

if [[ "${PLATFORM}" == "local" ]]; then
  cat <<'EOF'

Local client for MCP fragments:
  1) Continue
  2) Cline
EOF
  local_choice=""
  read -r -p "Select [1-2] (default 1): " local_choice || true
  case "${local_choice}" in
    2) LOCAL_CLIENT="cline" ;;
    *) LOCAL_CLIENT="continue" ;;
  esac
fi

if [[ "${MODE}" != "dry-run" && "${PLATFORM}" != "chatgpt" && -t 0 ]]; then
  API_KEY="$(prompt_secret "Optional STREAMTV_API_KEY")"
fi

info ""
info "Platform: ${PLATFORM}"
info "Mode:     ${MODE}"
info "Repo:     ${REPO_ROOT}"
info "Python:   ${PYTHON_BIN}"
info "Base URL: ${BASE_URL}"
info "Archive:  ${WITH_ARCHIVE}"
info "Deps:     ${INSTALL_DEPS}"
[[ -n "${LOCAL_CLIENT}" ]] && info "Local client: ${LOCAL_CLIENT}"
info ""

render_template() {
  local src="$1"
  local dest="$2"
  python3 - "${src}" "${dest}" "${PYTHON_BIN}" "${REPO_ROOT}" "${BASE_URL}" \
    "${WITH_ARCHIVE}" "${TEMPLATE_DIR}" <<'PY'
import pathlib
import sys

src, dest, python_bin, repo_root, base_url, with_archive, template_dir = sys.argv[1:8]
text = pathlib.Path(src).read_text(encoding="utf-8")
archive_block = ""
archive_continue_block = ""
if with_archive == "y":
    def fill(path: str) -> str:
        return (
            pathlib.Path(path)
            .read_text(encoding="utf-8")
            .replace("__PYTHON__", python_bin)
            .replace("__REPO_ROOT__", repo_root)
            .replace("__BASE_URL__", base_url)
        )

    archive_block = fill(f"{template_dir}/archive_block.json.tmpl").rstrip("\n")
    archive_continue_block = fill(
        f"{template_dir}/archive_continue_block.json.tmpl"
    ).rstrip("\n")

text = (
    text.replace("__PYTHON__", python_bin)
    .replace("__REPO_ROOT__", repo_root)
    .replace("__BASE_URL__", base_url)
    .replace("__ARCHIVE_BLOCK__", archive_block)
    .replace("__ARCHIVE_CONTINUE_BLOCK__", archive_continue_block)
)
pathlib.Path(dest).parent.mkdir(parents=True, exist_ok=True)
pathlib.Path(dest).write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
PY
}

emit_file() {
  local dest="$1"
  local label="$2"
  if [[ "${MODE}" == "dry-run" ]]; then
    info "[dry-run] would write ${label}: ${dest}"
    return 0
  fi
  mkdir -p "$(dirname "${dest}")"
  info "Wrote ${label}: ${dest}"
}

copy_intake() {
  local dest="${GENERATED_DIR}/intake_system_prompt.md"
  if [[ "${MODE}" == "dry-run" ]]; then
    info "[dry-run] would copy intake → ${dest}"
    return 0
  fi
  if [[ ! -f "${INTAKE_SRC}" ]]; then
    err "missing intake prompt: ${INTAKE_SRC}"
    exit 1
  fi
  mkdir -p "${GENERATED_DIR}"
  cp "${INTAKE_SRC}" "${dest}"
  info "Wrote intake: ${dest}"
}

install_deps_now() {
  if [[ "${INSTALL_DEPS}" != "y" ]]; then
    return 0
  fi
  if [[ "${MODE}" == "dry-run" ]]; then
    info "[dry-run] would pip install -r requirements-mcp-streamtv.txt"
    [[ "${WITH_ARCHIVE}" == "y" ]] && info "[dry-run] would pip install -r requirements-mcp-archive-org.txt"
    return 0
  fi
  info "Installing MCP dependencies with ${PYTHON_BIN} ..."
  "${PYTHON_BIN}" -m pip install -r "${REPO_ROOT}/requirements-mcp-streamtv.txt"
  if [[ "${WITH_ARCHIVE}" == "y" ]]; then
    "${PYTHON_BIN}" -m pip install -r "${REPO_ROOT}/requirements-mcp-archive-org.txt"
  fi
  info "MCP dependencies installed."
}

merge_mcp_servers_json() {
  local target="$1"
  local fragment="$2"
  if [[ "${MODE}" == "dry-run" ]]; then
    info "[dry-run] would merge MCP servers into ${target}"
    return 0
  fi
  mkdir -p "$(dirname "${target}")"
  if [[ -f "${target}" ]]; then
    local bak="${target}.bak.$(date +%Y%m%d%H%M%S)"
    cp "${target}" "${bak}"
    info "Backup: ${bak}"
  else
    echo '{}' >"${target}"
  fi
  python3 - "${target}" "${fragment}" <<'PY'
import json
import sys
from pathlib import Path

target = Path(sys.argv[1])
fragment = Path(sys.argv[2])
base = json.loads(target.read_text(encoding="utf-8") or "{}")
frag = json.loads(fragment.read_text(encoding="utf-8"))
servers = base.setdefault("mcpServers", {})
if not isinstance(servers, dict):
    raise SystemExit("ERROR: mcpServers in target is not an object")
incoming = frag.get("mcpServers", {})
if not isinstance(incoming, dict):
    raise SystemExit("ERROR: fragment mcpServers is not an object")
servers.update(incoming)
target.write_text(json.dumps(base, indent=2) + "\n", encoding="utf-8")
print(f"Merged MCP servers into {target}")
PY
}

print_paste_steps() {
  local kind="$1"
  local fragment="$2"
  cat <<EOF

Paste steps (${kind}):
  1. Open ${kind} MCP / config settings.
  2. Merge the JSON from:
       ${fragment}
  3. Add system / custom instructions from:
       ${GENERATED_DIR}/intake_system_prompt.md
  4. Restart the host client if required.
EOF
  if [[ -n "${API_KEY}" ]]; then
    warn "Set STREAMTV_API_KEY in the host MCP env (not written to disk by this script)."
  fi
}

emit_cursor() {
  local dest="${GENERATED_DIR}/cursor.mcp.json"
  if [[ "${MODE}" != "dry-run" ]]; then
    mkdir -p "${GENERATED_DIR}"
    render_template "${TEMPLATE_DIR}/mcp_servers.json.tmpl" "${dest}"
  fi
  emit_file "${dest}" "Cursor MCP JSON"
  copy_intake
  if [[ "${MODE}" == "apply" ]]; then
    local live="${REPO_ROOT}/.cursor/mcp.json"
    merge_mcp_servers_json "${live}" "${dest}"
    info "Applied Cursor project MCP config: ${live}"
    info "Enable skill: streamtv-channel-creator"
  elif [[ "${MODE}" == "emit-only" ]]; then
    info "Emit-only: copy ${dest} into Cursor Settings → MCP or .cursor/mcp.json"
  fi
}

emit_continue() {
  local dest="${GENERATED_DIR}/continue.mcp.fragment.json"
  if [[ "${MODE}" != "dry-run" ]]; then
    mkdir -p "${GENERATED_DIR}"
    render_template "${TEMPLATE_DIR}/continue_mcp.fragment.json.tmpl" "${dest}"
  fi
  emit_file "${dest}" "Continue MCP fragment"
  copy_intake
  if [[ "${MODE}" == "apply" ]]; then
    warn "Continue global config path varies — cannot safely auto-merge."
    print_paste_steps "Continue" "${dest}"
  elif [[ "${MODE}" == "emit-only" ]]; then
    print_paste_steps "Continue" "${dest}"
  fi
}

emit_cline() {
  local dest="${GENERATED_DIR}/cline.mcp.fragment.json"
  if [[ "${MODE}" != "dry-run" ]]; then
    mkdir -p "${GENERATED_DIR}"
    render_template "${TEMPLATE_DIR}/cline_mcp.fragment.json.tmpl" "${dest}"
  fi
  emit_file "${dest}" "Cline MCP fragment"
  copy_intake
  if [[ "${MODE}" == "apply" ]]; then
    warn "Cline MCP settings path varies — cannot safely auto-merge."
    print_paste_steps "Cline" "${dest}"
  elif [[ "${MODE}" == "emit-only" ]]; then
    print_paste_steps "Cline" "${dest}"
  fi
}

emit_claude() {
  local dest="${GENERATED_DIR}/claude_desktop.mcp.fragment.json"
  if [[ "${MODE}" != "dry-run" ]]; then
    mkdir -p "${GENERATED_DIR}"
    render_template "${TEMPLATE_DIR}/mcp_servers.json.tmpl" "${dest}"
  fi
  emit_file "${dest}" "Claude Desktop MCP fragment"
  copy_intake
  if [[ "${MODE}" == "apply" ]]; then
    if [[ "$(uname -s)" != "Darwin" ]]; then
      warn "Claude Desktop auto-apply is macOS-only; fragment left at ${dest}"
      print_paste_steps "Claude Desktop" "${dest}"
      return 0
    fi
    local live="${HOME}/Library/Application Support/Claude/claude_desktop_config.json"
    merge_mcp_servers_json "${live}" "${dest}"
    info "Applied Claude Desktop config: ${live}"
    info "Restart Claude Desktop. Prefer prompt channel_intake."
  elif [[ "${MODE}" == "emit-only" ]]; then
    print_paste_steps "Claude Desktop" "${dest}"
  fi
}

emit_local() {
  local checklist="${GENERATED_DIR}/local_ollama_checklist.md"
  if [[ "${MODE}" != "dry-run" ]]; then
    mkdir -p "${GENERATED_DIR}"
    render_template "${TEMPLATE_DIR}/local_ollama_checklist.md.tmpl" "${checklist}"
  fi
  emit_file "${checklist}" "local Ollama checklist"
  if [[ "${LOCAL_CLIENT}" == "cline" ]]; then
    emit_cline
  else
    emit_continue
  fi
  info "Recommended: ollama pull qwen3:32b (or llama3.3:70b / qwen3:8b)"
}

emit_chatgpt() {
  local dest="${GENERATED_DIR}/chatgpt_deferred.md"
  if [[ "${MODE}" != "dry-run" ]]; then
    mkdir -p "${GENERATED_DIR}"
    render_template "${TEMPLATE_DIR}/chatgpt_deferred.md.tmpl" "${dest}"
  fi
  emit_file "${dest}" "ChatGPT deferred checklist"
  if [[ "${MODE}" == "apply" ]]; then
    warn "ChatGPT has nothing to merge in this release — checklist only."
  fi
  if [[ "${MODE}" != "dry-run" ]]; then
    cat "${dest}"
  fi
}

install_deps_now

case "${PLATFORM}" in
  cursor) emit_cursor ;;
  vscode-continue) emit_continue ;;
  vscode-cline) emit_cline ;;
  claude) emit_claude ;;
  local) emit_local ;;
  chatgpt) emit_chatgpt ;;
esac

info ""
info "Done."
info "Docs: docs/guides/CHANNEL_CREATOR_MCP_HOST_WIRING.md"
info "Smoke: list channels via MCP, then Search vs Paste → build."
exit 0
