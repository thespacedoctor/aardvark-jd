#!/bin/zsh --no-rcs
#
# What Return does on a row from the `av` Script Filter.
#
# One entry point rather than one object per outcome, because a Script
# Filter's unmodified connection has a single destination and the rows are
# not all the same kind of thing: an entity row opens its mirrors, an error
# row copies the install command.
#
# Alfred passes the row's `arg` as `argv[1]` and its item variables as
# environment variables.

set -u

scriptDir="${0:A:h}"
source "${scriptDir}/_resolve.sh"

rowArg="${1:-}"

# AN ERROR ROW'S ENTER COPIES THE COMMAND RATHER THAN PRE-TYPING IT INTO A
# TERMINAL, WHICH WOULD RESURRECT THE APPLESCRIPT THE HANDOFF DECISION
# REMOVED.
if [ "${action:-}" = "copy" ]; then
    printf '%s' "$rowArg" | pbcopy
    print -r -- "Copied: ${rowArg}"
    exit 0
fi

if ! aardvark_resolve; then
    print -r -- "aardvark could not be found - run \`${AARDVARK_INSTALL_COMMAND}\`"
    exit 1
fi

"$aardvarkInterpreter" "${scriptDir}/action.py"
