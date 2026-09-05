#!/bin/zsh --no-rcs
#
# The `av` Script Filter's entry point.
#
# Three jobs, in order: resolve the `aardvark` console script, fetch the
# whole index as JSON, and render it as Alfred items. Every failure is
# emitted as a single Alfred item carrying the diagnosis, because a Script
# Filter has no error channel - see `docs/alfred-workflow-spec.md`.

set -u

scriptDir="${0:A:h}"
source "${scriptDir}/_resolve.sh"

# EMIT ONE ALFRED ITEM AND STOP. `arg` CARRIES THE TEXT ENTER SHOULD COPY TO
# THE CLIPBOARD; AN INVALID ROW IS INERT. JSON STRING ESCAPING IS DONE BY
# HAND BECAUSE NOTHING ELSE IS REACHABLE YET - A RECORDED PATH CAN CARRY A
# BACKSLASH OR A DOUBLE QUOTE, AND BOTH WOULD BREAK THE PAYLOAD ALFRED
# PARSES.
emit_row() {
    local rowTitle="$1"
    local rowSubtitle="$2"
    local rowArg="$3"
    local rowValid="$4"
    rowTitle="${rowTitle//\\/\\\\}"
    rowTitle="${rowTitle//\"/\\\"}"
    rowSubtitle="${rowSubtitle//\\/\\\\}"
    rowSubtitle="${rowSubtitle//\"/\\\"}"
    rowArg="${rowArg//\\/\\\\}"
    rowArg="${rowArg//\"/\\\"}"
    print -r -- "{\"items\":[{\"title\":\"${rowTitle}\",\"subtitle\":\"${rowSubtitle}\",\"arg\":\"${rowArg}\",\"valid\":${rowValid},\"variables\":{\"action\":\"copy\"}}]}"
    exit 0
}

if ! aardvark_resolve; then
    case "$aardvarkResolution" in
        missing)
            emit_row "aardvark has not been set up on this Mac" \
                "Press ↩ to copy \`${AARDVARK_INSTALL_COMMAND}\`, then run it in a terminal" \
                "$AARDVARK_INSTALL_COMMAND" "true"
            ;;
        dead)
            # THE DEAD PATH IS SHOWN, NOT SWALLOWED: A RECORDED-BUT-WRONG
            # PATH IS THE SILENT FAILURE THIS WHOLE DESIGN GUARDS AGAINST.
            emit_row "aardvark is not at ${aardvarkBinary}" \
                "Recorded by the ${aardvarkSource}. Press ↩ to copy \`${AARDVARK_INSTALL_COMMAND}\`, then run it in a terminal" \
                "$AARDVARK_INSTALL_COMMAND" "true"
            ;;
        *)
            emit_row "aardvark's interpreter could not be found" \
                "No usable shebang in ${aardvarkBinary}. Press ↩ to copy \`${AARDVARK_INSTALL_COMMAND}\`" \
                "$AARDVARK_INSTALL_COMMAND" "true"
            ;;
    esac
fi

payload="$("$aardvarkBinary" fd --json 2>/dev/null)"

if [ -z "$payload" ]; then
    emit_row "aardvark returned nothing" \
        "\`${aardvarkBinary} fd --json\` produced no output" "" "false"
fi

print -r -- "$payload" | "$aardvarkInterpreter" "${scriptDir}/index.py"
