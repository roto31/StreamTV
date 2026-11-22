#!/usr/bin/env zsh
# install_vintage_kids_xmas.zsh
# Adds channel 1225 "Vintage Kids Christmas" to StreamTV:
#   1. checks the two YAML files, 2. checks every source URL is still online,
#   3. checks the StreamTV server, 4. installs the schedule, 5. imports the channel,
#   6. confirms the channel is in the M3U and the guide (XMLTV).
#
# Usage:
#   ./install_vintage_kids_xmas.zsh [-d /path/to/StreamTV-source] [-u http://192.168.1.120:8410] [-k API_KEY] [--skip-url-check]
# Env equivalents: STREAMTV_HOME, STREAMTV_URL, STREAMTV_API_KEY
#
# Files expected next to this script:
#   channel-1225-vintage-kids-christmas.yaml
#   schedules/1225.yml

emulate -L zsh
setopt pipefail no_nomatch
autoload -U colors && colors

# ---------- settings ----------
SCRIPT_DIR=${0:A:h}
CHANNEL_NO="1225"
CHANNEL_YAML="$SCRIPT_DIR/channel-1225-vintage-kids-christmas.yaml"
SCHEDULE_YAML="$SCRIPT_DIR/schedules/1225.yml"
STREAMTV_URL=${STREAMTV_URL:-http://192.168.1.120:8410}
STREAMTV_HOME=${STREAMTV_HOME:-}
STREAMTV_API_KEY=${STREAMTV_API_KEY:-}
SKIP_URL_CHECK=0
WORK=$(mktemp -d /tmp/stv-xmas.XXXXXX)

while (( $# )); do
  case $1 in
    -d) STREAMTV_HOME=$2; shift 2 ;;
    -u) STREAMTV_URL=$2; shift 2 ;;
    -k) STREAMTV_API_KEY=$2; shift 2 ;;
    --skip-url-check) SKIP_URL_CHECK=1; shift ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    *) print -r -- "$fg_bold[red]Unknown option: $1$reset_color"; exit 2 ;;
  esac
done

typeset -a STEP_NAMES STEP_RESULTS
typeset -a ARTIFACTS

hdr()  { print -r -- ""; print -r -- "$fg_bold[cyan]==> $1$reset_color"; }
ok()   { print -r -- "$fg[green]  ✔ $1$reset_color"; }
info() { print -r -- "$fg[blue]  • $1$reset_color"; }
warn() { print -r -- "$fg[yellow]  ! $1$reset_color"; }

record() { STEP_NAMES+=("$1"); STEP_RESULTS+=("$2"); }

