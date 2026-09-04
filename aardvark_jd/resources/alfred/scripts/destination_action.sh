#!/bin/zsh --no-rcs
#
# What Return does on a row of the destinations sub-list.
#
# A synced destination opens its URL. An unsynced one runs that mirror's
# sync instead of failing silently, which is the whole reason the four
# mirrors are a sub-list rather than four modifier chords.
#
# Alfred passes the row's `arg` as `argv[1]`: either a URL, or
# `sync:<command>` for a mirror that has nothing to open yet, where
# `<command>` is the aardvark command that mints that mirror's links.

set -u

scriptDir="${0:A:h}"
source "${scriptDir}/_resolve.sh"

rowArg="${1:-}"

if [ -z "$rowArg" ]; then
    print -r -- "nothing to open"
    exit 1
fi

case "$rowArg" in
    sync:*)
        syncCommand="${rowArg#sync:}"
        if ! aardvark_resolve; then
            print -r -- "aardvark could not be found - run \`${AARDVARK_INSTALL_COMMAND}\`"
            exit 1
        fi
        # THE SYNC STAYS BACKGROUNDED, AS IT IS ON THE COMMAND LINE: ALFRED
        # FIRES IT, SAYS SO, AND LETS THE EXISTING DRIFT MARKERS CATCH A
        # FAILURE LATER.
        "$aardvarkBinary" "$syncCommand" >/dev/null 2>&1 &
        print -r -- "running ${syncCommand}…"
        ;;
    *)
        open "$rowArg"
        ;;
esac
