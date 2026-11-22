#!/bin/zsh
# channel_creator_mcp_hosts.zsh — emit/apply MCP host configs (§7B)
# Usage:
#   zsh scripts/channel_creator_mcp_hosts.zsh --host all --mode emit --profile guided
#   zsh scripts/channel_creator_mcp_hosts.zsh --host cursor --mode dry-run

emulate -L zsh
setopt pipefail no_nomatch
autoload -U colors && colors

SCRIPT_DIR=${0:A:h}
STREAMTV_HOME=${STREAMTV_HOME:-${SCRIPT_DIR:h}}
HOST=all
MODE=emit
PROFILE=guided
PYTHON="${STREAMTV_HOME}/venv/bin/python"
REPO="$STREAMTV_HOME"
OUT_DIR="${STREAMTV_HOME}/scripts/channel-creator-mcp/generated"

typeset -a STEP_NAMES STEP_RESULTS
hdr()  { print -r -- ""; print -r -- "$fg_bold[cyan]==> $1$reset_color"; }
ok()   { print -r -- "$fg[green]  ✔ $1$reset_color"; }
info() { print -r -- "$fg[blue]  • $1$reset_color"; }
warn() { print -r -- "$fg[yellow]  ! $1$reset_color"; }
record() { STEP_NAMES+=("$1"); STEP_RESULTS+=("$2"); }
fail() {
  record "$1" FAIL
  print -r -- "$fg_bold[red]  ✘ FAILED: $1$reset_color"
  print -r -- "$fg[red]    $2$reset_color"
  summary
  exit 1
}
summary() {
  print -r -- ""
  print -r -- "$fg_bold[white]──────────────── SUMMARY ────────────────$reset_color"
  local i
  for (( i=1; i<=${#STEP_NAMES}; i++ )); do
    case ${STEP_RESULTS[$i]} in
      PASS) printf "%-40s %s\n" "${STEP_NAMES[$i]}" "$fg_bold[green]PASS$reset_color" ;;
      FAIL) printf "%-40s %s\n" "${STEP_NAMES[$i]}" "$fg_bold[red]FAIL$reset_color" ;;
      *)    printf "%-40s %s\n" "${STEP_NAMES[$i]}" "$fg[yellow]${STEP_RESULTS[$i]}$reset_color" ;;
    esac
  done
}

while (( $# )); do
  case $1 in
    --host) HOST=$2; shift 2 ;;
    --mode) MODE=$2; shift 2 ;;
    --profile) PROFILE=$2; shift 2 ;;
    --repo) REPO=$2; STREAMTV_HOME=$2; shift 2 ;;
    --python) PYTHON=$2; shift 2 ;;
    -h|--help)
      cat <<'EOF'
Usage: channel_creator_mcp_hosts.zsh --host <name|all> --mode <emit|apply|dry-run> [--profile guided]

Hosts: cursor vscode claude-desktop claude-code lmstudio continue cline goose
       open-webui chatgpt claude-web all

Interactive wrapper (recommended for humans):
  bash scripts/setup_channel_creator_mcp.sh

GitHub one-liner:
  curl -fsSL https://raw.githubusercontent.com/roto31/StreamTV/main/scripts/install_channel_creator_mcp.sh | bash

Env: STREAMTV_MCP_SKIP_SMOKE=1  skip stdio smoke (emit/apply still run)
EOF
      exit 0 ;;
    *) fail "args" "Unknown option: $1" ;;
  esac
done

[[ -x $PYTHON ]] || PYTHON=python3
mkdir -p "$OUT_DIR"

emit_stdio_block() {
  local name=$1
  local file=$2
  cat >"$file" <<EOF
{
  "mcpServers": {
    "streamtv-channel-creator": {
      "command": "${PYTHON}",
      "args": ["-m", "mcp_streamtv.main", "--profile", "${PROFILE}", "--transport", "stdio"],
      "cwd": "${REPO}",
      "env": {
        "STREAMTV_BASE_URL": "http://127.0.0.1:8410",
        "STREAMTV_MCP_PROFILE": "${PROFILE}"
      }
    }
  }
}
EOF
}

emit_vscode() {
  local file=$1
  cat >"$file" <<EOF
{
  "servers": {
    "streamtv-channel-creator": {
      "type": "stdio",
      "command": "${PYTHON}",
      "args": ["-m", "mcp_streamtv.main", "--profile", "${PROFILE}", "--transport", "stdio"],
      "cwd": "${REPO}",
      "env": {
        "STREAMTV_BASE_URL": "http://127.0.0.1:8410",
        "STREAMTV_MCP_PROFILE": "${PROFILE}"
      }
    }
  }
}
EOF
}

emit_open_webui() {
  local file=$1
  cat >"$file" <<EOF
{
  "type": "MCP (Streamable HTTP)",
  "url": "http://127.0.0.1:8411/mcp",
  "auth": "none (loopback) or Bearer \${STREAMTV_MCP_TOKEN}",
  "profile": "${PROFILE}",
  "notes": "Start: ${PYTHON} -m mcp_streamtv.main --transport http --host 127.0.0.1 --port 8411 --auth none --profile ${PROFILE}"
}
EOF
}

