#!/bin/zsh
# channel_creator_mcp_remote.zsh — Cloudflare tunnel checklist for ChatGPT/Claude web (§7A.3)
# Usage:
#   zsh scripts/channel_creator_mcp_remote.zsh
#   zsh scripts/channel_creator_mcp_remote.zsh --apply   # backup + append tunnel ingress (owner)
#   zsh scripts/channel_creator_mcp_remote.zsh --public-url https://mcp.example.com

emulate -L zsh
setopt pipefail no_nomatch
autoload -U colors && colors

SCRIPT_DIR=${0:A:h}
STREAMTV_HOME=${STREAMTV_HOME:-${SCRIPT_DIR:h}}
APPLY=0
PUBLIC_URL=""
HOST=127.0.0.1
PORT=8411
PATH_MCP=/mcp

typeset -a STEP_NAMES STEP_RESULTS
hdr()  { print -r -- ""; print -r -- "$fg_bold[cyan]==> $1$reset_color"; }
ok()   { print -r -- "$fg[green]  ✔ $1$reset_color"; }
info() { print -r -- "$fg[blue]  • $1$reset_color"; }
warn() { print -r -- "$fg[yellow]  ! $1$reset_color"; }
record() { STEP_NAMES+=("$1"); STEP_RESULTS+=("$2"); }
fail() {
  record "$1" FAIL
  print -r -- "$fg_bold[red]  ✘ FAILED: $1 — $2$reset_color"
  summary
  exit 1
}
summary() {
  print -r -- ""
  print -r -- "$fg_bold[white]──────────────── SUMMARY ────────────────$reset_color"
  local i
  for (( i=1; i<=${#STEP_NAMES}; i++ )); do
    case ${STEP_RESULTS[$i]} in
      PASS) printf "%-46s %s\n" "${STEP_NAMES[$i]}" "$fg_bold[green]PASS$reset_color" ;;
      FAIL) printf "%-46s %s\n" "${STEP_NAMES[$i]}" "$fg_bold[red]FAIL$reset_color" ;;
      *)    printf "%-46s %s\n" "${STEP_NAMES[$i]}" "$fg[yellow]${STEP_RESULTS[$i]}$reset_color" ;;
    esac
  done
}

while (( $# )); do
  case $1 in
    --apply) APPLY=1; shift ;;
    --public-url) PUBLIC_URL=$2; shift 2 ;;
    --host) HOST=$2; shift 2 ;;
    --port) PORT=$2; shift 2 ;;
    -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
    *) fail "args" "Unknown option $1" ;;
  esac
done

AUTH=${STREAMTV_MCP_AUTH:-none}

hdr "1. Auth must not be none for remote"
case $AUTH in
  bearer|oauth|dual) ok "auth=$AUTH" ; record "1. Auth" PASS ;;
  none)
    fail "1. Auth" "STREAMTV_MCP_AUTH=none — set bearer, oauth, or dual before tunneling"
    ;;
  *)
    fail "1. Auth" "unknown STREAMTV_MCP_AUTH=$AUTH (want bearer|oauth|dual)"
    ;;
esac

