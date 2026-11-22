#!/usr/bin/env zsh
# install_vintage_holiday_channels.zsh
# Adds the vintage holiday channels to StreamTV:
#   101 New Year's · 214 Valentine's Day · 401 Easter · 704 Fourth of July · 1031 Halloween · 1128 Thanksgiving
# Steps: 1. preflight, 2. check the YAML files, 3. check every source URL is still online,
#        4. check the StreamTV server, 5. install the schedules, 6. import the channels,
#        7. confirm each channel is in the M3U, 8. confirm each channel has guide (XMLTV) entries.
#
# Usage:
#   ./install_vintage_holiday_channels.zsh [-c 1031,1128] [-d /path/to/StreamTV-source] [-u http://192.168.1.120:8410] [-k API_KEY] [--skip-url-check]
#   -c  only these channel numbers (default: every channel-*.yaml in ./channels)
# Env equivalents: STREAMTV_HOME, STREAMTV_URL, STREAMTV_API_KEY
#
# Files expected next to this script:
#   channels/channel-<number>-<name>.yaml
#   schedules/<number>.yml

emulate -L zsh
setopt pipefail no_nomatch
autoload -U colors && colors

# ---------- settings ----------
SCRIPT_DIR=${0:A:h}
STREAMTV_URL=${STREAMTV_URL:-http://192.168.1.120:8410}
STREAMTV_HOME=${STREAMTV_HOME:-}
STREAMTV_API_KEY=${STREAMTV_API_KEY:-}
SKIP_URL_CHECK=0
ONLY=""
WORK=$(mktemp -d /tmp/stv-holidays.XXXXXX)

while (( $# )); do
  case $1 in
    -c) ONLY=$2; shift 2 ;;
    -d) STREAMTV_HOME=$2; shift 2 ;;
    -u) STREAMTV_URL=$2; shift 2 ;;
    -k) STREAMTV_API_KEY=$2; shift 2 ;;
    --skip-url-check) SKIP_URL_CHECK=1; shift ;;
    -h|--help) sed -n '2,18p' "$0"; exit 0 ;;
    *) print -r -- "$fg_bold[red]Unknown option: $1$reset_color"; exit 2 ;;
  esac
done

typeset -a STEP_NAMES STEP_RESULTS ARTIFACTS
typeset -A CH_YAML CH_NAME

hdr()  { print -r -- ""; print -r -- "$fg_bold[cyan]==> $1$reset_color"; }
ok()   { print -r -- "$fg[green]  ✔ $1$reset_color"; }
info() { print -r -- "$fg[blue]  • $1$reset_color"; }
warn() { print -r -- "$fg[yellow]  ! $1$reset_color"; }
record() { STEP_NAMES+=("$1"); STEP_RESULTS+=("$2"); }

