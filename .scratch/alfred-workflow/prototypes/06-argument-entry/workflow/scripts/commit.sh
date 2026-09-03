#!/bin/bash
# PROTOTYPE - wayfinder ticket 06. THROWAWAY.
# Final step: really run `aardvark add_id` against the throwaway system, reveal
# the new folder in Finder, and print a line for the notification.
set -euo pipefail
cd "$(dirname "$0")"
source ./env.sh

CODE="${CATEGORY_CODE:?no category chosen}"
TITLE="${TITLE:?no title}"
DESC="${DESCRIPTION:-}"

if OUT=$("$AARDVARK_BIN" add_id "$CODE" "$TITLE" "$DESC" -w -s "$AARDVARK_SETTINGS" 2>&1); then
	FIRST=$(printf '%s\n' "$OUT" | head -1)
	NEW_CODE=${FIRST%%  *}
	NEW_PATH=${FIRST#*  }
	[ -d "$NEW_PATH" ] && open -R "$NEW_PATH"
	printf 'Created %s  %s' "$NEW_CODE" "$TITLE"
else
	printf 'add_id failed: %s' "$OUT"
fi
