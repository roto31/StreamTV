#!/bin/bash
# Interactive Channel Creator MCP wiring — installs deps, emits/applies host
# configs (guided profile), optional Archive.org MCP, remote tunnel checklist.
# Delegates emit/apply/smoke to channel_creator_mcp_hosts.zsh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
HOSTS_ZSH="${SCRIPT_DIR}/channel_creator_mcp_hosts.zsh"
REMOTE_ZSH="${SCRIPT_DIR}/channel_creator_mcp_remote.zsh"
HELPER_DIR="${SCRIPT_DIR}/channel-creator-mcp"
GENERATED_DIR="${HELPER_DIR}/generated"

PLATFORM=""
MODE=""
REPO_ROOT=""
PYTHON_BIN=""
BASE_URL="http://127.0.0.1:8410"
PROFILE="guided"
WITH_ARCHIVE=""
INSTALL_DEPS=""
RUN_SMOKE=""
RUN_REMOTE=""
HOST_KEY=""

usage() {
  cat <<'EOF'
Usage: setup_channel_creator_mcp.sh [options]

Wire StreamTV Channel Creator MCP for your AI host (interactive by default).

  1) Platform  2) Mode (apply / dry-run / emit)  3) Shared options
  → pip deps → hosts.zsh emit/apply/smoke → next-step docs

Options:
  --platform cursor|vscode|continue|cline|claude-desktop|claude-code|
             lmstudio|goose|open-webui|local|remote|chatgpt|claude-web|all
  --apply | --dry-run | --emit-only
  --profile guided|planner|builder|full   (default: guided)
  --repo-root PATH
  --python PATH
  --base-url URL                          (default: http://127.0.0.1:8410)
  --with-archive | --no-archive
  --install-deps | --no-install-deps
  --smoke | --no-smoke
  --remote-check                          Run channel_creator_mcp_remote.zsh after
  -h, --help

Docs:
  Wiki  https://github.com/roto31/StreamTV/wiki/Channel-Creator-MCP-Host-Wiring
  Repo  docs/guides/CHANNEL_CREATOR_MCP_HOST_WIRING.md

GitHub one-liner (clone public repo + this setup):
  curl -fsSL https://raw.githubusercontent.com/roto31/StreamTV/main/scripts/install_channel_creator_mcp.sh | bash

Non-interactive emit (generator this wraps):
  zsh scripts/channel_creator_mcp_hosts.zsh --host all --mode emit --profile guided

Exit: 0 success, 1 runtime, 2 usage/config
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

while [[ $# -gt 0 ]]; do
  case "$1" in
    --platform) PLATFORM="${2:-}"; shift 2 ;;
    --apply) MODE="apply"; shift ;;
    --dry-run) MODE="dry-run"; shift ;;
    --emit-only) MODE="emit"; shift ;;
    --profile) PROFILE="${2:-}"; shift 2 ;;
    --repo-root) REPO_ROOT="${2:-}"; shift 2 ;;
    --python) PYTHON_BIN="${2:-}"; shift 2 ;;
    --base-url) BASE_URL="${2:-}"; shift 2 ;;
    --with-archive) WITH_ARCHIVE="y"; shift ;;
    --no-archive) WITH_ARCHIVE="n"; shift ;;
    --install-deps) INSTALL_DEPS="y"; shift ;;
    --no-install-deps) INSTALL_DEPS="n"; shift ;;
    --smoke) RUN_SMOKE="y"; shift ;;
    --no-smoke) RUN_SMOKE="n"; shift ;;
    --remote-check) RUN_REMOTE="y"; shift ;;
    -h|--help) usage; exit 0 ;;
    *)
      err "unknown option: $1"
      usage >&2
      exit 2
      ;;
  esac
done

case "${PROFILE}" in
  guided|planner|builder|full) ;;
  *)
    err "invalid --profile: ${PROFILE}"
    exit 2
    ;;
esac

prompt_platform() {
  cat <<'EOF'

Which host are you wiring?
  1) Cursor                          (recommended — apply .cursor/mcp.json)
  2) VS Code Copilot agent
  3) VS Code — Continue
  4) VS Code — Cline
  5) Claude Desktop
  6) Claude Code
  7) LM Studio
  8) Goose
  9) Open WebUI (loopback HTTP :8411)
 10) Local model helper (LM Studio + Continue checklist)
 11) ChatGPT / Claude web (remote tunnel :8411)
 12) All local hosts (emit snippets only)