summary() {
  print -r -- ""
  print -r -- "$fg_bold[white]──────────────── SUMMARY ────────────────$reset_color"
  printf "%-50s %s\n" "STEP" "RESULT"
  local i
  for (( i=1; i<=${#STEP_NAMES}; i++ )); do
    case ${STEP_RESULTS[$i]} in
      PASS) printf "%-50s %s\n" "${STEP_NAMES[$i]}" "$fg_bold[green]PASS$reset_color" ;;
      FAIL) printf "%-50s %s\n" "${STEP_NAMES[$i]}" "$fg_bold[red]FAIL$reset_color" ;;
      *)    printf "%-50s %s\n" "${STEP_NAMES[$i]}" "$fg[yellow]${STEP_RESULTS[$i]}$reset_color" ;;
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
S="1. Preflight (tools, files, StreamTV folder)"
hdr "$S"
for t in curl python3; do
  command -v $t >/dev/null || fail "$S" "Missing tool: $t" "" "brew install $t"
done
for f in $SCRIPT_DIR/channels/channel-*.yaml(N); do
  n=${${f:t}#channel-}; n=${n%%-*}
  if [[ -n $ONLY && ",$ONLY," != *",$n,"* ]]; then continue; fi
  CH_YAML[$n]=$f
done
(( ${#CH_YAML} )) || fail "$S" "No channel files found${ONLY:+ for -c $ONLY}." "$(ls -1 $SCRIPT_DIR/channels 2>&1)" \
  "Keep the channels/ and schedules/ folders next to this script; check the numbers given to -c."
NUMS=(${(on)${(k)CH_YAML}})
for n in $NUMS; do
  [[ -f $SCRIPT_DIR/schedules/$n.yml ]] || fail "$S" "Schedule file missing: schedules/$n.yml" "" "Re-extract the zip; every channel needs its schedule."
done
if [[ -z $STREAMTV_HOME ]]; then
  for c in "$HOME/StreamTV-source" "$HOME/streamtv-source" "$HOME/StreamTV" "$HOME/streamtv" "$HOME/Developer/StreamTV-source" "$HOME/Projects/StreamTV-source"; do
    [[ -f $c/streamtv/main.py && -d $c/schedules ]] && { STREAMTV_HOME=$c; break; }
  done
fi
[[ -n $STREAMTV_HOME && -f $STREAMTV_HOME/streamtv/main.py && -d $STREAMTV_HOME/schedules ]] || \
  fail "$S" "Could not find the StreamTV install folder (needs streamtv/main.py and schedules/)." \
       "Checked: ${STREAMTV_HOME:-auto-detect list}" "Re-run with -d /path/to/StreamTV-source"
ok "Channels: ${(j:, :)NUMS}"
ok "StreamTV folder: $STREAMTV_HOME"
ok "Server URL: $STREAMTV_URL"
record "$S" PASS

# ---------- STEP 2: validate YAML locally ----------
S="2. Validate YAML (StreamTV schemas)"
hdr "$S"
PY=python3
[[ -x $STREAMTV_HOME/venv/bin/python ]] && PY=$STREAMTV_HOME/venv/bin/python
info "Python: $PY"
for n in $NUMS; do
  ( cd "$STREAMTV_HOME" && "$PY" - "$n" "${CH_YAML[$n]}" "$SCRIPT_DIR/schedules/$n.yml" ) > "$WORK/validate-$n.log" 2>&1 <<'PYEOF'
import sys, yaml
from pathlib import Path
num, ch, sc = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
c = yaml.safe_load(ch.read_text()); s = yaml.safe_load(sc.read_text())
chan = c['channels'][0]; streams = chan['streams']
assert chan['number'] == num, f'channel number is {chan["number"]}, expected {num}'
keys = {k['key'] for k in s['content']}
used = {i.get('all') for q in s['sequence'] for i in q['items']} - {None}
assert not (used - keys), f'schedule references unknown content keys: {used - keys}'
colls = {x['collection'] for x in streams}
bad = [k['collection'] for k in s['content'] if k['collection'] not in colls]
assert not bad, f'schedule collections not in channel file: {bad[:5]}'
print(f'{num} {chan["name"]}: {len(streams)} streams, {len(keys)} schedule keys')
try:
    sys.path.insert(0, '.')
    from streamtv.validation import YAMLValidator
    v = YAMLValidator()
    r1 = v.validate_channel_file(ch); r2 = v.validate_schedule_file(sc)
    print('  channel schema:', r1['valid'], r1.get('errors') or '')
    print('  schedule schema:', r2['valid'], r2.get('errors') or '')
    assert r1['valid'] and r2['valid'], 'schema validation failed'
except ImportError as e:
    print('  StreamTV validator not importable here (', e, ') - basic checks only')
PYEOF
  (( $? == 0 )) || fail "$S" "YAML validation failed for channel $n." "$WORK/validate-$n.log" \
    "Fix the entry named in the error, or re-extract the original files."
  CH_NAME[$n]=$(head -1 "$WORK/validate-$n.log" | sed -E 's/^[0-9]+ ([^:]*):.*/\1/')
  sed 's/^/    /' "$WORK/validate-$n.log"
done
record "$S" PASS

# ---------- STEP 3: source URL check ----------
S="3. Source URLs online (archive.org/YouTube)"
hdr "$S"
if (( SKIP_URL_CHECK )); then
  warn "Skipped by --skip-url-check"
  record "$S" SKIPPED
else
  : > "$WORK/urls.txt"
  for n in $NUMS; do
    "$PY" - "${CH_YAML[$n]}" "$n" >> "$WORK/urls.txt" <<'PYEOF'
import sys, yaml
for s in yaml.safe_load(open(sys.argv[1]))['channels'][0]['streams']:
    print(sys.argv[2], s['id'], s['url'])
PYEOF
  done
  : > "$WORK/dead.txt"; total=0; bad=0; last=""
  while read -r n sid url; do
    [[ $n != $last ]] && { [[ -n $last ]] && print ""; print -n -- "  $fg[blue]$n$reset_color "; last=$n; }
    (( total++ ))
    if [[ $url == *youtube.com* ]]; then
      code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 "https://www.youtube.com/oembed?format=json&url=${url}")
    else
      code=$(curl -s -o /dev/null -w '%{http_code}' -I -L --max-time 30 "$url")
    fi
    if [[ $code == 200 || $code == 302 ]]; then
      print -n -- "$fg[green].$reset_color"
    else
      print -n -- "$fg[red]x$reset_color"; (( bad++ )); print -r -- "$code channel $n  $sid  $url" >> "$WORK/dead.txt"
    fi
  done < "$WORK/urls.txt"
  print ""
  (( bad == 0 )) || fail "$S" "$bad of $total source URLs did not answer 200." "$WORK/dead.txt" \
    "Remove each listed id from its channels/channel-<n>-*.yaml (and its 'all:' line in schedules/<n>.yml), or re-run with --skip-url-check if it was a temporary outage."
  ok "All $total URLs answered"
  record "$S" PASS
fi

# ---------- STEP 4: server reachable ----------
S="4. StreamTV server reachable"
hdr "$S"
code=$(curl -s -o "$WORK/channels.json" -w '%{http_code}' --max-time 15 $curl_auth "$STREAMTV_URL/api/channels")
[[ -s $WORK/channels.json ]] || print -r -- "No response from server (connection refused or timed out)" > "$WORK/channels.json"
[[ $code == 200 ]] || fail "$S" "GET $STREAMTV_URL/api/channels returned HTTP $code" "$WORK/channels.json" \
  "Start StreamTV (cd $STREAMTV_HOME && ./venv/bin/python -m streamtv.main), check the URL (-u), or pass the API key (-k)."
for n in $NUMS; do
  grep -q "\"number\":\"$n\"" "$WORK/channels.json" && warn "Channel $n already exists - the import will update it in place."
done
ok "Server answered HTTP 200"
record "$S" PASS

# ---------- STEP 5: install schedules ----------
S="5. Install schedule files"
hdr "$S"
STAMP=$(date +%Y%m%d-%H%M%S)
for n in $NUMS; do
  DEST="$STREAMTV_HOME/schedules/$n.yml"
  if [[ -f $DEST ]] && ! cmp -s "$SCRIPT_DIR/schedules/$n.yml" "$DEST"; then
    BK="$DEST.bak.$STAMP"
    cp "$DEST" "$BK" || fail "$S" "Could not back up existing $DEST" "" "Check folder permissions: ls -l $STREAMTV_HOME/schedules"
    info "Backed up existing schedule to $BK"; ARTIFACTS+=("$BK")
  fi
  cp "$SCRIPT_DIR/schedules/$n.yml" "$DEST" 2> "$WORK/cp.log" || fail "$S" "Copy failed for $n.yml" "$WORK/cp.log" "Check permissions: ls -ld $STREAMTV_HOME/schedules"
  cmp -s "$SCRIPT_DIR/schedules/$n.yml" "$DEST" || fail "$S" "Installed $n.yml does not match the source file" "" "Re-run the script."
  ok "Schedule installed: $DEST"; ARTIFACTS+=("$DEST")
done
record "$S" PASS

# ---------- STEP 6: import channels ----------
S="6. Import channels (validate=true)"
hdr "$S"
for n in $NUMS; do
  code=$(curl -s -o "$WORK/import-$n.json" -w '%{http_code}' --max-time 300 $curl_auth \
    -X POST "$STREAMTV_URL/api/import/channels/yaml?validate=true" \
    -F "yaml_file=@${CH_YAML[$n]}")
  [[ $code == 200 ]] || fail "$S" "Import of channel $n returned HTTP $code" "$WORK/import-$n.json" \
    "Read the error above. Schema errors name the bad entry; 401/403 means pass -k API_KEY. Channels before $n were already imported."
  grep -q "\"number\":\"$n\"" "$WORK/import-$n.json" || fail "$S" "Import response does not include channel $n" "$WORK/import-$n.json" "Check the StreamTV log."
  ok "Imported $n ${CH_NAME[$n]}"; ARTIFACTS+=("StreamTV channel $n - ${CH_NAME[$n]}")
done
record "$S" PASS

# ---------- STEP 7: M3U ----------
S="7. Channels listed in M3U"
hdr "$S"
curl -s --max-time 30 $curl_auth "$STREAMTV_URL/iptv/channels.m3u" > "$WORK/channels.m3u"
for n in $NUMS; do
  grep -q "tvg-id=\"$n\"" "$WORK/channels.m3u" || fail "$S" "Channel $n not in /iptv/channels.m3u" "$WORK/channels.m3u" \
    "Make sure the channel is enabled: curl -s $STREAMTV_URL/api/channels | grep '\"number\":\"$n\"'"
  ok "$n stream URL: $STREAMTV_URL/iptv/channel/$n.m3u8"
done
record "$S" PASS

# ---------- STEP 8: guide ----------
S="8. Guide (XMLTV) has programmes"
hdr "$S"
curl -s --max-time 180 $curl_auth "$STREAMTV_URL/iptv/xmltv.xml" > "$WORK/xmltv.xml"
[[ -s $WORK/xmltv.xml ]] || fail "$S" "Empty guide from /iptv/xmltv.xml" "" "Check the StreamTV log; the guide can take a minute to build after import."
for n in $NUMS; do
  cnt=$(grep -c "<programme[^>]*channel=\"$n\"" "$WORK/xmltv.xml")
  (( cnt > 1 )) || fail "$S" "No guide entries for channel $n" \
    "$(grep -n "channel=\"$n\"" "$WORK/xmltv.xml" | head -5)" \
    "Confirm $STREAMTV_HOME/schedules/$n.yml exists, then check the StreamTV log for 'schedule' errors."
  first=$(grep -A3 "<programme[^>]*channel=\"$n\"" "$WORK/xmltv.xml" | grep -o '<title[^>]*>[^<]*' | sed 's/<title[^>]*>//' | head -1)
  ok "$n: $cnt guide entries (first: ${first:-?})"
done
record "$S" PASS

summary
print -r -- ""
print -r -- "$fg_bold[green]OVERALL: PASS$reset_color  — In Plex, refresh the guide for the StreamTV tuner to see channels ${(j:, :)NUMS}."
