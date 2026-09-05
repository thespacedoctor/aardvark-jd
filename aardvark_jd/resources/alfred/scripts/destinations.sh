#!/bin/zsh --no-rcs
#
# The destinations sub-list: Craft, Todoist, Google Drive and Dropbox as
# four rows, reached with ⌃ on an entity row.
#
# A sub-list rather than four modifier chords, because it can *show* which
# mirrors are unsynced: a row whose URL is missing reads "not synced to
# Craft" and offers to run that mirror's sync. An unbound chord cannot.
#
# Alfred exports the originating item's variables into this script's
# environment, so `urls` arrives already populated.

set -u

scriptDir="${0:A:h}"
source "${scriptDir}/_resolve.sh"

if ! aardvark_resolve; then
    print -r -- "{\"items\":[{\"title\":\"aardvark could not be found\",\"subtitle\":\"Run \`${AARDVARK_INSTALL_COMMAND}\` in a terminal\",\"valid\":false}]}"
    exit 0
fi

"$aardvarkInterpreter" "${scriptDir}/destinations.py"