EOF
  local choice
  read -r -p "Select [1-12]: " choice || true
  case "${choice}" in
    1) PLATFORM="cursor" ;;
    2) PLATFORM="vscode" ;;
    3) PLATFORM="continue" ;;
    4) PLATFORM="cline" ;;
    5) PLATFORM="claude-desktop" ;;
    6) PLATFORM="claude-code" ;;
    7) PLATFORM="lmstudio" ;;
    8) PLATFORM="goose" ;;
    9) PLATFORM="open-webui" ;;
    10) PLATFORM="local" ;;
    11) PLATFORM="remote" ;;
    12) PLATFORM="all" ;;
    *)
      err "invalid platform choice: ${choice}"
      exit 2
      ;;
  esac
}

prompt_mode() {
  cat <<'EOF'

Mode?
  1) Apply — write live host config where supported (Cursor; Claude Desktop on macOS)
  2) Dry-run — print actions; write nothing
  3) Emit — write snippets under scripts/channel-creator-mcp/generated/
EOF
  local choice
  read -r -p "Select [1-3]: " choice || true
  case "${choice}" in
    1) MODE="apply" ;;
    2) MODE="dry-run" ;;
    3) MODE="emit" ;;
    *)
      err "invalid mode choice: ${choice}"
      exit 2
      ;;
  esac
}

map_host_key() {
  case "${PLATFORM}" in
    cursor) HOST_KEY="cursor" ;;
    vscode) HOST_KEY="vscode" ;;
    continue|vscode-continue) HOST_KEY="continue"; PLATFORM="continue" ;;
    cline|vscode-cline) HOST_KEY="cline"; PLATFORM="cline" ;;
    claude|claude-desktop) HOST_KEY="claude-desktop"; PLATFORM="claude-desktop" ;;
    claude-code) HOST_KEY="claude-code" ;;
    lmstudio) HOST_KEY="lmstudio" ;;
    goose) HOST_KEY="goose" ;;
    open-webui) HOST_KEY="open-webui" ;;
    local) HOST_KEY="lmstudio" ;;
    remote|chatgpt|claude-web)
      HOST_KEY="chatgpt"
      PLATFORM="remote"
      ;;
    all) HOST_KEY="all" ;;
    *)
      err "invalid --platform: ${PLATFORM}"
      exit 2
      ;;
  esac
}

[[ -z "${PLATFORM}" ]] && prompt_platform
map_host_key
[[ -z "${MODE}" ]] && prompt_mode
case "${MODE}" in
  apply|dry-run|emit) ;;
  *)
    err "invalid mode: ${MODE}"
    exit 2
    ;;
esac

if [[ -z "${REPO_ROOT}" ]]; then
  if [[ -t 0 ]]; then
    REPO_ROOT="$(prompt_default "StreamTV repo root" "${DEFAULT_REPO_ROOT}")"
  else
    REPO_ROOT="${DEFAULT_REPO_ROOT}"
  fi
fi
REPO_ROOT="$(cd "${REPO_ROOT}" && pwd)" || {
  err "repo root not found: ${REPO_ROOT}"
  exit 2
}

if [[ ! -d "${REPO_ROOT}/mcp_streamtv" ]]; then
  err "mcp_streamtv not found under ${REPO_ROOT}"
  exit 2
fi
if [[ ! -f "${HOSTS_ZSH}" ]]; then
  err "missing ${HOSTS_ZSH}"
  exit 2
fi

HELPER_DIR="${REPO_ROOT}/scripts/channel-creator-mcp"
GENERATED_DIR="${HELPER_DIR}/generated"
INTAKE_SRC="${REPO_ROOT}/mcp_streamtv/prompts/channel_intake.md"
INTAKE_COMPACT_SRC="${REPO_ROOT}/mcp_streamtv/prompts/channel_intake_compact.md"

if [[ -z "${PYTHON_BIN}" ]]; then
  local_default="python3"
  if [[ -x "${REPO_ROOT}/venv/bin/python" ]]; then
    local_default="${REPO_ROOT}/venv/bin/python"
  fi
  if [[ -t 0 ]]; then
    PYTHON_BIN="$(prompt_default "Python binary" "${local_default}")"
  else
    PYTHON_BIN="${local_default}"
  fi
fi

