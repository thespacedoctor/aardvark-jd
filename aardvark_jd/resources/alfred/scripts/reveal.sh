#!/bin/zsh --no-rcs
#
# The reveal: show an entity's folder in Finder.
#
# `open -R` selects the folder in its parent rather than opening it, which
# is what "reveal" means everywhere else on macOS. Alfred passes the folder
# path as `argv[1]`.

set -u

targetPath="${1:-}"

if [ -z "$targetPath" ]; then
    print -r -- "nothing to reveal - no path was passed"
    exit 1
fi

if ! open -R "$targetPath"; then
    print -r -- "could not reveal ${targetPath}"
    exit 1
fi
