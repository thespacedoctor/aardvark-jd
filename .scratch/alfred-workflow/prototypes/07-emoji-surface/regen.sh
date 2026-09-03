#!/bin/bash
# PROTOTYPE - wayfinder ticket 07. THROWAWAY.
# Zip workflow/ into AardvarkEmojiProbe.alfredworkflow (an .alfredworkflow IS
# a zip). Re-run after editing anything under workflow/.
set -euo pipefail
cd "$(dirname "$0")"

[ -f workflow/scripts/env.sh ] || { echo "run ./setup.sh first"; exit 1; }

OUT="AardvarkEmojiProbe.alfredworkflow"
rm -f "$OUT"
( cd workflow && zip -r -X "../$OUT" . -x '.*' -x '*/__pycache__/*' >/dev/null )
echo "built $OUT"
echo "import it into Alfred (double-click), or double-click to replace an earlier import"