if [[ -t 0 ]]; then
  BASE_URL="$(prompt_default "STREAMTV_BASE_URL" "${BASE_URL}")"
  if [[ -z "${WITH_ARCHIVE}" ]]; then
    if prompt_yn "Also emit optional Archive.org MCP (mcp_archive_org) snippet?" "n"; then
      WITH_ARCHIVE="y"
    else
      WITH_ARCHIVE="n"
    fi
  fi
  if [[ -z "${INSTALL_DEPS}" ]]; then
    if [[ "${MODE}" == "dry-run" ]]; then
      INSTALL_DEPS="n"
    elif prompt_yn "Install MCP pip deps now?" "y"; then
      INSTALL_DEPS="y"
    else
      INSTALL_DEPS="n"
    fi
  fi
  if [[ -z "${RUN_SMOKE}" ]]; then
    if [[ "${MODE}" == "dry-run" ]]; then
      RUN_SMOKE="n"
    elif prompt_yn "Run stdio MCP smoke after wire?" "y"; then
      RUN_SMOKE="y"
    else
      RUN_SMOKE="n"
    fi
  fi
  if [[ "${PLATFORM}" == "remote" || "${PLATFORM}" == "open-webui" ]]; then
    if [[ -z "${RUN_REMOTE}" ]] && prompt_yn "Run remote/tunnel checklist (channel_creator_mcp_remote.zsh)?" "y"; then
      RUN_REMOTE="y"
    fi
  fi
else
  WITH_ARCHIVE="${WITH_ARCHIVE:-n}"
  INSTALL_DEPS="${INSTALL_DEPS:-n}"
  RUN_SMOKE="${RUN_SMOKE:-n}"
  RUN_REMOTE="${RUN_REMOTE:-n}"
fi

info ""
info "Platform: ${PLATFORM} → hosts.zsh --host ${HOST_KEY}"
info "Mode:     ${MODE}"
info "Profile:  ${PROFILE}"
info "Repo:     ${REPO_ROOT}"
info "Python:   ${PYTHON_BIN}"
info "Base URL: ${BASE_URL}"
info "Archive:  ${WITH_ARCHIVE}"
info "Deps:     ${INSTALL_DEPS}"
info "Smoke:    ${RUN_SMOKE}"
info ""

install_deps_now() {
  if [[ "${INSTALL_DEPS}" != "y" ]]; then
    return 0
  fi
  if [[ "${MODE}" == "dry-run" ]]; then
    info "[dry-run] would: ${PYTHON_BIN} -m pip install -r requirements-mcp-streamtv.txt"
    [[ "${WITH_ARCHIVE}" == "y" ]] && info "[dry-run] would: pip install -r requirements-mcp-archive-org.txt"
    return 0
  fi
  info "Installing MCP dependencies…"
  "${PYTHON_BIN}" -m pip install -r "${REPO_ROOT}/requirements-mcp-streamtv.txt"
  if [[ "${WITH_ARCHIVE}" == "y" ]]; then
    "${PYTHON_BIN}" -m pip install -r "${REPO_ROOT}/requirements-mcp-archive-org.txt"
  fi
  info "MCP dependencies installed."
}

emit_intake_copies() {
  if [[ "${MODE}" == "dry-run" ]]; then
    info "[dry-run] would copy intake prompts → ${GENERATED_DIR}/"
    return 0
  fi
  mkdir -p "${GENERATED_DIR}"
  if [[ -f "${INTAKE_SRC}" ]]; then
    cp "${INTAKE_SRC}" "${GENERATED_DIR}/intake_system_prompt.md"
    info "Wrote ${GENERATED_DIR}/intake_system_prompt.md"
  else
    warn "missing ${INTAKE_SRC}"
  fi
  if [[ -f "${INTAKE_COMPACT_SRC}" ]]; then
    cp "${INTAKE_COMPACT_SRC}" "${GENERATED_DIR}/intake_compact.md"
  else
    (
      cd "${REPO_ROOT}"
      "${PYTHON_BIN}" - <<'PY'
from pathlib import Path
from mcp_streamtv.resources import CHANNEL_INTAKE_COMPACT
Path("scripts/channel-creator-mcp/generated/intake_compact.md").write_text(
    CHANNEL_INTAKE_COMPACT if CHANNEL_INTAKE_COMPACT.endswith("\n") else CHANNEL_INTAKE_COMPACT + "\n",
    encoding="utf-8",
)
print("Wrote scripts/channel-creator-mcp/generated/intake_compact.md")
PY
    )
  fi
  [[ -f "${GENERATED_DIR}/intake_compact.md" ]] && info "Wrote ${GENERATED_DIR}/intake_compact.md"
}

emit_archive_snippet() {
  if [[ "${WITH_ARCHIVE}" != "y" ]]; then
    return 0
  fi
  local dest="${GENERATED_DIR}/archive_org.${PROFILE}.json"
  if [[ "${MODE}" == "dry-run" ]]; then
    info "[dry-run] would write ${dest}"
    return 0
  fi
  mkdir -p "${GENERATED_DIR}"
  cat >"${dest}" <<EOF
{
  "mcpServers": {
    "archive-org": {
      "command": "${PYTHON_BIN}",
      "args": ["-m", "mcp_archive_org.main"],
      "cwd": "${REPO_ROOT}",
      "env": {}
    }
  }
}
EOF
  info "Wrote optional Archive.org MCP fragment: ${dest}"
  info "Merge into the host MCP config alongside streamtv-channel-creator."
}

