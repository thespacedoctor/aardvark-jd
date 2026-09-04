#!/bin/zsh --no-rcs
#
# Resolve the `aardvark` console script and the interpreter it runs under.
#
# Sourced by every other script in this workflow, never run on its own. It
# sets two variables and returns a status; how a failure is reported is the
# caller's business, because a Script Filter has to answer with an item and
# an action has to answer with a notification.
#
#   aardvarkBinary       the `aardvark` console script
#   aardvarkInterpreter  the interpreter its shebang names
#   aardvarkResolution   `ok`, `missing`, `dead` or `nointerpreter`
#   aardvarkSource       `config` or `pointer`, for the diagnosis
#
# This is a replica of `aardvark_jd.alfred.binary`, which is the definitive,
# unit-tested statement of the three-step order. It has to be a replica
# rather than a call: resolving the binary is what lets the workflow run
# Python at all, so it cannot import the module that says where Python is.
# Keep the two in step.

AARDVARK_POINTER_FILE="${HOME}/.config/aardvark/alfred-binary-path"
AARDVARK_INSTALL_COMMAND="aardvark install_alfred"

aardvark_resolve() {
    aardvarkBinary=""
    aardvarkInterpreter=""
    aardvarkResolution="missing"

    # STEP 1: THE WORKFLOW CONFIGURATION VARIABLE, A MANUAL OVERRIDE. AN
    # EMPTY STRING IS THE NORMAL CASE, NOT AN EDGE CASE - ALFRED'S
    # CONFIGURATION VARIABLES DEFAULT TO EMPTY.
    aardvarkSource="config"
    aardvarkBinary="${AARDVARK_BINARY:-}"

    # STEP 2: THE PER-MACHINE BINARY POINTER.
    if [ -z "${aardvarkBinary// /}" ]; then
        aardvarkSource="pointer"
        if [ -f "$AARDVARK_POINTER_FILE" ]; then
            aardvarkBinary="$(head -n 1 "$AARDVARK_POINTER_FILE")"
        else
            aardvarkBinary=""
        fi
    fi

    # STEP 3: HARD FAILURE. THERE IS DELIBERATELY NO `PATH` PROBE AND NO
    # PLAUSIBLE-DEFAULT FALLBACK: ALFRED'S `PATH` CARRIES NO CONDA, VENV,
    # PIPX OR UV BINARY, AND THE RARE SUCCESS IS THE DANGEROUS ONE -
    # SILENTLY RUNNING A DIFFERENT AARDVARK.
    if [ -z "${aardvarkBinary// /}" ]; then
        aardvarkResolution="missing"
        return 1
    fi

    if [ ! -x "$aardvarkBinary" ]; then
        aardvarkResolution="dead"
        return 1
    fi

    # THE CONSOLE SCRIPT'S SHEBANG NAMES THE INTERPRETER THE PACKAGE IS
    # INSTALLED INTO, WHICH IS THE ONE INTERPRETER THAT CAN IMPORT
    # `aardvark_jd`. DERIVING IT FROM THE SHEBANG NEEDS NO ENVIRONMENT
    # ACTIVATION AND NO SECOND POINTER FILE.
    aardvarkInterpreter="$(sed -n '1s/^#!//p' "$aardvarkBinary")"

    if [ -z "$aardvarkInterpreter" ] || [ ! -x "$aardvarkInterpreter" ]; then
        aardvarkResolution="nointerpreter"
        return 1
    fi

    aardvarkResolution="ok"
    return 0
}
