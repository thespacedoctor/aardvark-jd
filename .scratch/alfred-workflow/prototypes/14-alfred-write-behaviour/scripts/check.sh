#!/bin/bash
# PROTOTYPE - TICKET 14. RUN AFTER EACH GUI STEP:  ./scripts/check.sh "step 2a"
# APPENDS A SNAPSHOT TO report.txt SO THE GUI STEPS NEED NO TYPING BACK.
set -uo pipefail
D="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PREFS="/Users/Dave/Dropbox/Apps/alfred/Alfred.alfredpreferences"
LABEL="${1:-unlabelled}"
REPORT="$D/report.txt"

snapshot() {
    local dir="$1" name="$2"
    printf '  %-14s info.plist=%s  ' "$name" "$(shasum -a 256 "$dir/info.plist" 2>/dev/null | cut -c1-16)"
    if [[ -f "$dir/prefs.plist" ]]; then
        printf 'prefs.plist=%s\n' "$(plutil -p "$dir/prefs.plist" | tr -d '\n ' )"
    else
        printf 'prefs.plist=<none>\n'
    fi
    printf '  %-14s default=%s\n' "" "$(plutil -extract userconfigurationconfig json -o - "$dir/info.plist" 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["config"]["default"])' 2>/dev/null)"
    printf '  %-14s objects order=%s\n' "" "$(python3 -c 'import plistlib,sys; d=plistlib.load(open(sys.argv[1],"rb")); print([o["uid"][:8] for o in d["objects"]])' "$dir/info.plist" 2>/dev/null)"
}

{
    printf '\n=== %s   (%s)\n' "$LABEL" "$(date +%H:%M:%S)"
    printf '  workflows in prefs folder: %s\n' "$(ls "$PREFS/workflows" | wc -l | tr -d ' ')"
    printf '  aardvark-test is: %s\n' "$([[ -L "$PREFS/workflows/aardvark-test" ]] && echo symlink || { [[ -d "$PREFS/workflows/aardvark-test" ]] && echo "REAL DIRECTORY" || echo missing; })"
    snapshot "$D/aardvark-test" "symlinked"
    imported="$(grep -rl 'wayfinder-ticket-14-import' "$PREFS/workflows"/*/info.plist 2>/dev/null | head -1)"
    if [[ -n "$imported" ]]; then
        snapshot "$(dirname "$imported")" "imported"
        printf '  %-14s at %s\n' "" "$(dirname "$imported")"
    else
        printf '  %-14s not imported yet\n' "imported"
    fi
} | tee -a "$REPORT"