emit_local_checklist() {
  [[ "${PLATFORM}" == "local" ]] || return 0
  local dest="${GENERATED_DIR}/local_model_checklist.md"
  if [[ "${MODE}" == "dry-run" ]]; then
    info "[dry-run] would write ${dest}"
    return 0
  fi
  mkdir -p "${GENERATED_DIR}"
  cat >"${dest}" <<EOF
# Local model — Channel Creator MCP

1. Pull a tool-capable model: \`ollama pull qwen3:32b\` (or llama3.3:70b / qwen3:8b).
2. Wire MCP via LM Studio / Continue / Cline using:
   \`${GENERATED_DIR}/lmstudio.${PROFILE}.json\`
   (or continue/cline fragments from the same directory).
3. Use **compact** intake for small context:
   \`${GENERATED_DIR}/intake_compact.md\`
   MCP resource: \`streamtv://prompts/channel-intake-compact\`
4. Verify up to \`channel_plan\`; say **build** only when ready.

StreamTV API: ${BASE_URL}
Profile: ${PROFILE}
EOF
  info "Wrote ${dest}"
}

emit_remote_checklist() {
  [[ "${PLATFORM}" == "remote" ]] || return 0
  local dest="${GENERATED_DIR}/remote_chatgpt_claude_web.md"
  if [[ "${MODE}" == "dry-run" ]]; then
    info "[dry-run] would write ${dest}"
    return 0
  fi
  mkdir -p "${GENERATED_DIR}"
  cat >"${dest}" <<EOF
# ChatGPT / Claude web — Channel Creator MCP (remote)

Never tunnel StreamTV **:8410**. Expose only MCP Streamable HTTP **:8411**.

## Start MCP HTTP on the Mac

\`\`\`bash
export STREAMTV_MCP_AUTH=dual   # or oauth | bearer
export STREAMTV_MCP_TOKEN="\$(openssl rand -hex 32)"
# dual also needs:
#   STREAMTV_MCP_ACCESS_TEAM=myteam
#   STREAMTV_MCP_ACCESS_AUDIENCE=<Access AUD tag>

${PYTHON_BIN} -m mcp_streamtv.main \\
  --transport http --host 127.0.0.1 --port 8411 \\
  --auth dual --profile ${PROFILE}
\`\`\`

## Tunnel checklist

\`\`\`bash
zsh scripts/channel_creator_mcp_remote.zsh
# optional: --public-url https://YOUR_HOST/mcp
\`\`\`

## Host values

| Field | Value |
|-------|-------|
| MCP URL | \`https://YOUR_HOST/mcp\` |
| Auth (oauth) | Sign in with Auth0 / Cloudflare Access |
| Auth (dual Lock 1) | Cloudflare Access on the hostname |
| Auth (dual Lock 2) | Bearer \`STREAMTV_MCP_TOKEN\` |

Generated JSON sketch: \`${GENERATED_DIR}/chatgpt.${PROFILE}.json\`

Wiki: https://github.com/roto31/StreamTV/wiki/Channel-Creator-MCP-Auth
EOF
  info "Wrote ${dest}"
}

run_hosts_zsh() {
  local hosts_mode="${MODE}"
  local -a cmd=(
    zsh "${HOSTS_ZSH}"
    --host "${HOST_KEY}"
    --mode "${hosts_mode}"
    --profile "${PROFILE}"
    --repo "${REPO_ROOT}"
    --python "${PYTHON_BIN}"
  )

  if [[ "${RUN_SMOKE}" != "y" ]]; then
    export STREAMTV_MCP_SKIP_SMOKE=1
  else
    unset STREAMTV_MCP_SKIP_SMOKE || true
  fi

  info "Running: STREAMTV_MCP_SKIP_SMOKE=${STREAMTV_MCP_SKIP_SMOKE:-0} ${cmd[*]}"
  if ! "${cmd[@]}"; then
    warn "hosts.zsh failed (often smoke if StreamTV :8410 is down)."
    warn "Check ${GENERATED_DIR} — start StreamTV and re-run with --smoke if needed."
    if [[ "${RUN_SMOKE}" == "y" ]]; then
      return 1
    fi
  fi
  return 0
}

apply_claude_desktop_if_needed() {
  [[ "${MODE}" == "apply" ]] || return 0
  [[ "${HOST_KEY}" == "claude-desktop" || "${HOST_KEY}" == "all" ]] || return 0
  [[ "$(uname -s)" == "Darwin" ]] || {
    warn "Claude Desktop apply is macOS-only; use emitted fragment."
    return 0
  }
  local frag="${GENERATED_DIR}/claude-desktop.${PROFILE}.json"
  local live="${HOME}/Library/Application Support/Claude/claude_desktop_config.json"
  if [[ ! -f "${frag}" ]]; then
    warn "missing fragment ${frag}"
    return 0
  fi
  mkdir -p "$(dirname "${live}")"
  if [[ -f "${live}" ]]; then
    local bak="${live}.bak.$(date +%Y%m%d%H%M%S)"
    cp "${live}" "${bak}"
    info "Backup: ${bak}"
  else
    echo '{}' >"${live}"
  fi
  python3 - "${live}" "${frag}" <<'PY'
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
  info "Restart Claude Desktop. Prefer prompt channel_intake."
}

print_next_steps() {
  cat <<EOF

──────────────── next steps ────────────────
1. StreamTV must listen on ${BASE_URL} (production LaunchAgent cwd = this repo).
2. Host fragment(s): ${GENERATED_DIR}/*.${PROFILE}.json
3. Intake (system rule): ${GENERATED_DIR}/intake_system_prompt.md
   Compact (local models): ${GENERATED_DIR}/intake_compact.md
4. First ask: create a channel in plain language → Search vs Paste → say **build**.
5. Never use Archive.org *.ia.mp4 URLs — canonical …/download/<id>/<file>.mp4 only.

Docs (wiki-first):
  https://github.com/roto31/StreamTV/wiki/Channel-Creator-MCP
  https://github.com/roto31/StreamTV/wiki/Channel-Creator-MCP-Host-Wiring
  https://github.com/roto31/StreamTV/wiki/Channel-Creator-MCP-Auth

Repo mirrors:
  docs/guides/CHANNEL_CREATOR_MCP.md
  docs/guides/CHANNEL_CREATOR_MCP_HOST_WIRING.md
  docs/guides/CHANNEL_CREATOR_MCP_AUTH.md
EOF
  case "${PLATFORM}" in
    cursor)
      info "Cursor: enable skill streamtv-channel-creator; MCP at .cursor/mcp.json"
      ;;
    claude-code)
      info "Or: claude mcp add streamtv-channel-creator -- ${PYTHON_BIN} -m mcp_streamtv.main --profile ${PROFILE}"
      ;;
    open-webui)
      info "Start HTTP: ${PYTHON_BIN} -m mcp_streamtv.main --transport http --host 127.0.0.1 --port 8411 --auth none --profile ${PROFILE}"
      ;;
    remote)
      info "Start HTTP with auth≠none, then: zsh scripts/channel_creator_mcp_remote.zsh"
      ;;
  esac
}

install_deps_now
run_hosts_zsh
emit_intake_copies
emit_archive_snippet
emit_local_checklist
emit_remote_checklist
apply_claude_desktop_if_needed

# Patch STREAMTV_BASE_URL in generated JSON if non-default
if [[ "${MODE}" != "dry-run" && "${BASE_URL}" != "http://127.0.0.1:8410" ]]; then
  info "Rewriting STREAMTV_BASE_URL → ${BASE_URL} in generated JSON…"
  python3 - "${GENERATED_DIR}" "${PROFILE}" "${BASE_URL}" <<'PY'
import json
import sys
from pathlib import Path

gen, profile, base = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
for path in gen.glob(f"*.{profile}.json"):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        continue
    changed = False
    for key in ("mcpServers", "servers"):
        block = data.get(key)
        if not isinstance(block, dict):
            continue
        for _name, cfg in block.items():
            if isinstance(cfg, dict) and isinstance(cfg.get("env"), dict):
                if "STREAMTV_BASE_URL" in cfg["env"]:
                    cfg["env"]["STREAMTV_BASE_URL"] = base
                    changed = True
    if changed:
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"updated {path}")
PY
fi

if [[ "${RUN_REMOTE}" == "y" ]]; then
  if [[ -f "${REMOTE_ZSH}" ]]; then
    info ""
    info "Remote checklist…"
    if [[ "${MODE}" == "dry-run" ]]; then
      info "[dry-run] would run: zsh ${REMOTE_ZSH}"
    else
      zsh "${REMOTE_ZSH}" || warn "remote checklist reported issues (auth/tunnel not ready yet is OK)."
    fi
  else
    warn "missing ${REMOTE_ZSH}"
  fi
fi

print_next_steps
info ""
info "Done."
exit 0
