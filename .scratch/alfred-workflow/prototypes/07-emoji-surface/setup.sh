#!/bin/bash
# PROTOTYPE - wayfinder ticket 07. THROWAWAY.
# Detect the aardvark interpreter, write workflow/scripts/env.sh, make a cache
# dir. Run once before ./regen.sh.
set -euo pipefail
cd "$(dirname "$0")"

PY="$(command -v python3.14 || command -v python3 || command -v python)"
if [ -n "${CONDA_PREFIX:-}" ] && [ -x "$CONDA_PREFIX/bin/python" ]; then
	PY="$CONDA_PREFIX/bin/python"
fi
"$PY" -c 'import aardvark_jd, anthropic' 2>/dev/null || {
	echo "!! $PY cannot import aardvark_jd + anthropic."
	echo "   activate the aardvark env first, or edit PY in this script."
	exit 1
}

CACHE="${TMPDIR:-/tmp}"
CACHE="${CACHE%/}/aardvark-tk07"
mkdir -p "$CACHE"

sed -e "s|__AARDVARK_PY__|$PY|" -e "s|__PROTO_CACHE__|$CACHE|" \
	workflow/scripts/env.sh.template > workflow/scripts/env.sh

echo "interpreter : $PY"
echo "cache dir   : $CACHE   (rm -rf this to force fresh Claude calls)"
if [ -f "$HOME/.aardvark-proto-key" ]; then
	echo "api key     : ~/.aardvark-proto-key found"
else
	echo "api key     : MISSING - put your Anthropic key in ~/.aardvark-proto-key"
	echo "              printf %s \"sk-ant-...\" > ~/.aardvark-proto-key && chmod 600 ~/.aardvark-proto-key"
fi
echo "next        : ./regen.sh, then import AardvarkEmojiProbe.alfredworkflow"