emit_chatgpt() {
  local file=$1
  cat >"$file" <<EOF
{
  "app_url": "https://YOUR_TUNNEL_HOST/mcp",
  "auth": "oauth (Sign in with Auth0/Access) OR dual (Access email + STREAMTV_MCP_TOKEN)",
  "never": "none on public URL; never tunnel :8410",
  "profile_recommendation": "streamtv.write → guided; streamtv.read → planner (see CHANNEL_CREATOR_MCP_AUTH.md)",
  "values_to_type": {
    "MCP URL": "https://YOUR_TUNNEL_HOST/mcp",
    "Auth (oauth)": "OAuth / Sign in with your IdP",
    "Auth (dual Lock 2)": "Bearer token from STREAMTV_MCP_TOKEN (do not commit)",
    "Auth (dual Lock 1)": "Cloudflare Access policy on the tunnel hostname"
  }
}
EOF
}

HOSTS=(cursor vscode claude-desktop claude-code lmstudio continue cline goose open-webui chatgpt claude-web)
if [[ $HOST != all ]]; then
  HOSTS=($HOST)
fi

hdr "1. Emit host configs (mode=$MODE profile=$PROFILE)"
for h in $HOSTS; do
  out="$OUT_DIR/${h}.${PROFILE}.json"
  case $h in
    cursor|claude-desktop|lmstudio|continue|cline|goose)
      emit_stdio_block "$h" "$out" ;;
    vscode)
      emit_vscode "$out" ;;
    claude-code)
      print -r -- "{\"mcpServers\":{\"streamtv-channel-creator\":{\"command\":\"${PYTHON}\",\"args\":[\"-m\",\"mcp_streamtv.main\",\"--profile\",\"${PROFILE}\"],\"cwd\":\"${REPO}\",\"env\":{\"STREAMTV_BASE_URL\":\"http://127.0.0.1:8410\",\"STREAMTV_MCP_PROFILE\":\"${PROFILE}\"}}},\"claude_mcp_add\":\"claude mcp add streamtv-channel-creator -- ${PYTHON} -m mcp_streamtv.main --profile ${PROFILE}\"}" >"$out"
      ;;
    open-webui)
      emit_open_webui "$out" ;;
    chatgpt|claude-web)
      emit_chatgpt "$out" ;;
    *) fail "emit" "unknown host $h" ;;
  esac
  "$PYTHON" -m json.tool "$out" >/dev/null || fail "json" "$out invalid"
  ok "wrote $out"
done
record "1. Emit configs" PASS

if [[ $MODE == dry-run ]]; then
  info "dry-run: not applying or smoking"
  record "2. Apply" SKIP
  record "3. Smoke" SKIP
  summary
  print -r -- "$fg_bold[green]OVERALL: PASS$reset_color"
  exit 0
fi

hdr "2. Apply"
if [[ $MODE == apply ]]; then
  warn "apply merges into live host configs — backups use .bak.<stamp>"
  # Cursor project config
  if [[ " ${HOSTS[*]} " == *" cursor "* ]] || [[ $HOST == all ]]; then
    dest="${REPO}/.cursor/mcp.json"
    stamp=$(date +%Y%m%d%H%M%S)
    [[ -f $dest ]] && cp "$dest" "${dest}.bak.${stamp}" && ok "backed up $dest"
    cp "$OUT_DIR/cursor.${PROFILE}.json" "$dest"
    ok "applied cursor → $dest"
  fi
  record "2. Apply" PASS
else
  info "mode=emit — skip live apply"
  record "2. Apply" SKIP
fi

hdr "3. Smoke (stdio)"
if [[ ${STREAMTV_MCP_SKIP_SMOKE:-0} == 1 ]]; then
  info "STREAMTV_MCP_SKIP_SMOKE=1 — skip smoke"
  record "3. Smoke stdio" SKIP
elif "$PYTHON" "${STREAMTV_HOME}/scripts/mcp_smoke.py" --transport stdio --profile "$PROFILE"; then
  ok "stdio smoke"
  record "3. Smoke stdio" PASS
else
  fail "3. Smoke stdio" "mcp_smoke.py failed (is StreamTV on :8410? or set STREAMTV_MCP_SKIP_SMOKE=1)"
fi

hdr "4. Compact intake (local models)"
"$PYTHON" - <<PY
from mcp_streamtv import resources
print(resources.CHANNEL_INTAKE_COMPACT[:500])
print("…")
PY
ok "printed compact intake"
record "4. Compact intake" PASS

summary
print -r -- "$fg_bold[green]OVERALL: PASS$reset_color"
print -r -- "Interactive: bash scripts/setup_channel_creator_mcp.sh"
print -r -- "One-liner: curl -fsSL https://raw.githubusercontent.com/roto31/StreamTV/main/scripts/install_channel_creator_mcp.sh | bash"
