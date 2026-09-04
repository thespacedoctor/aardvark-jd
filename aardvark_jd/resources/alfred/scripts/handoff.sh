#!/bin/zsh --no-rcs
#
# The terminal handoff: open a new terminal tab at an entity's folder.
#
# `open -a` is the whole handoff, and there is deliberately no AppleScript
# here. Against a running iTerm it opens a new tab in the existing window,
# which is the wanted behaviour, and because it never builds a shell string
# it has none of the quoting holes the AppleScript alternative has -
# including the newline-in-a-folder-name case, which submits the line early.
#
# Alfred passes the folder path as `argv[1]` (`scriptargtype: 1`).

set -u

targetPath="${1:-}"

if [ -z "$targetPath" ]; then
    print -r -- "nothing to hand off - no path was passed"
    exit 1
fi

# THE CONFIGURATION VARIABLE WINS; OTHERWISE ITERM WHEN INSTALLED, ELSE
# `Terminal.app`. EVERY MAC HAS TERMINAL, SO THE CHAIN ALWAYS TERMINATES.
terminalApp="${AARDVARK_TERMINAL_APP:-}"
if [ -z "$terminalApp" ]; then
    if [ -d "/Applications/iTerm.app" ]; then
        terminalApp="iTerm"
    else
        terminalApp="Terminal"
    fi
fi

if ! open -a "$terminalApp" "$targetPath"; then
    print -r -- "Terminal app '${terminalApp}' was not found - set AARDVARK_TERMINAL_APP in the workflow's configuration"
    exit 1
fi