summary() {
  print -r -- ""
  print -r -- "$fg_bold[white]──────────────── SUMMARY ────────────────$reset_color"
  printf "%-46s %s\n" "STEP" "RESULT"
  local i
  for (( i=1; i<=${#STEP_NAMES}; i++ )); do
    case ${STEP_RESULTS[$i]} in
      PASS) printf "%-46s %s\n" "${STEP_NAMES[$i]}" "$fg_bold[green]PASS$reset_color" ;;
      FAIL) printf "%-46s %s\n" "${STEP_NAMES[$i]}" "$fg_bold[red]FAIL$reset_color" ;;
      *)    printf "%-46s %s\n" "${STEP_NAMES[$i]}" "$fg[yellow]${STEP_RESULTS[$i]}$reset_color" ;;
    esac
  done
  if (( ${#ARTIFACTS} )); then
    print -r -- ""
    print -r -- "$fg_bold[white]Completed artifacts:$reset_color"
    local a; for a in $ARTIFACTS; do print -r -- "  $fg[green]$a$reset_color"; done
  fi
  print -r -- "  Work files: $WORK"
}

fail() {
  # $1 step name, $2 message, $3 diagnostic file or text, $4 repair hint
  record "$1" FAIL
  print -r -- "$fg_bold[red]  ✘ FAILED: $1$reset_color"
  print -r -- "$fg[red]    $2$reset_color"
  if [[ -n $3 ]]; then
    print -r -- "$fg[yellow]    Diagnostic output:$reset_color"
    if [[ -f $3 ]]; then sed 's/^/      /' "$3" | head -40; else print -r -- "      $3"; fi
  fi
  [[ -n $4 ]] && print -r -- "$fg[magenta]    Repair: $4$reset_color"
  summary
  print -r -- "$fg_bold[red]OVERALL: FAIL$reset_color"
  exit 1
}

curl_auth=()
[[ -n $STREAMTV_API_KEY ]] && curl_auth=(-H "X-API-Key: $STREAMTV_API_KEY")

# ---------- STEP 1: preflight ----------
S="1. Preflight (tools + files)"
hdr "$S"
for t in curl python3; do
  command -v $t >/dev/null || fail "$S" "Missing tool: $t" "" "brew install $t"
done
[[ -f $CHANNEL_YAML ]]  || fail "$S" "Channel file not found: $CHANNEL_YAML" "" "Keep the YAML files in the same folder as this script."
[[ -f $SCHEDULE_YAML ]] || fail "$S" "Schedule file not found: $SCHEDULE_YAML" "" "Keep schedules/1225.yml next to this script."
if [[ -z $STREAMTV_HOME ]]; then
  for c in "$HOME/StreamTV-source" "$HOME/streamtv-source" "$HOME/StreamTV" "$HOME/streamtv" "$HOME/Developer/StreamTV-source" "$HOME/Projects/StreamTV-source"; do
    [[ -f $c/streamtv/main.py && -d $c/schedules ]] && { STREAMTV_HOME=$c; break; }
  done
fi
[[ -n $STREAMTV_HOME && -f $STREAMTV_HOME/streamtv/main.py && -d $STREAMTV_HOME/schedules ]] || \
  fail "$S" "Could not find the StreamTV install folder (needs streamtv/main.py and schedules/)." \
       "Checked: ${STREAMTV_HOME:-auto-detect list}" "Re-run with -d /path/to/StreamTV-source"
ok "StreamTV folder: $STREAMTV_HOME"
ok "Server URL: $STREAMTV_URL"
record "$S" PASS

# ---------- STEP 2: validate YAML locally ----------
S="2. Validate YAML (StreamTV schemas)"
hdr "$S"
PY=python3
[[ -x $STREAMTV_HOME/venv/bin/python ]] && PY=$STREAMTV_HOME/venv/bin/python
info "Python: $PY"
( cd "$STREAMTV_HOME" && "$PY" - "$CHANNEL_YAML" "$SCHEDULE_YAML" ) > "$WORK/validate.log" 2>&1 <<'PYEOF'
import sys, yaml
from pathlib import Path
ch, sc = Path(sys.argv[1]), Path(sys.argv[2])
c = yaml.safe_load(ch.read_text()); s = yaml.safe_load(sc.read_text())
streams = c['channels'][0]['streams']
assert c['channels'][0]['number'] == '1225', 'channel number is not 1225'
keys = {k['key'] for k in s['content']}
used = {i.get('all') for q in s['sequence'] for i in q['items']} - {None}
missing = used - keys
assert not missing, f'schedule references unknown content keys: {missing}'
colls = {x['collection'] for x in streams}
bad = [k['collection'] for k in s['content'] if k['collection'] not in colls]
assert not bad, f'schedule collections not in channel file: {bad[:5]}'
print(f'basic checks ok: {len(streams)} streams, {len(keys)} schedule content keys')
try:
    sys.path.insert(0, '.')
    from streamtv.validation import YAMLValidator
    v = YAMLValidator()
    r1 = v.validate_channel_file(ch); r2 = v.validate_schedule_file(sc)
    print('StreamTV channel schema:', r1['valid'], r1.get('errors'))
    print('StreamTV schedule schema:', r2['valid'], r2.get('errors'))
    assert r1['valid'] and r2['valid'], 'schema validation failed'
except ImportError as e:
    print('StreamTV validator not importable here (', e, ') - basic checks only')
PYEOF
(( $? == 0 )) || fail "$S" "YAML validation failed." "$WORK/validate.log" \
  "Fix the entry named in the error, or re-download the original files."
sed 's/^/    /' "$WORK/validate.log"
record "$S" PASS

# ---------- STEP 3: source URL check ----------
S="3. Source URLs online (archive.org/YouTube)"
hdr "$S"
if (( SKIP_URL_CHECK )); then
  warn "Skipped by --skip-url-check"
  record "$S" SKIPPED
else
  "$PY" - "$CHANNEL_YAML" > "$WORK/urls.txt" <<'PYEOF'
import sys, yaml
for s in yaml.safe_load(open(sys.argv[1]))['channels'][0]['streams']:
    print(s['id'], s['url'])
PYEOF
  : > "$WORK/dead.txt"; n=0; bad=0
  while read -r sid url; do
    (( n++ ))
    if [[ $url == *youtube.com* ]]; then
      code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 "https://www.youtube.com/oembed?format=json&url=${url}")
    else
      code=$(curl -s -o /dev/null -w '%{http_code}' -I -L --max-time 30 "$url")
    fi
    if [[ $code == 200 || $code == 302 ]]; then
      print -n -- "$fg[green].$reset_color"
    else
      print -n -- "$fg[red]x$reset_color"; (( bad++ )); print -r -- "$code $sid $url" >> "$WORK/dead.txt"
    fi
  done < "$WORK/urls.txt"
  print ""
  (( bad == 0 )) || fail "$S" "$bad of $n source URLs did not answer 200." "$WORK/dead.txt" \
    "Remove the listed ids from channel-1225-vintage-kids-christmas.yaml (and their 'all:' lines in schedules/1225.yml), or re-run with --skip-url-check if it was a temporary outage."
  ok "All $n URLs answered"
  record "$S" PASS
fi

# ---------- STEP 4: server reachable ----------
S="4. StreamTV server reachable"
hdr "$S"
code=$(curl -s -o "$WORK/channels.json" -w '%{http_code}' --max-time 15 $curl_auth "$STREAMTV_URL/api/channels")
[[ -s $WORK/channels.json ]] || print -r -- "No response from server (connection refused or timed out)" > "$WORK/channels.json"
[[ $code == 200 ]] || fail "$S" "GET $STREAMTV_URL/api/channels returned HTTP $code" "$WORK/channels.json" \
  "Start StreamTV (cd $STREAMTV_HOME && ./venv/bin/python -m streamtv.main), check the URL (-u), or pass the API key (-k)."
if grep -q "\"number\":\"$CHANNEL_NO\"" "$WORK/channels.json"; then
  warn "Channel $CHANNEL_NO already exists - the import will update it in place."
fi
ok "Server answered HTTP 200"
record "$S" PASS

# ---------- STEP 5: install schedule ----------
S="5. Install schedule file"
hdr "$S"
DEST="$STREAMTV_HOME/schedules/1225.yml"
if [[ -f $DEST ]]; then
  BK="$DEST.bak.$(date +%Y%m%d-%H%M%S)"
  cp "$DEST" "$BK" || fail "$S" "Could not back up existing $DEST" "" "Check folder permissions: ls -l $STREAMTV_HOME/schedules"
  info "Backed up existing schedule to $BK"; ARTIFACTS+=("$BK")
fi
cp "$SCHEDULE_YAML" "$DEST" 2> "$WORK/cp.log" || fail "$S" "Copy failed" "$WORK/cp.log" "Check permissions: ls -ld $STREAMTV_HOME/schedules"
cmp -s "$SCHEDULE_YAML" "$DEST" || fail "$S" "Installed schedule does not match the source file" "" "Re-run the script."
ok "Schedule installed: $DEST"; ARTIFACTS+=("$DEST")
record "$S" PASS

# ---------- STEP 6: import channel ----------
S="6. Import channel 1225 (validate=true)"
hdr "$S"
code=$(curl -s -o "$WORK/import.json" -w '%{http_code}' --max-time 300 $curl_auth \
  -X POST "$STREAMTV_URL/api/import/channels/yaml?validate=true" \
  -F "yaml_file=@$CHANNEL_YAML")
[[ $code == 200 ]] || fail "$S" "Import returned HTTP $code" "$WORK/import.json" \
  "Read the error above. Schema errors name the bad entry; 401/403 means pass -k API_KEY."
grep -q "\"number\":\"$CHANNEL_NO\"" "$WORK/import.json" || fail "$S" "Import response does not include channel $CHANNEL_NO" "$WORK/import.json" "Check StreamTV logs."
ok "Channel imported"; ARTIFACTS+=("StreamTV channel $CHANNEL_NO - Vintage Kids Christmas")
record "$S" PASS

# ---------- STEP 7: M3U ----------
S="7. Channel listed in M3U"
hdr "$S"
curl -s --max-time 30 $curl_auth "$STREAMTV_URL/iptv/channels.m3u" > "$WORK/channels.m3u"
grep -q "tvg-id=\"$CHANNEL_NO\"" "$WORK/channels.m3u" || fail "$S" "Channel $CHANNEL_NO not in /iptv/channels.m3u" "$WORK/channels.m3u" \
  "Make sure the channel is enabled: curl $STREAMTV_URL/api/channels | grep 1225"
ok "Stream URL: $STREAMTV_URL/iptv/channel/$CHANNEL_NO.m3u8"
record "$S" PASS

# ---------- STEP 8: guide ----------
S="8. Guide (XMLTV) has programmes"
hdr "$S"
curl -s --max-time 120 $curl_auth "$STREAMTV_URL/iptv/xmltv.xml" > "$WORK/xmltv.xml"
cnt=$(grep -c "channel=\"$CHANNEL_NO\"" "$WORK/xmltv.xml")
(( cnt > 1 )) || fail "$S" "No guide entries for channel $CHANNEL_NO" \
  "$(grep -n "$CHANNEL_NO" "$WORK/xmltv.xml" | head -5)" \
  "Confirm $STREAMTV_HOME/schedules/1225.yml exists, then check the StreamTV log for 'schedule' errors."
first=$(grep -A3 "<programme[^>]*channel=\"$CHANNEL_NO\"" "$WORK/xmltv.xml" | grep -o '<title[^>]*>[^<]*' | sed 's/<title[^>]*>//' | head -1)
ok "$cnt guide entries (first program: ${first:-?})"
record "$S" PASS

summary
print -r -- ""
print -r -- "$fg_bold[green]OVERALL: PASS$reset_color  — In Plex, refresh the guide for the StreamTV tuner to see channel $CHANNEL_NO."