if [[ $AUTH == dual || $AUTH == bearer ]]; then
  if [[ ${#STREAMTV_MCP_TOKEN} -lt 32 ]]; then
    fail "1b. Token" "STREAMTV_MCP_TOKEN must be ≥32 chars for auth=$AUTH"
  fi
  ok "STREAMTV_MCP_TOKEN length ok"
  record "1b. Token" PASS
else
  record "1b. Token" SKIP
fi

if [[ $AUTH == dual ]]; then
  if [[ -z ${STREAMTV_MCP_ACCESS_TEAM:-${STREAMTV_MCP_OAUTH_DOMAIN:-}} ]]; then
    fail "1c. Access" "dual needs STREAMTV_MCP_ACCESS_TEAM (or STREAMTV_MCP_OAUTH_DOMAIN)"
  fi
  if [[ -z ${STREAMTV_MCP_ACCESS_AUDIENCE:-${STREAMTV_MCP_OAUTH_AUDIENCE:-}} ]]; then
    fail "1c. Access" "dual needs STREAMTV_MCP_ACCESS_AUDIENCE (Access AUD tag)"
  fi
  ok "Access team + AUD present"
  record "1c. Access" PASS
elif [[ $AUTH == oauth ]]; then
  if [[ -z ${STREAMTV_MCP_OAUTH_ISSUER:-} && -z ${STREAMTV_MCP_OAUTH_DOMAIN:-} ]]; then
    fail "1c. OAuth" "oauth needs STREAMTV_MCP_OAUTH_ISSUER or provider domain"
  fi
  ok "OAuth issuer/domain present"
  record "1c. Access" PASS
else
  record "1c. Access" SKIP
fi

hdr "2. Loopback MCP HTTP"
CODE=$(curl -sS -o /tmp/streamtv_mcp_remote_body.txt -w '%{http_code}' \
  -H "Authorization: Bearer ${STREAMTV_MCP_TOKEN:-}" \
  "http://${HOST}:${PORT}${PATH_MCP}" || true)
# Any HTTP response (incl 401/406) means something is listening; 000 = down
if [[ $CODE == 000 ]]; then
  fail "2. Loopback" "nothing listening on ${HOST}:${PORT}${PATH_MCP} — start mcp_streamtv with --transport http"
fi
ok "loopback responded HTTP $CODE"
record "2. Loopback" PASS

hdr "3. Tunnel ingress block (print only unless --apply)"
BLOCK=$(cat <<EOF
  - hostname: YOUR_MCP_HOSTNAME
    service: http://127.0.0.1:${PORT}
EOF
)
print -r -- "$BLOCK"
info "Never route :8410 through the tunnel — only the MCP port ${PORT}."
if [[ $AUTH == dual ]]; then
  info "Put Cloudflare Access (email OTP / IdP) on YOUR_MCP_HOSTNAME — Lock 1."
  info "Mac still checks STREAMTV_MCP_TOKEN on Authorization: Bearer — Lock 2."
fi
record "3. Ingress block" PASS

if (( APPLY )); then
  hdr "3b. Apply to cloudflared config"
  CF="${HOME}/.cloudflared/config.yml"
  [[ -f $CF ]] || fail "3b. Apply" "missing $CF"
  stamp=$(date +%Y%m%d%H%M%S)
  cp "$CF" "${CF}.bak.${stamp}"
  ok "backed up ${CF}.bak.${stamp}"
  print -r -- "" >>"$CF"
  print -r -- "# streamtv MCP (added ${stamp})" >>"$CF"
  print -r -- "$BLOCK" >>"$CF"
  ok "appended ingress — edit YOUR_MCP_HOSTNAME then restart cloudflared"
  record "3b. Apply" PASS
else
  record "3b. Apply" SKIP
fi

hdr "4. Public URL unauthenticated initialize → 401/302 (owner-run if URL set)"
if [[ -n $PUBLIC_URL ]]; then
  PCODE=$(curl -sS -o /tmp/streamtv_mcp_public.txt -w '%{http_code}' \
    -X POST "$PUBLIC_URL" \
    -H 'Content-Type: application/json' \
    -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' || true)
  # Access may redirect (302) to login; Mac dual/oauth/bearer returns 401
  if [[ $PCODE == 401 || $PCODE == 302 || $PCODE == 301 ]]; then
    ok "public unauthenticated → HTTP $PCODE (expected challenge)"
    record "4. Public 401" PASS
  else
    warn "public returned HTTP $PCODE (expected 401 or Access redirect) — owner must verify"
    record "4. Public 401" "OWNER ($PCODE)"
  fi
else
  info "pass --public-url https://… to verify; recorded as owner-run"
  record "4. Public 401" OWNER
fi

hdr "5. Values for ChatGPT / Claude web"
info "MCP URL: https://YOUR_HOST/mcp"
case $AUTH in
  dual)
    info "Lock 1: Cloudflare Access (email login at the tunnel hostname)"
    info "Lock 2: Authorization: Bearer \$STREAMTV_MCP_TOKEN (type into ChatGPT/Claude)"
    ;;
  oauth)
    info "Auth: Sign in with Auth0 / Cloudflare Access (OAuth JWT → Mac JWKS check)"
    info "Scopes: streamtv.read → planner, streamtv.write → guided"
    ;;
  bearer)
    info "Auth: Bearer token from STREAMTV_MCP_TOKEN only (no Access edge)"
    ;;
esac
info "Claude web: Settings → Connectors → custom connector → same URL"
info "Owner decision recorded: docs/guides/CHANNEL_CREATOR_MCP_AUTH.md"
record "5. App values" PASS

summary
print -r -- "$fg_bold[green]OVERALL: PASS (local checks)$reset_color"
